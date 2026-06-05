"""
Cloud Run Jobs orchestrator.

Reads the JOB environment variable and dispatches to the right scraper.
Each scraper script in scripts/ is invoked as a subprocess so its argparse
CLI stays the contract — no import-shenanigans.

Job names map to gcloud Cloud Run Job names. Keep them in lockstep with
scraper/deploy.sh.

Scope (as of 5 Jun 2026):
  Live: SSC DA, profile.id.com.au, Domain auction-results
  Skipped: Domain /sale/ + /sold-listings/ — Akamai Bot Manager challenge
           blocks both curl_cffi impersonation and headless Playwright. We
           wait on McGrath to secure official Domain API access; when that
           lands, add a `_domain_sale_farm` / `_domain_sold_farm` here.
"""

import os
import subprocess
import sys
from datetime import date, timedelta

today = date.today()


# ----------------------------------------------------------------------------
# Job catalogue
# ----------------------------------------------------------------------------

def _auction_current():
    """This past weekend's Sydney auction-clearance result."""
    return ["python", "scripts/auction_clearance_scraper.py", "current"]


def _auction_backfill():
    """24 historical weeks — one-off bootstrap."""
    return ["python", "scripts/auction_clearance_scraper.py", "backfill"]


def _da_delta():
    """Fortnightly window — 14 days back to today.

    Idempotent: scraper upserts on da_id, so re-running over an overlapping
    window only updates existing rows and inserts genuinely new DAs.
    """
    start = today - timedelta(days=14)
    return ["python", "scripts/ssc_da_scraper.py", str(start), str(today)]


def _da_backfill_180d():
    """180 days back to today — one-off bootstrap."""
    start = today - timedelta(days=180)
    return ["python", "scripts/ssc_da_scraper.py", str(start), str(today)]


def _id_lga():
    """Sutherland Shire community profile, all topic pages."""
    return ["python", "scripts/id_scraper.py", "sutherland"]


def _vg_weekly_latest():
    """NSW Valuer General weekly delta — most recent published Sunday.

    Idempotent: scraper upserts on (source, dealing_number) so re-running
    against the same week harmlessly refreshes rows in place. Catches
    everything ≥6-8 weeks old; PriceFinder ingestion will later fill the
    recency gap.
    """
    return ["python", "scripts/vg_scraper.py", "weekly-latest"]


def _vg_annual_backfill_3y():
    """One-off: pull the last three annual bulks (today's year-3 ... year-1).

    ~15 MB per year, ~40-50 MB transferred total. The scraper filters
    Sutherland Shire only — DB load stays small. Run once after the table
    is created in Supabase.
    """
    today_year = date.today().year
    return [
        "python", "scripts/vg_scraper.py",
        "annual-backfill", str(today_year - 3), str(today_year - 1),
    ]


def _keepalive():
    """Tiny no-op that touches Supabase so the project never falls into
    7-day-inactivity pause. Belt-and-braces — the real scrapers should
    already keep the DB alive, but this guarantees it.
    """
    return [
        "python", "-c",
        "import os, urllib.request, json, sys; "
        "u = os.environ['SUPABASE_URL'] + '/rest/v1/da_applications?select=da_id&limit=1'; "
        "k = os.environ['SUPABASE_SERVICE_ROLE_KEY']; "
        "req = urllib.request.Request(u, headers={'apikey': k, 'Authorization': 'Bearer ' + k}); "
        "print('keepalive:', urllib.request.urlopen(req, timeout=15).status)"
    ]


JOBS = {
    # Live, scheduled
    "auction-current":        _auction_current,
    "da-delta":               _da_delta,
    "id-lga":                 _id_lga,
    "vg-weekly-latest":       _vg_weekly_latest,
    "keepalive":              _keepalive,
    # One-off, manual trigger
    "auction-backfill":       _auction_backfill,
    "da-backfill-180d":       _da_backfill_180d,
    "vg-annual-backfill-3y":  _vg_annual_backfill_3y,
}


# ----------------------------------------------------------------------------
# Dispatch
# ----------------------------------------------------------------------------

def main():
    job = os.environ.get("JOB")
    if not job:
        sys.exit("FATAL: JOB env var not set. Known jobs: "
                 + ", ".join(sorted(JOBS)))

    handler = JOBS.get(job)
    if handler is None:
        sys.exit(f"FATAL: unknown JOB={job!r}. "
                 f"Known: {', '.join(sorted(JOBS))}")

    # Sanity-check the service-role key is present. The scrapers fall back to
    # the public anon key for source fetches, but writes to Supabase fail with
    # RLS 401 without the service-role secret — and silently writing nothing
    # is the worst failure mode.
    if not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("[orchestrator] FATAL: SUPABASE_SERVICE_ROLE_KEY not set. "
              "Without it Supabase writes will 401 (RLS). Configure the "
              "secret in Cloud Run.", file=sys.stderr)
        sys.exit(2)

    # Also surface SUPABASE_URL for the keepalive job (other scripts have it
    # hardcoded; keepalive reads from env to stay generic).
    os.environ.setdefault(
        "SUPABASE_URL", "https://xzazkrudrgkcfcznkehb.supabase.co"
    )

    cmd = handler()
    print(f"[orchestrator] running JOB={job}: {' '.join(cmd[:3])}…", flush=True)
    sys.exit(subprocess.call(cmd, cwd="/app"))


if __name__ == "__main__":
    main()
