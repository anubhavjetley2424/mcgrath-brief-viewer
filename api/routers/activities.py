"""Activities — read-only timeline. Filter by deal_id."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from supabase import Client

from ..database import get_supabase

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("")
def list_activities(
    deal_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    supabase: Client = Depends(get_supabase),
):
    q = (
        supabase.table("activities")
        .select("*")
        .order("occurred_at", desc=True)
        .limit(limit)
    )
    if deal_id:
        q = q.eq("deal_id", deal_id)
    return q.execute().data
