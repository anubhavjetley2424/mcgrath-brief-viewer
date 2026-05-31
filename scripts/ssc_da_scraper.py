"""
Sutherland Shire Council DA scraper — eTrack portal.

Scrapes Development Applications via the SSC eTrack search:
  https://propertydevelopment.ssc.nsw.gov.au/T1PRProd/WebApps/eProperty/P1/eTrack/

Strategy: plain HTTP with ASP.NET WebForms ViewState handling. No browser needed.
Iterates one calendar month at a time to keep result sets small; handles pagination
within a month via the Next button postback. Upserts to Supabase public.da_applications.

Usage:
    python ssc_da_scraper.py 2026-04-26 2026-05-26      # one date range, one session
    python ssc_da_scraper.py 2025-05 2026-05            # month range (inclusive)
"""

import calendar
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from http.cookiejar import CookieJar

BASE = (
    "https://propertydevelopment.ssc.nsw.gov.au/T1PRProd/WebApps/eProperty/P1/"
    "eTrack/eTrackApplicationSearch.aspx"
)
QS = "?Group=DA&ResultsFunction=SSC.P1.ETR.RESULT.DA&r=SSC.P1.WEBGUEST&f=SSC.P1.ETR.SEARCH.DA"
START_URL = BASE + QS

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)
UPSERT_URL = f"{SUPABASE_URL}/rest/v1/da_applications?on_conflict=da_id"

HTTP_TIMEOUT = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppraisalBriefBot/0.1",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
}

DELAY_PAGE_SEC = 1.0
DELAY_MONTH_SEC = 2.0


# ----------------------------------------------------------------------------
# HTTP helpers
# ----------------------------------------------------------------------------

def fetch(opener, url, data=None):
    headers = dict(HEADERS)
    if data is not None:
        data = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data else "GET"
    )
    with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.url


def extract_state(page_html):
    state = {}
    for name in ("__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"):
        m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', page_html)
        state[name] = m.group(1) if m else ""
    return state


PAGER_LINK_RE = re.compile(
    r"<a[^>]*href=\"javascript:__doPostBack\('([^']+grdWebGridTabularView[^']*)','Page\$(\d+)'\)\"[^>]*>(\d+)</a>"
)


def find_next_page(page_html, current_page):
    """Return (grid_target, next_page_num) for the next numbered page link,
    or None if there is no higher-numbered page link visible."""
    next_targets = []
    for m in PAGER_LINK_RE.finditer(page_html):
        target = m.group(1)
        page_num = int(m.group(2))
        if page_num > current_page:
            next_targets.append((target, page_num))
    if not next_targets:
        return None
    # Pick the lowest page number greater than current
    next_targets.sort(key=lambda x: x[1])
    return next_targets[0]


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------

ROW_RE = re.compile(
    r'<tr class="(?:normalRow|alternateRow)">(.*?)</tr>', re.DOTALL
)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
POSTBACK_RE = re.compile(r"__doPostBack\(&#39;([^&]+)&#39;,\s*&#39;([^&]*)&#39;\)|__doPostBack\('([^']+)','([^']*)'\)")
ADDR_RE = re.compile(
    r"^(?P<street>.+?)\s+(?P<suburb>[A-Z][A-Z\s]+?)\s+NSW\s+(?P<postcode>\d{4})\s*$"
)


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", html.unescape(s)).strip()


def parse_da_rows(page_html: str, source_search: str):
    rows = []
    for m in ROW_RE.finditer(page_html):
        cells_html = CELL_RE.findall(m.group(1))
        if len(cells_html) < 8:
            continue
        cells = [strip_tags(c) for c in cells_html]
        da_id = cells[0]
        # Council issues several prefixes: DA, MA (modification), CC (construction cert),
        # CDC (complying development), S96 etc. Accept any 2-4 letter prefix + year + seq.
        if not re.match(r"^[A-Z]{2,4}\d{2}/\d{3,5}$", da_id):
            continue

        # Extract __doPostBack target from first cell (the DA ID link)
        pb = POSTBACK_RE.search(cells_html[0])
        postback = (pb.group(1) or pb.group(3)) if pb else None

        # Parse lodged_date (D/M/YYYY or DD/MM/YYYY → YYYY-MM-DD)
        lodged = None
        m_d = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", cells[1])
        if m_d:
            lodged = f"{m_d.group(3)}-{int(m_d.group(2)):02d}-{int(m_d.group(1)):02d}"

        # Parse address
        addr_full = cells[5]
        addr_m = ADDR_RE.match(addr_full)
        suburb = addr_m.group("suburb").strip() if addr_m else None
        postcode = addr_m.group("postcode") if addr_m else None

        rows.append({
            "da_id": da_id,
            "lodged_date": lodged,
            "description": cells[2] or None,
            "app_category": cells[3] or None,
            "app_subcategory": cells[4] or None,
            "full_address": addr_full or None,
            "suburb": suburb,
            "postcode": postcode,
            "applicant": cells[6] or None,
            "status": cells[7] or None,
            "detail_postback": postback,
            "source_search": source_search,
        })
    return rows


# ----------------------------------------------------------------------------
# Search session
# ----------------------------------------------------------------------------

