# Real Estate Lifecycle Automation — Project Context

> **For a new session:** load this file fully before acting. The system is **built and
> migrated to self-hosted infrastructure**. **Stage 1 regression (2026-06-27) believed
> fixed 2026-07-02** — root cause was `SIMON_EMAIL` misconfigured on the VPS (see §10).
> **Current priority — resume Jill's test pass at Stage 4** (Listing Preparation onward —
> Stages 1-3 tested, 4-7 + auction branch still unverified). §13 has the full log of
> changes from the 2026-06-27 session. Keep responses concise; prefer surgical edits over
> rebuilds.

---

## 1. Project

Lifecycle automation for **Simon Jaeger**, McGrath sales agent, Sutherland Shire, Sydney
(sales-only, ~90% houses). Flow: vendor first-contact → settlement → long-term nurture,
with **human-in-the-loop (HITL) approval on all AI-written content**.

**Cost goal achieved:** whole system runs at **~$0/month** — Airtable Free + self-hosted
n8n on Oracle Always-Free VPS + Supabase Free + GCP Cloud Run (within free limits).

---

## 2. Infrastructure — self-hosted n8n on Oracle VPS (the big change)

We migrated n8n OFF the paid n8n Cloud trial onto a self-hosted Oracle Always-Free VM.
This removes the subscription AND the cloud execution cap (critical — we poll Airtable a lot).

| | Detail |
|---|---|
| **VPS (CURRENT)** | Oracle ARM A1, **6 GB RAM**, Ubuntu 22.04 aarch64. Public IP **152.67.124.32** |
| **n8n URL** | `https://152-67-124-32.sslip.io` |
| **SSH** | `ssh -i "ssh-key-2026-06-12 (1).key" ubuntu@152.67.124.32` (key in project root) |
| **HTTPS** | Caddy reverse-proxy + Let's Encrypt, auto-renew. n8n bound to `127.0.0.1:5678`, Caddy fronts 443. Caddyfile at `~/caddy/Caddyfile`. |
| **Containers** | `n8n` + `caddy`, both `--restart always`. SQLite storage in volume `n8n_data`. 2 GB swap. |
| **Secrets** | `~/n8n.env` (chmod 600) → `TEABLE_APP_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `VERCEL_HUB_URL=https://apppskgs9zhzdgrux8z.teable.app`, `REVALIDATE_SECRET=mcgrath-cronulla-2026`, `SIMON_EMAIL`, `AIRTABLE_PAT` (legacy, only used by 2 un-migrated workflows), `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`. Loaded via `--env-file`. Code nodes read `$env.TEABLE_APP_TOKEN` etc. |
| **OLD box** | AMD micro, 1 GB, IP 137.23.17.164 — **STOPPED** (rollback only). Terminate after new box proven. |

⚠️ **DO NOT "Stop" the Oracle instance.** It's an ephemeral IP — stop/start changes the IP,
which breaks the sslip.io hostname + cert + every webhook. (We learned this the hard way: the
old box's IP was lost on a stop/start.) At handoff: reserve the IP + move to a real domain.

⚠️ **sslip.io hostname = `<dash-IP>.sslip.io`** — it literally encodes the IP. If the IP ever
changes, update: Caddyfile, n8n `WEBHOOK_URL`/`N8N_HOST`, `.mcp.json`, `index.html` webhookUrl,
and the Power Automate inbound-email URL.

### MCP connection
`.mcp.json` → `n8n-mcp` points at `https://152-67-124-32.sslip.io/mcp-server/http` with a
bearer token (migrated with the DB, still valid). **Requires full Claude Code restart** to
load. Verify on connect: `search_workflows` then `create` a throwaway workflow — the returned
URL host tells you which instance you're on. VPS workflows have **VPS scopes** (`workflow:export`,
`execution:reveal`) vs cloud's `workflow:updateRedactionSetting`.

⚠️ **Imported workflows have `availableInMCP: false`** — must toggle "Make available in MCP"
on the workflow card before MCP can edit them. Workflows BUILT via MCP are already enabled.

---

## 3. Stack & Accounts

| Component | Detail |
|---|---|
| **n8n** | self-hosted, see §2 |
| **Teable (operational)** | base `Simon Jaeger — Deal Pipeline` (base ID `bseNyDbT8NLAHqyiwoM`) — **Free plan** (1,000 records/base cap is the only constraint; automations moved to n8n polling so runs = 0) |
| **Supabase** | project `xzazkrudrgkcfcznkehb` — data warehouse (sales, scraped data, archive). Anon key browser-side; service-role server-side only. |
| **Power Automate** | email send/reply, calendar create, NewEmail→`…/webhook/inbound-email` |
| **Dashboard** | Next.js App `Simon-Real-Estate-Hub` hosted on Teable Apps (Cuppy). Source zip at `teable/Simon-Real-Estate-Hub.zip`. |
| **GCP** | project `mcgrath-real-estate-automation`, region `australia-southeast1` — Cloud Run scrapers (§7) |

### Teable operational tables (`bseNyDbT8NLAHqyiwoM`)
- Deals `tblppC4hN6LGYw1iV5M` · Tasks `tbln8AKizlrrLkGUPp9` · Drafts `tblpE8jHk3errXpJLEX`
- Signed Submissions `tbl2gpYW40uOPdBxw0N` · Offer Submissions `tblMIMaNdZMtIprku4V`
- Appraisal Submissions `tblO36MrMqlcxeH1pjo` · Activities `tbl0JMf5YxTiAw5wYsR` · Pre-filled Forms `tblvmNuJKXbmlVzCnnP`

### Supabase tables
`vg_sales` (8,500+ rows, Sutherland farm sales) · `da_applications` · `auction_clearance`
· `id_metric_rows` · `appraisal_briefs` · `airtable_archive` (cold storage, §6)

---

## 4. n8n Workflows (all on the VPS; migrated 100% to Teable API)

All 16 workflows use `$env.TEABLE_APP_TOKEN` and point to `https://app.teable.ai/api`.

**Core lifecycle (8):**
1. **Stage Change Handler v2** (`3HzdYO4BxsErioZV`, **89 nodes** after 2026-06-27 dedup hardening) — polls Deals every 2 mins → switch → 12 stage branches. The core. MCP-enabled. Edit big nodes via setNodeParameter. **Each of the 3 Personal Form POSTs now has a SQL-check + IF gate upstream** (`Check Personal {Appraisal,Signing,Offer} Exists` → `Skip If {…} Exists`) so re-firing never creates duplicate forms. **The self-loop on `Task — Personal Offer Received Form` was cut** (was looping to itself, generated 798 dupes — see §13).
2. **Inbound Email Handler** (`STeeyRzc8rSMgaa9`) — IMAP polling on Gmail → Gemini draft → Teable Drafts table (linked via Property Address / Vendor Name).
3. **Draft Approval Handler** (`YXVKtwA1JAigLmf5`) — Draft `Approved` in Teable → PA sends reply from Simon's Outlook.
4. **Dashboard Data API Webhook** (`fyFvlFDozYYDqHb2`) — `/webhook/dashboard-data` merges Teable deal + Supabase data → JSON.
5. **Scheduled Sender** (`2oeZvWLKd4i9Rl5g`) — daily cron to handle scheduled nudges and SMS alerts.
6. **AI Appraisal Prep Brief** (`01JRFxTGTy1H5NSQ`) — Gemini Agent Notes + dashboard inputs.
7. **Vendor Update Monday Cron** (`KfexfXBdrfihSszH`) — Mon 09:00 → weekly vendor-call task per Campaign Live deal.
8. **Scheduled SMS Drafts** (`KUVfvMWJq0gyKzT3`) — daily 09:00 → writes nurture SMS *drafts* onto Sold deals.
8b. **Appointment Readiness Reminder** (`qitydDRKek6xjS5N`) — daily 17:00 → Outlook email to Simon for tomorrow's appointments.

