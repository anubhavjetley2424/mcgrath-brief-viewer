"""Scheduled sends — future-dated SMS/email queued by n8n automation.

The Scheduled Sender n8n workflow polls this table every 15 minutes
and dispatches anything where status='scheduled' AND scheduled_for <= now().

Simon can see what's queued per deal and DELETE (cancel) any item.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from ..database import get_supabase

router = APIRouter(prefix="/api/scheduled-sends", tags=["scheduled-sends"])


@router.get("")
def list_scheduled_sends(
    deal_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="scheduled"),
    supabase: Client = Depends(get_supabase),
):
    """List queued sends. Default filter = status='scheduled' (upcoming)."""
    q = (
        supabase.table("scheduled_sends")
        .select("*")
        .order("scheduled_for", desc=False)
    )
    if deal_id:
        q = q.eq("deal_id", deal_id)
    if status:
        q = q.eq("status", status)
    return q.execute().data


@router.delete("/{send_id}")
def cancel_scheduled_send(
    send_id: str, supabase: Client = Depends(get_supabase)
):
    """Cancel a queued send (sets status='cancelled', won't be dispatched)."""
    result = (
        supabase.table("scheduled_sends")
        .update({"status": "cancelled"})
        .eq("id", send_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Scheduled send not found")
    return result.data[0]
