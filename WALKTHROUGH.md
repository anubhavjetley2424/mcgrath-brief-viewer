# McGrath Dashboard v3 — Production Upgrade Walkthrough

This document outlines the changes made for the McGrath Sutherland Shire AI Appraisal Prep Brief v3 upgrade, including Supabase SQL migrations, n8n scrapers, FastAPI router endpoints, React frontend, and manual Airtable configurations.

---

## 1. Supabase Schema Migrations

Run the following SQL script in the **Supabase SQL Editor** to support active/sold listing columns, council DAs with spatial lat/lng coordinates, and SA1 choropleth GeoJSON boundaries cache.

```sql
-- 1. Ensure domain_listings_active has photos and floorplan_url columns
ALTER TABLE domain_listings_active
  ADD COLUMN IF NOT EXISTS photos text[],
  ADD COLUMN IF NOT EXISTS floorplan_url text;

-- 2. Ensure da_applications has latitude and longitude columns
ALTER TABLE da_applications
  ADD COLUMN IF NOT EXISTS latitude double precision,
  ADD COLUMN IF NOT EXISTS longitude double precision;

-- 3. Ensure vg_sales has photos and floorplan_url columns
ALTER TABLE vg_sales
  ADD COLUMN IF NOT EXISTS photos text[],
  ADD COLUMN IF NOT EXISTS floorplan_url text;

-- 4. Create SA1 GeoJSON cache table to pre-store ABS SA1 boundaries per suburb
CREATE TABLE IF NOT EXISTS sa1_geojson_cache (
  suburb text PRIMARY KEY,
  geojson jsonb NOT NULL,
  updated_at timestamptz DEFAULT now()
);
```

---

## 2. n8n Scrapers & API Webhook Workflows

We built three major n8n workflows located in the `/n8n-workflows` folder:

1. **Weekly Domain Scraper** (`n8n-workflows/domain_scraper_workflow.json`):
   - Runs every **Sunday at 2:00 AM AEST** (`0 16 * * 6` UTC).
   - Scrapes active listings, sold listings, and medians for all **11 Sutherland Shire suburbs** using the proven Next.js `__NEXT_DATA__` extraction.
   - Upserts results to `domain_listings_active`, `domain_listings_sold`, and `domain_suburb_medians` on Supabase.
   - Saves CDN images directly to the database.

2. **Weekly SSC DA Scraper** (`n8n-workflows/ssc_da_scraper_workflow.json`):
   - Runs every **Monday at 2:00 AM AEST** (`0 16 * * 0` UTC).
   - Scrapes development applications from the **Sutherland Shire Council eProperty portal** using plain HTTP requests with ViewState validation.
   - Handles multi-page search results automatically and upserts them to `da_applications`.

3. **Dashboard Data API Webhook** (`n8n-workflows/dashboard_data_api.json`):
   - Serves as the high-speed production API endpoint: `GET /webhook/dashboard-data?deal={deal_id}&suburb={suburb}`.
   - Handles queries from both local dev and production GitHub Pages (`anubhavjetley2424.github.io`).
   - Resolves deals from Airtable and aggregates vg_sales, active listings, DAs, schools, and SA1 boundary polygons.
   - Returns standard JSON responses with full **CORS enabled** (`Access-Control-Allow-Origin: *`).

---

## 3. FastAPI Dashboard Router Endpoint

To ensure local parity, we added a parallel API router to the FastAPI backend:
- File created: `api/routers/dashboard.py`
- Wired into: `api/main.py`
- Exposes `GET /api/dashboard-data` which performs identical SQL operations as n8n.

---

## 4. Appraisal Map React Dashboard Frontend

We upgraded the React frontend in the `web` workspace with interactive map capabilities:
- **Map TypeScript Types** (`web/src/types/map.ts`): Type-safety for Sales, Active listings, DAs, Schools, and KPI structures.
- **AppRouter & Navigation Links** (`web/src/App.tsx` and `web/src/components/Sidebar.tsx`): Registered `/map` route and added a sidebar link to **Appraisal Map**.
- **Interactive UI Dashboard** (`web/src/pages/MapDashboard.tsx` and `.css`):
  - A premium dark-themed 3-column CSS Grid.
  - Interactive **Mapbox GL** viewport plotting sales (price-tiered colors), active listings, DAs, schools, and subject property.
  - Floating Glassmorphism **Layer Toggle** panel.
  - Left Rail displaying animated **KPI cards**, an **SVG sparkline** (12mo median trend), and an **SVG Donut Chart** (price tier volume).
  - Sortable Right Sidebar showcasing comparable listing cards with photo thumbnails (zooms/flies camera on click).
  - **Below-map content panels** displaying suburb context, active council infrastructure, and hazard flags.

---

## 5. Airtable Configuration (Manual Steps)

To tie the interactive map dashboard back to your Airtable CRM interface, perform these three simple manual configurations:

### A. Create "Interactive Map URL" Formula Field
In your **Deals** table (`tblZfaTySImrUc3CD`), add a new field:
- **Field Name**: `Interactive Map URL`
- **Type**: `Formula`
- **Formula**:
  ```text
  "https://anubhavjetley2424.github.io/mcgrath-brief-viewer/#/map?deal=" & RECORD_ID()
  ```

### B. Add Interface Navigation Button
On the **Deal Details** Airtable Interface page:
- Add a new **Button** element.
- Set the button label to **"Open Map Dashboard"**.
- Set the button action to **"Open URL"** and choose the `Interactive Map URL` field as the destination source.

### C. Create AI Draft Approval Action Buttons
On the **AI Draft Approvals** interface page, create two buttons in each row to approve or reject the AI generated brief:

1. **Approve Button** (Triggers power-automate send pipeline):
   - Set the button action to **"Run Script"** and paste this script:
     ```javascript
     let table = base.getTable('Drafts');
     let record = await input.recordAsync('Select a draft', table);
     if (record) {
       await table.updateRecordAsync(record.id, {
         'Approval Status': 'Approved',
         'Approval Date': new Date().toISOString().split('T')[0]
       });
       output.text("✅ Draft approved. Power Automate email pipeline will fire automatically.");
     }
     ```

2. **Reject Button**:
   - Set the button action to **"Run Script"** and paste this script:
     ```javascript
     let table = base.getTable('Drafts');
     let record = await input.recordAsync('Select a draft', table);
     if (record) {
       await table.updateRecordAsync(record.id, {
         'Approval Status': 'Rejected'
       });
       output.text("❌ Draft rejected.");
     }
     ```

> [!IMPORTANT]
> **Airtable Trigger setup**: To enable n8n to listen to changes when either **Approved** or **Rejected** is clicked by Simon, you must add a field named `'Approval Status Last Updated'` of type **Last Modified Time** in the `Drafts` table of your Airtable database, configured to watch specifically the `'Approval Status'` field. The `Draft Approval Handler` n8n trigger is now updated to watch this `'Approval Status Last Updated'` field, firing cleanly on both events. Rejections will now cleanly log a `"draft_rejected"` activity in your activities log.

---

## 6. End-to-End Verification

1. Run the database migration script.
2. Fire up the development environment:
   ```bash
   # Run FastAPI backend
   uvicorn api.main:app --reload --port 8000
   
   # Run Vite React frontend
   cd web
   npm run dev
   ```
3. Navigate to `http://localhost:5173/#/map` to test the appraisal map dashboard with live and mock databases.
4. Try passing a valid Airtable deal ID to test deep prefill: `http://localhost:5173/#/map?deal=recXXX`.
