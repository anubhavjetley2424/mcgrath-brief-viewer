"""Seed demo data for UI testing — deals at various stages, tasks, notifications, scheduled_sends.

Usage:
    python scripts/seed_demo.py

Requires FastAPI NOT running (writes directly to Supabase).
"""
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent.parent / "api" / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    sys.exit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in api/.env")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
now = datetime.now(timezone.utc)

# ──────────────────────────── Deals ────────────────────────────
deals_data = [
    {
        "vendor_name": "Sarah Mitchell",
        "vendor_email": "sarah.m@example.com",
        "vendor_phone": "+61412345001",
        "address": "14 Harbour View Rd, Mosman NSW 2088",
        "stage": "New Lead",
        "notes": "Referred by past client. Interested in selling before Christmas.",
    },
    {
        "vendor_name": "James & Priya Patel",
        "vendor_email": "jpatel@example.com",
        "vendor_phone": "+61412345002",
        "address": "7/22 Ocean St, Bondi NSW 2026",
        "stage": "Listing Appointment Booked",
        "notes": "Appointment set for next Tuesday 10am.",
    },
    {
        "vendor_name": "Margaret Chen",
        "vendor_email": "mchen@example.com",
        "vendor_phone": "+61412345003",
        "address": "45 Elm Ave, Chatswood NSW 2067",
        "stage": "Pre-Appointment Prep",
        "notes": "Downsizing. Looking for quick campaign.",
    },
    {
        "vendor_name": "Tom & Lisa Barrett",
        "vendor_email": "tbarrett@example.com",
        "vendor_phone": "+61412345004",
        "address": "3 Banksia Cres, Lane Cove NSW 2066",
        "stage": "Appraisal Completed",
        "notes": "Expecting $2.1–2.3M range. Follow-up draft pending.",
    },
    {
        "vendor_name": "Emma White",
        "vendor_email": "ewhite@example.com",
        "vendor_phone": "+61412345008",
        "address": "42 Market St, Sydney NSW 2000",
        "stage": "Listing Signed",
        "notes": "Contract just signed. Needs listing setup.",
        "bedrooms": 4,
        "bathrooms": 2,
        "appraisal_price": "$2,500,000",
        "access_notes": "Key under the mat",
        "auction_date": (now + timedelta(days=30)).strftime("%Y-%m-%d"),
        "launch_date": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
        "settlement_date": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
    },
    {
        "vendor_name": "David Nguyen",
        "vendor_email": "dnguyen@example.com",
        "vendor_phone": "+61412345005",
        "address": "Unit 12, 88 Pacific Hwy, St Leonards NSW 2065",
        "stage": "Negotiation",
        "notes": "Wants to test the market. Hasn't committed yet.",
    },
    {
        "vendor_name": "Rachel Ford",
        "vendor_email": "rford@example.com",
        "vendor_phone": "+61412345006",
        "address": "21 Jacaranda Dr, Willoughby NSW 2068",
        "stage": "Campaign Live",
        "notes": "Listed last week. First open home this Saturday.",
    },
    {
        "vendor_name": "Michael & Sue Thompson",
        "vendor_email": "mthompson@example.com",
        "vendor_phone": "+61412345007",
        "address": "9 Heritage Lane, Pymble NSW 2073",
        "stage": "Sold",
        "notes": "Sold at auction for $3.2M. Nurture follow-ups scheduled.",
    },
]

print("Seeding deals...")
inserted_deals = []
for d in deals_data:
    result = sb.table("deals").insert(d).execute()
    deal = result.data[0]
    inserted_deals.append(deal)
    print(f"  ✓ {deal['vendor_name']} → {deal['stage']} ({deal['id'][:8]}...)")

# Helper to find deal by stage
def deal_at(stage: str):
    return next((d for d in inserted_deals if d["stage"] == stage), None)

def make_airtable_url(base_url: str, deal: dict, field_map: dict):
    params = {}
    for k, v in field_map.items():
        if v:
            params[f"prefill_{k}"] = str(v)
    if not params:
        return base_url
    return f"{base_url}?{urllib.parse.urlencode(params)}"


# ──────────────────────────── Tasks ────────────────────────────
print("\nSeeding tasks...")

prep_deal = deal_at("Pre-Appointment Prep")
if prep_deal:
    marketing_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shrhVw3cM24Kk1Mke", prep_deal, {
        "Address": prep_deal.get("address"),
        "Number of Bedrooms?": prep_deal.get("bedrooms"),
        "Property Appraisal Price": prep_deal.get("appraisal_price"),
    })
    prep_tasks = [
        {"title": "Pull comparable sales from RP Data", "task_type": "external_form", "external_url": "https://rpdata.com", "order_index": 1},
        {"title": "Generate CMA in Pricefinder", "task_type": "external_form", "order_index": 2},
        {"title": "Request marketing quote", "task_type": "external_form", "external_url": marketing_url, "order_index": 3},
        {"title": "Prepare listing presentation slides", "task_type": "manual_action", "order_index": 4},
        {"title": "Confirm appointment 24h prior", "task_type": "system_reminder", "due_date": (now + timedelta(days=1)).strftime("%Y-%m-%d"), "order_index": 5},
    ]
    for t in prep_tasks:
        sb.table("tasks").insert({**t, "deal_id": prep_deal["id"], "stage": "Pre-Appointment Prep"}).execute()
        print(f"  ✓ [Prep] {t['title']}")

