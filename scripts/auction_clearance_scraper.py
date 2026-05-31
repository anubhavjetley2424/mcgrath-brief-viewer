"""
Domain auction-clearance scraper.

Fetches the weekly Sydney auction-results page and writes TWO rows per week:
  - 'Sydney'           → from citySummaryData (full city aggregate)
  - 'Sutherland Shire' → derived by filtering salesListings to SSC suburbs
                          and counting Domain auction result codes

Usage:
    python auction_clearance_scraper.py current               # this weekend
    python auction_clearance_scraper.py 2026-05-23            # one specific Sat
    python auction_clearance_scraper.py backfill              # all 24 historical weeks
                                                                # (driven by historicalAuctionDates)
"""

import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from statistics import median as stats_median

DOMAIN_BASE = "https://www.domain.com.au"

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)
UPSERT_URL = f"{SUPABASE_URL}/rest/v1/auction_clearance?on_conflict=auction_week,region"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# Comprehensive Sutherland Shire LGA suburb list (case-insensitive match on Domain's 'suburb')
SSC_SUBURBS = {s.lower() for s in [
    "Alfords Point", "Bangor", "Barden Ridge", "Bonnet Bay", "Bundeena", "Burraneer",
    "Caringbah", "Caringbah South", "Como", "Cronulla", "Dolans Bay", "Engadine",
    "Grays Point", "Greenhills Beach", "Gymea", "Gymea Bay", "Heathcote", "Illawong",
    "Jannali", "Kangaroo Point", "Kareela", "Kirrawee", "Kurnell", "Lilli Pilli",
    "Loftus", "Lucas Heights", "Maianbar", "Menai", "Miranda", "Oyster Bay",
    "Port Hacking", "Sandy Point", "Sutherland", "Sylvania", "Sylvania Waters",
    "Taren Point", "Waterfall", "Woolooware", "Woronora", "Woronora Heights",
    "Yarrawarrah", "Yowie Bay",
]}

# Result codes — Domain auction outcomes
SOLD_CODES = {"AUSP", "AUSV", "AUSO", "AUSB"}     # Sold at auction / vendor / prior / under bidder
PASSED_CODES = {"AUPI", "AUNL"}                    # Passed in / no bid (no sale)
WITHDRAWN_CODES = {"AUWD"}                         # Withdrawn

HTTP_TIMEOUT = 60
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', re.DOTALL
)


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


def parse_next_data(html_text: str) -> dict:
    m = NEXT_DATA_RE.search(html_text)
    if not m:
        raise RuntimeError("No __NEXT_DATA__ in response")
    return json.loads(m.group(1))


def safe_div(a, b):
    if not b:
        return None
    return round(a / b, 4)


def build_sydney_row(cp: dict, auction_week: str) -> dict:
    s = cp.get("citySummaryData", {}) or {}
    return {
        "auction_week":    auction_week,
        "region":          "Sydney",
        "listed":          s.get("numberListedForAuction"),
        "withdrawn":       s.get("numberWithdrawn"),
        "unreported":      s.get("numberUnreported"),
        "auctioned":       s.get("numberAuctioned"),
        "sold":            s.get("numberSold"),
        "passed_in":       s.get("numberPassedIn"),
        "total_sales_aud": s.get("totalSales"),
        "median_aud":      s.get("median"),
        "clearance_rate":  round(s["adjClearanceRate"], 4) if s.get("adjClearanceRate") is not None else None,
        "ly_clearance":    round(s["lastYearClearanceRate"], 4) if s.get("lastYearClearanceRate") is not None else None,
    }


def build_shire_row(cp: dict, auction_week: str) -> dict:
    """Derive Sutherland Shire stats from per-suburb salesListings."""
    sold = 0
    passed = 0
    withdrawn = 0
    other = 0
    sold_prices = []
    total_sales = 0.0
    for group in cp.get("salesListings", []) or []:
        suburb = (group.get("suburb") or "").lower()
        if suburb not in SSC_SUBURBS:
            continue
        for L in group.get("listings", []) or []:
            code = L.get("result") or ""
            price = L.get("price") or 0
            if code in SOLD_CODES:
                sold += 1
                if price:
                    sold_prices.append(price)
                    total_sales += float(price)
            elif code in PASSED_CODES:
                passed += 1
            elif code in WITHDRAWN_CODES:
                withdrawn += 1
            else:
                other += 1

    auctioned = sold + passed + other
    listed = sold + passed + withdrawn + other
    clearance = safe_div(sold, sold + passed + withdrawn)

    return {
        "auction_week":    auction_week,
        "region":          "Sutherland Shire",
        "listed":          listed,
        "withdrawn":       withdrawn,
        "unreported":      None,
        "auctioned":       auctioned,
        "sold":            sold,
        "passed_in":       passed,
        "total_sales_aud": total_sales if sold_prices else None,
        "median_aud":      float(stats_median(sold_prices)) if sold_prices else None,
        "clearance_rate":  clearance,
        "ly_clearance":    None,  # not available at LGA level
    }


def upsert(rows: list[dict]) -> tuple[bool, str]:
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
        return False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}"


def scrape_one(week_date: str | None) -> dict:
    """week_date = 'YYYY-MM-DD' (Saturday) or None for current."""
    if week_date:
        url = f"{DOMAIN_BASE}/auction-results/sydney/{week_date}"
    else:
        url = f"{DOMAIN_BASE}/auction-results/sydney/"
    page = fetch_html(url)
    nd = parse_next_data(page)
    cp = nd.get("props", {}).get("pageProps", {}).get("componentProps", {}) or {}
    actual_date = (cp.get("auctionDate") or "")[:10]
    if not actual_date:
        raise RuntimeError(f"no auctionDate in response for {url}")

    sydney = build_sydney_row(cp, actual_date)
    shire = build_shire_row(cp, actual_date)
    ok, msg = upsert([sydney, shire])
    return {
        "auction_week": actual_date,
        "sydney_clearance": sydney["clearance_rate"],
        "shire_sold": shire["sold"],
        "shire_passed": shire["passed_in"],
        "shire_withdrawn": shire["withdrawn"],
        "shire_clearance": shire["clearance_rate"],
        "upsert": msg,
        "ok": ok,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    arg = sys.argv[1]

    if arg == "current":
        r = scrape_one(None)
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["ok"] else 1)

    if arg == "backfill":
        # Fetch the current page once to enumerate historicalAuctionDates
        page = fetch_html(f"{DOMAIN_BASE}/auction-results/sydney/")
        nd = parse_next_data(page)
        dates = nd["props"]["pageProps"]["componentProps"].get("historicalAuctionDates", []) or []
        # Each entry is ISO datetime; take date portion
        dates = [d[:10] for d in dates if isinstance(d, str)]
        print(f"# Backfilling {len(dates)} weeks")
        totals = {"ok": 0, "fail": 0}
        for d in dates:
            try:
                r = scrape_one(d)
                print(f"  {r['auction_week']}  syd={r['sydney_clearance']}  "
                      f"shire sold={r['shire_sold']} passed={r['shire_passed']} "
                      f"wd={r['shire_withdrawn']} -> clr={r['shire_clearance']}  {r['upsert']}",
                      flush=True)
                totals["ok" if r["ok"] else "fail"] += 1
            except Exception as e:
                print(f"  {d}  FAIL: {type(e).__name__}: {e}", flush=True)
                totals["fail"] += 1
            time.sleep(1.2)
        print("---")
        print(json.dumps(totals, indent=2))
        sys.exit(0 if totals["fail"] == 0 else 1)

    # specific date
    r = scrape_one(arg)
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
