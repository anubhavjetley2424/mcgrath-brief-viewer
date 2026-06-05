# Scraper — Cloud Run Jobs deployment

Containerises the working scrapers in `scripts/` and runs each on a schedule
in GCP. Lifts the long-running work out of n8n (60s ceiling) and out of
Simon's laptop (manual runs).

## What ships

| Scraper | Job name | Schedule (Australia/Sydney) | Status |
|---|---|---|---|
| Domain weekly auction clearance | `auction-current` | Sun 02:30 | ✅ working (curl_cffi chrome124) |
| SSC DA portal — 14-day delta | `da-delta` | 1st & 15th 03:00 | ✅ working |
| profile.id.com.au LGA demographics | `id-lga` | Sun 04:00 | ✅ working |
| Supabase keepalive ping | `keepalive` | Wed 06:00 | ✅ working — guards against 7-day inactivity pause |
| SSC DA 180-day backfill | `da-backfill-180d` | one-off, manual | ✅ working |
| Auction clearance 24-week backfill | `auction-backfill` | one-off, manual | ✅ working |

## Not deployed (blocked)

| Scraper | Blocker |
|---|---|
| Domain `/sale/` active listings | Akamai Bot Manager — JS challenge. Both curl_cffi chrome124 and Playwright headless return 403. |
| Domain `/sold-listings/` history | Same. |

These unblock when McGrath secures official Domain API access (`developer@domain.com.au`). Until then, the dashboard's active-listings and recent-sales cards stay blank or fall back to RP Data exports.

## One-time GCP setup

```bash
gcloud auth login
gcloud config set project mcgrath-real-estate-automation
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

## Add the Supabase service-role key

The deploy script creates the secret resource but never writes the value. Get the service-role key from **Supabase Dashboard → Project Settings → API → `service_role` secret** (long JWT), then:

```bash
echo -n "eyJhbGciOi…<service-role JWT>" | \
  gcloud secrets versions add supabase-service-role-key --data-file=-
```

This must be the **service_role** key, not the **anon** key — RLS blocks anon writes on the scraper tables.

## Deploy

```bash
bash scraper/deploy.sh
```

That builds the image, creates 6 Cloud Run Jobs, and wires 4 Cloud Scheduler crons. Re-runnable.

## First-deploy backfills

After the schedule is live, run the one-off bootstraps:

```bash
gcloud run jobs execute da-backfill-180d \
  --region=australia-southeast1 --wait

gcloud run jobs execute auction-backfill \
  --region=australia-southeast1 --wait
```

Each takes 3–8 minutes.

## Run a job locally (debugging)

```bash
# Build the image locally (from project root)
docker build -t brief-scraper -f scraper/Dockerfile .

# Run one job (service-role key required — anon write fails on RLS)
docker run --rm \
  -e JOB=da-delta \
  -e SUPABASE_SERVICE_ROLE_KEY="$(cat ~/.supabase-service-role-key)" \
  brief-scraper
```

## Trigger any Job manually in GCP

```bash
gcloud run jobs execute auction-current \
  --region=australia-southeast1 --wait
```

## Notes on the no-pause guarantee

Supabase Free pauses a project after **7 consecutive days with zero DB activity**. With the schedule above the DB is touched at minimum every 3 days (Sun auction + Wed keepalive + Sun id-lga, plus DA on the 1st and 15th). The dedicated `keepalive` job is the belt-and-braces — even if every other scraper failed for a week, Wednesday's keepalive ping resets the inactivity clock.

## Open work

1. **Move sale + sold scraping off Domain** once McGrath has the API. Add `_domain_sale_farm` and `_domain_sold_farm` to `orchestrator.py`, and corresponding entries in `deploy.sh`'s `JOBS` array + crons.
2. **Pivot `index.html`** to read scraped data from Supabase directly. Today the dashboard still goes through the n8n webhook.
3. **Add a Cloud Run Job execution alert** — Cloud Monitoring → email Simon if any job fails 2× in a row.
