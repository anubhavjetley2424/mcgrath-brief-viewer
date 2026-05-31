-- Supabase Schema Migrations for McGrath Dashboard v3 Upgrade
-- Run these queries in the Supabase SQL Editor (https://supabase.com)

-- 1. Ensure domain_listings_active has photos and floorplan_url columns
ALTER TABLE domain_listings_active
  ADD COLUMN IF NOT EXISTS photos text[],
  ADD COLUMN IF NOT EXISTS floorplan_url text;

-- 2. Ensure da_applications has latitude and longitude columns (double precision for geo coordinates)
ALTER TABLE da_applications
  ADD COLUMN IF NOT EXISTS latitude double precision,
  ADD COLUMN IF NOT EXISTS longitude double precision;

-- 3. Ensure vg_sales has photos and floorplan_url columns
ALTER TABLE vg_sales
  ADD COLUMN IF NOT EXISTS photos text[],
  ADD COLUMN IF NOT EXISTS floorplan_url text;

-- 4. Create SA1 GeoJSON cache table to pre-store ABS SA1 boundaries per suburb for fast loads
CREATE TABLE IF NOT EXISTS sa1_geojson_cache (
  suburb text PRIMARY KEY,
  geojson jsonb NOT NULL,
  updated_at timestamptz DEFAULT now()
);

-- 5. Enable CORS or set permissions if needed (Routines and REST accesses bypass RLS in service role)

-- 6. suburb_demographics — the 5 high-value appraisal metrics + ABS extras.
--    The dashboard backend (api/routers/dashboard.py) queries this and
--    merges it into the dashboard JSON as `demographics_by_suburb`.
--    Until this table is seeded, the frontend uses local JS fixtures.
CREATE TABLE IF NOT EXISTS suburb_demographics (
  suburb text PRIMARY KEY,
  postcode text,
  -- Five high-value cards (drive the dashboard's socio-grid)
  seifa_irsad numeric,                       -- ABS SEIFA 2021 IRSAD score
  median_weekly_household_income numeric,    -- ABS Census 2021 G02
  owner_occupier_pct numeric,                -- ABS Census 2021 G32 (own outright + with mortgage) / total
  five_yr_turnover_pct numeric,              -- ABS Census 2021 G14 (different address 5 yrs ago)
  supply_months numeric,                     -- computed: active listings / avg monthly sales
  -- Optional extras (kept in payload, not displayed by default)
  population integer,
  median_age numeric,
  dwellings integer,
  avg_household_size numeric,
  updated_at timestamptz DEFAULT now()
);

-- Optional RLS: read-only public access (demographics are not sensitive).
-- ALTER TABLE suburb_demographics ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Anyone can read demographics" ON suburb_demographics FOR SELECT USING (true);
