/**
 * Typed fetch wrapper for the FastAPI backend.
 *
 * In dev, Vite proxies /api/* to localhost:8000, so we can use relative URLs.
 * In prod, set VITE_API_URL to the backend host.
 */

const BASE =
  import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL !== 'http://localhost:8000'
    ? import.meta.env.VITE_API_URL
    : '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

/* ──── Deals ──── */
import type {
  Deal,
  DealCreate,
  DealUpdate,
  DealWithActivities,
  StageUpdate,
  Draft,
  DraftEdit,
  Activity,
  Task,
  TaskCreate,
  TaskUpdate,
  Notification,
  NotificationUpdate,
  ScheduledSend,
} from '../types/api';

export const deals = {
  list: () => request<Deal[]>('/api/deals'),
  get: (id: string) => request<DealWithActivities>(`/api/deals/${id}`),
  create: (data: DealCreate) =>
    request<Deal>('/api/deals', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: DealUpdate) =>
    request<Deal>(`/api/deals/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateStage: (id: string, data: StageUpdate) =>
    request<Deal>(`/api/deals/${id}/stage`, { method: 'PATCH', body: JSON.stringify(data) }),
};

/* ──── Drafts ──── */
export const drafts = {
  list: (status = 'pending_approval') =>
    request<Draft[]>(`/api/drafts?status=${status}`),
  get: (id: string) => request<Draft>(`/api/drafts/${id}`),
  approve: (id: string) =>
    request<Draft>(`/api/drafts/${id}/approve`, { method: 'POST' }),
  editSend: (id: string, data: DraftEdit) =>
    request<Draft>(`/api/drafts/${id}/edit-send`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  discard: (id: string) =>
    request<Draft>(`/api/drafts/${id}/discard`, { method: 'POST' }),
};

/* ──── Activities ──── */
export const activities = {
  list: (params?: { deal_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.deal_id) sp.set('deal_id', params.deal_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<Activity[]>(`/api/activities${qs ? `?${qs}` : ''}`);
  },
};

/* ──── Tasks ──── */
export const tasks = {
  list: (params?: { deal_id?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.deal_id) sp.set('deal_id', params.deal_id);
    if (params?.status) sp.set('status', params.status);
    const qs = sp.toString();
    return request<Task[]>(`/api/tasks${qs ? `?${qs}` : ''}`);
  },
  create: (data: TaskCreate) =>
    request<Task>('/api/tasks', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: TaskUpdate) =>
    request<Task>(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};

/* ──── Notifications ──── */
export const notifications = {
  list: (status = 'unread') =>
    request<Notification[]>(`/api/notifications?status=${status}`),
  update: (id: string, data: NotificationUpdate) =>
    request<Notification>(`/api/notifications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

/* ──── Scheduled Sends ──── */
export const scheduledSends = {
  list: (params?: { deal_id?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.deal_id) sp.set('deal_id', params.deal_id);
    if (params?.status) sp.set('status', params.status);
    const qs = sp.toString();
    return request<ScheduledSend[]>(`/api/scheduled-sends${qs ? `?${qs}` : ''}`);
  },
  cancel: (id: string) =>
    request<ScheduledSend>(`/api/scheduled-sends/${id}`, { method: 'DELETE' }),
};
