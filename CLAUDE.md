# Real Estate Lifecycle Automation — Project Context

> **For a new session:** load this file fully before acting. The original workflow is
> built and tested end-to-end. **Current task:** Simon sent an updated process (`.docx`,
> attached to the prompt) — review it, diff against this doc, and propose the specific
> changes. Keep responses concise; prefer surgical edits over rebuilds.

---

## 1. Project

Lifecycle automation for **Simon Jaeger**, McGrath sales agent, Sutherland Shire, Sydney
(sales-only, ~90% houses). Flow: vendor first-contact → settlement → long-term nurture,
with **human-in-the-loop (HITL) approval on all AI-written content**.

---

## 2. Stack & Accounts

| Component | Detail |
|---|---|
| **n8n cloud (NEW)** | `https://jetley2424.app.n8n.cloud` — 7 workflows |
| **Airtable (operational)** | base `appZvH2KGn5rc6sd8` "Simon Jaeger — Deal Pipeline" |
| **Airtable (McGrath forms)** | base `appvTX5GSGGSRHV1c` — **NOT accessible by our PAT** (McGrath-owned); we only generate prefilled share-links into it |
| **Supabase (reference data)** | project `xzazkrudrgkcfcznkehb`, read via anon key |
| **Power Automate** | email send, email reply, calendar create, NewEmail→inbound webhook |
| **Twilio** | trial (verified numbers only); from `+18149836911`; adds trial prefix |
| **Dashboard** | GitHub Pages repo `anubhavjetley2424/mcgrath-brief-viewer`; local `index.html`; fetches `…/webhook/dashboard-data?deal=<recId>` |

### Airtable operational tables (`appZvH2KGn5rc6sd8`)
- Deals `tblZfaTySImrUc3CD`
- Tasks `tblC33Ign9bz568JD`
- Drafts
- Activities
- Notifications
- Scheduled Sends `tbl2CSzuBFI2mR6b6`
- Pre-Filled Forms / Submissions `tblOhSlZkzSIwSmvU`

### MCP connection
n8n MCP is configured in this project's `.mcp.json` → points to `jetley2424`.
**Requires a full Claude Code restart to take effect.** Verify with `search_workflows`:
NEW-instance workflows were created **2 June**; old ones created **late May**. If you see
May dates, the MCP is still on the old instance.

---

## 3. The 7 n8n Workflows

1. **Inbound Email Handler** — vendor email → deal match → Gemini draft → Drafts table (awaiting approval).
2. **Draft Approval Handler** — on Draft `Approved` → Power Automate sends the reply.
3. **Stage Change Handler** (~62 nodes, id `mF0Y7GOJuz2ZNvlx`) — **the core.** Airtable trigger on Deal `Stage` change → "Route by Stage" switch → 7 stage branches.
   - ⚠️ **Too large to safely re-emit via MCP — edit via n8n UI only.**
   - Dedup via a `Last Processed Stage` comparison; to re-fire a stage, bounce the deal back then forward.
4. **Dashboard Data API Webhook** — Code node merges Airtable deal + Supabase suburb data → JSON.
   - ⚠️ **Hardcodes the Airtable PAT** in the Code node (`AIRTABLE_TOKEN`); `AIRTABLE_BASE` must be `appZvH2KGn5rc6sd8` (a prior bug pasted a token fragment there). Should be refactored to use the bound credential.
5. **Scheduled Sender** — **hourly** poll of Scheduled Sends for due rows → sends SMS (Twilio) / email (PA), marks Sent/Failed. (Reduced from 15-min to save quota.)
6. **AI Appraisal Prep Brief** — generates Agent Notes + dashboard inputs (Gemini).
7. **Biweekly SSC DA Scraper** — DA scraper; **times out on n8n's 60s limit → needs external GCP Cloud Run** (not built yet).

---

## 4. Stage Flow — what each branch produces

| Stage | Outputs |
|---|---|
| Listing Appointment Booked | calendar invite, confirmation SMS, 24h reminder (scheduled), pre-appointment tasks |
| Pre-Appointment Prep | tasks (CMA, slides, confirm 24h, review brief) + **Marketing Quote** form + AI dashboard |
| Appraisal Completed | appraisal follow-up draft + Twilio reminder to Simon |
| Negotiation | Day 2/5/10 nudges (scheduled SMS **to Simon**) + auto-cancel remaining nudges on vendor reply |
| Listing Signed | welcome draft, tasks (New Listing Set Up, WhatsApp group) + 4 prefilled forms |
| Campaign Live | launch draft, weekly-update reminder (to Simon) + Launch Live Approval form |
| Sold | congrats draft, settlement tasks, 6/12-month nurture SMS (scheduled) + Sold Marketing + Prep Settlement forms |

---

## 5. The 8 Prefilled Forms (links in McGrath base `appvTX5GSGGSRHV1c`)

