"""Pydantic request/response schemas mirroring the Supabase tables."""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------- Deals ----------
class DealBase(BaseModel):
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    address: Optional[str] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    appraisal_price: Optional[float] = None
    access_notes: Optional[str] = None
    auction_date: Optional[str] = None      # ISO date YYYY-MM-DD
    launch_date: Optional[str] = None       # ISO date YYYY-MM-DD
    settlement_date: Optional[str] = None   # ISO date YYYY-MM-DD


class DealCreate(DealBase):
    vendor_name: str
    vendor_email: str


class DealUpdate(BaseModel):
    """PATCH /api/deals/{id} body — partial update of property metadata."""
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    appraisal_price: Optional[float] = None
    access_notes: Optional[str] = None
    auction_date: Optional[str] = None
    launch_date: Optional[str] = None
    settlement_date: Optional[str] = None
    updated_by: Optional[str] = None


class DealOut(DealBase):
    id: UUID
    vendor_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class StageUpdate(BaseModel):
    """PATCH /api/deals/{id}/stage body.

    `appointment_datetime` is optional but should be provided when
    `new_stage == "Listing Appointment Booked"` so the Calendar PA flow
    has a real start time.
    """

    new_stage: str
    updated_by: str
    appointment_datetime: Optional[str] = None  # ISO-8601


# ---------- Drafts ----------
class DraftOut(BaseModel):
    id: UUID
    inbound_email_id: Optional[UUID] = None
    recipient_email: Optional[str] = None
    original_subject: Optional[str] = None
    intent: Optional[str] = None
    urgency: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    suggested_reply: Optional[str] = None
    extracted_data: Optional[dict[str, Any]] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    final_reply_sent: Optional[str] = None
    created_at: datetime


class DraftEdit(BaseModel):
    edited_reply: str
    approved_by: Optional[str] = "simon"


# ---------- Activities ----------
class ActivityOut(BaseModel):
    id: UUID
    deal_id: Optional[UUID] = None
    action: Optional[str] = None
    channels: Optional[str] = None
    stage: Optional[str] = None
    occurred_at: datetime


# ---------- Tasks ----------
class TaskCreate(BaseModel):
    deal_id: UUID
    title: str
    description: Optional[str] = None
    stage: Optional[str] = None
    task_type: Optional[str] = None  # 'manual_action' | 'system_reminder' | 'external_form'
    due_date: Optional[str] = None  # ISO date (YYYY-MM-DD)
    external_url: Optional[str] = None
    order_index: Optional[int] = 0


class TaskUpdate(BaseModel):
    status: Optional[str] = None  # 'open' | 'in_progress' | 'done' | 'skipped'
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None


class TaskOut(BaseModel):
    id: UUID
    deal_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    stage: Optional[str] = None
    assigned_to: str
    status: str
    due_date: Optional[str] = None
    completed_at: Optional[datetime] = None
    task_type: Optional[str] = None
    external_url: Optional[str] = None
    order_index: int
    created_at: datetime


# ---------- Notifications ----------
class NotificationOut(BaseModel):
    id: UUID
    deal_id: Optional[UUID] = None
    notification_type: Optional[str] = None
    title: str
    body: Optional[str] = None
    action_url: Optional[str] = None
    status: str
    sms_sent: bool
    created_at: datetime


class NotificationUpdate(BaseModel):
    status: str  # 'read' | 'dismissed'


# ---------- Scheduled Sends ----------
class ScheduledSendOut(BaseModel):
    id: UUID
    deal_id: Optional[UUID] = None
    send_type: str  # 'sms' | 'email'
    recipient: str
    subject: Optional[str] = None
    body: str
    scheduled_for: datetime
    sent_at: Optional[datetime] = None
    status: str
    reason: Optional[str] = None
    created_at: datetime
