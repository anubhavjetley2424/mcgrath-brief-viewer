import os
import re
import sys
import json
import urllib.request
import urllib.parse
import time
import zlib
from datetime import datetime
from pathlib import Path

# Add scrapers folder to python path
SCRAPERS_DIR = Path(__file__).resolve().parent.parent / "Appraisal Dashboard Scrapers"
sys.path.append(str(SCRAPERS_DIR))

import mcgrath_sales
import mcgrath_listings
import belle_sales
import raywhite_sales
import backfill_ra_images
from property_filter import is_single_dwelling
from belle_sales import AARON_SUBURBS
from raywhite_sales import AARON_OFFICES, AARON_SUBURB_ALLOWLIST

SUPABASE_URL = "https://xzazkrudrgkcfcznkehb.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_KEY:
    print("SUPABASE_SERVICE_ROLE_KEY env var is not set.", file=sys.stderr)
    sys.exit(1)

def get_table_columns(table_name):
    """Retrieve actual table columns from Supabase OpenAPI schema.
    Ensures script only sends fields that exist in the database."""
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
            props = data.get("definitions", {}).get(table_name, {}).get("properties", {})
            if props:
                return list(props.keys())
    except Exception as e:
        print(f"Error fetching schema for {table_name}: {e}", file=sys.stderr)
    
    # Fallback to standard columns if OpenAPI lookup fails
    if table_name == "domain_listings_active":
        return ['domain_listing_id', 'url', 'street', 'suburb', 'state', 'postcode', 'lat', 'lng', 'price_text', 'beds', 'baths', 'parking', 'land_size_sqm', 'property_type', 'property_type_formatted', 'agency_name', 'source_search', 'scraped_at']
    else:
        return ['domain_listing_id', 'url', 'street', 'suburb', 'state', 'postcode', 'lat', 'lng', 'sold_price', 'sold_price_text', 'sold_date', 'beds', 'baths', 'parking', 'land_size_sqm', 'property_type', 'property_type_formatted', 'agency_name', 'source_search', 'scraped_at']

def get_existing_ids(table_name):
    """Fetch existing listing IDs from Supabase to prevent duplicate geocoding."""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=domain_listing_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            res = json.loads(r.read().decode("utf-8"))
            return {int(item["domain_listing_id"]) for item in res if "domain_listing_id" in item}
    except Exception as e:
        print(f"Error fetching existing IDs for {table_name}: {e}", file=sys.stderr)
    return set()