| Form | Share link | Stage |
|---|---|---|
| Marketing Quote | `shrhVw3cM24Kk1Mke` | Pre-Appointment Prep |
| New Listing Set Up | `shrmccNo8lY673vSZ` | Listing Signed |
| SWAT Request | `shrrOGHTRsgaWNLEt` | Listing Signed |
| Auction Booking | `shrj0SClkj45Ix7LQ` | Listing Signed |
| Listing Compliance | `shrOkU7NbCJwAfVFw` | Listing Signed |
| Launch Live Approval | `shr4pzOlv53l6Eyr6` | Campaign Live |
| Sold Marketing Request | `shrYeZHRfqn0SXvIw` | Sold |
| Preparation for Settlement | `shr7ZdWeoljzEF4Cd` | Sold |

Form-generator nodes live in the Stage Change Handler, named `Task — <Form>` (em dash `—`,
not hyphen). They write to Submissions table `tblOhSlZkzSIwSmvU`.

---

## 6. Conventions & Gotchas

- **`typecast: true`** required in form-generator request bodies when a `Form Type`/`Stage`
  single-select value doesn't yet exist as an option (else Airtable 422).
- **Airtable prefill** = `prefill_<exact field label>`, URL-encoded **char-for-char**
  (spaces `%20`, `?`→`%3F`). A label mismatch silently fails to fill.
- In the n8n UI, paste expression bodies **without the leading `=`** (the `=` is n8n's
  internal/SDK marker only).
- **Node names use em dash `—`**, not hyphen — search without the dash to find them.
- **Twilio internal nudges/reminders** currently hardcoded to `+61404869284` (test number
  standing in for Simon) → **swap to Simon's real mobile at handoff**.
- **HITL boundary:** all AI-written content → Drafts approval before send; scheduled sends
  are reminders / fixed templates only.
- Simon's documented marketing defaults: `Si realestate processes.docx` (already encoded in
  the Marketing Quote prefill).
- **Never paste a new Airtable PAT in chat.** A PAT must have base `appZvH2KGn5rc6sd8` in its
  **Access** list + scopes `data.records:read` / `:write`.
- MCP `update_workflow` re-emits the WHOLE workflow and drops credential bindings — fine for
  small workflows (e.g. Scheduled Sender, 12 nodes), **not** for the 62-node Stage Change
  Handler (UI edits only there).
- n8n Workflow SDK quirks: `switchCase` uses numeric `onCase(0,…)` not string labels;
  `onDefault` is blocked; error branch wiring = `.add(node.output(1).to(target))`.

---

## 7. Current Status

- Original workflow **built + tested end-to-end** on the new instance.
- Test deal: **"Deal #2" / 14 Gannons Road, Caringbah** (record `rectVRtSYfU1cVuOz`).
- Dashboard live and returning correct data.
- All 8 forms generating + prefilling correctly.
- Showcase email to Jill & Simon essentially done.

---

## 8. Outstanding (pre-handoff)

- [x] GCP Cloud Run scraper scaffolded — see `scraper/`. Ships **3 live jobs** (auction-current, da-delta, id-lga) + keepalive + 2 manual backfills. Deploy with `bash scraper/deploy.sh` after running `gcloud auth login` and adding `supabase-service-role-key` to Secret Manager.
- [ ] **Domain sale + sold scraping is BLOCKED** by Akamai Bot Manager — `/sale/` and `/sold-listings/` paths only (`/auction-results/` still works via curl_cffi chrome124). Both curl_cffi impersonation and Playwright headless return 403 on those two paths. Unblocks when McGrath secures official Domain API access — ask `developer@domain.com.au` or whether McGrath corporate already has a data licence. Until then, dashboard's sales + active-listings cards stay blank.
- [ ] **Supabase service-role key:** scrapers now read `SUPABASE_SERVICE_ROLE_KEY` from env (anon fallback for local read-only). Cloud Run jobs read it from Secret Manager. Add the secret version once before first deploy: `echo -n "<service-role JWT>" | gcloud secrets versions add supabase-service-role-key --data-file=-`.
- [ ] **Upgrade Supabase to Pro ($25/mo) before McGrath handoff** — Free auto-pauses after 7 inactive days. The keepalive job mitigates but Pro removes the pause behaviour entirely + adds proper backups.
- [ ] Swap test phone `+61404869284` → Simon's real number.
- [ ] Transfer Supabase project to McGrath ownership.
- [ ] Rotate Google Maps API key + restrict by referrer.
- [ ] Set Stage Change Handler trigger back to **hourly** (currently fast-polling for testing).
- [ ] Refactor Dashboard webhook to use bound Airtable credential (remove hardcoded PAT).
- [ ] Pivot `index.html` to read scraped data from Supabase directly (today still goes through n8n webhook).
- [ ] Finalize the non-technical workbook (`.docx`).

---

## 9. Current Task

**Simon sent an updated workflow/process in the attached `.docx`.** Review it, diff against
sections 3–5 above, and propose the specific changes (new/edited stage branches, forms,
drafts, scheduling, tasks). Confirm assumptions before large edits; keep it concise.
