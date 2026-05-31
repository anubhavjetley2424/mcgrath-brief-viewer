#!/usr/bin/env python3
"""
McGrath Reference Data Acquisition Engine:
Autonomously connects to open government APIs and REST feeds:
1. NSW Government Public Schools Master Dataset (CKAN REST API)
2. OpenStreetMap Overpass Interpreter REST API (Geographic bounding box for Sutherland Shire)
Extracts and immediately batch upserts active live schools and transport/leisure amenities
directly into your Airtable tables ("Schools" and "Amenities").
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

# 1. Config & Airtable Creds
AIRTABLE_BASE = "appZvH2KGn5rc6sd8"
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")

# Fallback to local api/.env
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

def parse_num(s):
    if s is None or s == "": return None
    try: return float(s)
    except ValueError: return None

def parse_int(s):
    if s is None or s == "": return None
    try: return int(float(s))
    except ValueError: return None

def upsert_to_airtable(table_name, key_field, records):
    """Upsert records into Airtable Base using batch merge in chunks of 10."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{urllib.parse.quote(table_name)}"
    print(f"Upserting {len(records)} records into Airtable table '{table_name}'...")
    
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
        
        success = False
        last_error = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status in (200, 201):
                        success = True
                        break
            except urllib.error.HTTPError as e:
                last_error = f"HTTP Error {e.code}: {e.reason}"
                if e.code == 401:
                    print("\n[ERROR] Airtable API returned 401 Unauthorized.")
                    print("  -> The token used by the seeder is invalid or has expired.")
                    print("  -> Please set your active, valid Airtable PAT inside your local 'api/.env' file:")
                    print("     AIRTABLE_TOKEN=patYourRealTokenHere...")
                    sys.exit(1)
                time.sleep(1)
            except Exception as e:
                last_error = str(e)
                time.sleep(1)
        if not success:
            print(f"\n[ERROR] Failed to upsert chunk to Airtable. Last error: {last_error}", file=sys.stderr)
            sys.exit(1)
        time.sleep(0.25)

def fetch_live_schools():
    """Acquires schools autonomously via the live NSW Department of Education CKAN API."""
    print("Connecting to live NSW Department of Education CKAN API...")
    resource_id = "3e6d5f6a-055c-440d-a690-fc0537c31095" # Public Schools Master Dataset
    url = f"https://data.nsw.gov.au/data/api/3/action/datastore_search?resource_id={resource_id}&q=Sutherland&limit=150"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "McGrathRefAcquisition/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            records = data.get("result", {}).get("records", [])
            print(f"Successfully retrieved {len(records)} live school records.")
            
            schools = []
            for r in records:
                # Filter specifically for schools within Sutherland Shire LGA on the client side
                if (r.get("LGA") or "").strip().lower() != "sutherland":
                    continue
                
                school_code = str(r.get("School_code") or "").strip()
                school_name = (r.get("School_name") or "").strip()
                level_of_schooling = (r.get("Level_of_schooling") or "").strip() or None
                town_suburb = (r.get("Town_suburb") or "").strip().upper() or None
                selective_school = (r.get("Selective_school") or "").strip() or "Not Selective"
                
                schools.append({
                    "school_code": school_code,
                    "school_name": school_name,
                    "level_of_schooling": level_of_schooling,
                    "town_suburb": town_suburb,
                    "icsea_value": parse_int(r.get("ICSEA_value")),
                    "latitude": parse_num(r.get("Latitude")),
                    "longitude": parse_num(r.get("Longitude")),
                    "selective_school": selective_school
                })
            
            print(f"Isolated {len(schools)} schools inside the Sutherland Shire LGA boundary.")
            # Sort by ICSEA value descending
            schools.sort(key=lambda s: s["icsea_value"] or 0, reverse=True)
            return schools
    except Exception as e:
        print(f"Error fetching live schools from NSW Gov API: {e}", file=sys.stderr)
        return []

def fetch_live_amenities():
    """Acquires train stations, beaches, malls, and parks autonomously via OSM Overpass API."""
    print("Connecting to live OpenStreetMap Overpass Interpreter API...")
    bbox = "-34.12,151.00,-33.98,151.18" # Bounding box covering the Sutherland Shire
    
    # Overpass QL query targeting train stations, beaches, parks, and major retail centers
    query = f"""
    [out:json][timeout:25];
    (
      node["railway"="station"]({bbox});
      node["natural"="beach"]({bbox});
      node["shop"="mall"]({bbox});
      node["leisure"="park"]({bbox});
    );
    out body;
    """
    url = "https://overpass-api.de/api/interpreter"
    data_bytes = urllib.parse.urlencode({"data": query}).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data_bytes, headers={"User-Agent": "McGrathRefAcquisition/0.1"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elements = data.get("elements", [])
            print(f"Successfully retrieved {len(elements)} live geographical points from OSM.")
            
            amenities = []
            for elem in elements:
                tags = elem.get("tags", {})
                name = tags.get("name", "").strip()
                if not name: continue
                
                # Exclude duplicate entries or unnamed parks
                if "Unnamed" in name or "Park" not in name and "leisure" in tags and tags["leisure"] == "park":
                    continue
                
                # Determine standard category and type
                category = "other"
                itype = "Leisure"
                
                if "railway" in tags and tags["railway"] == "station":
                    category = "transport"
                    itype = "Train Station"
                elif "natural" in tags and tags["natural"] == "beach":
                    category = "other"
                    itype = "Beach"
                elif "shop" in tags and tags["shop"] == "mall":
                    category = "shopping"
                    itype = "Shopping Centre"
                elif "leisure" in tags and tags["leisure"] == "park":
                    category = "other"
                    itype = "Park"
                
                amenities.append({
                    "name": name,
                    "type": itype,
                    "category": category,
                    "latitude": elem.get("lat"),
                    "longitude": elem.get("lon")
                })
            
            # Deduplicate on name
            seen_names = set()
            deduped = []
            for a in amenities:
                if a["name"] not in seen_names:
                    seen_names.add(a["name"])
                    deduped.append(a)
            
            print(f"Isolated and deduplicated {len(deduped)} prominent amenities in the Shire.")
            return deduped
    except Exception as e:
        print(f"Error fetching live amenities from OSM Overpass API: {e}", file=sys.stderr)
        return []

def main():
    print("=== PROGRAMMATIC REFERENCE DATA ACQUISITION & AIRTABLE SYNC ===")
    
    # 1. Fetch and Sync Schools
    schools = fetch_live_schools()
    if schools:
        # Upsert top 60 high-performance schools to keep Base lightweight
        upsert_to_airtable("Schools", "school_code", schools[:60])
        
    # 2. Fetch and Sync Amenities
    amenities = fetch_live_amenities()
    if amenities:
        upsert_to_airtable("Amenities", "name", amenities[:50])
        
    print("\n[OK] Reference data synchronization completed!")

if __name__ == "__main__":
    main()
