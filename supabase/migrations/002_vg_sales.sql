-- NSW Valuer General bulk Property Sales Information (PSI).
-- One row per sale, written by scripts/vg_scraper.py.
-- Schema deliberately accommodates additional sources too (PriceFinder,
-- Domain) — `source` distinguishes; (source, dealing_number) is the key.

create table if not exists public.vg_sales (
  id              bigserial primary key,

  -- Provenance + idempotency
  source          text not null,    -- 'vg-weekly' | 'vg-annual' | 'pricefinder' | 'domain'
  dealing_number  text not null,    -- LRS title-transfer reference, unique per sale

  -- Property identity
  district_code   text,
  property_id     text,
  sale_counter    int,

  -- Address
  address         text,
  suburb          text,
  postcode        text,

  -- Land
  area_sqm        numeric,

  -- Sale
  contract_date   date,             -- treat as "transfer date" for trend charts
  settlement_date date,
  sale_price      bigint,

  -- Zoning / use
  zoning          text,
  nature_of_property text,
  primary_purpose text,
  sale_code       text,

  -- Geocoded later
  latitude        numeric,
  longitude       numeric,

  -- Bookkeeping
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),

  unique (source, dealing_number)
);

-- Dashboard query patterns: "sales in suburb X over last 12 months"
-- and "sales in date range across all suburbs".
create index if not exists vg_sales_suburb_contract_date_idx
  on public.vg_sales (suburb, contract_date desc);
create index if not exists vg_sales_contract_date_idx
  on public.vg_sales (contract_date desc);

-- Touch updated_at on every upsert
create or replace function public.touch_vg_sales_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists vg_sales_touch_updated_at on public.vg_sales;
create trigger vg_sales_touch_updated_at
  before update on public.vg_sales
  for each row execute function public.touch_vg_sales_updated_at();

-- RLS: anon can read for the public dashboard; only service_role can write
-- (matches how scrapers are deployed — service-role key in Secret Manager).
alter table public.vg_sales enable row level security;

drop policy if exists "anon can read" on public.vg_sales;
create policy "anon can read"
  on public.vg_sales
  for select
  to anon
  using (true);

drop policy if exists "service_role can write" on public.vg_sales;
create policy "service_role can write"
  on public.vg_sales
  for all
  to service_role
  using (true) with check (true);