**Polling-based database workflows (5, built in n8n to bypass Teable Automation Run limits):**
*To stay under Teable's 100 free automation runs/month, these workflows poll Teable via standard API GET requests every 2 minutes (0 Teable automation runs used):*
9. **Set Stage on New Deal** (`QR9FNLVxy8BSEJjF`) — Polls Deals where Stage is empty → sets Stage to `"Listing Appointment Booked"`.
10. **Apply Signed Submission → Deal** (`4cYzXDKyv5sHPFgH`) — Polls unprocessed Signed Submissions → PATCH Deal Stage to `"Signed"` + sets processed flag.
11. **Apply Offer Submission → Deal** (`tb81pQFLqSNkrYVG`) — Polls unprocessed Offer Submissions → PATCH Deal Stage to `"Offer Received"`.
12. **Route Offer Outcome → Deal Stage** (`s3shFfCs4B3vQInA`) — Polls offer outcomes → Accepted→Sold / Negotiating→Offer Received / Rejected→Campaign Live.
13. **Apply Appraisal Submission → Deal** (`jhFdTwk0b9CAax14`) — Polls unprocessed Appraisal Submissions → PATCH Deal Appraisal Price + Notes and sets `Processed = true`.
14. **Teable Archive Sweep** (`rqErcUwN65oV32BS`) — weekly completed tasks/drafts sweep.

**Credential on VPS:** Teable Token = `$env.TEABLE_APP_TOKEN`. Gemini (`googlePalmApi`) credential bound.
---

**Bug pattern fixed across form→deal workflows (Jun 2026):** Airtable Trigger output nests fields under `.fields` (only `.id`/`createdTime` are top-level). Original builds read `$json["Field"]` (top-level) → empty; and `Deal Match` is a formula carrying literal quotes → 422 invalid filter. Fix = read `$json.fields["Field"]` **and** patch via the linked **`Deal Reference`** record id (drop the filterByFormula Find-Deal step entirely). Also fixed: a `==` (double-equals) typo in Stage Change Handler's calendar/email jsonBody (made body invalid JSON).

### Airtable Trigger gotchas (learned during the 5-automation build)
- Trigger node **must have credential bound** or activation fails with *"request is invalid or
  could not be processed"*. MCP `setNodeCredential` works for the **trigger** but is rejected
  for **httpRequest** nodes (bind those manually in UI).
- `triggerField` must be a **native "Last Modified Time" or "Created Time" field type** — a
  *formula* returning `LAST_MODIFIED_TIME()` is rejected. For "watch Outcome", add a native
  Last-Modified-Time field tracking that column.
- The PAT needs scope **`schema.bases:read`** (plus `data.records:read/write`) for triggers to
  activate — they introspect the table schema.
- Clear the trigger's `additionalFields.fields` filter if a listed field name mismatches → 422.

---

## 5. SMS policy (FINAL — enforced)

| Channel | Recipient | Examples |
|---|---|---|
| **Airtable tap-send button** → `sms.html` bridge → Simon's phone | **Vendor only** | Confirmation, Welcome, Launch, Congrats, 30/6/12-mo nurture |
| **Outlook email (automated)** | **Simon only** | Day-before appointment reminder (Appointment Readiness Reminder, daily 17:00). Was Twilio SMS — **now email, free**. |
| Twilio (any recipient) | ❌ **RETIRED** | No Twilio anywhere in the system |

**Vendor confirmation at appointment-booking** is a tap-send SMS draft on the Deal (+ the calendar invite, which now carries a 1-line confirmation in its body — the separate "Send Confirmation Email" node is **disabled**). The old 24h *vendor* "meeting tomorrow" Twilio send was removed; Simon gets an email nudge instead and tap-sends the vendor himself.

**Tap-send mechanism:** Airtable button → `Go to URL in record` → `SMS Open URL` formula field →
`https://anubhavjetley2424.github.io/mcgrath-brief-viewer/sms.html?to=<phone>&body=<encoded>` →
the bridge page (`sms.html`) redirects to the native `sms:` scheme → iOS/Android Messages opens
pre-filled → Simon reviews + sends. (Airtable buttons refuse non-http URLs, hence the bridge.)
Contact need NOT be saved — works with a raw number. SMS bodies are **hardcoded templates**
(not Gemini) written into `Deals.Outbound SMS Body`, status `Pending Send`. Confirmation SMS
aligned to Simon's doc (day/time + calendar invite + reviews link + reschedule `0413 032 387`).

---

## 6. Data architecture — Airtable (hot) + Supabase (cold)

Airtable = front desk (live deals/tasks Simon works in). Supabase = warehouse (sales/market
data + archived old records). Keeps Airtable under the 1,000-record Free cap indefinitely.

- **Archive sweep** (`rqErcUwN65oV32BS`): weekly cron copies old completed Tasks/Drafts/
  Scheduled Sends → `airtable_archive` (Supabase), then deletes from Airtable. **DRY_RUN=true,
  INACTIVE** — enable at ~700 records (currently ~240). To enable: set env vars already present,
  run a week in dry-run to verify `airtable_archive` fills, then flip `DRY_RUN=false`.
- Appraisal brief heavy content → Supabase `appraisal_briefs` (Airtable keeps a Brief URL ref).
- Future: internal-ops dashboard reading `airtable_archive` for "look back at old deals".

---

## 7. GCP Cloud Run scrapers (all live + working)

Deploy: `bash scraper/deploy.sh`. Jobs read `SUPABASE_SERVICE_ROLE_KEY` from Secret Manager.

| Job | Cron (AEST) | Writes | Status |
|---|---|---|---|
| vg-weekly-latest | Mon 05:00 | `vg_sales` (Sutherland farm) | ✅ |
| da-delta | 1st & 15th 03:00 | `da_applications` | ✅ |
| auction-current | Sun 02:30 | `auction_clearance` | ✅ |
| id-lga | Sun 04:00 | `id_metric_rows` | ✅ |
| keepalive | Wed 06:00 | Supabase no-pause guard | ✅ |

⚠️ **Newline-in-secret lesson:** if scrapers silently stop writing (scheduler reports success
but container exits 1, `ValueError: Invalid header value …\n`), the Secret Manager
`supabase-service-role-key` has a **trailing newline**. Fix:
`grep '^SUPABASE_SERVICE_KEY=' api/.env | cut -d= -f2- | tr -d '\r\n' | gcloud secrets versions add supabase-service-role-key --data-file=-`

- **Domain `/sale/` + `/sold-listings/` BLOCKED** by Akamai (both curl_cffi + Playwright 403).
  Only `/auction-results/` works. **Superseded by the agency-site scraper pipeline below for
  live listings + recent sales** — Domain is no longer the only path to that data.
  vg_sales table already accepts `source='pricefinder'` rows for when/if PriceFinder lands.
- VG licence CC BY-NC-ND 4.0 — attribution in dashboard footer; McGrath may want commercial licence.

### 7b. Agency-site scrapers (McGrath/Ray White/Belle) — live listings + recent sales (2026-07-02)

