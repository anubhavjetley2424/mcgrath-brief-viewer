/* ──── Type definitions mirroring Supabase tables + FastAPI Pydantic models ──── */

export interface Deal {
  id: string;
  vendor_name: string | null;
  vendor_email: string | null;
  vendor_phone: string | null;
  address: string | null;
  stage: string | null;
  notes: string | null;
  vendor_id: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  appraisal_price: number | null;
  access_notes: string | null;
  auction_date: string | null;       // YYYY-MM-DD
  launch_date: string | null;        // YYYY-MM-DD
  settlement_date: string | null;    // YYYY-MM-DD
  created_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface DealWithActivities extends Deal {
  activities: Activity[];
}

export interface DealCreate {
  vendor_name: string;
  vendor_email: string;
  vendor_phone?: string;
  address?: string;
  stage?: string;
  notes?: string;
  bedrooms?: number;
  bathrooms?: number;
  appraisal_price?: number;
  access_notes?: string;
  auction_date?: string;
  launch_date?: string;
  settlement_date?: string;
}

export interface DealUpdate {
  vendor_name?: string;
  vendor_email?: string;
  vendor_phone?: string;
  address?: string;
  notes?: string;
  bedrooms?: number;
  bathrooms?: number;
  appraisal_price?: number;
  access_notes?: string;
  auction_date?: string;
  launch_date?: string;
  settlement_date?: string;
  updated_by?: string;
}

export interface StageUpdate {
  new_stage: string;
  updated_by: string;
  appointment_datetime?: string;
}

export interface InboundEmail {
  id: string;
  from_email: string | null;
  from_name: string | null;
  subject: string | null;
  body_preview: string | null;
  received_at: string | null;
  created_at: string;
}

export interface Draft {
  id: string;
  inbound_email_id: string | null;
  recipient_email: string | null;
  original_subject: string | null;
  intent: string | null;
  urgency: string | null;
  confidence: number | null;
  summary: string | null;
  suggested_reply: string | null;
  extracted_data: Record<string, unknown> | null;
  status: 'pending_approval' | 'approved_sent' | 'edited_sent' | 'discarded';
  approved_by: string | null;
  approved_at: string | null;
  final_reply_sent: string | null;
  created_at: string;
  inbound_emails?: InboundEmail | null;
}

export interface DraftEdit {
  edited_reply: string;
  approved_by?: string;
}

export interface Activity {
  id: string;
  deal_id: string | null;
  action: string | null;
  channels: string | null;
  stage: string | null;
  occurred_at: string;
}

/* Pipeline stages — canonical order */
export const STAGES = [
  'New Lead',
  'Listing Appointment Booked',
  'Pre-Appointment Prep',
  'Appraisal Completed',
  'Negotiation',
  'Listing Signed',
  'Campaign Live',
  'Sold',
] as const;

export type Stage = (typeof STAGES)[number];

/* ──── Tasks ──── */
export type TaskStatus = 'open' | 'in_progress' | 'done' | 'skipped';
export type TaskType = 'manual_action' | 'system_reminder' | 'external_form';

export interface Task {
  id: string;
  deal_id: string | null;
  title: string;
  description: string | null;
  stage: string | null;
  assigned_to: string;
  status: TaskStatus;
  due_date: string | null;
  completed_at: string | null;
  task_type: TaskType | null;
  external_url: string | null;
  order_index: number;
  created_at: string;
}

export interface TaskCreate {
  deal_id: string;
  title: string;
  description?: string;
  stage?: string;
  task_type?: TaskType;
  due_date?: string;
  external_url?: string;
  order_index?: number;
}

export interface TaskUpdate {
  status?: TaskStatus;
  title?: string;
  description?: string;
  due_date?: string;
}

/* ──── Notifications ──── */
export type NotificationStatus = 'unread' | 'read' | 'dismissed';

export interface Notification {
  id: string;
  deal_id: string | null;
  notification_type: string | null;
  title: string;
  body: string | null;
  action_url: string | null;
  status: NotificationStatus;
  sms_sent: boolean;
  created_at: string;
}

export interface NotificationUpdate {
  status: 'read' | 'dismissed';
}

/* ──── Scheduled Sends ──── */
export interface ScheduledSend {
  id: string;
  deal_id: string | null;
  send_type: 'sms' | 'email';
  recipient: string;
  subject: string | null;
  body: string;
  scheduled_for: string;
  sent_at: string | null;
  status: 'scheduled' | 'sent' | 'cancelled' | 'failed';
  reason: string | null;
  created_at: string;
}

/* Urgency levels for colour coding */
export type Urgency = 'high' | 'medium' | 'low';

/* Stage labels for display (handles column widths nicely) */
export const STAGE_SHORT_LABELS: Record<string, string> = {
  'New Lead': 'New Lead',
  'Listing Appointment Booked': 'Appt Booked',
  'Pre-Appointment Prep': 'Pre-Appt Prep',
  'Appraisal Completed': 'Appraisal Done',
  'Negotiation': 'Negotiation',
  'Listing Signed': 'Listing Signed',
  'Campaign Live': 'Campaign Live',
  'Sold': 'Sold',
};

/* Intent categories returned by LLM */
export type Intent =
  | 'appointment_confirm'
  | 'appointment_reschedule'
  | 'price_question'
  | 'marketing_question'
  | 'offer_received'
  | 'unsubscribe'
  | 'vendor_concern'
  | 'general_chat'
  | 'other';
