# McGrath Workflow Hub

A local development stack that mirrors Airtable's role in the McGrath real-estate automation system. Built for testing and iterating on the n8n + Power Automate + Supabase workflow pipeline before production deployment.

---

## Architecture

```
┌──────────────┐   REST/JSON   ┌──────────────┐  webhooks   ┌──────────────┐  HTTP   ┌────────────────┐
│  React SPA   │ ────────────► │   FastAPI     │ ──────────► │   n8n Cloud  │ ──────► │ Power Automate │
│  :5173       │               │   :8000       │             │  (webhooks)  │         │  (Outlook/Cal) │
└──────┬───────┘               └──────┬────────┘             └──────┬───────┘         └────────────────┘
       │                              │                             │
       │        ┌─────────────────────┴─────────────────────────────┘
       │        │
       ▼        ▼
  ┌────────────────┐
  │    Supabase    │
  │  (PostgreSQL)  │
  │  Single source │
  │  of truth      │
  └────────────────┘
```

**Data flow rule:** React → FastAPI → n8n → Power Automate. React never calls n8n or PA directly.

---

## Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19 + Vite + TypeScript + Tailwind v4 | Simon's dashboard |
| Data fetching | TanStack Query | Cache, polling, optimistic updates |
| Drag & drop | dnd-kit | Kanban board stage changes |
| Backend | FastAPI (Python) | REST API, Supabase client, n8n webhook relay |
| Database | Supabase (PostgreSQL) | deals, contacts, activities, inbound_emails, drafts, errors |
| Orchestration | n8n Cloud | Workflow automation (email, calendar, SMS, LLM classify) |
| Email/Calendar | Power Automate | Outlook send, calendar create, inbound email capture |
| LLM | Google Gemini (via n8n) | Inbound email classification + draft reply generation |

---

## Local Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- Supabase project (tables already created)
- n8n Cloud instance with workflows deployed

### 1. Backend (FastAPI)

```bash
cd api
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create .env from template
copy .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY

# Start
uvicorn api.main:app --reload --port 8000
```

Run from the **project root** (parent of `api/`):
```bash
uvicorn api.main:app --reload --port 8000
```

### 2. Frontend (React)

```bash
cd web
npm install

# Start dev server
npm run dev
```

Opens at http://localhost:5173. The Vite dev server proxies `/api/*` to `localhost:8000`.

---

## Testing End-to-End

### Simulate an inbound email (triggers LLM classification + draft creation)

```bash
curl -X POST https://anubhavjetley.app.n8n.cloud/webhook/inbound-email \
  -H "Content-Type: application/json" \
  -d '{
    "from_email": "vendor@example.com",
    "from_name": "Test Vendor",
    "subject": "Can we reschedule the appraisal?",
    "body_preview": "Hi Simon, I need to move our Tuesday appointment to Thursday if possible. Thanks, Test Vendor",
    "received_at": "2026-05-13T10:00:00Z"
  }'
```

Then check the Drafts page — a new pending draft should appear with AI analysis.

### Create a deal manually

```bash
curl -X POST http://localhost:8000/api/deals \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_name": "Jane Smith",
    "vendor_email": "jane@example.com",
    "vendor_phone": "0412345678",
    "address": "42 Test Street, Sydney",
    "stage": "New Lead"
  }'
```

### Change a deal's stage (triggers n8n workflow)

```bash
curl -X PATCH http://localhost:8000/api/deals/{DEAL_ID}/stage \
  -H "Content-Type: application/json" \
  -d '{"new_stage": "Listing Appointment Booked", "updated_by": "simon"}'
```

### Approve a draft reply

```bash
curl -X POST http://localhost:8000/api/drafts/{DRAFT_ID}/approve
```

---

## n8n Workflows

| Workflow | Webhook Path | Status |
|----------|-------------|--------|
| Inbound Email Handler | `/webhook/inbound-email` | Active (attach Gemini credential) |
| Stage Change Handler | `/webhook/stage-change` | Active |
| Draft Approval Handler | `/webhook/draft-approved` | Inactive (activate manually) |

---

## What's NOT Built Yet

- **Authentication** — single user assumption, no login
- **Row Level Security** — RLS disabled, using service_role key
- **Production hosting** — local dev only
- **Real-time subscriptions** — using polling (30s) instead of Supabase Realtime
- **Email threading** — replies don't track conversation threads
- **File attachments** — not handled
- **Mobile responsive** — desktop-first layout

---

## Project Structure

```
Real_Estate_Automation/
├── api/                    # FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── deals.py
│   │   ├── drafts.py
│   │   └── activities.py
│   ├── requirements.txt
│   └── .env.example
├── web/                    # React frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── hooks/          # TanStack Query hooks
│   │   ├── lib/            # API client, utilities
│   │   ├── pages/          # Route pages
│   │   └── types/          # TypeScript interfaces
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
└── README.md
```