Domain being Akamai-blocked led to scraping the agency office sites directly instead —
`curl` with browser headers gets through (no Akamai/Cloudflare on these... except see the
McGrath/Belle caveat below). Code lives in `Appraisal Dashboard Scrapers/`
(`mcgrath_sales.py`, `mcgrath_listings.py`, `raywhite_sales.py`, `belle_sales.py`,
`property_filter.py`, `backfill_ra_images.py`) plus the orchestrator
`scripts/franchise_scraper.py`, which upserts into Supabase `domain_listings_active`
(live/for-sale) and `domain_listings_sold` (recently sold, gap-fills `vg_sales`' 1-3mo
settlement lag). Scope is **Sutherland Shire suburbs only** (`AARON_SUBURBS`/
`AARON_SUBURB_ALLOWLIST`/`AARON_OFFICES` constants in each scraper file — name is a holdover
from the separate TASS project these scrapers were built for, don't be confused by it).

⚠️ **`api/routers/dashboard.py` is DEAD CODE — do not edit it expecting it to affect the live
dashboard.** It has no Dockerfile/Cloud Run config/deploy script anywhere in the repo; nothing
hosts it. The **actual** live appraisal dashboard is the static site `index.html` (repo root
= the `mcgrath-brief-viewer` GitHub Pages site, confirmed via `git remote`), which calls the
**n8n webhook workflow `Dashboard Data API Webhook`** (`fyFvlFDozYYDqHb2`, active, hosted at
`https://152-67-124-32.sslip.io/webhook/dashboard-data`). That n8n workflow's
`Assemble Dashboard Data` Code node — not the Python router — is what actually merges
`domain_listings_sold` into `sales` alongside `vg_sales`, and wires `domain_listings_active`
into `active_listings`. It already had this merge logic before this session (last touched
2026-06-22, predates the McGrath/Ray White live-listing scraper work) — the new scrapers just
feed more/fresher rows into the same tables it already reads.

⚠️ **McGrath and Belle are bot-walled for any datacenter IP** (Vercel Security Checkpoint /
Cloudflare JS challenge respectively) — confirmed via curl from the Oracle VPS: McGrath
returns `429` + `x-vercel-mitigated: challenge`, Belle returns a Cloudflare "Just a
moment..." page. **Ray White has no such wall** and scrapes fine from the VPS. All three
work fine from a residential/ISP IP (e.g. a dev machine).

**Free-tier options tried (2026-07-02), for the record:**
- **Tor** (`apt install tor`, SOCKS5 on 127.0.0.1:9050) — bootstraps fine, but the exit-node
  IP still gets the identical 429/403. Tor exit IPs are public and heavily blocklisted by
  bot-management vendors. Uninstalled — not viable, don't re-try without a new angle.
- **Webshare free tier** (10 free datacenter proxies, account under
  anubhav.jetley123@gmail.com) — all tested proxies are bulk-hosting ASNs (Leaseweb,
  Sollutium, UK-2, Server-Mania) and hit the same wall. No residential bandwidth is actually
  provisioned on the free plan despite marketing copy implying otherwise (confirmed via
  `/api/v2/subscription/plan/`: `proxy_type: "free"`, datacenter only). Not viable.
- **ScraperAPI** (`SCRAPER_PROXY_URL` in `~/n8n.env`, proxy-mode via
  `http://scraperapi:<key>@proxy-server.scraperapi.com:8001`) — **this is what's live today**:
  - **McGrath: works reliably** via plain proxy mode, no premium tier needed. Confirmed live
    in `domain_listings_sold`/`active` with real data.
  - **Belle: unreliable, effectively not viable on the free plan.** Belle's block is a
    Cloudflare *JS challenge*, not just IP reputation — `render=true` (headless-browser
    execution, auto-injected by `belle_sales.py` into the proxy username when
    `SCRAPER_PROXY_URL` contains `scraperapi:`) got through ONCE in testing but failed 3
    times immediately after (~59s each, "Request failed... not charged" — free credits
    aren't burned by failures, but don't expect Belle data from the VPS run). Belle's
    `franchise_scraper.py` crawl is wrapped in try/except so this degrades to 0 results,
    not a crash. Belle coverage instead comes from the **local supplemental run** below.
  - **`-k`/`--insecure` is required** on proxied curl calls (`mcgrath_sales.py` and
    `belle_sales.py`'s `fetch()`, gated behind `if PROXY:`) — ScraperAPI's proxy terminates
    TLS itself and re-encrypts with its own cert, which won't validate against the real
    target hostname. Only affects requests actually routed through the proxy; direct/Ray
    White fetches are untouched.
  - **Plan reality**: the dashboard shows 5,000 credits/month, but that's the **7-day
    trial** (ends 2026-07-09) — the *permanent* free plan is **1,000 credits/month**, no
    card required, no auto-charge on expiry. `franchise_scraper.py`'s `MAX_PROPS` is
    `15` when `SCRAPER_PROXY_URL` is set (else `30`) — with the cron now weekly (~4-5
    runs/month, see below) that's only ~150-190 credits/month, well under the 1,000 cap
    with room to spare even after the trial ends.
  - Account credit usage: `curl "https://api.scraperapi.com/account?api_key=$KEY"`.
  - **McGrath photo galleries** (`backfill_ra_images.py`): McGrath's gallery is client-rendered
    (SPA, `mcgrath-titan.inhabit.com.au`). **Playwright + Chromium is now installed on the VPS**
    (2026-07-02: `pip3 install playwright && python3 -m playwright install --with-deps
    chromium` — works fine on Oracle's ARM64 box, native `manylinux_..._aarch64` wheel exists,
    ~300MB total, well within the 6GB/29GB-free box). `backfill()` already tried Playwright
    first with a ScraperAPI `render=true` fallback (`gallery_mcgrath_via_proxy()`, kept as a
    backstop) — no code change needed once the package existed, it just started using it.
    **Getting Playwright itself to reliably capture the gallery took one more fix**:
    `wait_until="networkidle"` + a fixed `time.sleep()` was NOT a reliable signal for this
    SPA's lazy-mounted carousel (sometimes 0 photos found even when the listing has 8; the
    ScraperAPI proxy version had the exact same unreliability, ~25-50% hit rate). Switched to
    `page.wait_for_selector('img[src*="inhabit.com.au"]', timeout=12000, state="attached")`
    before reading images — a targeted wait for the actual thing we need, not a generic
    network-idle/sleep guess. Result on the small test batch: 3/5 got real galleries, 2/5
    genuinely have zero `inhabit.com.au` references anywhere (verified by direct HTML
    inspection — some older/sold listings just don't have a gallery in McGrath's system, not a
    scraper bug). **At full-pipeline scale the hit rate is much better: 27/30 McGrath listings
    got real galleries** (many with 5-8 photos) in the first full `franchise_scraper.py` run
    after the Playwright install — uploaded to Supabase and confirmed live.

**Dashboard card/data cleanup (2026-07-02, same session)** — three more `index.html` fixes,
found by inspecting the live Kurnell test deal:
- **Property card layout**: address was the small secondary line, price/status was the big
  bold header — backwards from how an agent scans a comps list. Swapped so address is the
  16px header, price/status is the smaller line underneath.
- **Duplicate suburb** ("288 Prince Charles Parade, Kurnell, Kurnell"): the agency scrapers'
  `full_address` already includes the suburb; the card template appended `item.suburb` again
  unconditionally. Fixed to only append if not already present.
- **Marketing copy in the price field**: McGrath's `displayPrice` sometimes carries hype text
  instead of a price ("CALLING FOR OFFERS - MUST BE SOLD NOW!"), or a real price with hype
  appended ("$2,095,000 BUY NOW!"). Added `sanitizePriceText()` — extracts the real price
  figure if one exists, drops pure hype text to a plain "Contact Agent" fallback. Applied in
  three places for defense-in-depth: `index.html` (client-side, fixes already-scraped data
  immediately), and Python (`property_filter.py`'s `sanitize_price_text()`, used by
  `mcgrath_listings.py`/`raywhite_sales.py` so future scrapes store clean text — also means the
  AI Appraisal Prep Brief's Gemini prompt, which reads `price_text` from the same Supabase
  tables, gets clean input too). Three known-dirty existing rows fixed directly via SQL rather
  than waiting for a re-scrape to overwrite them.

**Hybrid model (per user decision 2026-07-02):** the VPS+ScraperAPI cron is the permanent,
always-on baseline (Ray White always; McGrath via proxy; Belle mostly absent) — this is what
keeps running with zero action from Simon/Jill after handoff. A **local supplemental run**
(`scripts/run_franchise_scraper_local.bat`, Windows Task Scheduler task
`RealEstateFranchiseScraperLocal`, weekly Monday 9am, opportunistic — only runs if the dev
machine happens to be on) covers all three agencies at full depth with **zero ScraperAPI
credits**, since a residential/ISP IP isn't blocked by any of the three. **This is the
reliable path for Belle** (and a backstop for anything ScraperAPI's free-tier credit limit
can't cover) — the VPS/ScraperAPI side alone is a complete, functioning system for McGrath +
Ray White, but Belle coverage specifically depends on this local run actually firing.

### 7c. Appraisal-dashboard bug-fixing round (2026-07-02) — n8n workflow fixes

Jill/Simon reported a batch of live-dashboard issues via screenshot (deal `reccHHhqrU21jL0yCBP`,
33 Dampier Street, Kurnell). Fixes landed in **two places**: `index.html` (the static
dashboard site) and **two n8n workflows** (edited live via MCP `update_workflow` +
`publish_workflow` — remember the publish step or the webhook keeps serving the old draft).

**`Dashboard Data API Webhook` (`fyFvlFDozYYDqHb2`) — `Assemble Dashboard Data` node:**
- `subject` object was missing `suburb`/`postcode` entirely — the client tried to regex them
  out of `subject.address`, which is just the raw Teable "Property Address" field (e.g. "33
  Dampier Street", no suburb/state/postcode suffix), so it silently fell back to a hardcoded
  `'Cronulla'` default for EVERY deal whose address didn't already carry a full "`, SUBURB NSW
  POSTCODE`" string. This one bug explained three separate symptoms at once: page title
  missing suburb, map centering on Cronulla regardless of the actual property (Kurnell was
  ~15km outside the visible viewport, so its real comps/listings markers were rendering, just
  off-screen), and suburb-dependent client-side calcs (Property Index cohort, appraisal range
  baseline) silently using the wrong suburb. **Fix**: now returns `subject.suburb` /
  `subject.postcode` (server already resolves these correctly from Teable's `Suburb`/
  `Postcode` fields for its own Supabase queries — it just never passed them back), plus a
  `SUBURB_CENTROIDS` lookup (averaged from real `domain_listings_active` coordinates) used as
  `subject.latitude`/`longitude` fallback whenever Teable has no Lat/Lng set, instead of
  leaving them `null` and having the client fall back to a hardcoded Cronulla center.

**`AI Appraisal Prep Brief` (`01JRFxTGTy1H5NSQ`) — had FOUR independent bugs, meaning no deal
has ever successfully gotten an AI-generated Agent Notes summary before this session, even
ones that reached Pre-Appointment Prep:**
1. **`Map Webhook Payload` (Code node)**: configured as "Run Once for All Items" mode but
   used the bare `input.item.json` syntax, which only exists in "Run Once for Each Item" mode
   → `ReferenceError: input is not defined` on literally every invocation, instantly. Fixed to
   `$input.first().json`.
2. **`Insert appraisal_briefs` (httpRequest, PATCHes the Teable Deal)**: sent
   `{fields: {...}}}` — Teable's API now rejects this with `400 Validation error: Invalid
   input: expected object, received undefined at "record"`. **Teable's single-record PATCH
   endpoint (`PATCH /api/table/{id}/record/{recordId}`) now requires the body wrapped as
   `{record: {fields: {...}}}`** — a breaking API change vs. what the rest of this project's
   workflows assume. Fixed here; **not audited elsewhere** — if other single-record PATCH
   calls across the n8n workflows start failing, check for this exact wrapper first.
3. **`Create Review Task` (httpRequest, creates a Task record)**: sent `"Deal":
   [dealId]` (array) — Teable's `Deal` link field on that table wants a plain object, not an
   array (`400: expected object, received array`). Removed the `Deal` field entirely instead
   of reformatting it — the Tasks table (`tbln8AKizlrrLkGUPp9`) doesn't actually have a working
   Deal link (§9: links via `Property Address` lookup only, already the documented convention
   other Task-creation nodes use).
4. **`Notify Simon` (httpRequest, writes to the notifications table)**: same array-vs-object
   `Deal` field bug (this table DOES have a working Deal link, unlike Tasks — fixed to `{id:
   dealId}` rather than removing it) **plus** two stale field names (`"Notification Name"` →
   `"Title"`, `"Message"` → `"Body"`) that don't exist on the current table schema at all.

All four fixed and verified via a full webhook re-trigger (`POST
https://152-67-124-32.sslip.io/webhook/teable-appraisal-prep` with `{data: {id, fields: {...}}}`
matching Teable's native automation payload shape) → execution status `success` end-to-end,
real Gemini-generated Agent Notes confirmed written back to the Teable deal record.

**Two things Jill/Simon will still notice that are NOT bugs — real data sparsity, not a broken
dashboard:**
- **Some tiles/charts are still legitimately greyed** (Avg Days on Market KPI, the Historical
  DOM chart, the Buyer Engagement/enquiry-volume chart, Withdrawn Listings). None of our
  sources — VG, McGrath, Ray White, Belle — expose *how long* a listing sat on the market over
  time or *how many enquiries* it got; that's platform-internal analytics data (Domain/REA
  have it, we don't scrape it). Property Index and Active Listings were the two that were
  wrongly greyed (fixed above) — these four are correctly greyed pending a real data source
  (Domain API access or PriceFinder, see §12).
- **"Sold" tab looking empty for low-turnover suburbs** (e.g. Kurnell: 0 rows in `vg_sales`,
  1 in `domain_listings_sold` as of 2026-07-02) is real thinness, not a query bug — small
  suburbs just don't transact often, and the agency scrapers have only run a handful of times
  so far. Confirmed both tables directly via SQL before concluding this. Coverage should
  improve as the weekly cron accumulates more runs; if it doesn't after a few weeks, check
  whether `vg_sales`' VG bulk-load actually covers every Sutherland Shire suburb (it may have
  been loaded for a narrower date range or suburb list than the full LGA).

### 7d. Follow-up round the same day — gallery contamination, similar-filter bugs, Supabase cleanup

- **Supabase had 691 stale rows in `domain_listings_active` and 122 in `domain_listings_sold`**
  from before this session's scraper work — legacy `sale:<suburb>` rows from an old
  Domain-based scraper, out-of-scope suburbs from the TASS project's broader council list
  (before this session narrowed scope), and **78 rows literally named `sim_seed`/
  `sim_seed_b2`** — fabricated/simulated test data, not real scrapes at all. Deleted
  everything not matching `source_search LIKE 'franchise_%'` plus any `franchise_%` row
  outside the Sutherland Shire allowlist. Clean state: 36 active (100% with real photos), 46
  sold (42/46 with real photos), all traceable to the actual scraper pipeline.
- **McGrath's "Similar Properties" carousel was contaminating the gallery scrape** —
  `backfill_ra_images.py` grabbed every `<img>` on the page, including a "similar listings"
  widget elsewhere on the page, not just the subject property's own hero gallery (surfaced as
  a listing's photos visibly not matching each other — different houses mixed together).
  McGrath's CDN buckets each *listing's* photos under one numeric folder id
  (`.../hires/<folder_id>/<photo>.jpg`); confirmed one contaminated listing had 8 images split
  ~evenly across 3 different folder ids, not one dominant gallery + stragglers. Fix:
  `_own_gallery_only()` keeps only the leading contiguous run of images sharing the first
  image's folder id (the subject's own gallery is always first in DOM/HTML order) — applied
  in both `gallery_mcgrath_playwright()` and `gallery_mcgrath_via_proxy()`.
