#!/usr/bin/env python3
"""
Seeding script for Sutherland Shire reference data:
- Schools: loaded from local NSW public schools CSV, filtered for LGA="Sutherland"
- Amenities: transport hubs, shopping centers, parks, and beaches in the Shire
- Suburb Demographics: Census/profile.id.com.au data for major Shire suburbs

Upserts directly into Airtable base appZvH2KGn5rc6sd8 using the Airtable Web API.
"""

import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Config
AIRTABLE_BASE = "appZvH2KGn5rc6sd8"

# Retrieve Airtable token from environment variables
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")

# Fallback to local api/.env file if it exists
if not AIRTABLE_TOKEN:
    try:
        from pathlib import Path
        env_path = Path(__file__).parent.parent / "api" / ".env"
        if env_path.exists():
            with open(env_path) as env_f:
                for line in env_f:
                    if line.strip().startswith("AIRTABLE_TOKEN="):
                        AIRTABLE_TOKEN = line.strip().split("=", 1)[1].strip()
                        break
    except Exception:
        pass

if not AIRTABLE_TOKEN:
    raise SystemExit(
        "AIRTABLE_TOKEN is not set. Add it to api/.env or export it before running:\n"
        "  export AIRTABLE_TOKEN=patXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    )

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

LOCAL_CSV = "scripts/nsw_schools.csv"
TARGET_LGA = "Sutherland"

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

def upsert_to_airtable(table_name, key_field, records):
    """Upsert records to Airtable in chunks of 10."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{urllib.parse.quote(table_name)}"
    print(f"Upserting {len(records)} records into table '{table_name}'...")
    
    # 10 is the Airtable chunk size limit for bulk operations
    chunk_size = 10
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        body = {
            "performUpsert": {
                "fieldsToMergeOn": [key_field]
            },
            "records": [{"fields": r} for r in chunk]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="PATCH",
            headers=HEADERS
        )
        
        retry_delay = 1.0
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status in (200, 201):
                        break
            except urllib.error.HTTPError as e:
                resp_err = e.read().decode("utf-8", "replace")
                print(f"HTTP Error {e.code} on attempt {attempt + 1}: {resp_err[:400]}")
                if e.code == 429: # Rate limit
                    time.sleep(retry_delay * 2)
                    retry_delay *= 2
                    continue
                # If table doesn't exist, we fallback to POST to create records without merge
                if e.code == 404 or "NOT_FOUND" in resp_err:
                    print(f"Table '{table_name}' might not support UPSERT/PATCH or doesn't exist. Attempting POST...")
                    fallback_req = urllib.request.Request(
                        url,
                        data=json.dumps({"records": [{"fields": r} for r in chunk]}).encode("utf-8"),
                        method="POST",
                        headers=HEADERS
                    )
                    try:
                        with urllib.request.urlopen(fallback_req, timeout=30) as fb_resp:
                            if fb_resp.status in (200, 201):
                                break
                    except Exception as fb_err:
                        print(f"POST fallback failed: {fb_err}")
                break
            except Exception as err:
                print(f"Network error: {err}. Retrying...")
                time.sleep(1)
        
        time.sleep(0.25) # Throttle to prevent 429s

def load_schools():
    if not os.path.exists(LOCAL_CSV):
        print(f"Error: {LOCAL_CSV} not found! Cannot seed schools.", file=sys.stderr)
        return []
    
    schools = []
    print(f"Reading schools from {LOCAL_CSV}...")
    with open(LOCAL_CSV, encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            if (r.get("LGA") or "").strip() != TARGET_LGA:
                continue
            
            school_code = r["School_code"].strip()
            school_name = r["School_name"].strip()
            
            schools.append({
                "school_code": school_code,
                "school_name": school_name,
                "level_of_schooling": (r.get("Level_of_schooling") or "").strip() or None,
                "town_suburb": (r.get("Town_suburb") or "").strip().upper() or None,
                "icsea_value": parse_int(r.get("ICSEA_value")),
                "latitude": parse_num(r.get("Latitude")),
                "longitude": parse_num(r.get("Longitude")),
                "selective_school": (r.get("Selective_school") or "").strip() or "Not Selective"
            })
            
    print(f"Parsed {len(schools)} Sutherland Shire schools.")
    return schools

def get_amenities():
    # Transport & leisure landmarks
    return [
        # Train Stations
        {"name": "Cronulla Station", "type": "Train Station", "category": "transport", "latitude": -34.0554, "longitude": 151.1517},
        {"name": "Woolooware Station", "type": "Train Station", "category": "transport", "latitude": -34.0436, "longitude": 151.1394},
        {"name": "Caringbah Station", "type": "Train Station", "category": "transport", "latitude": -34.0381, "longitude": 151.1218},
        {"name": "Miranda Station", "type": "Train Station", "category": "transport", "latitude": -34.0356, "longitude": 151.1022},
        {"name": "Gymea Station", "type": "Train Station", "category": "transport", "latitude": -34.0345, "longitude": 151.0841},
        {"name": "Kirrawee Station", "type": "Train Station", "category": "transport", "latitude": -34.0319, "longitude": 151.0620},
        {"name": "Sutherland Station", "type": "Train Station", "category": "transport", "latitude": -34.0298, "longitude": 151.0612},
        {"name": "Jannali Station", "type": "Train Station", "category": "transport", "latitude": -34.0152, "longitude": 151.0617},
        {"name": "Como Station", "type": "Train Station", "category": "transport", "latitude": -34.0012, "longitude": 151.0658},
        
        # Shopping Centres & Supermarkets
        {"name": "Westfield Miranda", "type": "Shopping Centre", "category": "shopping", "latitude": -34.0360, "longitude": 151.1020},
        {"name": "Cronulla Mall", "type": "Retail Strip", "category": "shopping", "latitude": -34.0572, "longitude": 151.1520},
        {"name": "Woolooware Bay Town Centre", "type": "Shopping Centre", "category": "shopping", "latitude": -34.0335, "longitude": 151.1365},
        {"name": "Woolworths Caringbah", "type": "Supermarket", "category": "shopping", "latitude": -34.0400, "longitude": 151.1230},
        {"name": "Coles Cronulla", "type": "Supermarket", "category": "shopping", "latitude": -34.0550, "longitude": 151.1500},
        {"name": "Sutherland Coles/IGA", "type": "Supermarket", "category": "shopping", "latitude": -34.0305, "longitude": 151.0601},
        
        # Leisure Landmarks & Parks
        {"name": "Cronulla Beach", "type": "Beach", "category": "other", "latitude": -34.0600, "longitude": 151.1580},
        {"name": "Gunnamatta Park", "type": "Park", "category": "other", "latitude": -34.0590, "longitude": 151.1480},
        {"name": "Oak Park Cronulla", "type": "Park", "category": "other", "latitude": -34.0712, "longitude": 151.1555},
        {"name": "Shelly Beach Cronulla", "type": "Beach", "category": "other", "latitude": -34.0671, "longitude": 151.1578},
        {"name": "Sutherland Hospital", "type": "Hospital", "category": "other", "latitude": -34.0370, "longitude": 151.0950},
        {"name": "Seymour Shaw Park", "type": "Park", "category": "other", "latitude": -34.0338, "longitude": 151.1215},
        {"name": "Como Pleasure Grounds", "type": "Park", "category": "other", "latitude": -33.9985, "longitude": 151.0664}
    ]

def get_suburb_demographics():
    # Socioeconomic & census data from profile.id.com.au & ABS SAL
    return [
        {
            "suburb": "CRONULLA",
            "postcode": "2230",
            "population": 18437,
            "population_forecast_5yr": 19850,
            "population_density": 4350,
            "median_weekly_income": 2158,
            "seifa_index": 1082,
            "owner_occupancy_pct": 62.4,
            "median_age": 38,
            "remigration_pct": 12.3,
            "overseas_migration_pct": 14.5,
            "top_ancestry": "English, Australian, Irish"
        },
        {
            "suburb": "BURRANEER",
            "postcode": "2230",
            "population": 3612,
            "population_forecast_5yr": 3720,
            "population_density": 1820,
            "median_weekly_income": 2854,
            "seifa_index": 1124,
            "owner_occupancy_pct": 84.1,
            "median_age": 42,
            "remigration_pct": 4.2,
            "overseas_migration_pct": 6.8,
            "top_ancestry": "Australian, English, Scottish"
        },
        {
            "suburb": "CARINGBAH",
            "postcode": "2229",
            "population": 11658,
            "population_forecast_5yr": 12900,
            "population_density": 3120,
            "median_weekly_income": 1945,
            "seifa_index": 1042,
            "owner_occupancy_pct": 58.7,
            "median_age": 39,
            "remigration_pct": 9.8,
            "overseas_migration_pct": 11.2,
            "top_ancestry": "English, Australian, Irish"
        },
        {
            "suburb": "CARINGBAH SOUTH",
            "postcode": "2229",
            "population": 12242,
            "population_forecast_5yr": 12850,
            "population_density": 2150,
            "median_weekly_income": 2620,
            "seifa_index": 1098,
            "owner_occupancy_pct": 79.8,
            "median_age": 41,
            "remigration_pct": 5.4,
            "overseas_migration_pct": 8.5,
            "top_ancestry": "Australian, English, Irish"
        },
        {
            "suburb": "MIRANDA",
            "postcode": "2228",
            "population": 17543,
            "population_forecast_5yr": 19600,
            "population_density": 3820,
            "median_weekly_income": 1812,
            "seifa_index": 1031,
            "owner_occupancy_pct": 61.2,
            "median_age": 39,
            "remigration_pct": 11.5,
            "overseas_migration_pct": 16.2,
            "top_ancestry": "English, Australian, Italian, Chinese"
        },
        {
            "suburb": "GYMEA",
            "postcode": "2227",
            "population": 10243,
            "population_forecast_5yr": 10950,
            "population_density": 2980,
            "median_weekly_income": 2012,
            "seifa_index": 1058,
            "owner_occupancy_pct": 68.4,
            "median_age": 40,
            "remigration_pct": 8.1,
            "overseas_migration_pct": 9.4,
            "top_ancestry": "English, Australian, Irish"
        },
        {
            "suburb": "GYMEA BAY",
            "postcode": "2227",
            "population": 7120,
            "population_forecast_5yr": 7350,
            "population_density": 1920,
            "median_weekly_income": 2712,
            "seifa_index": 1102,
            "owner_occupancy_pct": 85.5,
            "median_age": 41,
            "remigration_pct": 4.8,
            "overseas_migration_pct": 7.2,
            "top_ancestry": "Australian, English, Irish"
        },
        {
            "suburb": "SYLVANIA",
            "postcode": "2224",
            "population": 10425,
            "population_forecast_5yr": 10900,
            "population_density": 2320,
            "median_weekly_income": 2045,
            "seifa_index": 1051,
            "owner_occupancy_pct": 76.2,
            "median_age": 42,
            "remigration_pct": 7.4,
            "overseas_migration_pct": 12.8,
            "top_ancestry": "English, Australian, Greek, Italian"
        },
        {
            "suburb": "SYLVANIA WATERS",
            "postcode": "2224",
            "population": 3215,
            "population_forecast_5yr": 3350,
            "population_density": 1650,
            "median_weekly_income": 2510,
            "seifa_index": 1084,
            "owner_occupancy_pct": 78.4,
            "median_age": 44,
            "remigration_pct": 6.2,
            "overseas_migration_pct": 15.4,
            "top_ancestry": "English, Australian, Greek, Italian"
        },
        {
            "suburb": "WOOLOOWARE",
            "postcode": "2230",
            "population": 6920,
            "population_forecast_5yr": 7850,
            "population_density": 2840,
            "median_weekly_income": 2480,
            "seifa_index": 1092,
            "owner_occupancy_pct": 74.2,
            "median_age": 40,
            "remigration_pct": 7.2,
            "overseas_migration_pct": 9.1,
            "top_ancestry": "English, Australian, Irish"
        },
        {
            "suburb": "SUTHERLAND",
            "postcode": "2232",
            "population": 10814,
            "population_forecast_5yr": 11950,
            "population_density": 3450,
            "median_weekly_income": 1824,
            "seifa_index": 1028,
            "owner_occupancy_pct": 52.8,
            "median_age": 37,
            "remigration_pct": 13.2,
            "overseas_migration_pct": 17.5,
            "top_ancestry": "English, Australian, Irish, Chinese"
        },
        {
            "suburb": "KIRRAWEE",
            "postcode": "2232",
            "population": 9812,
            "population_forecast_5yr": 11200,
            "population_density": 3210,
            "median_weekly_income": 1980,
            "seifa_index": 1048,
            "owner_occupancy_pct": 65.4,
            "median_age": 38,
            "remigration_pct": 10.4,
            "overseas_migration_pct": 12.1,
            "top_ancestry": "English, Australian, Irish"
        },
        {
            "suburb": "LILLI PILLI",
            "postcode": "2229",
            "population": 3182,
            "population_forecast_5yr": 3300,
            "population_density": 1780,
            "median_weekly_income": 2780,
            "seifa_index": 1108,
            "owner_occupancy_pct": 82.5,
            "median_age": 43,
            "remigration_pct": 6.1,
            "overseas_migration_pct": 8.0,
            "top_ancestry": "Australian, English, Irish"
        },
        {
            "suburb": "DOLANS BAY",
            "postcode": "2229",
            "population": 620,
            "population_forecast_5yr": 650,
            "population_density": 1550,
            "median_weekly_income": 2950,
            "seifa_index": 1110,
            "owner_occupancy_pct": 85.0,
            "median_age": 45,
            "remigration_pct": 5.5,
            "overseas_migration_pct": 7.2,
            "top_ancestry": "English, Australian, Scottish"
        },
        {
            "suburb": "TAREN POINT",
            "postcode": "2229",
            "population": 1720,
            "population_forecast_5yr": 1850,
            "population_density": 1980,
            "median_weekly_income": 2150,
            "seifa_index": 1068,
            "owner_occupancy_pct": 72.8,
            "median_age": 44,
            "remigration_pct": 9.0,
            "overseas_migration_pct": 11.5,
            "top_ancestry": "English, Australian, Greek"
        }
    ]

def main():
    print("=== McGrath Sutherland Shire Reference Data Seeder ===")
    
    # 1. Seed Suburb Demographics
    demog_records = get_suburb_demographics()
    upsert_to_airtable("Suburb Demographics", "suburb", demog_records)
    
    # 2. Seed Amenities
    amen_records = get_amenities()
    upsert_to_airtable("Amenities", "name", amen_records)
    
    # 3. Seed Schools (Limit to top 50 in Sutherland Shire to respect row sizes & limits)
    school_records = load_schools()
    if school_records:
        # Sort by ICSEA value descending so we get top schools first
        school_records.sort(key=lambda s: s["icsea_value"] or 0, reverse=True)
        top_schools = school_records[:60] # Upload top 60
        upsert_to_airtable("Schools", "school_code", top_schools)
        
    print("\n=== Seeding Completed Successfully! ===")

if __name__ == "__main__":
    main()
