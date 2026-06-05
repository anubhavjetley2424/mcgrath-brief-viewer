"""
NSW Valuer General — Bulk Property Sales Information (PSI) scraper.

Source:
    https://www.valuergeneral.nsw.gov.au/__psi/weekly/<YYYYMMDD>.zip
    https://www.valuergeneral.nsw.gov.au/__psi/yearly/<YYYY>.zip
Format:
    ZIP of NNN_SALES_DATA_NNME_DDMMYYYY.DAT files (one per district).
    Each .DAT is semicolon-delimited records:
        A — header
        B — property + sale row  <-- what we want
        C — legal description (lot/plan)
        D — previous sale (skipped)
        Z — footer
Licence:
    CC BY-NC-ND 4.0 — attribution shown in dashboard footer.

Usage:
    python vg_scraper.py weekly 20260601                       # one weekly file
    python vg_scraper.py weekly-latest                         # most recent Sunday
    python vg_scraper.py annual 2024                           # one calendar year
    python vg_scraper.py annual-backfill 2023 2025             # year range
"""

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta

# Defensive: strip stale Windows CA env vars before curl_cffi loads
for _e in ("CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
    os.environ.pop(_e, None)

from curl_cffi import requests as cc_requests  # type: ignore

VG_BASE = "https://www.valuergeneral.nsw.gov.au/__psi"

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)
# Try the modern env var first; fall back to legacy name used in api/.env, then anon.
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SERVICE_KEY")
    or _SUPABASE_ANON_KEY
)
# Idempotency key on the existing vg_sales table:
#   UNIQUE (property_id, contract_date, purchase_price, sale_counter)
UPSERT_URL = (
    f"{SUPABASE_URL}/rest/v1/vg_sales"
    "?on_conflict=property_id,contract_date,purchase_price,sale_counter"
)

HTTP_TIMEOUT = 60
UPSERT_BATCH = 500
INTER_BATCH_DELAY = 0.2

# Primary filter: NSW VG district code 144 = Sutherland Shire LGA.
# (Stronger than suburb-name matching because it survives any spelling drift
# in the VG dataset — district codes are canonical.)
SSC_DISTRICT_CODE = "144"

# Defensive secondary filter — covers the rare case where a property in the
# LGA is filed under a neighbouring district code due to boundary edge cases.
# Lowercased for case-insensitive match.
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


# ----------------------------------------------------------------------------
# HTTP + ZIP
# ----------------------------------------------------------------------------

def download_zip(url: str) -> bytes:
    """Fetch a ZIP via curl_cffi (impersonates Chrome — VG endpoint isn't
    Akamai-protected today, but curl_cffi is a no-cost insurance policy)."""
    r = cc_requests.get(url, impersonate="chrome124", timeout=HTTP_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"GET {url} -> HTTP {r.status_code}")
    return r.content


def iter_dat_lines(zip_bytes: bytes):
    """Yield (dat_filename, line) for every .DAT line in a VG ZIP.

    Skips any non-Sutherland district file by filename — VG names files
    `NNN_SALES_DATA_NNME_DDMMYYYY.DAT` where NNN is the district code, so
    we can short-circuit before parsing for the ~250 non-SSC districts.
    """
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    for info in zf.infolist():
        upper = info.filename.upper()
        if not upper.endswith(".DAT"):
            continue
        # Filename starts with the 3-digit district code
        if not upper.startswith(f"{SSC_DISTRICT_CODE}_"):
            continue
        # Latin-1 to be safe — VG files occasionally contain non-ASCII bytes
        text = zf.read(info.filename).decode("latin-1", errors="replace")
        for line in text.split("\n"):
            line = line.rstrip("\r")
            if line:
                yield info.filename, line


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------