- **"Similar Properties Only" filter had a real field-name bug, not just strictness**:
  `index.html` compared against `s.cars` in 4 places, but the subject object's field is
  `s.parking` — `s.cars` is always `undefined`, so the comparison silently used a hardcoded
  fallback of `2` regardless of the vendor's actual car spaces. Compounding bug upstream: the
  n8n `Dashboard Data API Webhook`'s field-alias list for parking didn't include Teable's
  actual field name **"Car Spaces"** (nor did land_size include **"Property Area (Sqm2)"**),
  so `subject.parking`/`subject.land_size` were always `null` regardless of the client-side
  fix. Fixed both, and loosened the car-space tolerance from ±1 to ±2 while at it — parking is
  the least defining comp criterion (a 1-car vs 3-car garage shouldn't disqualify an otherwise
  well-matched bed/bath/land comp).
- **AI Agent Notes had a mojibake bug**: Gemini's UTF-8 output (bullets "•", en-dashes "–")
  round-trips through Teable/n8n and comes back misdecoded as Windows-1252 (`"•"` →
  literal `"â€¢"`). Added `fixMojibake()` — reverses the CP1252→UTF-8-bytes misdecoding when
  every character in the string maps cleanly back through the CP1252 high-byte table,
  otherwise leaves genuinely non-Latin text untouched. **Also redesigned the whole section**:
  was one flat bullet list; now parses each `"**Label**: body"` line by label
  (`parseAgentNotes()`) and routes it into a distinct visual block — price range as a large
  stat, commute times as a two-up stat row, talking points as their own list, hazards as a
  green/red status pill, market profile as closing prose. **Gotcha repeated from the original
  code's own comment and worth remembering**: bullet-marker stripping (`^[•\-\*\s]+`) must NOT
  run before matching the `**Label**` pattern — `*` is itself a bullet-marker character, so
  stripping first eats the opening `**` and the label regex never matches again. Match the
  label on the raw line first, strip bullets from whatever's left over.