neg_deal = deal_at("Negotiation")
if neg_deal:
    neg_tasks = [
        {"title": f"Check in with {neg_deal['vendor_name']} about {neg_deal['address']}", "task_type": "manual_action", "due_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"), "order_index": 1},
        {"title": f"Send {neg_deal['vendor_name']} an update on {neg_deal['address']}", "task_type": "manual_action", "due_date": (now + timedelta(days=5)).strftime("%Y-%m-%d"), "order_index": 2},
        {"title": f"Call {neg_deal['vendor_name']} directly — email isn't working", "task_type": "manual_action", "due_date": (now + timedelta(days=10)).strftime("%Y-%m-%d"), "order_index": 3},
    ]
    for t in neg_tasks:
        sb.table("tasks").insert({**t, "deal_id": neg_deal["id"], "stage": "Negotiation"}).execute()
        print(f"  ✓ [Negotiation] {t['title']}")

signed_deal = deal_at("Listing Signed")
if signed_deal:
    listing_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shrmccNo8lY673vSZ", signed_deal, {
        "Property Address": signed_deal.get("address"),
        "Bedrooms": signed_deal.get("bedrooms"),
        "Bathrooms": signed_deal.get("bathrooms"),
        "Property Access Notes": signed_deal.get("access_notes"),
    })
    swat_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shrrOGHTRsgaWNLEt", signed_deal, {
        "Property Address": signed_deal.get("address"),
        "Proposed Launch Date": signed_deal.get("launch_date"),
    })
    auction_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shrj0SClkj45Ix7LQ", signed_deal, {
        "Property Address": signed_deal.get("address"),
        "Auction Date": signed_deal.get("auction_date"),
    })
    compliance_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shrOkU7NbCJwAfVFw", signed_deal, {"Property Address": signed_deal.get("address")})
    signed_tasks = [
        {"title": "2. New Listing Set Up", "task_type": "external_form", "external_url": listing_url, "order_index": 1},
        {"title": "3. SWAT Request", "task_type": "external_form", "external_url": swat_url, "order_index": 2},
        {"title": "5. Auction Booking Form", "task_type": "external_form", "external_url": auction_url, "order_index": 3},
        {"title": "Listing Compliance Checklist", "task_type": "external_form", "external_url": compliance_url, "order_index": 4},
        {"title": "Create WhatsApp Group", "task_type": "manual_action", "order_index": 5},
    ]
    for t in signed_tasks:
        sb.table("tasks").insert({**t, "deal_id": signed_deal["id"], "stage": "Listing Signed"}).execute()
        print(f"  ✓ [Listing Signed] {t['title']}")

campaign_deal = deal_at("Campaign Live")
if campaign_deal:
    launch_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shr4pzOlv53l6Eyr6", campaign_deal, {
        "Property Address": campaign_deal.get("address"),
        "Launch Date": campaign_deal.get("launch_date"),
    })
    campaign_tasks = [
        {"title": "Launch Live Approval", "task_type": "external_form", "external_url": launch_url, "order_index": 1},
        {"title": f"Send weekly vendor update for {campaign_deal['address']}", "task_type": "manual_action", "due_date": now.strftime("%Y-%m-%d"), "order_index": 2, "description": "Compile campaign stats from Agentbox and send a short email update to the vendor."},
    ]
    for t in campaign_tasks:
        sb.table("tasks").insert({**t, "deal_id": campaign_deal["id"], "stage": "Campaign Live"}).execute()
        print(f"  ✓ [Campaign] {t['title']}")

sold_deal = deal_at("Sold")
if sold_deal:
    sold_marketing_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shrYeZHRfqn0SXvIw", sold_deal, {"Property Address": sold_deal.get("address")})
    settlement_url = make_airtable_url("https://airtable.com/appvTX5GSGGSRHV1c/shr7ZdWeoljzEF4Cd", sold_deal, {
        "Property Address": sold_deal.get("address"),
        "Confirmed Settlement Date": sold_deal.get("settlement_date"),
    })
    sold_tasks = [
        {"title": "Sold Marketing Request", "task_type": "external_form", "external_url": sold_marketing_url, "order_index": 1},
        {"title": "Preparation for Settlement", "task_type": "external_form", "external_url": settlement_url, "order_index": 2},
        {"title": f"Call {sold_deal['vendor_name']} personally to congratulate", "task_type": "manual_action", "due_date": now.strftime("%Y-%m-%d"), "order_index": 3},
        {"title": "Add vendor to 'Past Clients' contact type", "task_type": "manual_action", "order_index": 4},
    ]
    for t in sold_tasks:
        sb.table("tasks").insert({**t, "deal_id": sold_deal["id"], "stage": "Sold"}).execute()
        print(f"  ✓ [Sold] {t['title']}")