def _to_date(s: str):
    s = (s or "").strip()
    if len(s) < 8:
        return None
    try:
        return datetime.strptime(s[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _to_int(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _to_float(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_b_record(line: str, dat_filename: str, source_tag: str) -> dict | None:
    """
    Map a VG B-record line to one public.vg_sales row.

    Existing public.vg_sales schema (idempotent on
    (property_id, contract_date, purchase_price, sale_counter)):

        property_id      text NOT NULL
        district_code    text NOT NULL
        unit_number      text
        house_number     text
        street_name      text
        suburb           text NOT NULL
        postcode         text
        contract_date    date
        settlement_date  date
        purchase_price   numeric NOT NULL
        land_area_sqm    numeric
        area_type        text       ('M' m², 'H' hectares)
        property_type    text       ('R' residential, 'V' vacant, etc.)
        zone_code        text       ('R2', etc.)
        source_file      text NOT NULL     ← provenance: e.g. 'vg-weekly:144_…DAT'
        loaded_at        timestamptz NOT NULL
        sale_counter     int
        latitude         numeric    (geocoded later)
        longitude        numeric    (geocoded later)

    VG B record layout (semicolon-delimited):
        0  record type 'B'
        1  district code
        2  property ID
        3  sale counter
        4  download datetime
        5  property name        (often blank)
        6  property unit number
        7  property house number
        8  property street name
        9  property locality (suburb)
        10 property post code
        11 area
        12 area type            ('M' = m², 'H' = hectares)
        13 contract date
        14 settlement date
        15 purchase price
        16 zoning
        17 nature of property   ('R' residential, 'V' vacant, etc.)
        18 primary purpose
        19 strata lot number
        20 component code
        21 sale code
        22 % interest of sale
        23 dealing number
    """
    parts = line.split(";")
    if len(parts) < 24 or parts[0] != "B":
        return None

    district_code = (parts[1] or "").strip()
    suburb = (parts[9] or "").strip()
    # Belt-and-braces — file-name filter already restricted us to district 144,
    # but a stray non-SSC suburb in the LGA file would be an upstream surprise.
    if district_code != SSC_DISTRICT_CODE and suburb.lower() not in SSC_SUBURBS:
        return None

    contract_date = _to_date(parts[13])
    purchase_price = _to_int(parts[15])
    property_id = (parts[2] or "").strip()
    if not property_id or not contract_date or purchase_price is None or purchase_price <= 0:
        return None

    area = _to_float(parts[11])
    area_type = (parts[12] or "").strip().upper() or None
    if area is not None and area_type == "H":
        land_area_sqm = area * 10000.0
    else:
        land_area_sqm = area

    return {
        "property_id":     property_id,
        "district_code":   district_code or SSC_DISTRICT_CODE,
        "unit_number":     (parts[6] or "").strip() or None,
        "house_number":    (parts[7] or "").strip() or None,
        # Street name kept as-is from VG (already uppercase like "ARMIDALE ST")
        "street_name":     (parts[8] or "").strip() or None,
        # Suburb stored UPPERCASE to match the 1.8k existing rows already in
        # the table — keeps "where suburb = 'CRONULLA'" working uniformly.
        # Dashboard formats to title case at display time.
        "suburb":          suburb.upper(),
        "postcode":        (parts[10] or "").strip() or None,
        "contract_date":   contract_date,
        "settlement_date": _to_date(parts[14]),
        "purchase_price":  purchase_price,
        "land_area_sqm":   land_area_sqm,
        "area_type":       area_type,
        "property_type":   (parts[17] or "").strip() or None,
        "zone_code":       (parts[16] or "").strip() or None,
        "source_file":     f"{source_tag}:{dat_filename}",
        "loaded_at":       datetime.utcnow().isoformat() + "Z",
        "sale_counter":    _to_int(parts[3]),
    }


# ----------------------------------------------------------------------------
# Supabase
# ----------------------------------------------------------------------------

def upsert(rows: list[dict]) -> tuple[int, int]:
    """Batch-upsert; returns (ok, fail) batch counts."""
    ok = fail = 0
    for i in range(0, len(rows), UPSERT_BATCH):
        batch = rows[i:i + UPSERT_BATCH]
        body = json.dumps(batch).encode("utf-8")
        req = urllib.request.Request(
            UPSERT_URL, data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                if 200 <= resp.status < 300:
                    ok += 1
                else:
                    fail += 1
                    print(f"  upsert batch[{i}] HTTP {resp.status}", flush=True)
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"  upsert batch[{i}] HTTP {e.code}: "
                  f"{e.read().decode('utf-8', errors='replace')[:300]}",
                  flush=True)
        time.sleep(INTER_BATCH_DELAY)
    return ok, fail


# ----------------------------------------------------------------------------
# Drivers
# ----------------------------------------------------------------------------

def process_zip(url: str, source_tag: str) -> dict:
    print(f"  downloading {url}", flush=True)
    zip_bytes = download_zip(url)
    print(f"  parsing ZIP ({len(zip_bytes)} bytes)…", flush=True)

    rows = []
    scanned = 0
    for dat_filename, line in iter_dat_lines(zip_bytes):
        if not line.startswith("B;"):
            continue
        scanned += 1
        r = parse_b_record(line, dat_filename, source_tag)
        if r:
            rows.append(r)

    # Dedupe within this file (rare but defensive). Matches the table's
    # UNIQUE (property_id, contract_date, purchase_price, sale_counter).
    by_key = {}
    for r in rows:
        key = (r["property_id"], r["contract_date"],
               r["purchase_price"], r["sale_counter"])
        by_key[key] = r
    rows = list(by_key.values())

    print(f"  B records scanned: {scanned}, SSC rows kept: {len(rows)}",
          flush=True)
    if not rows:
        return {"url": url, "scanned_B": scanned, "ssc_rows": 0,
                "upsert_ok_batches": 0, "upsert_fail_batches": 0}

    ok, fail = upsert(rows)
    return {"url": url, "scanned_B": scanned, "ssc_rows": len(rows),
            "upsert_ok_batches": ok, "upsert_fail_batches": fail}


def candidate_weekly_dates(max_lookback_weeks: int = 6):
    """Yield candidate Monday-stamped weekly file dates, most-recent first.

    VG publishes its weekly PSI bulk on Mondays. The URL date is the
    publication date itself, not the preceding Sunday. Walks back week-
    by-week so the Monday cron stays healthy if VG runs late.
    """
    today = date.today()
    # Mon=0; how many days back to the most recent Monday
    days_back = today.weekday()
    if days_back == 0:
        # Today is Monday — try today first; fall through to last week if
        # VG hasn't published by Cloud Run's 05:00 AEDT fire time.
        monday = today
    else:
        monday = today - timedelta(days=days_back)
    for _ in range(max_lookback_weeks):
        yield monday.strftime("%Y%m%d")
        monday -= timedelta(days=7)


def head_ok(url: str) -> bool:
    """Cheap pre-flight: does this weekly URL exist?"""
    try:
        r = cc_requests.head(url, impersonate="chrome124",
                             timeout=15, allow_redirects=False)
        return r.status_code == 200
    except Exception:
        return False


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "mode",
        choices=("weekly", "weekly-latest", "annual", "annual-backfill"),
    )
    p.add_argument("arg1", nargs="?")
    p.add_argument("arg2", nargs="?")
    args = p.parse_args()

    if args.mode == "weekly":
        if not args.arg1:
            p.error("weekly requires <YYYYMMDD>")
        url = f"{VG_BASE}/weekly/{args.arg1}.zip"
        print(json.dumps(process_zip(url, "vg-weekly"), indent=2))
        sys.exit(0)

    if args.mode == "weekly-latest":
        # Walk back week-by-week until we find a published file. Keeps the
        # Monday cron healthy when VG runs late.
        chosen_url = None
        for ymd in candidate_weekly_dates():
            url = f"{VG_BASE}/weekly/{ymd}.zip"
            if head_ok(url):
                chosen_url = url
                print(f"[weekly-latest] using {ymd}", flush=True)
                break
            print(f"[weekly-latest] {ymd} not yet published, trying older",
                  flush=True)
        if not chosen_url:
            sys.exit("No published VG weekly file in the last 6 weeks — "
                     "investigate VG outage.")
        print(json.dumps(process_zip(chosen_url, "vg-weekly"), indent=2))
        sys.exit(0)

    if args.mode == "annual":
        if not args.arg1:
            p.error("annual requires <YYYY>")
        url = f"{VG_BASE}/yearly/{args.arg1}.zip"
        print(json.dumps(process_zip(url, "vg-annual"), indent=2))
        sys.exit(0)

    if args.mode == "annual-backfill":
        if not args.arg1 or not args.arg2:
            p.error("annual-backfill requires <START_YEAR> <END_YEAR>")
        results = []
        for y in range(int(args.arg1), int(args.arg2) + 1):
            url = f"{VG_BASE}/yearly/{y}.zip"
            print(f"=== {y} ===", flush=True)
            results.append(process_zip(url, "vg-annual"))
            time.sleep(2.0)
        print("---")
        print(json.dumps({
            "years": [int(args.arg1), int(args.arg2)],
            "total_ssc_rows": sum(r["ssc_rows"] for r in results),
            "per_year": results,
        }, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
