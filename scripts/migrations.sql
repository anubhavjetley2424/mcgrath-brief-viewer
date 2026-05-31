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
