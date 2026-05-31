"""
Domain.com.au scraper — active listings, recent solds, suburb medians.

Strategy: GET the suburb search page (`/sale/<suburb>-nsw-<postcode>/?page=N`)
with browser-like headers, extract __NEXT_DATA__ JSON, parse out three datasets
and upsert each into its dedicated Supabase table.

Usage:
    python domain_scraper.py sale cronulla 2230                 # all pages, sale
    python domain_scraper.py sale cronulla 2230 --max-pages 1   # smoke test
    python domain_scraper.py sold cronulla 2230                 # /sold-listings/
    python domain_scraper.py rent cronulla 2230                 # /rent/ (medians + DOM)
    python domain_scraper.py farm                               # all 8 Simon suburbs, sale mode
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

DOMAIN_BASE = "https://www.domain.com.au"

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)

HTTP_TIMEOUT = 60
PAGE_DELAY_SEC = 1.5

# These are the browser-like headers required to get past Domain's anti-bot
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

SIMON_FARM_SUBURBS = [
    ("cronulla", "2230"),
    ("caringbah", "2229"),
    ("caringbah-south", "2229"),
    ("gymea-bay", "2227"),
    ("sylvania-waters", "2224"),
    ("woolooware", "2230"),
    ("miranda", "2228"),
    ("jannali", "2226"),
]

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', re.DOTALL
)
TITLE_TOTAL_RE = re.compile(r"<title[^>]*>(\d+)[^|]*\|", re.IGNORECASE)


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------

def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read()
        # Handle gzip if present
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


def extract_next_data(html_text: str) -> dict | None:
    m = NEXT_DATA_RE.search(html_text)
    if not m:
        return None
    return json.loads(m.group(1))


def total_results_from_title(html_text: str) -> int | None:
    m = TITLE_TOTAL_RE.search(html_text)
    return int(m.group(1)) if m else None


# ----------------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------------

def parse_iso_dt(s: str | None):
    if not s:
        return None
    # Domain uses "2026-05-30T10:15:00" — naive ISO
    try:
        from datetime import datetime
        return datetime.fromisoformat(s).isoformat()
    except Exception:
        return None


def map_active_listing(item: dict, source_search: str) -> dict | None:
    """Map one `listingsMap` entry to a domain_listings_active row."""
    if item.get("listingType") != "listing":
        return None
    lm = item.get("listingModel") or {}
    def safe_dict(v):
        return v if isinstance(v, dict) else {}
    addr = safe_dict(lm.get("address"))
    feat = safe_dict(lm.get("features"))
    tags = safe_dict(lm.get("tags"))
    auction = safe_dict(lm.get("auction"))
    inspection = safe_dict(lm.get("inspection"))
    branding = safe_dict(lm.get("branding"))
    agency = branding.get("agencyName") or lm.get("agencyName")

    listing_id = item.get("id")
    if not listing_id:
        return None

    return {
        "domain_listing_id": int(listing_id),
        "url": lm.get("url"),
        "street": addr.get("street"),
        "suburb": addr.get("suburb"),
        "state": addr.get("state"),
        "postcode": addr.get("postcode"),
        "lat": addr.get("lat"),
        "lng": addr.get("lng"),
        "price_text": lm.get("price"),
        "beds": feat.get("beds"),
        "baths": feat.get("baths"),
        "parking": feat.get("parking"),
        "land_size_sqm": feat.get("landSize") if feat.get("landUnit") in ("m²", "m²") else None,
        "property_type": feat.get("propertyType"),
        "property_type_formatted": feat.get("propertyTypeFormatted"),
        "listing_tag": tags.get("tagText"),
        "auction_dt": parse_iso_dt(auction.get("date")),
        "has_inspection": bool(inspection.get("openTime")),
        "agency_name": agency,
        "promo_type": lm.get("promoType"),
        "source_search": source_search,
    }


def map_sold_listing(item: dict, source_search: str) -> dict | None:
    """Map a UPVSoldListings or /sold-listings/ entry to a domain_listings_sold row."""
    lm = item.get("listingModel") or item
    addr = lm.get("address") or {}
    feat = lm.get("features") or {}
    listing_id = item.get("id") or lm.get("id")
    if not listing_id:
        return None

    # Sold price may be in 'price' (display) or 'soldData' or as numeric
    sold_data = lm.get("soldData") or {}
    sold_price_text = lm.get("price") or sold_data.get("priceText")
    sold_price = None
    # Try to extract a numeric price from text like "$1,500,000"
    if sold_price_text:
        m = re.search(r"\$?([0-9,]+)", sold_price_text.replace(" ", ""))
        if m:
            try:
                sold_price = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    sold_date = sold_data.get("soldDate")  # YYYY-MM-DD or similar
    if sold_date and isinstance(sold_date, str) and len(sold_date) >= 10:
        sold_date = sold_date[:10]
    else:
        sold_date = None

    return {
        "domain_listing_id": int(listing_id),
        "url": lm.get("url"),
        "street": addr.get("street"),
        "suburb": addr.get("suburb"),
        "state": addr.get("state"),
        "postcode": addr.get("postcode"),
        "lat": addr.get("lat"),
        "lng": addr.get("lng"),
        "sold_price": sold_price,
        "sold_price_text": sold_price_text,
        "sold_date": sold_date,
        "beds": feat.get("beds"),
        "baths": feat.get("baths"),
        "parking": feat.get("parking"),
        "land_size_sqm": feat.get("landSize") if feat.get("landUnit") in ("m²", "m²") else None,
        "property_type": feat.get("propertyType"),
        "property_type_formatted": feat.get("propertyTypeFormatted"),
        "agency_name": (lm.get("branding") or {}).get("agencyName") or lm.get("agencyName"),
        "source_search": source_search,
    }


def parse_suburb_medians(next_data: dict, listing_type: str) -> list[dict]:
    """Extract suburb medians from locationPriceVolumeProps.dataPoints."""
    cp = next_data.get("props", {}).get("pageProps", {}).get("componentProps", {})
    lpv = cp.get("locationPriceVolumeProps") or {}
    suburb = lpv.get("suburb")
    postcode = None
    creloc = cp.get("creLocationObject") or {}
    postcode = creloc.get("postCode") or postcode
    rows = []
    for dp in lpv.get("dataPoints", []) or []:
        ptype = dp.get("propertyType")
        for pv in dp.get("priceAndVolumeData", []) or []:
            label = pv.get("label") or ""
            m = re.match(r"(\d+)\s*Beds?", label)
            if not m:
                continue
            bedrooms = int(m.group(1))
            median = pv.get("medianPrice")
            volume = pv.get("volume")
            if median is None:
                continue
            rows.append({
                "suburb": suburb,
                "postcode": postcode,
                "property_type": ptype,
                "bedrooms": bedrooms,
                "median_price": median,
                "volume": volume,
                "listing_type": listing_type,
                "snapshot_date": date.today().isoformat(),
            })
    return rows


# ----------------------------------------------------------------------------
# Supabase
# ----------------------------------------------------------------------------

def upsert(table: str, rows: list[dict], on_conflict: str) -> tuple[bool, str]:
    if not rows:
        return True, "empty"
    # Dedupe within batch on the conflict columns
    cols = [c.strip() for c in on_conflict.split(",")]
    by_key = {}
    for r in rows:
        key = tuple(r.get(c) for c in cols)
        by_key[key] = r
    rows = list(by_key.values())

    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    body = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
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
# Mode: sale (active + bonus solds + medians)
# ----------------------------------------------------------------------------

def scrape_sale(suburb: str, postcode: str, max_pages: int | None = None) -> dict:
    source_search = f"sale:{suburb}-{postcode}"
    base = f"{DOMAIN_BASE}/sale/{suburb}-nsw-{postcode}/"
    total = {"active": 0, "sold_bonus": 0, "medians": 0, "pages": 0, "total_results": None}

    page = 1
    while True:
        url = base if page == 1 else f"{base}?page={page}"
        html_text = fetch_html(url)
        nd = extract_next_data(html_text)
        if not nd:
            print(f"  page {page}: no NEXT_DATA, stopping", flush=True)
            break
        cp = nd.get("props", {}).get("pageProps", {}).get("componentProps", {})

        if page == 1:
            total["total_results"] = total_results_from_title(html_text)
            # Suburb medians — once is enough
            medians = parse_suburb_medians(nd, "Sale")
            ok, msg = upsert("domain_suburb_medians", medians,
                             "suburb,property_type,bedrooms,listing_type,snapshot_date")
            print(f"  medians: {len(medians)} rows  {msg}", flush=True)
            if ok:
                total["medians"] = len(medians)

            # UPV sold (bonus 10)
            sold_bonus_raw = cp.get("UPVSoldListings", []) or []
            sold_rows = [r for r in (map_sold_listing(x, source_search) for x in sold_bonus_raw) if r]
            ok, msg = upsert("domain_listings_sold", sold_rows, "domain_listing_id")
            print(f"  upv-sold: {len(sold_rows)} rows  {msg}", flush=True)
            if ok:
                total["sold_bonus"] = len(sold_rows)

        # Active listings
        lm = cp.get("listingsMap") or {}
        active_rows = []
        for item in lm.values():
            r = map_active_listing(item, source_search)
            if r:
                active_rows.append(r)

        ok, msg = upsert("domain_listings_active", active_rows, "domain_listing_id")
        print(f"  page {page} active: {len(active_rows)} rows  {msg}", flush=True)
        if ok:
            total["active"] += len(active_rows)
        total["pages"] = page

        # Stop conditions
        if not active_rows:
            break
        if max_pages and page >= max_pages:
            break
        # Domain pages run out when listingsMap is empty or page is beyond total
        if total["total_results"] and total["active"] >= total["total_results"]:
            break
        page += 1
        time.sleep(PAGE_DELAY_SEC)

    return total


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("sale", "sold", "rent", "farm"))
    p.add_argument("suburb", nargs="?", help="suburb slug e.g. cronulla")
    p.add_argument("postcode", nargs="?", help="postcode e.g. 2230")
    p.add_argument("--max-pages", type=int, default=None)
    args = p.parse_args()

    if args.mode == "sale":
        if not args.suburb or not args.postcode:
            p.error("sale mode requires suburb and postcode")
        r = scrape_sale(args.suburb, args.postcode, args.max_pages)
        print(json.dumps(r, indent=2))
        sys.exit(0)

    if args.mode == "farm":
        results = []
        for sb, pc in SIMON_FARM_SUBURBS:
            print(f"=== {sb} {pc} ===", flush=True)
            r = scrape_sale(sb, pc, args.max_pages)
            r["suburb"] = sb
            results.append(r)
            time.sleep(2.0)
        print("---")
        print(json.dumps({
            "total_active": sum(r["active"] for r in results),
            "total_sold_bonus": sum(r["sold_bonus"] for r in results),
            "total_medians": sum(r["medians"] for r in results),
            "per_suburb": results,
        }, indent=2))
        sys.exit(0)

    if args.mode in ("sold", "rent"):
        print(f"NOT YET IMPLEMENTED: {args.mode} (V1 ships sale mode only)")
        sys.exit(2)


if __name__ == "__main__":
    main()
