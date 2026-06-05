#!/usr/bin/env bash
#
# One-shot deploy script for the Cloud Run scraper Jobs (3 live + 2 backfills
# + 1 keepalive).
#
# Domain /sale/ and /sold-listings/ are NOT deployed — Akamai Bot Manager
# blocks both curl_cffi impersonation and headless Playwright. Unblocks
# when McGrath secures official Domain API access.
#
# Prereqs (one-time):
#   gcloud auth login
#   gcloud config set project mcgrath-real-estate-automation
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#                          cloudscheduler.googleapis.com \
#                          secretmanager.googleapis.com \
#                          artifactregistry.googleapis.com
#
# Add the Supabase service-role key as a secret version BEFORE first run:
#   echo -n "<service-role JWT>" | \
#     gcloud secrets versions add supabase-service-role-key --data-file=-
#
# Then, from the project root:
#   bash scraper/deploy.sh

set -euo pipefail

PROJECT_ID="mcgrath-real-estate-automation"
REGION="australia-southeast1"
REPO="scraper"
IMAGE_NAME="brief-scraper"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:${IMAGE_TAG}"
SCHEDULER_TZ="Australia/Sydney"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Artifact Registry repo
# ─────────────────────────────────────────────────────────────────────────────
echo "▶ Ensuring Artifact Registry repo exists…"
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="McGrath brief scraper images" \
  2>/dev/null || echo "  (already exists)"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Build + push image via Cloud Build
# ─────────────────────────────────────────────────────────────────────────────
echo "▶ Building image with Cloud Build → ${IMAGE}"
gcloud builds submit \
  --config=- \
  --substitutions=_IMAGE="${IMAGE}" \
  . <<'YAML'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-t', '${_IMAGE}', '-f', 'scraper/Dockerfile', '.']
images:
  - '${_IMAGE}'
YAML

# ─────────────────────────────────────────────────────────────────────────────
# 3. Secret Manager — Supabase service-role key
# ─────────────────────────────────────────────────────────────────────────────
echo "▶ Ensuring secret 'supabase-service-role-key' exists…"
gcloud secrets create supabase-service-role-key --replication-policy=automatic \
  2>/dev/null || echo "  (already exists — add a version manually if it has none)"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "▶ Granting ${SA} read access to the secret…"
gcloud secrets add-iam-policy-binding supabase-service-role-key \
  --member="serviceAccount:${SA}" \
  --role=roles/secretmanager.secretAccessor \
  --quiet >/dev/null

# ─────────────────────────────────────────────────────────────────────────────
# 4. Create / update Cloud Run Jobs
# ─────────────────────────────────────────────────────────────────────────────
JOBS=(
  "auction-current"     # weekly Sun 02:30 AEDT
  "da-delta"            # fortnightly (1st & 15th) 03:00 AEDT
  "id-lga"              # weekly Sun 04:00 AEDT
  "keepalive"           # weekly Wed 06:00 AEDT — guarantees Supabase no-pause
  "auction-backfill"    # one-off, manual trigger
  "da-backfill-180d"    # one-off, manual trigger
)

for J in "${JOBS[@]}"; do
  echo "▶ Deploying Cloud Run Job: ${J}"
  gcloud run jobs deploy "${J}" \
    --image="${IMAGE}" \
    --region="${REGION}" \
    --task-timeout=15m \
    --max-retries=1 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars="JOB=${J}" \
    --set-secrets="SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest" \
    --quiet
done

# ─────────────────────────────────────────────────────────────────────────────
# 5. Cloud Scheduler crons
# ─────────────────────────────────────────────────────────────────────────────
create_cron() {
  local NAME="$1"
  local CRON="$2"
  local JOB_NAME="$3"
  local URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"

  echo "▶ Scheduling ${NAME} (${CRON}) → ${JOB_NAME}"
  gcloud scheduler jobs create http "${NAME}" \
    --location="${REGION}" \
    --schedule="${CRON}" \
    --time-zone="${SCHEDULER_TZ}" \
    --uri="${URL}" \
    --http-method=POST \
    --oauth-service-account-email="${SA}" \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
    2>/dev/null \
  || gcloud scheduler jobs update http "${NAME}" \
       --location="${REGION}" \
       --schedule="${CRON}" \
       --time-zone="${SCHEDULER_TZ}" \
       --uri="${URL}" \
       --http-method=POST \
       --oauth-service-account-email="${SA}" \
       --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
}

# Weekly Sunday 02:30 AEDT — Sydney auction clearance for that weekend
create_cron "cron-auction-current" "30 2 * * 0"     "auction-current"

# Fortnightly 1st & 15th of every month at 03:00 AEDT — SSC DA delta
create_cron "cron-da-delta"        "0 3 1,15 * *"   "da-delta"

# Weekly Sunday 04:00 AEDT — LGA demographics refresh
create_cron "cron-id-lga"          "0 4 * * 0"      "id-lga"

# Weekly Wednesday 06:00 AEDT — Supabase keepalive (no-op SELECT)
create_cron "cron-keepalive"       "0 6 * * 3"      "keepalive"

# Backfills are NOT scheduled — trigger manually after first deploy:
#   gcloud run jobs execute da-backfill-180d --region=australia-southeast1 --wait
#   gcloud run jobs execute auction-backfill --region=australia-southeast1 --wait

echo
echo "✅ Deploy complete."
