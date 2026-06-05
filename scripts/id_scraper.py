"""
profile.id.com.au Community Profile scraper — LGA-level demographics.

Fetches a set of key topic pages for an LGA (Sutherland Shire) and parses the
entity-tables on each. Stores long-form rows in public.id_metric_rows.

Only LGA-level coverage — profile.id.com.au's free Community Profile does not
publish sub-suburb breakdowns for Sutherland Shire. SA1-level data requires
ABS Census (separate source, deferred).

Usage:
    python id_scraper.py sutherland           # scrape all key pages for one LGA
    python id_scraper.py sutherland migration # one page (URL slug)
"""

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ID_BASE = "https://profile.id.com.au"

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
# Public anon key — RLS blocks writes, so production uses the service-role
# key from env. Anon stays as a read-only fallback for local smoke tests.
_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", _SUPABASE_ANON_KEY)
UPSERT_URL = (
    f"{SUPABASE_URL}/rest/v1/id_metric_rows"
    "?on_conflict=lga,source_page,table_index,row_label,column_label"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# Pages most useful for appraisal context
APPRAISAL_PAGES = [
    "population",
    "population-estimate",
    "migration",
    "annual-migration-by-location",
    "migration-by-age-by-location",
    "household-income",
    "household-income-quartiles",
    "household-composition",
    "household-size",
    "households-with-children",
    "tenure",                  # owner-occupier vs renter
    "dwellings",
    "building-approvals",
    "occupations",
    "individual-income",
]

HTTP_TIMEOUT = 60
DELAY_BETWEEN_PAGES = 1.0


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------

def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


# ----------------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------------

TABLE_RE = re.compile(r"<table[^>]*\bclass=\"[^\"]*entity-table[^\"]*\"[^>]*>(.*?)</table>", re.DOTALL)
TR_RE    = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
TH_RE    = re.compile(r"<th[^>]*>(.*?)</th>", re.DOTALL)
TD_RE    = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
TAG_RE   = re.compile(r"<[^>]+>")
NUM_RE   = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def clean(s: str) -> str:
    return TAG_RE.sub("", html.unescape(s)).strip()


def to_num(s: str):
    if not s or s in ("-", "--", "N/A", "n/a"):
        return None
    m = NUM_RE.match(s.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_entity_tables(page_html: str, lga: str, source_page: str) -> list[dict]:
    """Return long-form rows for every entity-table on the page."""
    rows = []
    for idx, table_match in enumerate(TABLE_RE.finditer(page_html)):
        table_html = table_match.group(1)
        trs = TR_RE.findall(table_html)
        if not trs:
            continue

        # Locate the title (first th with class table-area-name) and column headers
        title = None
        col_labels: list[str] = []
        data_trs: list[str] = []

        for tr_html in trs:
            ths = TH_RE.findall(tr_html)
            tds = TD_RE.findall(tr_html)
            if ths and not tds:
                # Header row
                if title is None:
                    # First <th> that's a non-label header — pick the area name
                    raw = clean(ths[0])
                    # Heuristic: title appears in colspan-spanning header
                    if "colSpan" in tr_html or "colspan" in tr_html.lower():
                        title = raw
                        continue
                # If we already have title, this row likely has column headers
                col_labels = [clean(th) for th in ths]
            elif tds:
                data_trs.append(tr_html)

        if not title:
            title = f"Table {idx + 1}"
        if not col_labels or not data_trs:
            continue

        # First column header is typically the row-label header (e.g. "State / Territory")
        # Following columns are data columns
        data_col_labels = col_labels[1:] if len(col_labels) > 1 else col_labels

        for tr_html in data_trs:
            tds = TD_RE.findall(tr_html)
            if not tds:
                continue
            row_label = clean(tds[0])
            if not row_label:
                continue
            for ci, td_html in enumerate(tds[1:]):
                col_label = data_col_labels[ci] if ci < len(data_col_labels) else f"col_{ci+1}"
                val_text = clean(td_html)
                val_num = to_num(val_text)
                rows.append({
                    "lga": lga,
                    "source_page": source_page,
                    "table_index": idx,
                    "table_title": title,
                    "row_label": row_label,
                    "column_label": col_label,
                    "value_num": val_num,
                    "value_text": val_text,
                })
    return rows


# ----------------------------------------------------------------------------
# Supabase
# ----------------------------------------------------------------------------

def upsert(rows: list[dict]) -> tuple[bool, str]:
    if not rows:
        return True, "empty"
    # Dedupe within batch
    by_key = {(r["lga"], r["source_page"], r["table_index"], r["row_label"], r["column_label"]): r for r in rows}
    rows = list(by_key.values())
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
            return True, f"{resp.status} (rows={len(rows)})"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def scrape_page(lga: str, slug: str) -> dict:
    url = f"{ID_BASE}/{lga}/{slug}"
    source_page = f"/{lga}/{slug}"
    try:
        page = fetch_html(url)
    except urllib.error.HTTPError as e:
        return {"page": slug, "ok": False, "rows": 0, "err": f"HTTP {e.code}"}
    rows = parse_entity_tables(page, lga, source_page)
    ok, msg = upsert(rows)
    return {"page": slug, "ok": ok, "rows": len(rows), "msg": msg}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    lga = sys.argv[1]
    if len(sys.argv) == 3:
        slugs = [sys.argv[2]]
    else:
        slugs = APPRAISAL_PAGES

    totals = {"pages_ok": 0, "pages_fail": 0, "rows": 0}
    for slug in slugs:
        r = scrape_page(lga, slug)
        print(f"  /{lga}/{slug:<35} rows={r['rows']:>4} {'OK' if r['ok'] else 'FAIL ' + r.get('err', r.get('msg', ''))}", flush=True)
        if r["ok"]:
            totals["pages_ok"] += 1
            totals["rows"] += r["rows"]
        else:
            totals["pages_fail"] += 1
        time.sleep(DELAY_BETWEEN_PAGES)
    print("---")
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