def search_das(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    suburb: str = "",
    street: str = "",
    source_search: str = "",
):
    """Run one search, follow pagination, return all rows.

    Per-deal pattern: pass suburb + street + a multi-year date range to get
    the ~15 most relevant DAs near a subject property. Returns at most ~15
    rows due to portal-side cap (no pagination available)."""
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # GET to obtain session URL + initial ViewState
    page, current_url = fetch(opener, START_URL)
    state = extract_state(page)

    df = date_from.strftime("%d/%m/%Y") if date_from else ""
    dt = date_to.strftime("%d/%m/%Y") if date_to else ""

    payload = {
        "__VIEWSTATE": state["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": state["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": state["__EVENTVALIDATION"],
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "ctl00$Content$txtApplicationID$txtText": "",
        "ctl00$Content$txtDateFrom$txtText": df,
        "ctl00$Content$txtDateTo$txtText": dt,
        "ctl00$Content$txtSuburb$txtText": suburb.upper(),
        "ctl00$Content$txtDescription$txtText": "",
        "ctl00$Content$txtStreetNoFrom$txtText": "",
        "ctl00$Content$txtStreetNoTo$txtText": "",
        "ctl00$Content$txtStreet$txtText": street,
        "ctl00$Content$txtStreetType$txtText": "",
        "ctl00$Content$ddlApplicationType$elbList": "",
        "ctl00$Content$btnSearch": "Search",
    }
    page, current_url = fetch(opener, current_url, data=payload)

    # DEBUG: dump first page HTML for inspection
    import os
    debug_dir = "scripts"
    if os.path.isdir(debug_dir):
        with open(os.path.join(debug_dir, "ssc_scraper_lastpage.html"), "w", encoding="utf-8") as _f:
            _f.write(page)

    all_rows = []
    page_num = 1
    while True:
        rows = parse_da_rows(page, source_search)
        all_rows.extend(rows)
        nxt = find_next_page(page, page_num)
        if nxt is None:
            break
        grid_target, next_page_num = nxt
        # Numbered-page-link pagination: postback with grid target + Page$N argument.
        # Original search-criteria fields must persist so the result set carries over.
        state = extract_state(page)
        next_payload = dict(payload)  # carry forward all search fields
        next_payload.update({
            "__VIEWSTATE": state["__VIEWSTATE"],
            "__VIEWSTATEGENERATOR": state["__VIEWSTATEGENERATOR"],
            "__EVENTVALIDATION": state["__EVENTVALIDATION"],
            "__EVENTTARGET": grid_target,
            "__EVENTARGUMENT": f"Page${next_page_num}",
        })
        # Remove the search-button trigger from the post — it's a pager event now
        next_payload.pop("ctl00$Content$btnSearch", None)
        time.sleep(DELAY_PAGE_SEC)
        page, current_url = fetch(opener, current_url, data=next_payload)
        page_num = next_page_num
        if page_num > 500:  # safety
            print(f"  WARN: pagination exceeded 500 pages, stopping", flush=True)
            break
    return all_rows, page_num


# ----------------------------------------------------------------------------
# Supabase upsert
# ----------------------------------------------------------------------------

def upsert_batch(rows):
    if not rows:
        return True, "empty"
    # Dedupe by da_id within this batch — same DA can appear on multiple result
    # pages due to grid sort instability. Last occurrence wins.
    by_id = {r["da_id"]: r for r in rows}
    rows = list(by_id.values())
    body = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(
        UPSERT_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return True, f"{resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def month_iter(start_yyyymm, end_yyyymm):
    sy, sm = (int(x) for x in start_yyyymm.split("-"))
    ey, em = (int(x) for x in end_yyyymm.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        last_day = calendar.monthrange(y, m)[1]
        yield date(y, m, 1), date(y, m, last_day)
        m += 1
        if m == 13:
            m = 1
            y += 1


def run_one(df: date, dt: date) -> dict:
    label = f"{df.isoformat()}..{dt.isoformat()}"
    rows, pages = search_das(date_from=df, date_to=dt, source_search=label)
    ok, msg = upsert_batch(rows)
    return {
        "range": label,
        "rows": len(rows),
        "pages": pages,
        "upsert_ok": ok,
        "upsert_msg": msg,
    }


def main():
    if len(sys.argv) == 3 and "-" in sys.argv[1] and len(sys.argv[1]) == 10:
        # exact date range
        df = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        dt = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
        result = run_one(df, dt)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["upsert_ok"] else 1)

    if len(sys.argv) == 3 and len(sys.argv[1]) == 7:
        # month range
        totals = {"months": 0, "rows": 0, "pages": 0, "failures": []}
        for df, dt in month_iter(sys.argv[1], sys.argv[2]):
            r = run_one(df, dt)
            totals["months"] += 1
            totals["rows"] += r["rows"]
            totals["pages"] += r["pages"]
            print(
                f"[{r['range']}] rows={r['rows']:>4} pages={r['pages']} "
                f"upsert={'OK' if r['upsert_ok'] else 'FAIL ' + r['upsert_msg']}",
                flush=True,
            )
            if not r["upsert_ok"]:
                totals["failures"].append(r)
            time.sleep(DELAY_MONTH_SEC)
        print("---")
        print(json.dumps(totals, indent=2))
        sys.exit(0 if not totals["failures"] else 1)

    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
