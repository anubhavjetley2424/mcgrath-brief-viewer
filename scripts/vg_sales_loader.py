"""
NSW VG Property Sales Information loader — Sutherland Shire (district 144).

Downloads weekly bulk PSI ZIPs from valuergeneral.nsw.gov.au, extracts the
single 144_*.DAT file (Sutherland Shire), parses B-records, and bulk-upserts
into Supabase public.vg_sales.

Usage:
    python vg_sales_loader.py 20260406                # load one week
    python vg_sales_loader.py 20240101 20260525       # backfill date range
                                                       # (every Monday in range)

NSW VG 2002 PSI B-record format (semicolon-delimited):
    B;DistrictCode;PropertyId;SaleCounter;DownloadDateTime;PropertyName;
      UnitNumber;HouseNumber;StreetName;Locality;Postcode;Area;AreaType;
      ContractDate;SettlementDate;PurchasePrice;Zoning;NatureOfProperty;
      PrimaryPurpose;StrataLotNumber;ComponentCode;SalesCode;
      PercentageInterestOfSale;DealingNumber
"""

import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

DISTRICT_CODE = "144"  # Sutherland Shire LGA
VG_WEEKLY_URL = "https://www.valuergeneral.nsw.gov.au/__psi/weekly/{date}.zip"

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)
UPSERT_URL = (
    f"{SUPABASE_URL}/rest/v1/vg_sales"
    "?on_conflict=property_id,contract_date,purchase_price,sale_counter"
)

BATCH_SIZE = 200
HTTP_TIMEOUT = 60
REQUEST_DELAY_SEC = 0.3  # polite throttle between weekly downloads


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------

def parse_vg_date(s: str):
    """YYYYMMDD → 'YYYY-MM-DD' or None."""
    if not s or len(s) != 8 or not s.isdigit():
        return None
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def parse_num(s: str):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_dat_b_records(dat_text: str, source_file: str):
    """Yield row dicts for B-records (sales) in this district's DAT file."""
    for line in dat_text.splitlines():
        if not line or line[0] != "B":
            continue
        f = line.split(";")
        # Defensive: spec is 23+ fields after the B, but trailing semicolons vary
        if len(f) < 16:
            continue

        property_id = f[2].strip() if len(f) > 2 else ""
        purchase_price = parse_num(f[15]) if len(f) > 15 else None
        contract_date = parse_vg_date(f[13]) if len(f) > 13 else None

        if not property_id or purchase_price is None:
            continue

        sale_counter_raw = f[3] if len(f) > 3 else ""
        try:
            sale_counter = int(sale_counter_raw) if sale_counter_raw else None
        except ValueError:
            sale_counter = None

        yield {
            "property_id": property_id,
            "district_code": f[1],
            "sale_counter": sale_counter,
            "unit_number": (f[6] or None) if len(f) > 6 else None,
            "house_number": (f[7] or None) if len(f) > 7 else None,
            "street_name": (f[8] or None) if len(f) > 8 else None,
            "suburb": (f[9].strip() if len(f) > 9 and f[9] else "UNKNOWN"),
            "postcode": (f[10] or None) if len(f) > 10 else None,
            "contract_date": contract_date,
            "settlement_date": parse_vg_date(f[14]) if len(f) > 14 else None,
            "purchase_price": purchase_price,
            "land_area_sqm": parse_num(f[11]) if len(f) > 11 else None,
            "area_type": (f[12] or None) if len(f) > 12 else None,
            "property_type": (f[17] or None) if len(f) > 17 else None,
            "zone_code": (f[16] or None) if len(f) > 16 else None,
            "source_file": source_file,
        }


# ----------------------------------------------------------------------------
# IO
# ----------------------------------------------------------------------------

def download_weekly_zip(yyyymmdd: str) -> bytes:
    url = VG_WEEKLY_URL.format(date=yyyymmdd)
    req = urllib.request.Request(url, headers={"User-Agent": "vg-sales-loader/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def extract_district_dat(zip_bytes: bytes, district: str) -> str | None:
    """Return the text content of the DAT file for the given district, or None
    if this week's bundle doesn't include that district (no sales that week)."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        prefix = f"{district}_SALES_DATA"
        for name in z.namelist():
            if name.startswith(prefix):
                with z.open(name) as f:
                    return f.read().decode("utf-8", errors="replace")
    return None


def upsert_batch(rows: list[dict]) -> tuple[bool, str]:
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

def mondays_between(start_yyyymmdd: str, end_yyyymmdd: str):
    start = datetime.strptime(start_yyyymmdd, "%Y%m%d").date()
    end = datetime.strptime(end_yyyymmdd, "%Y%m%d").date()
    # Align to Monday on or after start
    d = start + timedelta(days=(0 - start.weekday()) % 7)
    while d <= end:
        yield d.strftime("%Y%m%d")
        d += timedelta(days=7)


def load_one_week(yyyymmdd: str) -> dict:
    source_file = f"{yyyymmdd}.zip"
    try:
        zip_bytes = download_weekly_zip(yyyymmdd)
    except urllib.error.HTTPError as e:
        return {"date": yyyymmdd, "ok": False, "reason": f"download {e.code}"}
    except Exception as e:
        return {"date": yyyymmdd, "ok": False, "reason": f"download {type(e).__name__}: {e}"}

    dat = extract_district_dat(zip_bytes, DISTRICT_CODE)
    if dat is None:
        return {"date": yyyymmdd, "ok": True, "rows": 0, "note": "no district-144 file"}

    rows = list(parse_dat_b_records(dat, source_file))
    if not rows:
        return {"date": yyyymmdd, "ok": True, "rows": 0, "note": "parsed but no rows"}

    inserted = 0
    failures = []
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        ok, msg = upsert_batch(chunk)
        if ok:
            inserted += len(chunk)
        else:
            failures.append({"batch_start": i, "err": msg})

    return {
        "date": yyyymmdd,
        "ok": not failures,
        "rows": inserted,
        "failures": failures,
    }


def main():
    if len(sys.argv) == 2:
        result = load_one_week(sys.argv[1])
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["ok"] else 1)

    if len(sys.argv) == 3:
        start, end = sys.argv[1], sys.argv[2]
        dates = list(mondays_between(start, end))
        print(f"# Backfilling {len(dates)} weekly files from {start} to {end}", flush=True)
        totals = {"weeks_ok": 0, "weeks_failed": 0, "rows": 0}
        for i, d in enumerate(dates, 1):
            r = load_one_week(d)
            print(
                f"[{i}/{len(dates)}] {d}  "
                f"rows={r.get('rows', 0):>5}  "
                f"{'OK' if r['ok'] else 'FAIL ' + r.get('reason', '')}"
                f"{' (' + r['note'] + ')' if r.get('note') else ''}",
                flush=True,
            )
            if r["ok"]:
                totals["weeks_ok"] += 1
                totals["rows"] += r.get("rows", 0)
            else:
                totals["weeks_failed"] += 1
            time.sleep(REQUEST_DELAY_SEC)
        print("---")
        print(json.dumps(totals, indent=2))
        sys.exit(0 if totals["weeks_failed"] == 0 else 1)

    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