**VPS deployment (self-hosted, `152.67.124.32`):** files live at `~/scrapers/` (mirrors the
local repo layout: `~/scrapers/Appraisal Dashboard Scrapers/*.py` +
`~/scrapers/scripts/franchise_scraper.py` — `franchise_scraper.py` resolves the scrapers
folder via `Path(__file__).parent.parent`, so the layout must match). Runs via
`~/scrapers/run_franchise_scraper.sh` (reads `SUPABASE_SERVICE_ROLE_KEY` from `~/n8n.env`,
runs the scrape, POSTs the dashboard revalidate webhook), on a **host crontab** (not inside
the n8n Docker container — that image has no python3, and rebuilding it just to add Python
isn't worth it for a lightweight stdlib-only script). Crontab (weekly, updated 2026-07-02 —
was every-3-days-8am originally):
```
CRON_TZ=Australia/Sydney
0 9 * * 1 /home/ubuntu/scrapers/run_franchise_scraper.sh >> /home/ubuntu/scraper.log 2>&1
```
Runs Monday 9am Sydney time. `CRON_TZ` still matters even weekly — the VPS host clock is
UTC and would otherwise drift against Sydney's DST changes.
`CRON_TZ` matters — the VPS host clock is UTC, and a plain `0 8 * * *` would fire at 6pm
Sydney time today and drift by an hour again in October when Sydney DST changes. Ubuntu
22.04's cron (3.0pl1-137+) supports `CRON_TZ` as the first crontab line.

### 7e. Dashboard fake-data audit (2026-07-02) — Jill's "greyed tiles" report turned into a
wider fabrication audit

Jill flagged the appraisal dashboard's greyed-out tiles (Avg DOM KPI, Historical DOM chart,
Buyer Engagement, Sub-Region Property Liquidity Index). Investigating found those 3 grey
tiles are honestly disclosed — genuinely no DOM/buyer-engagement data source exists anywhere
in the stack (no Domain API access). **But** two charts that looked real were not: the
**Sub-Region Property Liquidity Index** chart and the Analytics **Avg Days on Market** /
**Auction Clearance Rate** charts were rendering `Math.random()`/hardcoded/sine-wave numbers
with no `data-pending` disclosure — i.e. showing fabricated stats to Simon as if real, worse
than being honestly greyed. (Also found, but explicitly out of scope this session per user
decision: the Analytics **Median Price Trend** chart is *also* 100% fabricated from
`BASELINE_MEDIANS` + sine-wave noise, not real `vg_sales` data — flagged for a future pass,
not touched.)

**Fixed (per explicit user decisions):**
- **Real data wired in**: Supabase `auction_clearance` (real weekly Domain auction-results
  scrape, Sydney + Sutherland Shire, back to 2025-10-25) was sitting unused. Added a 7th
  Supabase query to the `Dashboard Data API Webhook` (`fyFvlFDozYYDqHb2`) → `Assemble
  Dashboard Data` Code node, returning `auction_clearance: [{week, region, clearance_rate,
  ...}]` in the JSON payload (edited via MCP `update_workflow` + `publish_workflow` — don't
  forget the publish step, see §8). Both `index.html`'s Analytics "Auction Clearance Rate"
  chart (`renderCharts`) and the Vendor Demand section's chart 4 now plot real
  Sutherland-Shire-vs-Sydney weekly clearance % instead of fake data. Neither chart varies
  with the suburb-comparison pills — clearance data is shire-wide only, no per-suburb
  granularity exists anywhere.
- **Fake series removed entirely** (not just greyed): the Liquidity Index chart's two fake
  DOM lines (`auctionDomData`, `ptDomData`) and the whole Analytics "Avg Days on Market" bar
  chart (`domChart`, plus its HTML card) are gone — there's no real DOM data to back them.
  The now-real Analytics auction chart card was widened to `grid-column: span 2` to fill the
  row left by the removed DOM card. Both charts' `<h4>` titles now say "— real weekly data"
  so it's visible in the UI, not just the code, that they're grounded in something real.
- **Historical snapshotting started** for future Withdrawn Listings support: added Supabase
  table `domain_listings_snapshot_log` (insert-only, unique on `domain_listing_id,
  scraped_week` — unlike `domain_listings_active`, which is upsert-overwritten every run and
  has no history). `scripts/franchise_scraper.py` now writes a snapshot row per active
  listing on every run (step 10, after the existing upserts) and has been deployed to
  `~/scrapers/scripts/franchise_scraper.py` on the VPS via `scp` (verified with
  `python3 -m py_compile`). Nothing reads this table yet — needs several weeks of Monday-cron
  accumulation before a diff job (listing present in an old snapshot week, absent from both
  the current snapshot and `domain_listings_sold` = withdrawn) is meaningful. **Next step
  when picking this back up**: write that diff job once ~4-6 weeks of snapshots exist, wire
  its output into the `Withdrawn Listings` section the same way `auction_clearance` was wired
  in this session.
- Added `.claude/launch.json` (`static-dashboard`, `python -m http.server 8532` at repo root)
  so `index.html` can be previewed locally against the live VPS webhook without a real Mapbox
  token — map tiles fail (expected, token is normally injected by the GitHub Pages/Actions
  deploy, not present locally) but all Chart.js panels render fine off the real webhook data.

---

## 8. Conventions & Gotchas

