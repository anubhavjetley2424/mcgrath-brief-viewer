"""Drafts — list pending, approve, edit-and-send, discard.

approve and edit-send write Supabase first, then fire the n8n
draft-approved webhook fire-and-forget. n8n looks the draft back up,
sends the reply via PA-Send-Email, and logs the activity.
"""
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from ..config import N8N_DRAFT_APPROVED_WEBHOOK
from ..database import get_supabase
from ..models import DraftEdit

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fire_n8n(draft_id: str, final_reply: str) -> None:
    if not N8N_DRAFT_APPROVED_WEBHOOK:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                N8N_DRAFT_APPROVED_WEBHOOK,
                json={"draft_id": draft_id, "final_reply": final_reply},
            )
    except httpx.HTTPError as exc:
        print(f"[drafts] n8n webhook error: {exc}")


@router.get("")
def list_drafts(
    status: str = Query("pending_approval"),
    supabase: Client = Depends(get_supabase),
):
    return (
        supabase.table("drafts")
        .select("*, inbound_emails(*)")
        .eq("status", status)
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/{draft_id}")
def get_draft(draft_id: str, supabase: Client = Depends(get_supabase)):
    result = (
        supabase.table("drafts")
        .select("*, inbound_emails(*)")
        .eq("id", draft_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    return result.data[0]


@router.post("/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    approved_by: str = "simon",
    supabase: Client = Depends(get_supabase),
):
    # 1. Read the existing draft to grab suggested_reply
    fetch = (
        supabase.table("drafts").select("*").eq("id", draft_id).limit(1).execute()
    )
    if not fetch.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft = fetch.data[0]
    if draft["status"] != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Draft already in status '{draft['status']}'",
        )
    final_reply = draft.get("suggested_reply") or ""

    # 2. Update Supabase status
    updated = (
        supabase.table("drafts")
        .update(
            {
                "status": "approved_sent",
                "approved_at": _now_iso(),
                "approved_by": approved_by,
                "final_reply_sent": final_reply,
            }
        )
        .eq("id", draft_id)
        .execute()
        .data[0]
    )

    # 3. Fire n8n
    await _fire_n8n(draft_id, final_reply)
    return updated


@router.post("/{draft_id}/edit-send")
async def edit_send_draft(
    draft_id: str,
    payload: DraftEdit,
    supabase: Client = Depends(get_supabase),
):
    # Status guard
    fetch = (
        supabase.table("drafts").select("status").eq("id", draft_id).limit(1).execute()
    )
    if not fetch.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    if fetch.data[0]["status"] != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Draft already in status '{fetch.data[0]['status']}'",
        )

    updated = (
        supabase.table("drafts")
        .update(
            {
                "status": "edited_sent",
                "approved_at": _now_iso(),
                "approved_by": payload.approved_by or "simon",
                "final_reply_sent": payload.edited_reply,
            }
        )
        .eq("id", draft_id)
        .execute()
        .data[0]
    )

    await _fire_n8n(draft_id, payload.edited_reply)
    return updated


@router.post("/{draft_id}/discard")
def discard_draft(draft_id: str, supabase: Client = Depends(get_supabase)):
    result = (
        supabase.table("drafts")
        .update({"status": "discarded"})
        .eq("id", draft_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    return result.data[0]
