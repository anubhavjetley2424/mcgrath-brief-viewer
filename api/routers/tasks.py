"""Tasks — Simon's per-deal checklist driven by stage-change automation.

Simon ticks tasks done in the React app. Task completion is purely a UI
state change — no downstream n8n automation fires from a tick.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from ..database import get_supabase
from ..models import TaskCreate, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    deal_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    supabase: Client = Depends(get_supabase),
):
    """List tasks. Optionally filter by deal_id and/or status."""
    q = (
        supabase.table("tasks")
        .select("*")
        .order("order_index")
        .order("created_at", desc=False)
    )
    if deal_id:
        q = q.eq("deal_id", deal_id)
    if status:
        q = q.eq("status", status)
    return q.execute().data


@router.post("", status_code=201)
def create_task(
    payload: TaskCreate, supabase: Client = Depends(get_supabase)
):
    """Allow Simon to add an ad-hoc task to a deal."""
    body = payload.model_dump(exclude_unset=True, exclude_none=True, mode="json")
    result = supabase.table("tasks").insert(body).execute()
    return result.data[0]


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    payload: TaskUpdate,
    supabase: Client = Depends(get_supabase),
):
    """Update task status / title / description / due_date.

    Setting status='done' auto-sets completed_at. Moving back to any
    other status clears completed_at.
    """
    update_dict = payload.model_dump(exclude_unset=True, exclude_none=True)
    if payload.status == "done":
        update_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
    elif payload.status in ("open", "in_progress", "skipped"):
        update_dict["completed_at"] = None

    result = (
        supabase.table("tasks").update(update_dict).eq("id", task_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return result.data[0]