- **`typecast: true`** in form/PATCH bodies when a single-select value doesn't yet exist (else 422).
- **Airtable/Teable prefill** = `prefill_<exact field label>`, URL-encoded char-for-char.
- **Form Pre-fill Convention**: Keep `Property Address` **visible** on the form (auto-filled by the prefill URL — gives Simon context if he returns to the form later). Hide `Deal` (technical link field), `Status`, `Order Index`, and `Approval Status` from the form layout (system-managed by n8n). Prefill URLs use `prefill_Property%20Address=<encoded address>` only — no Deal record ID needed.
- **Node names use em dash `—`**, not hyphen — search without the dash.
- **HITL boundary:** all AI content → Drafts approval before send; scheduled sends are reminders/templates only.
- **Never paste a PAT in chat.** Put secrets in `~/n8n.env` on the VPS / `api/.env` locally.
- **SSH from PowerShell:** key filenames with spaces/parens need quotes: `"ssh-key-2026-06-12 (1).key"`. Don't pipe `Select-Object` inside a Bash-tool ssh call (use PowerShell tool).
- **iptables on Oracle Ubuntu:** insert ACCEPT rules ABOVE the REJECT (which sits ~line 5), e.g. `iptables -I INPUT 5 -p tcp --dport 443 -j ACCEPT`, then `netfilter-persistent save`. Two firewall layers: Oracle Security List (console) + host iptables.
- **MCP `update_workflow`** drops httpRequest credential bindings — rebind manually after, or use setNodeParameter for surgical edits to big workflows.
- **MCP `update_workflow` writes a draft version; you MUST call `publish_workflow` afterwards** or scheduled triggers keep running the previous published version. Symptom: edit succeeds, polls keep hitting the old node logic.
- Large `get_workflow_details` results spill to a file — parse with Python, don't re-fetch.
- **`docker restart n8n` does NOT reload env vars.** Editing `~/n8n.env` requires `docker stop n8n && docker rm n8n && docker run -d --name n8n --restart always --network host -v n8n_data:/home/node/.n8n --env-file /home/ubuntu/n8n.env -e N8N_HOST=152-67-124-32.sslip.io -e N8N_PROTOCOL=https -e N8N_SECURE_COOKIE=true -e N8N_RUNNERS_ENABLED=true -e WEBHOOK_URL=https://152-67-124-32.sslip.io/ -e TZ=Australia/Sydney -e GENERIC_TIMEZONE=Australia/Sydney -e EXECUTIONS_DATA_PRUNE=true -e EXECUTIONS_DATA_MAX_AGE=168 -e EXECUTIONS_DATA_MAX_COUNT=5000 n8nio/n8n` (preserves the `-e` flags that aren't in the env file). Symptom: `docker exec n8n env` still shows old value after edit-then-restart.
- **`SIMON_EMAIL` env var IS the From-address for vendor-facing emails.** PA's "Send email V2" reads it from the n8n webhook payload as "Send As". If the value is an account the PA O365 connection doesn't have SendAs permission for, PA falls back to sending from the connection account itself (which is currently Jill's, hence test emails arrived with FROM=Jill's email when SIMON_EMAIL was a stale UTS student address).
- **`SIMON_EMAIL` corrected to `SimonJaeger@mcgrath.com.au` (2026-07-02).** The previous value was wrong (a stale test address), which is why vendor-facing sends misbehaved — see above. Fix already applied to `~/n8n.env` on the VPS (container restarted with the full `docker run` recreate command below to pick it up — `docker restart` alone does not reload env vars).

---

## 9. Current Status (as of 2026-06-25)

### Backend — n8n on VPS
All write paths migrated to **Teable API** via `$env.TEABLE_APP_TOKEN`. Stage Change Handler is **polling every 2 min** (last 100+ executions all success → confirmed operational). Set Stage on New Deal auto-fills `Stage = "Listing Appointment Booked"` on new deals where Stage is empty.

| Workflow | Status | Backend |
|---|---|---|
| Stage Change Handler v2 | ✅ Active, polling 2min | Teable |
| Set Stage on New Deal | ✅ Active, polling | Teable |
| Apply Signed Submission → Deal | ✅ Active, polling | Teable |
| Apply Offer Submission → Deal | ✅ Active, polling | Teable |
| Apply Appraisal Submission → Deal | ✅ Active, polling | Teable |
| Route Offer Outcome → Deal Stage | ✅ Active, polling | Teable |
| Inbound Email Handler | ✅ Active, IMAP + Teable | Teable (filters by vendor email match) |
| Draft Approval Handler | ✅ Active, polling | Teable |
| AI Appraisal Prep Brief | ✅ Active | Teable + Gemini |
| Appointment Readiness Reminder | ✅ Active daily 17:00 | Teable |
| Vendor Update Monday Cron | ✅ Active Mon 09:00 | Teable |
| Scheduled SMS Drafts | ✅ Active daily 09:00 | Teable |
| Scheduled Sender | ✅ Active daily | Teable |
| Teable Archive Sweep | ✅ Active (DRY_RUN until ~700 rows) | Teable |
| Dashboard Data API Webhook | ✅ Active | Teable + Supabase |
| Daily Action Digest → Simon | ✅ Migrated 2026-06-25 — was Airtable, now Teable | Teable |
| **Mobile App API** | ⚠️ Active but **still on Airtable** — breaks if PWA used | Airtable (needs migration) |
| **New Draft Alert → Simon** | 🗑️ Marked for deletion (Simon doesn't want per-draft alerts; daily digest covers it) | n/a |

### Front-end — Simon Real Estate Hub (Next.js)
Live at `https://apppskgs9zhzdgrux8z.teable.app` (Teable Apps / Cuppy hosting). Source in `teable/Simon Real Estate Hub-source-code/`, zipped to `teable/Simon-Real-Estate-Hub.zip` for re-deploy. **Build tested via `docker run node:20-alpine` against `next@16.1.6` on the VPS** — always rebuild the zip via Python (`zipfile.as_posix()`) NOT PowerShell `Compress-Archive` (it writes Windows backslashes that break the Teable Apps extractor).

**Performance (current, 2026-06-27 rebuild):**
- ISR everywhere: `revalidate=10` on Kanban/Tasks/Email, `revalidate=30` on Home/Forms/SMS/Offers/Personal Forms, `revalidate=60` on Appraisal. **No `force-dynamic` anywhere.**
- Sidebar `getHubStats()` wrapped in `unstable_cache(..., { revalidate: 30, tags: ['hub-stats'] })`. `/api/revalidate` busts the `hub-stats` tag so n8n writes flip badges instantly.
- `AutoRefresh` is 60s (was 30s — too chatty).
- `app/loading.tsx` skeleton + `components/nav-progress.tsx` top-bar = instant click feedback.
- Tactile button press: `active:scale-[0.97] active:brightness-95` on all Buttons.
- **Hub revalidate webhook**: `POST /api/revalidate?secret=<REVALIDATE_SECRET>` (also accepts `&path=/x`). Wired into 5 n8n workflows (Stage Change v2, Apply Signed, Apply Appraisal, Draft Approval, Inbound Email) as final node "Revalidate Hub Cache".

⚠️ **`sqlQuery` build-time resilience** (`lib/teable.ts`): returns empty `{rows:[]}` only when `NEXT_PHASE === 'phase-production-build'` AND env is missing. At RUNTIME it retries once then **throws** so ISR doesn't cache empty pages (was the "page goes blank for 30s" bug). `app/error.tsx` catches the throw with a friendly Retry UI.

**Home page:**
- Left sidebar (`components/app-sidebar.tsx`) with live badge counts.
- Workflow Guide collapsible (`components/home/workflow-guide.tsx`).
- Live Deals table, Upcoming Appointments, AI Brief preview, Mapbox suburb map.
- Mapbox token in `.env`: `NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1IjoiYW51YmhhdmpldGxleSI…`
- Suburb centroids in `lib/suburbs.ts`.

**Listing Kanban (`components/listings-kanban.tsx`):**
- 8 main-flow columns + Thinking/Not Proceeding branch lanes. Confetti on drag-into-Sold.
- **Method-of-sale filter DROPPED** (2026-06-27, Jill's feedback).
- **Deal Cockpit dialog** (`components/deal-detail-dialog.tsx`) — tap any card. Pre-fetched in `app/listings-pipeline/page.tsx` via parallel `Promise.all` (deals + tasks + email/SMS drafts + forms). Filters per active deal client-side.
  - Quick actions: tap-send SMS / email vendor (`mailto:`) / call vendor (`tel:`) / open appraisal brief
  - Vendor & Property facts (10 fields)
  - Agent notes (amber panel)
  - Linked open tasks with `Mark Done`
  - Linked pending drafts with `Approve` / `Reject`
  - Linked pending pre-filled forms with `Open`

**Open Tasks (`components/open-tasks-list.tsx`, refactored 2026-06-27):**
- Always grouped **Deal → Stage → Task** (no toggle — Jill wanted simplest possible).
- Stage derived in dashboard via `STAGE_HINTS` regex map keyed on task name (Tasks table has no Stage field). Map mirrors which Stage Change Handler branch creates which task.
- Each task shows **Created Xh ago** + **Due [date]**.
- Top sort: **Newest first | Oldest first** (by `__created_time`).
- ⚠️ **Workflow gap**: only 4 of 30 task-creation nodes in Stage Change Handler set a Due Date (the appointment-prep tasks). The other 26 tasks show "No due date" — needs workflow update if Simon wants real due dates per task type.

**Email Drafts (`components/email-drafts-view.tsx`):**
- Header summary block + show-sent toggle REMOVED (Jill's feedback). Pending-only view.
- Each preview now ends with a divider + **Simon's McGrath signature** under "(appended on send)" label — so previewed content = what gets sent.
- ⚠️ **Power Automate's `Send email V2` does NOT auto-append Outlook signature.** Body sent = body field. Until PA is patched to concat `SIMON_SIGNATURE`, the *actual* outbound email has no signature even though the preview shows one. See §11.

**SMS Drafts (`components/sms-drafts-view.tsx`):**
- "Show sent" toggle (filters by `SMS_Status`).
- Sticky sent-time badge on each card.
- ⚠️ **Send-SMS button doesn't flip `SMS_Status` to Sent** (Jill, 2026-06-27). The `sms.html` bridge has the webhook (`8aad189` commit) but something between the bridge and Teable is broken. See §11.

**Performance charts (`components/home/stats-charts.tsx`):**
- Gantt redesigned **multiple times this session**. Current revision (live in the file) reads new `stageEntryDate{Booked,Prep,Signed,ListingPrep,LiveAuction,Sold}` fields off the Deal type — **these fields don't exist in Teable yet**, so the gantt falls back to estimated dates.
- ⚠️ Those "Stage Entry Date — *" fields are appearing in the new-listing form (Jill, 2026-06-27) because they were added to the Deals table without being hidden from the form layout. **MUST hide them from form layout.**
- Method of Sale chart: derives from `auctionDate` (Auction) or stage past Pre-Appointment Prep (Private Treaty) since the `Method_of_Sale` field doesn't exist on Deals.
- Custom branded tooltips on both charts.

**Action writes use field NAMES not IDs** (`hub-actions.ts` passes `fieldKeyType:"name"` to `updateRecord`) — survives Teable table rebuilds where field IDs change.

### Teable
Base `bseNyDbT8NLAHqyiwoM` clean state (user wiped + rebuilt test records). Forms working.

⚠️ **Tasks table has NO Deal link field** — links to Deals via `Property Address` lookup only. Stage Change Handler's 30 Task POST nodes patched to send `"Property Address"` instead of `"Deal": [recId]` (Jun 25).

⚠️ **Activities table `Vendor` is singleLineText** (not link) — patched to write vendor name string, not record ID array.

⚠️ **Field IDs reset when tables are recreated** — never rely on `fldXXX` in client code; use field names + `fieldKeyType:"name"`.

---

## 10. CURRENT TASK — Jill regression test (2026-06-27)

Jill's 2026-06-27 pass found that **new-listing form submissions were not triggering downstream automations** — no emails, no tasks, no SMS.

**Root cause found + fixed 2026-07-02**: `SIMON_EMAIL` on the VPS was a stale test address (see §12 history). Corrected to `SimonJaeger@mcgrath.com.au` and the n8n container was recreated to pick up the env change. **Believed resolved but not yet retested end-to-end** — flagging this because a wrong From-address cleanly explains broken/misdirected *email* sends, but doesn't obviously explain missing *task* or *SMS-draft* creation (those don't read `SIMON_EMAIL` at all). Before fully closing this out: submit one fresh test listing and confirm all three (email, tasks, SMS draft) appear, not just email. If tasks/SMS are still missing, the original investigate steps below are still the right next move.

**If it recurs, investigate:**
1. Is `Set Stage on New Deal` (`QR9FNLVxy8BSEJjF`) still active and polling? It should set the stage within 2 min of form submission.
2. If stage IS set, does Stage Change Handler see the change? Check `Last Processed Stage` on the test deal vs `Stage`.
3. Did the form submit even create a Deals row? Check `__created_time` on the most recent Deal.
4. **`Stage Entry Date — *` fields appearing in the form** (Jill, 2026-06-27) — these were added to the Deals table for the gantt chart but never hidden from the form layout, so Jill sees a wall of confusing fields when filling in a new listing. Hide them in form builder.

### Test pass status
- [x] **Stage 1 — Listing Appointment Booked**: believed fixed 2026-07-02 (see above) — retest to confirm before checking off for real
- [x] **Stage 2 — Pre-Appointment Prep**: drag → AI brief + 3 prep tasks + Personal Appraisal Form (tested 2026-06-25)
- [x] **Stage 3 — Signed**: drag (or submit Signed Submission form) → Personal Signing Form + welcome SMS + marketing tasks (tested 2026-06-25)
- [ ] **Stage 4 — Listing Preparation**: drag → compliance task + Launch Live Approval form
- [ ] **Stage 5 — Campaign Live**: drag → Launch SMS + weekly vendor update task + Personal Offer Received Form
- [ ] **Stage 6 — Offer Received**: submit Personal Offer Received form → outcome routing
- [ ] **Stage 7 — Sold**: outcome=Accepted → congrats SMS + sold marketing + 30/60/12-month nurture drafts
- [ ] Auction branch: drag deal Method=Auction to Auction stage → 5 auction tasks

### Form-creation convention (2026-06-25)
Personal Forms appear **at the stage when Simon needs them**, not pre-loaded:
- `Personal Appraisal Form` → Pre-Appointment Prep
- `Personal Signing Form` → Signed
- `Personal Offer Received Form` → Campaign Live

---

## 11. Known UX issues

### From Jill — 2026-06-27 regression pass (latest)
- [x] 🟡 **New listing form produces no emails, no tasks, no SMS** — believed fixed 2026-07-02 (wrong `SIMON_EMAIL` on VPS, corrected). Not yet retested — see §10.
- [ ] 🔴 **`Stage Entry Date — *` fields appearing in new-listing form**. Eight fields (Booked, Prep, Signed, ListingPrep, LiveAuction, Sold, Thinking, NotProceeding) added to Deals table for the gantt chart but never hidden from the form layout. **Hide them in Teable form builder.**
- [ ] 🔴 **Send-SMS button doesn't flip `SMS_Status` to Sent.** The `sms.html` bridge (commit `8aad189`) is supposed to webhook on tap, but status sticks at `Pending Send`. Trace: bridge → which webhook? → which workflow updates `SMS_Status`?
- [x] **Appraisal dashboard doesn't change per listing** — fixed 2026-07-02, see §7c. The `?deal=` param WAS being read correctly; the real bug was the n8n webhook never returning `subject.suburb`, so several suburb-dependent things (map center, Property Index cohort) silently defaulted to Cronulla regardless of the actual deal, making it look like the brief wasn't differentiating per listing.
- [ ] **Kanban detail dialog is action-only, not editable.** Jill wants to edit vendor name/email/phone/appraisal price etc. from the cockpit. Currently only buttons (mark done, approve, send SMS).
- [ ] **"Add new listing" button on Home Screen.** Currently only on the Listing Kanban page.
- [ ] **Tasks need Monday-style fields**: assignee (for when Simon adds team members), editable due date, editable status, filter by status/date/person, notes. Reference: `https://app.teable.ai/share/shrAHKsbhIvTJp32br8/base`.
- [ ] **Pipeline stage consolidation.** Jill is sending a proposal "this afternoon" (2026-06-27) for a simpler stage list. Currently 8 main + 2 branches. Don't refactor until proposal lands.

### From earlier passes (carry-over)
- [ ] **Listing Opportunity form requires manual Stage selection** — should pre-fill `Listing Appointment Booked`. Fix: in Teable Deals table → click `Stage` column header → Edit field → set Default Value = `Listing Appointment Booked`. Then either keep the field on the form (now pre-filled) or hide it (Set Stage on New Deal polling will set it within 2 min anyway).
- [ ] **Mapbox mobile rendering untested** — may look cramped on phone. If bad, swap for a static suburb-count list or wrap in a `lg:block` so map only shows on desktop.
- [ ] **Daily digest stale email artifacts** — 4 drafts with subjects like "Re: Daily action list: …" exist in Drafts table from prior test cycles. Cleanup: filter Drafts where Reviewer = jillian@reillys.com.au or Draft Name contains "Daily action list" → delete.
- [ ] **Power Automate `Send email V2` does not append Outlook signature.** Dashboard preview shows Simon's signature (cosmetic), but actual outbound emails end at `— Simon` with no contact details. Fix: edit the PA flow's Send-email step to concat `SIMON_SIGNATURE` constant onto the body field. Single source of truth. Constant lives in `components/email-drafts-view.tsx`.
- [ ] **Workflow gap — Due Dates**: only 4 of 30 task-creation nodes set a Due Date in Stage Change Handler (the appointment-prep tasks). Other 26 tasks (Thinking Day X Follow Up, Nurture N Month, Sold Marketing Request, etc.) have no due date. Add sensible defaults per task type if Open Tasks "due" column matters.
- [ ] **Prefill on visible fields didn't work in past tests** (Anubhav). Per Teable docs it should, but a 30-second retry test is needed before designing fallback (dashboard modal that pins property address above an embedded form iframe).
- [ ] **`Method_of_Sale` field doesn't exist on Deals table.** Dashboard derives it from `auctionDate` (Auction) or stage past Pre-Appointment Prep (Private Treaty). If you want Simon to manually set it, add the field to Deals + a select on the cockpit dialog.

---

## 12. Outstanding (pre-handoff)

- [ ] **Migrate Mobile App API to Teable** (~10 min, if Simon uses PWA).
- [ ] **Migrate or delete New Draft Alert → Simon** (~5 min, currently inactive so no urgency).
- [ ] **Set Stage default on Deals table** (UI click — see §11).
- [ ] **Simon's Outlook forwarding rule** → `mcgrath.cronulla.vendor.inbox@gmail.com`. Inbound flow won't work without this.
- [ ] **Domain API project promotion** — wait for Domain approval on pending primary listings package requests.
- [ ] **Rotate exposed credentials at handoff:** Teable Token · Gmail App Password · Domain client_secret · Azure app client secret · `REVALIDATE_SECRET`.
- [x] `SIMON_EMAIL` on VPS swapped to `SimonJaeger@mcgrath.com.au` (2026-07-02).
- [ ] Swap test email `anubhav.jetley123@gmail.com` in vendor records in Teable for Simon's real email (VPS env var already fixed above; Teable test-vendor rows still need updating).
- [ ] Swap test phone `+61404869284` → Simon's real mobile.
- [ ] Transfer Teable base ownership to McGrath.
- [ ] Add free uptime monitor (UptimeRobot) on `https://152-67-124-32.sslip.io` + `https://apppskgs9zhzdgrux8z.teable.app`.
- [ ] **PriceFinder / RP Data**: confirm Simon will use the dashboard + which data source (API vs CSV export).
- [x] **McGrath/Belle proxy decision made 2026-07-02** (see §7b) — ScraperAPI free tier
  wired in via `SCRAPER_PROXY_URL`. McGrath works reliably, $0/mo (permanent free plan is
  1,000 credits/mo, current usage ~475/mo at `MAX_PROPS=15`). Belle remains unreliable even
  with `render=true` — covered instead by the local supplemental Task Scheduler run.
- [ ] **Watch the July 9 2026 ScraperAPI trial-to-free-plan transition** — dashboard
  currently shows 5,000 credits/mo (7-day trial); confirm it actually steps down to the
  1,000/mo permanent free plan rather than requiring card entry, and that `MAX_PROPS=15`'s
  ~475/mo usage still fits comfortably once the trial ends.
- [ ] **Belle live-listing/sold coverage on the VPS is unreliable** — only the local
  supplemental scraper (`RealEstateFranchiseScraperLocal` Task Scheduler job, needs the dev
  machine on) reliably covers Belle. If Belle data matters for handoff, revisit (paid
  ScraperAPI tier, a different vendor, or drop Belle from scope).
- [ ] Editable "Message Templates" area (SMS/email text in Teable) — agreed as a v2 follow-up.
- [ ] Send Anubhav's invoice for hours (at end of testing).
- [ ] Finalize non-technical workbook (`.docx`) for Jill.
- [ ] **Invite Jill to the Teable Apps dashboard** (she asked for access to test directly).

---

## 13. 2026-06-27 session log (the work that happened)

### n8n — Stage Change Handler v2 (live changes via MCP)
- **Cut self-loop** on `Task — Personal Offer Received Form` (was edge `node → node[0]`). This was the source of 798 duplicates of `Offer Received Form - 36 Grange` in the Pre-filled Forms table.
- **Added 3 dedup gates** (6 new nodes) — one SQL-query node + one IF node upstream of each Personal Form POST:
  - `Check Personal Appraisal Exists` → `Skip If Appraisal Exists` → `Task — Personal Appraisal Form` (sits between `Task — 24h Confirm` and the POST)
  - `Check Personal Signing Exists` → `Skip If Signing Exists` → `Task — Personal Signing Form` (sits on Route by Stage[2] = Listing Signed branch)
  - `Check Personal Offer Exists` → `Skip If Offer Exists` → `Task — Personal Offer Received Form` (sits after `Log Campaign Live Started`)
  - SQL pattern: `SELECT "__id" FROM "{base}"."{prefilled-forms}" WHERE "Form_Type" = '<type>' AND "Submission_Name" = '<exact name>' AND lower(COALESCE("Status",'')) = 'pending' LIMIT 1`. IF gates on `($json.rows || []).length === 0`.
- Workflow node count: 83 → 89.

### Teable cleanup
- **Deleted 797 stale Personal Offer Received forms** for `Offer Received Form - 36 Grange`, kept the newest 1. Pending Personal Forms total went 799 → 2.
- Cleanup script pattern (reusable): `POST /api/base/{baseId}/sql-query` to list, then `DELETE /api/table/{tableId}/record?recordIds=...` in batches of 50. Run from the VPS — Teable Cloud has Cloudflare UA filtering that 403s requests from arbitrary IPs; needs a real browser User-Agent header.

### Dashboard — `Simon-Real-Estate-Hub.zip` (108 files, ~128 KB, ready to upload)
1. **Sidebar badge mismatch fixed.** Personal vs non-Personal filter moved into SQL on both `getPendingPreFilledForms` and `getHubStats` so counters can never disagree with page contents.
2. **ISR everywhere, all `force-dynamic` removed.** revalidate: 10s for Kanban/Tasks/Email, 30s for most, 60s for Appraisal.
3. **Sidebar cached** with `unstable_cache(getHubStats, ['hub-stats'], { revalidate: 30, tags: ['hub-stats'] })`. `/api/revalidate` now busts the tag.
4. **`AutoRefresh` slowed** 30s → 60s.
5. **`sqlQuery` resilient**: returns empty only at build time (`NEXT_PHASE === 'phase-production-build'`); retries once then throws at runtime. Fixes the "page goes blank for 30s after navigation" bug.
6. **`app/error.tsx` added** — friendly Retry UI for transient runtime failures.
7. **Open Tasks completely refactored** — always Deal → Stage → Task. Stage derived from task-name regex map (Tasks table has no Stage field). Sort by created date (newest/oldest). Task creation date shown alongside due date.
8. **Email Drafts UI cleaned** — header summary block removed. Each draft preview now shows `SIMON_SIGNATURE` constant below the AI body under "Signature (appended on send)".
9. **Listing Kanban** — method-of-sale filter removed.
10. **Deal Cockpit dialog** (`components/deal-detail-dialog.tsx`) added. Page pre-fetches deals + tasks + email/SMS drafts + forms in one parallel `Promise.all`. Cockpit shows vendor facts, agent notes, linked tasks (Mark Done), linked drafts (Approve/Reject), linked forms (Open), and quick-action strip (tap-send SMS, mailto, tel, appraisal brief deep-link).
11. **Appraisal selector** now reads `?deal=<id>` URL param to pre-select; wrapped in `<Suspense>` (Next 16 requirement for `useSearchParams`).
12. **Performance charts** redesigned. User further customised gantt to read `stageEntryDate*` fields (see §11 — those fields need to be hidden from the form layout).
13. **Build verified** on VPS via `docker run node:20-alpine` against `next@16.1.6` — all 14 pages prerender, zero errors.

### Things I changed but the user further iterated on (after my edits)
- `components/open-tasks-list.tsx` — added safer date parsing (handles invalid `createdTime`).
- `components/sms-drafts-view.tsx` — restored "Show sent" toggle + softer colour styling.
- `components/home/stats-charts.tsx` — added stage-entry-date fields to the gantt for a true timeline (requires Deals table changes — see §11).

### Critical reminders for next session
- **Always zip via Python**: `python3 -c "import zipfile; ..."`. PowerShell `Compress-Archive` writes Windows backslashes that the Teable Apps extractor rejects (silent "Internal Server Error" on upload).
- **Always test-build the source on the VPS** before zipping (`docker run --rm -v /tmp/hub-build:/build -w /build node:20-alpine sh -c 'cd /build && npx next build 2>&1 | tail -30'`). Vercel's "Publish failed" message hides the real build error.
- **Teable Cloud blocks default Python UA** with Cloudflare 1010. Always set `User-Agent: Mozilla/5.0 ...` header for any API call from local or VPS.