def geocode(address, suburb):
    """Geocode address using OpenStreetMap Nominatim API, respecting rate limits."""
    query = f"{address}, {suburb}, NSW, Australia"
    enc_query = urllib.parse.quote(query)
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=au&q={enc_query}"
    headers = {
        "User-Agent": "McGrathAppraisalBriefBot/0.1 (anubhav.jetley123@gmail.com)"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        print(f"  Geocoding: {query}...", end="", flush=True)
        time.sleep(1.0)  # nominatim rate limit compliant (1s delay)
        with urllib.request.urlopen(req, timeout=10) as r:
            res = json.loads(r.read().decode("utf-8"))
            if res and isinstance(res, list):
                lat = float(res[0]["lat"])
                lng = float(res[0]["lon"])
                print(f" success ({lat:.5f}, {lng:.5f})")
                return lat, lng
            print(" no match")
    except Exception as e:
        print(f" error ({e})")
    return None, None

def get_numeric_id(scraped_id_str):
    """Produce a unique integer ID. Uses CRC32 hash for alphanumeric IDs (like McGrath)."""
    if not scraped_id_str:
        return 0
    clean_id = re.sub(r'[^a-zA-Z0-9]', '', str(scraped_id_str))
    if clean_id.isdigit():
        return int(clean_id)
    return zlib.crc32(clean_id.encode('utf-8'))

def upsert_to_supabase(table, key_field, records):
    """Upsert records into Supabase PostgREST table."""
    if not records:
        print(f"No records to upsert to {table}.")
        return
    
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={key_field}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    # PostgREST batching
    chunk_size = 50
    for idx in range(0, len(records), chunk_size):
        chunk = records[idx:idx+chunk_size]
        req = urllib.request.Request(
            url,
            data=json.dumps(chunk).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                print(f"Upserted {len(chunk)} records into {table} (chunk {idx//chunk_size + 1}).")
        except Exception as e:
            print(f"Error upserting chunk to {table}: {e}", file=sys.stderr)
            # Try to print server response details if possible
            if hasattr(e, 'read'):
                try:
                    print("Server response:", e.read().decode(), file=sys.stderr)
                except Exception:
                    pass

# McGrath/Belle fetches only cost ScraperAPI credits when SCRAPER_PROXY_URL is
# set (i.e. this run can't reach them directly — see mcgrath_sales.py). Keep
# per-run volume low enough that ~10 runs/month stays well under the 1,000
# free-plan monthly credit cap. When running unproxied (a direct connection
# works — e.g. from a residential/ISP IP), there's no credit cost, so scrape
# at full depth.
MAX_PROPS = 15 if os.environ.get("SCRAPER_PROXY_URL") else 30


def main():
    print("====================================================")
    print("Starting McGrath, Belle, and Ray White Scrape & Sync")
    print("====================================================")

    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)

    # 1. Fetch McGrath listings (sold + live for-sale)
    print("\n--- Crawling McGrath (Sold Sitemap) ---")
    try:
        mcgrath_props = mcgrath_sales.crawl(AARON_SUBURBS, max_props=MAX_PROPS)
    except Exception as e:
        print(f"Error in McGrath crawl: {e}", file=sys.stderr)
        mcgrath_props = []

    print("\n--- Crawling McGrath (Buy/Live Sitemap) ---")
    try:
        mcgrath_live_props = mcgrath_listings.crawl(AARON_SUBURBS, max_props=MAX_PROPS)
    except Exception as e:
        print(f"Error in McGrath live-listing crawl: {e}", file=sys.stderr)
        mcgrath_live_props = []
    mcgrath_props = mcgrath_props + mcgrath_live_props

    # Write raw McGrath JSON to disk for image backfilling
    mcgrath_out = {"summary": {"sold_properties": len(mcgrath_props)}, "properties": mcgrath_props}
    Path("data/mcgrath_sales.json").write_text(json.dumps(mcgrath_out, indent=2, default=str), encoding="utf-8")

    # 2. Fetch Belle listings
    print("\n--- Crawling Belle (Active & Sold) ---")
    try:
        belle_props = belle_sales.crawl(AARON_SUBURBS, max_props=MAX_PROPS)
    except Exception as e:
        print(f"Error in Belle crawl: {e}", file=sys.stderr)
        belle_props = []

    belle_out = {"summary": {"listings": len(belle_props)}, "properties": belle_props}
    Path("data/belle_sales.json").write_text(json.dumps(belle_out, indent=2, default=str), encoding="utf-8")

    # 3. Fetch Ray White listings (sold + live for-sale)
    print("\n--- Crawling Ray White (Target Offices, Sold) ---")
    raywhite_props = []
    for idx, office in enumerate(AARON_OFFICES, 1):
        try:
            # Crawl up to 5 properties per office to stay fast and avoid rate limits
            props = raywhite_sales.crawl_office(office, max_pages=1, max_per_office=5)
            raywhite_props.extend(props)
            print(f"  [{idx}/{len(AARON_OFFICES)}] Scraped {len(props)} sold properties from Ray White {office}")
        except Exception as e:
            print(f"  [{idx}/{len(AARON_OFFICES)}] Error scraping Ray White {office}: {e}", file=sys.stderr)
        time.sleep(0.5)

    print("\n--- Crawling Ray White (Target Offices, Live For-Sale) ---")
    for idx, office in enumerate(AARON_OFFICES, 1):
        try:
            props = raywhite_sales.crawl_office_for_sale(office, max_pages=1, max_per_office=5)
            raywhite_props.extend(props)
            print(f"  [{idx}/{len(AARON_OFFICES)}] Scraped {len(props)} live listings from Ray White {office}")
        except Exception as e:
            print(f"  [{idx}/{len(AARON_OFFICES)}] Error scraping Ray White {office} live listings: {e}", file=sys.stderr)
        time.sleep(0.5)

    # Deduplicate and filter Ray White properties
    seen_rw = set()
    filtered_rw = []
    for p in raywhite_props:
        if p.get("url") in seen_rw:
            continue
        seen_rw.add(p["url"])
        sub = (p.get("suburb") or "").lower()
        if sub and sub not in AARON_SUBURB_ALLOWLIST:
            continue
        if not is_single_dwelling(p.get("property_type"), p.get("address")):
            continue
        filtered_rw.append(p)
        
    print(f"Ray White Total matched single dwellings: {len(filtered_rw)}")
    raywhite_out = {"summary": {"sold_properties": len(filtered_rw)}, "properties": filtered_rw}
    Path("data/raywhite_sales.json").write_text(json.dumps(raywhite_out, indent=2, default=str), encoding="utf-8")

    # 4. Programmatic image backfilling (full photo galleries)
    print("\n--- Backfilling Photo Galleries ---")
    for agency in ["mcgrath", "belle", "raywhite"]:
        try:
            backfill_ra_images.backfill(agency, max_n=30)
        except Exception as e:
            print(f"Error backfilling images for {agency}: {e}", file=sys.stderr)

    # 5. Read backfilled data from disk
    print("\n--- Loading Backfilled Properties ---")
    try:
        mcgrath_data = json.loads(Path("data/mcgrath_sales.json").read_text(encoding="utf-8")).get("properties", [])
    except Exception:
        mcgrath_data = []
        
    try:
        belle_data = json.loads(Path("data/belle_sales.json").read_text(encoding="utf-8")).get("properties", [])
    except Exception:
        belle_data = []
        
    try:
        raywhite_data = json.loads(Path("data/raywhite_sales.json").read_text(encoding="utf-8")).get("properties", [])
    except Exception:
        raywhite_data = []

    all_props = mcgrath_data + belle_data + raywhite_data
    print(f"Loaded {len(all_props)} total properties from scrapers.")

    # 6. Fetch existing database IDs to cache/skip geocoding
    print("\n--- Checking Existing Listings in Supabase ---")
    existing_active = get_existing_ids("domain_listings_active")
    existing_sold = get_existing_ids("domain_listings_sold")
    print(f"Found {len(existing_active)} active and {len(existing_sold)} sold listings already in Supabase.")

    # 7. Map properties and geocode if new
    print("\n--- Mapping and Geocoding New Properties ---")
    active_cols = get_table_columns("domain_listings_active")
    sold_cols = get_table_columns("domain_listings_sold")
    
    print(f"domain_listings_active columns: {active_cols}")
    print(f"domain_listings_sold columns: {sold_cols}")
    
    scraped_at = datetime.utcnow().isoformat() + "Z"
    
    mapped_active = []
    mapped_sold = []
    
    for idx, p in enumerate(all_props, 1):
        url = p.get("url", "")
        if not url:
            continue
            
        # Parse ID from URL tail
        tail_match = re.search(r'[-/]([A-Za-z0-9]+)$', url)
        scraped_id = tail_match.group(1) if tail_match else url
        num_id = get_numeric_id(scraped_id)
        
        status = (p.get("status") or "Sold").strip()
        is_sold = status.lower() == "sold"
        
        # Check if already exists in Supabase
        is_existing = num_id in existing_sold if is_sold else num_id in existing_active
        
        # Extract location details
        address = p.get("address") or p.get("street") or ""
        suburb = p.get("suburb") or ""
        
        # Geocode if new
        lat = p.get("lat")
        lng = p.get("lng")
        if (lat is None or lng is None) and not is_existing:
            if address and suburb:
                lat, lng = geocode(address, suburb)
        
        # Prepare photo gallery
        photos = p.get("images") or []
        if not photos and p.get("image_url"):
            photos = [p.get("image_url")]
            
        # Standardize record
        std_rec = {
            "domain_listing_id": num_id,
            "url": url,
            "street": address,
            "suburb": suburb.upper(),
            "state": p.get("state") or "NSW",
            "postcode": p.get("postcode") or "",
            "lat": lat,
            "lng": lng,
            "beds": p.get("bedrooms") or p.get("beds"),
            "baths": p.get("bathrooms") or p.get("baths"),
            "parking": p.get("car_spaces") or p.get("parking"),
            "land_size_sqm": p.get("land_size_sqm") or p.get("land_area"),
            "property_type": p.get("property_type") or "House",
            "property_type_formatted": p.get("property_type") or "House",
            "agency_name": p.get("agency") or p.get("agency_name"),
            "source_search": f"franchise_{p.get('agency', '').lower().replace(' ', '_')}",
            "scraped_at": scraped_at,
            "photos": photos,
            "floorplan_url": p.get("floorplan_url") or None
        }
        
        if is_sold:
            # Add sold-specific fields
            sold_price = None
            price_text = p.get("sold_price_text") or p.get("price_text") or ""
            if p.get("sold_price"):
                sold_price = float(p["sold_price"])
            elif price_text:
                clean_txt = price_text.replace(" ", "").replace(",", "")
                m_p = re.search(r'\$?([0-9]+)', clean_txt)
                if m_p:
                    sold_price = float(m_p.group(1))
            
            std_rec["sold_price"] = sold_price
            std_rec["sold_price_text"] = price_text or (f"${int(sold_price):,}" if sold_price else "Sold")
            std_rec["sold_date"] = p.get("sold_date") or scraped_at[:10]
            
            # Filter keys to match target columns in Supabase
            filtered_rec = {k: v for k, v in std_rec.items() if k in sold_cols}
            mapped_sold.append(filtered_rec)
        else:
            # Active listing
            std_rec["price_text"] = p.get("price_text") or "Contact Agent"
            
            filtered_rec = {k: v for k, v in std_rec.items() if k in active_cols}
            mapped_active.append(filtered_rec)

    # 8. Deduplicate records by domain_listing_id to avoid ON CONFLICT duplicate key errors in PostgREST batch calls
    unique_active = []
    seen_active = set()
    for item in mapped_active:
        if item["domain_listing_id"] not in seen_active:
            seen_active.add(item["domain_listing_id"])
            unique_active.append(item)
            
    unique_sold = []
    seen_sold = set()
    for item in mapped_sold:
        if item["domain_listing_id"] not in seen_sold:
            seen_sold.add(item["domain_listing_id"])
            unique_sold.append(item)

    # 9. Upload to Supabase
    print(f"\n--- Uploading {len(unique_active)} active and {len(unique_sold)} sold properties to Supabase ---")
    if unique_active:
        upsert_to_supabase("domain_listings_active", "domain_listing_id", unique_active)
    if unique_sold:
        upsert_to_supabase("domain_listings_sold", "domain_listing_id", unique_sold)

    # 10. Insert-only weekly snapshot of active listings (domain_listings_snapshot_log).
    # domain_listings_active is upsert-overwritten every run, so it has no history --
    # this log accumulates one row per (domain_listing_id, scraped_week) so a future job
    # can diff week-over-week and detect listings that dropped out of domain_listings_active
    # without appearing in domain_listings_sold (= withdrawn). Needs several weeks of
    # accumulation before it's usable; see dashboard Withdrawn Listings section.
    scraped_week = scraped_at[:10]
    snapshot_rows = [
        {
            "domain_listing_id": item["domain_listing_id"],
            "scraped_week": scraped_week,
            "suburb": item.get("suburb"),
            "street": item.get("street"),
            "price_text": item.get("price_text"),
            "beds": item.get("beds"),
            "baths": item.get("baths"),
            "parking": item.get("parking"),
            "land_size_sqm": item.get("land_size_sqm"),
            "property_type": item.get("property_type"),
            "agency_name": item.get("agency_name"),
            "source_search": item.get("source_search"),
        }
        for item in unique_active
    ]
    if snapshot_rows:
        upsert_to_supabase("domain_listings_snapshot_log", "domain_listing_id,scraped_week", snapshot_rows)

    print("\nFranchise scrape and sync completed successfully!")

if __name__ == "__main__":
    main()
