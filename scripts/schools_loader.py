"""
One-shot loader for NSW Education public-schools master dataset → public.schools.

Filters to Sutherland Shire LGA only (V1 scope). Re-run is idempotent
(upsert on school_code).
"""

import csv
import json
import sys
import urllib.error
import urllib.request

CSV_URL = (
    "https://data.nsw.gov.au/data/dataset/78c10ea3-8d04-4c9c-b255-bbf8547e37e7/"
    "resource/3e6d5f6a-055c-440d-a690-fc0537c31095/download/master_dataset.csv"
)
LOCAL_CSV = "scripts/nsw_schools.csv"

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "Inh6YXprcnVkcmdrY2Zjem5rZWhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2NTg0Nz"
    "ksImV4cCI6MjA5NDIzNDQ3OX0.VN3bJoTI2nXJ4QJh-aBQaIWCPVMQJ7_PdICaetmxawo"
)
UPSERT_URL = f"{SUPABASE_URL}/rest/v1/schools?on_conflict=school_code"

TARGET_LGA = "Sutherland"  # exact value used in the master dataset's LGA column


def parse_num(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_int(s):
    if s is None or s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def main():
    rows_out = []
    with open(LOCAL_CSV, encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            if (r.get("LGA") or "").strip() != TARGET_LGA:
                continue
            rows_out.append({
                "school_code":      r["School_code"].strip(),
                "school_name":      r["School_name"].strip(),
                "street":           (r.get("Street") or "").strip() or None,
                "town_suburb":      (r.get("Town_suburb") or "").strip() or None,
                "postcode":         (r.get("Postcode") or "").strip() or None,
                "phone":            (r.get("Phone") or "").strip() or None,
                "website":          (r.get("Website") or "").strip() or None,
                "lga":              r["LGA"].strip(),
                "level_of_schooling": (r.get("Level_of_schooling") or "").strip() or None,
                "school_subtype":   (r.get("School_subtype") or "").strip() or None,
                "school_gender":    (r.get("School_gender") or "").strip() or None,
                "selective_school": (r.get("Selective_school") or "").strip() or None,
                "opportunity_class": (r.get("Opportunity_class") or "").strip() or None,
                "icsea_value":      parse_int(r.get("ICSEA_value")),
                "enrolment_fte":    parse_int(r.get("latest_year_enrolment_FTE")),
                "indigenous_pct":   parse_num(r.get("Indigenous_pct")),
                "lbote_pct":        parse_num(r.get("LBOTE_pct")),
                "foei_value":       parse_num(r.get("FOEI_Value")),
                "latitude":         parse_num(r.get("Latitude")),
                "longitude":        parse_num(r.get("Longitude")),
                "source":           "data.nsw.gov.au/master_dataset.csv",
            })

    print(f"Loaded {len(rows_out)} {TARGET_LGA} schools from CSV")

    # Upsert in batches
    body = json.dumps(rows_out).encode("utf-8")
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(f"Upsert OK: {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"FAIL: HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
