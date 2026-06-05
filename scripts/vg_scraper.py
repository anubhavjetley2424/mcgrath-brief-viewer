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
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", _SUPABASE_ANON_KEY)
UPSERT_URL = (
    f"{SUPABASE_URL}/rest/v1/vg_sales"
    "?on_conflict=source,dealing_number"
)

HTTP_TIMEOUT = 60
UPSERT_BATCH = 500
INTER_BATCH_DELAY = 0.2

# Sutherland Shire suburbs — same list as auction scraper, lowercased for match
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
    """Yield (filename, line) for every .DAT line in a VG ZIP."""
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    for info in zf.infolist():
        if not info.filename.upper().endswith(".DAT"):
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


def parse_b_record(line: str, source: str) -> dict | None:
    """
    NSW VG B record layout (semicolon-delimited):
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
        13 contract date        ← treat as transfer_date
        14 settlement date
        15 purchase price
        16 zoning
        17 nature of property   ('R' residential, 'V' vacant, etc.)
        18 primary purpose
        19 strata lot number
        20 component code
        21 sale code            (e.g. 'AAD' = arms-length agreement…)
        22 % interest of sale
        23 dealing number       ← unique LRS title-transfer reference
    """
    parts = line.split(";")
    if len(parts) < 24 or parts[0] != "B":
        return None

    suburb = (parts[9] or "").strip()
    if suburb.lower() not in SSC_SUBURBS:
        return None  # Drop everything outside Sutherland Shire

    contract_date = _to_date(parts[13])
    sale_price = _to_int(parts[15])
    if not contract_date or sale_price is None or sale_price <= 0:
        return None  # Skip rows with no usable contract date or price

    dealing_number = (parts[23] or "").strip()
    if not dealing_number:
        # Synthesise a stable fallback so the upsert key still works
        dealing_number = f"NODN:{(parts[2] or '').strip()}:{contract_date}"

    house_no = (parts[7] or "").strip()
    unit_no = (parts[6] or "").strip()
    street = (parts[8] or "").strip().title()
    suburb_title = suburb.title()
    address_parts = []
    if unit_no:
        address_parts.append(f"{unit_no}/")
    address_parts.append(house_no)
    address_parts.append(street)
    street_line = " ".join(p for p in address_parts if p).replace("/ ", "/")

    area_type = (parts[12] or "").strip().upper()
    area = _to_float(parts[11])
    area_sqm = None
    if area is not None:
        if area_type == "H":
            area_sqm = area * 10000.0
        elif area_type in ("M", ""):
            area_sqm = area

    return {
        "source": source,                       # 'vg-weekly' or 'vg-annual'
        "district_code": (parts[1] or "").strip(),
        "property_id": (parts[2] or "").strip(),
        "sale_counter": _to_int(parts[3]),
        "dealing_number": dealing_number,
        "address": street_line or None,
        "suburb": suburb_title,
        "postcode": (parts[10] or "").strip() or None,
        "area_sqm": area_sqm,
        "contract_date": contract_date,
        "settlement_date": _to_date(parts[14]),
        "sale_price": sale_price,
        "zoning": (parts[16] or "").strip() or None,
        "nature_of_property": (parts[17] or "").strip() or None,
        "primary_purpose": (parts[18] or "").strip() or None,
        "sale_code": (parts[21] or "").strip() or None,
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

def process_zip(url: str, source: str) -> dict:
    print(f"  downloading {url}", flush=True)
    zip_bytes = download_zip(url)
    print(f"  parsing ZIP ({len(zip_bytes)} bytes)…", flush=True)

    rows = []
    scanned = 0
    for _, line in iter_dat_lines(zip_bytes):
        if not line.startswith("B;"):
            continue
        scanned += 1
        r = parse_b_record(line, source)
        if r:
            rows.append(r)

    # Dedupe within this file (rare but defensive)
    by_key = {}
    for r in rows:
        by_key[(r["source"], r["dealing_number"])] = r
    rows = list(by_key.values())

    print(f"  B records scanned: {scanned}, SSC rows kept: {len(rows)}",
          flush=True)
    if not rows:
        return {"url": url, "scanned_B": scanned, "ssc_rows": 0,
                "upsert_ok_batches": 0, "upsert_fail_batches": 0}

    ok, fail = upsert(rows)
    return {"url": url, "scanned_B": scanned, "ssc_rows": len(rows),
            "upsert_ok_batches": ok, "upsert_fail_batches": fail}


def latest_sunday_yyyymmdd() -> str:
    today = date.today()
    days_back = (today.weekday() - 6) % 7  # Mon=0 … Sun=6
    if days_back == 0:
        days_back = 7  # use previous Sunday, not today, so the file exists
    sunday = today - timedelta(days=days_back)
    return sunday.strftime("%Y%m%d")


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
        ymd = latest_sunday_yyyymmdd()
        url = f"{VG_BASE}/weekly/{ymd}.zip"
        print(json.dumps(process_zip(url, "vg-weekly"), indent=2))
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
