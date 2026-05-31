"""Deals — list / get / create / change stage.

A stage change PATCH writes Supabase first, then fires the n8n
stage-change webhook fire-and-forget. The HTTP response returns the
updated row; the n8n side runs async (Calendar/Email/SMS/log).
"""
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from ..config import N8N_STAGE_CHANGE_WEBHOOK
from ..database import get_supabase
from ..models import DealCreate, DealUpdate, StageUpdate

router = APIRouter(prefix="/api/deals", tags=["deals"])


def _webhook_body(deal: dict, new_stage: str, appt: str | None) -> dict:
    """Payload sent to n8n stage-change webhook — includes all prefill fields."""
    return {
        "dealId": deal["id"],
        "newStage": new_stage,
        "vendorName": deal.get("vendor_name"),
        "vendorEmail": deal.get("vendor_email"),
        "vendorPhone": deal.get("vendor_phone"),
        "address": deal.get("address"),
        "bedrooms": deal.get("bedrooms"),
        "bathrooms": deal.get("bathrooms"),
        "appraisalPrice": deal.get("appraisal_price"),
        "accessNotes": deal.get("access_notes"),
        "auctionDate": deal.get("auction_date"),
        "launchDate": deal.get("launch_date"),
        "settlementDate": deal.get("settlement_date"),
        "appointmentDateTime": appt,
    }


@router.get("")
def list_deals(supabase: Client = Depends(get_supabase)):
    return (
        supabase.table("deals")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/{deal_id}")
def get_deal(deal_id: str, supabase: Client = Depends(get_supabase)):
    deal_result = (
        supabase.table("deals").select("*").eq("id", deal_id).limit(1).execute()
    )
    if not deal_result.data:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal = deal_result.data[0]
    activities = (
        supabase.table("activities")
        .select("*")
        .eq("deal_id", deal_id)
        .order("occurred_at", desc=True)
        .execute()
        .data
    )
    return {**deal, "activities": activities}


@router.post("", status_code=201)
def create_deal(payload: DealCreate, supabase: Client = Depends(get_supabase)):
    result = (
        supabase.table("deals")
        .insert(payload.model_dump(exclude_unset=True))
        .execute()
    )
    return result.data[0]


@router.patch("/{deal_id}/stage")
async def update_stage(
    deal_id: str,
    payload: StageUpdate,
    supabase: Client = Depends(get_supabase),
):
    # 1. Update Supabase (updated_at auto-bumped by trigger)
    update_result = (
        supabase.table("deals")
        .update({"stage": payload.new_stage, "updated_by": payload.updated_by})
        .eq("id", deal_id)
        .execute()
    )
    if not update_result.data:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal = update_result.data[0]

    # 2. Fire n8n stage-change webhook (fire-and-forget; n8n responds immediately)
    webhook_body = _webhook_body(deal, payload.new_stage, payload.appointment_datetime)
    print(f"\n{'='*60}")
    print(f"[STAGE CHANGE] {deal.get('vendor_name')} → {payload.new_stage}")
    print(f"[WEBHOOK PAYLOAD] {webhook_body}")
    print(f"[WEBHOOK URL] {N8N_STAGE_CHANGE_WEBHOOK or '(not configured)'}")
    print(f"{'='*60}\n")

    if N8N_STAGE_CHANGE_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(N8N_STAGE_CHANGE_WEBHOOK, json=webhook_body)
                print(f"[n8n RESPONSE] {resp.status_code} {resp.text[:200]}")
        except httpx.HTTPError as exc:
            print(f"[n8n ERROR] {exc}")

    return deal


@router.patch("/{deal_id}")
def update_deal(
    deal_id: str,
    payload: DealUpdate,
    supabase: Client = Depends(get_supabase),
):
    """Partial-update a deal's property metadata (does NOT touch stage).

    Used by the React "Edit Details" form to add/update bedrooms,
    bathrooms, appraisal_price, dates etc. after the deal was created.
    """
    body = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not body:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        supabase.table("deals").update(body).eq("id", deal_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Deal not found")
    return result.data[0]
