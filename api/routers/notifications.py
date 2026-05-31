"""Simon's in-app notifications (bell icon).

Created by n8n stage-change automation (e.g. "Draft ready"). React
polls /api/notifications?status=unread every 30s.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from ..database import get_supabase
from ..models import NotificationUpdate

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    status: str = Query(default="unread"),
    limit: int = Query(default=50, le=200),
    supabase: Client = Depends(get_supabase),
):
    return (
        supabase.table("simon_notifications")
        .select("*")
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


@router.patch("/{notification_id}")
def update_notification(
    notification_id: str,
    payload: NotificationUpdate,
    supabase: Client = Depends(get_supabase),
):
    if payload.status not in ("read", "dismissed"):
        raise HTTPException(
            status_code=400, detail="status must be 'read' or 'dismissed'"
        )
    result = (
        supabase.table("simon_notifications")
        .update({"status": payload.status})
        .eq("id", notification_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result.data[0]
