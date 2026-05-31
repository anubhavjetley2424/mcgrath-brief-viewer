"""Seed a single test vendor at stage = 'New' (no workflow fires on insert).

Usage:
    python scripts/seed_vendor.py

After it prints the deal id, slide through stages by calling:
    curl -X PATCH http://localhost:8000/api/deals/<DEAL_ID>/stage \
         -H "Content-Type: application/json" \
         -d '{"new_stage": "Listing Appointment Booked", "updated_by": "simon", "appointment_datetime": "2026-05-20T15:30:00"}'

(See the printed examples at the bottom of this script's output.)
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

# Load from api/.env (single source of truth for SUPABASE creds)
load_dotenv(Path(__file__).parent.parent / "api" / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    sys.exit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in api/.env")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

VENDOR = {
    "vendor_name": "Jane Test",
    "vendor_email": "anubhav.jetley@student.uts.edu.au",
    "vendor_phone": "+61404869284",
    "address": "12 Smith Street, Sydney NSW 2000",
    "stage": "New",  # not in the n8n Switch — won't trigger any branch on insert
    "notes": "Seeded by scripts/seed_vendor.py — used for stage-slide testing.",
}

result = supabase.table("deals").insert(VENDOR).execute()
deal = result.data[0]

print("\n=== Seeded deal ===")
print(f"  id      : {deal['id']}")
print(f"  vendor  : {deal['vendor_name']}")
print(f"  address : {deal['address']}")
print(f"  stage   : {deal['stage']}")
print(f"  email   : {deal['vendor_email']}")
print(f"  phone   : {deal['vendor_phone']}")

print("\n=== curl examples — slide through each stage ===")
stages_in_order = [
    "Listing Appointment Booked",
    "Pre-Appointment Prep",
    "Appraisal Completed",
    "Negotiation",
    "Listing Signed",
    "Campaign Live",
    "Sold",
]
for stage in stages_in_order:
    body = (
        '{"new_stage": "' + stage + '", "updated_by": "simon"'
        + (', "appointment_datetime": "2026-05-20T15:30:00"' if stage == "Listing Appointment Booked" else "")
        + "}"
    )
    print(
        f'\n# → {stage}\n'
        f"curl -X PATCH http://localhost:8000/api/deals/{deal['id']}/stage "
        f"-H 'Content-Type: application/json' -d '{body}'"
    )

print("\nDone. FastAPI must be running on port 8000 for the curl commands to work.")