# One task that's already done (for testing progress bars)
if prep_deal:
    sb.table("tasks").insert({
        "deal_id": prep_deal["id"],
        "title": "Review vendor's property details",
        "task_type": "manual_action",
        "stage": "Pre-Appointment Prep",
        "status": "done",
        "completed_at": now.isoformat(),
        "order_index": 0,
    }).execute()
    print("  ✓ [Prep] Review vendor's property details (DONE)")


# ──────────────────────────── Notifications ────────────────────────────
print("\nSeeding notifications...")

appraisal_deal = deal_at("Appraisal Completed")
notifications_data = []

if appraisal_deal:
    notifications_data.append({
        "deal_id": appraisal_deal["id"],
        "notification_type": "draft_ready",
        "title": f"Appraisal follow-up draft ready for {appraisal_deal['vendor_name']}",
        "body": f"Review and approve the follow-up email for {appraisal_deal['address']}.",
        "action_url": "/drafts",
    })

if campaign_deal:
    notifications_data.append({
        "deal_id": campaign_deal["id"],
        "notification_type": "task_due",
        "title": f"Weekly update due for {campaign_deal['vendor_name']}",
        "body": f"Time to send the weekly campaign update for {campaign_deal['address']}.",
        "action_url": f"/deals/{campaign_deal['id']}",
    })

if sold_deal:
    notifications_data.append({
        "deal_id": sold_deal["id"],
        "notification_type": "check_in_nudge",
        "title": f"Congratulate {sold_deal['vendor_name']}!",
        "body": "Don't forget to call them personally.",
        "action_url": f"/deals/{sold_deal['id']}",
    })

for n in notifications_data:
    sb.table("simon_notifications").insert(n).execute()
    print(f"  ✓ {n['title']}")


# ──────────────────────────── Scheduled Sends ────────────────────────────
print("\nSeeding scheduled sends...")

sends_data = []

booked_deal = deal_at("Listing Appointment Booked")
if booked_deal:
    sends_data.append({
        "deal_id": booked_deal["id"],
        "send_type": "sms",
        "recipient": booked_deal["vendor_phone"],
        "body": f"Hi {booked_deal['vendor_name'].split()[0]}, just confirming our meeting tomorrow at 10am at {booked_deal['address']}. Look forward to it. — Simon",
        "scheduled_for": (now + timedelta(hours=20)).isoformat(),
        "reason": "appointment_reminder_24h",
    })

if appraisal_deal:
    sends_data.append({
        "deal_id": appraisal_deal["id"],
        "send_type": "sms",
        "recipient": "+61404869284",
        "body": f"Time to check in with {appraisal_deal['vendor_name']} re: {appraisal_deal['address']} — they haven't responded yet.",
        "scheduled_for": (now + timedelta(days=3)).isoformat(),
        "reason": "3_day_check_in",
    })

if neg_deal:
    for day, label in [(2, "day_2_nudge"), (5, "day_5_nudge"), (10, "day_10_nudge")]:
        sends_data.append({
            "deal_id": neg_deal["id"],
            "send_type": "sms",
            "recipient": "+61404869284",
            "body": f"Reminder: follow up with {neg_deal['vendor_name']} about {neg_deal['address']}.",
            "scheduled_for": (now + timedelta(days=day)).isoformat(),
            "reason": label,
        })

if sold_deal:
    sends_data.append({
        "deal_id": sold_deal["id"],
        "send_type": "sms",
        "recipient": sold_deal["vendor_phone"],
        "body": f"Hi {sold_deal['vendor_name'].split()[0]}, hope you're settled into the new place. Just wanted to check in. — Simon",
        "scheduled_for": (now + timedelta(days=180)).isoformat(),
        "reason": "6_month_nurture",
    })
    sends_data.append({
        "deal_id": sold_deal["id"],
        "send_type": "sms",
        "recipient": sold_deal["vendor_phone"],
        "body": f"Hi {sold_deal['vendor_name'].split()[0]}, one year ago today you sold {sold_deal['address']}. Hope life is treating you well. — Simon",
        "scheduled_for": (now + timedelta(days=365)).isoformat(),
        "reason": "12_month_nurture",
    })

for s in sends_data:
    sb.table("scheduled_sends").insert(s).execute()
    print(f"  ✓ [{s['reason']}] {s['send_type']} → {s['recipient']}")


# ──────────────────────────── Summary ────────────────────────────
print(f"\n{'='*60}")
print(f"SEEDED: {len(inserted_deals)} deals, tasks, notifications, scheduled sends")
print(f"{'='*60}")
print("\nStart the servers and open http://localhost:5173")
print("  Backend:  uvicorn api.main:app --reload --port 8000")
print("  Frontend: cd web && npm run dev")
print("\nTest flow:")
print("  1. Dashboard → check Tasks Due Today widget + pipeline breakdown")
print("  2. Kanban → see deals across 8 stages, drag one to test confirmation modal")
print("  3. Click a deal → see Tasks tab, Scheduled Comms tab, Activity tab")
print("  4. Bell icon → 3 unread notifications")
print(f"{'='*60}")
