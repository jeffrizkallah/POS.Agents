# New Agents Spec

These 6 agents are **generic and reusable**. They are not built for any specific company. When connected to a new client's database, they read their configuration from a `brands` table and adapt their behavior accordingly — tone, channels, language, industry, keywords, and business rules all come from config, not code.

This follows the same pattern as the existing agents: plug in a new `client_id`, and the agents pick it up automatically on the next job run.

---

## How Plug-and-Play Works

Every agent loops over all active clients and brands, exactly like the existing agents loop over restaurants:

```python
async def _async_scout_job():
    clients = await get_all_clients(pool)
    for client in clients:
        brands = await get_brands_for_client(pool, client["id"])
        for brand in brands:
            try:
                await run_scout(pool, client["id"], brand)
            except Exception as e:
                print(f"[Scout] {brand['name']}: {e}")
```

All brand-specific behavior (tone, channels, language, industry, target audience) is stored in the `brands` table and passed into Claude prompts as context. No brand names or rules are hardcoded in agent logic.

---

## Core Config Tables (Required Before Any Agent Runs)

These tables drive all agent behavior. They are set up once per client onboarding.

### `clients`
One row per company using the platform.
```
id, name, owner_email, owner_whatsapp, timezone, currency, created_at, is_active
```

### `brands`
One row per brand a client operates. A client can have one or many brands.
```
id, client_id, name, industry, business_model (b2b | d2c | both),
primary_channel (linkedin | instagram | email | whatsapp),
tone (professional | warm | casual | authoritative),
language_primary, language_secondary (nullable — for bilingual brands),
target_audience (free text: who they sell to),
avg_deal_value, avg_customer_ltv, currency,
roi_target_multiplier (default 20),
is_active
```

### `brand_channels`
Which platforms each brand is active on, with credentials.
```
id, brand_id, platform (linkedin | instagram | whatsapp | email | web),
account_id, access_token, is_active
```

### `brand_keywords`
SEO and content keywords per brand.
```
id, brand_id, keyword, intent (informational | transactional | navigational),
cluster_topic, is_priority, status (identified | in_progress | published)
```

---

## Agent 1 — Scout

**Purpose:** Lead discovery and qualification. Finds potential customers for a brand and scores them.

**Schedule:** Daily 7:00 AM weekdays

**Claude Model:** `claude-sonnet-4-5`

### What it reads
- `brands` — industry, target_audience, avg_deal_value, roi_target_multiplier
- `client_leads` — existing leads (to avoid re-qualifying)
- `client_contracts` — renewal dates, contract values (if client tracks contracts)
- External: web scraping via SerpAPI (optional)

### What it does
1. For each brand, fetches its target audience profile and industry from config
2. Researches and qualifies potential leads using a scoring rubric built from brand config:
   - Score 1–10 based on fit signals (size, location, budget signals, competitor usage, timing)
   - Only queues leads with score ≥ 6 (configurable via `brand.lead_score_threshold`)
3. Detects renewal windows on existing contracts (90-day alert window)
4. Calculates ROI potential per lead: `avg_deal_value × roi_target_multiplier` to justify outreach cost
5. Queues qualified leads for owner approval before any contact is made

### What it writes
- `client_prospects` — researched companies/individuals + `qualification_score`, `roi_estimate`, `fit_signals`
- `client_leads` — `status: pending_approval` (after passing score threshold)
- `client_intelligence` — renewal alerts, market insights

### Guardrails
- Score ≥ 6 required (configurable per brand)
- Max 3 new prospect lookups per brand per cycle (API cost control)
- No lead enters pipeline without owner approval
- ROI estimate must be ≥ `brand.roi_target_multiplier` × research cost before queuing

### Claude receives (built from config, not hardcoded)
```json
{
  "brand_name": "...",
  "industry": "...",
  "target_audience": "...",
  "avg_deal_value": 0,
  "currency": "...",
  "roi_target": 20,
  "prospect": { "name": "...", "signals": [...] }
}
```

### Claude Prompts Needed
- `prompts/scout_qualify.txt` — Generic qualification framework. Receives brand config + prospect data. Returns score, reasoning, fit_signals, roi_estimate.
- `prompts/scout_research.txt` — Generic research brief. Given brand target audience, identifies what to look for and how to score prospects.

### New DB Tables
- `client_prospects`
- `client_leads`
- `client_contracts` (optional — only if client tracks contracts)
- `client_intelligence`

### New Env Vars
- `SERPAPI_KEY` (optional — web research)

---

## Agent 2 — Pipeline

**Purpose:** Generates outreach sequences for approved leads. Personalizes per brand, channel, and funnel stage.

**Schedule:** Daily 9:00 AM weekdays + triggered when leads are approved

**Claude Model:** `claude-sonnet-4-5`

### What it reads
- `client_leads` where `status = approved`
- `client_subscribers` — existing customers in nurture funnel (by stage)
- `brands` — tone, primary_channel, language settings
- `brand_channels` — which platforms are active
- Lead metadata (deal value, fit signals, renewal dates from Scout)

### What it does
1. For each approved lead, generates a multi-step outreach sequence adapted to:
   - The brand's primary channel (email, LinkedIn, WhatsApp, etc.)
   - The brand's tone (professional, warm, casual)
   - The lead's specific signals (industry, size, timing, pain points from Scout)
   - Language config (bilingual if `language_secondary` is set)
2. For existing customers, generates stage-appropriate nurture messages (awareness → trial → subscribed → win_back)
3. Drafts Step 1 only for approval — subsequent steps auto-schedule after Step 1 is approved

### Sequence structure (configurable per brand)
- Default: 5-step new acquisition sequence
- Renewal leads: 3-step sequence triggered by contract renewal window
- Nurture: stage-specific single messages per funnel transition

### What it writes
- `client_outreach` — all steps drafted, Step 1 `status: pending_approval`, Steps 2–N `status: draft`
- `client_nurture_messages` — stage-based messages for existing customers, `status: pending_approval`

### Guardrails
- Step 1 always requires approval before anything goes out
- Steps 2–N auto-execute on schedule only after Step 1 is approved
- Word limits come from brand config (`brand.outreach_word_limit`, default 130 for Step 1, 100 for subsequent)
- Tone pulled from `brands.tone` — never hardcoded
- Bilingual content generated only when `brands.language_secondary` is set

### Claude receives (built from config)
```json
{
  "brand_name": "...",
  "tone": "professional",
  "primary_channel": "email",
  "language_primary": "en",
  "language_secondary": null,
  "lead": { "name": "...", "industry": "...", "fit_signals": [...] },
  "sequence_type": "new_acquisition | renewal | nurture",
  "step_number": 1,
  "word_limit": 130
}
```

### Claude Prompts Needed
- `prompts/pipeline_sequence.txt` — Generic outreach sequence generator. Brand tone + channel + lead context in, personalized message out.
- `prompts/pipeline_nurture.txt` — Generic nurture message per funnel stage. Stage-aware, brand tone aware.

### New DB Tables
- `client_outreach`
- `client_nurture_messages`

### New Env Vars
- `LINKEDIN_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`

---

## Agent 3 — Broadcast

**Purpose:** Social media content generation, scheduling, publishing, and comment engagement.

**Schedule:**
- Every 30 minutes: check publish queue
- Every 2 hours: sync engagement metrics
- Every Monday 6:00 AM: generate weekly content batch

**Claude Model:** `claude-sonnet-4-5`

### What it reads
- `brands` — tone, language settings, industry, target audience
- `brand_channels` — which platforms + credentials
- `client_social_posts` where `status = approved` (publish queue)
- `client_social_comments` — unresponded comments on published posts
- `client_content_catalog` — products, services, offerings (for content ideas)

### What it does
1. **Weekly batch (Monday):** Generates a week of content per brand per active channel:
   - Post type, frequency, and pillars come from `brand_content_config` table
   - Captions adapt to channel (LinkedIn long-form vs Instagram short + visual brief)
   - Bilingual captions generated automatically when `language_secondary` is set
2. Publishes approved posts at optimal times
3. Syncs engagement metrics (likes, comments, reach, impressions)
4. Classifies comments (positive, neutral, negative, spam) and drafts replies in brand tone
5. Flags for human escalation: safety issues, legal threats, complaints requiring judgement

### What it writes
- `client_social_posts` — `status: pending_approval → approved → published` + engagement metrics
- `client_social_comments` — classification, sentiment, reply_draft, `status: pending_approval | escalated`

### Guardrails
- Every post requires approval before publishing
- Reply drafts require approval before sending
- Tone and word count come from brand config, not hardcoded
- Bilingual only when configured — never assumed
- Escalation to human when: safety/legal risk, complaint, requires info agent doesn't have

### Claude receives (built from config)
```json
{
  "brand_name": "...",
  "industry": "...",
  "tone": "professional",
  "platform": "linkedin",
  "language_primary": "en",
  "language_secondary": null,
  "content_pillar": "thought_leadership",
  "target_audience": "...",
  "word_limit": 250,
  "catalog_items": [...]
}
```

### Claude Prompts Needed
- `prompts/broadcast_post.txt` — Generic post generator. Platform + tone + pillar + brand context in, caption (+ visual brief for video) out.
- `prompts/broadcast_comment.txt` — Generic comment classifier + reply drafter. Brand tone aware. Returns: sentiment, requires_reply, reply_draft, escalate_to_human.

### New DB Tables
- `client_social_posts`
- `client_social_comments`
- `brand_content_config` (post frequency, pillars, word limits per brand per platform)

### New Env Vars
- `META_INSTAGRAM_ACCOUNT_ID`
- `META_ACCESS_TOKEN`
- `LINKEDIN_ACCESS_TOKEN`

---

## Agent 4 — SEO Engine

**Purpose:** Generates SEO keyword clusters and long-form articles for any brand in any industry.

**Schedule:** Every Monday 6:00 AM

**Claude Model:** `claude-sonnet-4-5`

### What it reads
- `brand_keywords` where `status = identified` — keywords to write about
- `client_seo_content` — existing articles (to avoid duplication)
- `brands` — industry, target audience, location (for geo-specific SEO)

### What it does
1. Identifies new keyword clusters (10–15 keywords per cluster: search_volume_estimate, difficulty_estimate, intent, cluster_topic) — based on brand's industry + target audience
2. Generates articles (950–1,400 words) per keyword:
   - Primary keyword in H1, first 80 words, one H2, meta description
   - 4+ FAQ section (for featured snippets)
   - JSON-LD schema (Article + FAQPage, with LocalBusiness if location-based)
   - Natural keyword density (1–2% primary, 0.5–1% secondary)
   - 2–3 internal link suggestions
   - Geographic references pulled from brand config (city, region)
   - `seo_score` 1–100
3. Targets 4 articles/week per client (configurable) after approval

### What it writes
- `brand_keywords` — updates `status: identified → in_progress`
- `client_seo_content` — title, slug, content_markdown, meta_title, meta_description, schema_markup, word_count, seo_score, `status: pending_approval`

### Guardrails
- Every article requires approval before publishing
- Never duplicate a keyword already covered in `client_seo_content`
- Quality over quantity — max articles/week pulled from brand config

### Claude receives (built from config)
```json
{
  "brand_name": "...",
  "industry": "...",
  "target_audience": "...",
  "location": "...",
  "primary_keyword": "...",
  "secondary_keywords": [...],
  "word_count_target": 1200,
  "existing_articles": ["slug1", "slug2"]
}
```

### Claude Prompts Needed
- `prompts/seo_article.txt` — Generic SEO article generator. Brand context + keyword in, full article with schema out.
- `prompts/seo_keywords.txt` — Generic keyword cluster generator. Brand industry + audience in, keyword cluster with intent/difficulty out.

### New DB Tables
- `client_seo_content`
- `brand_keywords` (also used by config setup)

### New Env Vars
- None

---

## Agent 5 — Customer Care

**Purpose:** Feedback triage, response drafting, competitor intelligence, and strategic opportunity analysis.

**Schedule:**
- Every 30 minutes: process new feedback
- 1st of every month, 6:00 AM: competitive intelligence deep scan

**Claude Model:** `claude-sonnet-4-5`

### What it reads
- `client_feedback` — new entries (from QR codes, email, WhatsApp, web forms)
- `client_competitors` — competitor profiles per brand
- Competitor data: Google reviews (SerpAPI), websites, social (Apify) — all optional
- `brands` — tone, LTV values, escalation rules
- Own feedback patterns (last 90 days)

### What it does
1. **Feedback classification:**
   - Type: complaint, testimonial, suggestion, neutral
   - Urgency: critical (<1hr), urgent (<4hr), normal (<24hr), low (<48hr)
   - At-risk flag: triggered by churn signals (configurable keywords + patterns per brand)
2. **Response drafting:** Tone and length from `brands.tone` + `brand.response_word_limit`
3. **At-risk retention:** When flagged, response includes a retention offer (configurable per brand)
4. **Testimonial requests:** For high-sentiment feedback (threshold configurable), requests permission to publish
5. **QR code generation:** Feedback collection codes linked to products, locations, or campaigns
6. **Monthly competitor analysis:** Scrapes and summarizes competitor positioning, strengths, weaknesses
7. **Monthly strategic report:** ELIMINATE / REDUCE / RAISE / CREATE framework — all opportunities filtered by ROI target from brand config

### What it writes
- `client_feedback` — type, sentiment_score, urgency, is_at_risk_flag, response_draft, `status: new → classified → pending_approval → responded`
- `client_testimonials` — quote_original, quote_edited, `status: pending_permission → approved`
- `client_qr_codes` — code, brand_id, purpose, linked_entity, scan_count
- `client_competitors` — name, website_url, social handles
- `client_competitor_snapshots` — monthly: website_summary, review_data, social_data, strengths, weaknesses, positioning
- `client_strategic_reports` — opportunities ranked by ROI, `status: pending_approval`

### Guardrails
- CRITICAL escalation (immediate owner WhatsApp): safety/health issues, legal threats, senior-level anger
- At-risk flag keywords and patterns are stored per brand in `brand_care_config` — not hardcoded
- LTV-at-risk value pulled from `brands.avg_customer_ltv` to frame urgency in escalations
- Tone pulled from `brands.tone` — responses never hardcoded for a specific company
- Strategic opportunities must meet `brand.roi_target_multiplier` — evidence-based only (3+ mentions = real signal)

### Claude receives (built from config)
```json
{
  "brand_name": "...",
  "tone": "professional",
  "language_primary": "en",
  "language_secondary": null,
  "avg_customer_ltv": 0,
  "currency": "...",
  "response_word_limit": 150,
  "feedback": { "text": "...", "channel": "email", "customer_type": "..." },
  "at_risk_keywords": ["cancel", "switch", "leaving"]
}
```

### Claude Prompts Needed
- `prompts/care_classify.txt` — Generic feedback classifier. Brand context + feedback in, type/urgency/at_risk/sentiment out.
- `prompts/care_respond.txt` — Generic response drafter. Brand tone + feedback classification in, response draft out.
- `prompts/care_competitor.txt` — Generic competitor profiler. Review/website/social data in, strengths/weaknesses/positioning out.
- `prompts/care_strategy.txt` — Generic strategic opportunity analyzer. ELIMINATE/REDUCE/RAISE/CREATE framework. ROI filter applied from brand config.

### New DB Tables
- `client_feedback`
- `client_testimonials`
- `client_qr_codes`
- `client_competitors`
- `client_competitor_snapshots`
- `client_strategic_reports`
- `brand_care_config` (at-risk keywords, escalation rules, retention offers per brand)

### New Env Vars
- `SERPAPI_KEY` (optional)
- `APIFY_API_TOKEN` (optional)

---

## Agent 6 — Orchestrator

**Purpose:** Master governance layer. Routes all approvals, enforces ROI discipline, manages budgets, and sends daily briefings to each client owner.

**Schedule:**
- Every 4 hours: escalation check + ROI signal check
- Daily 7:30 AM: morning briefing per client
- Every Monday 6:00 AM: weekly financial review

**Claude Model:** `claude-sonnet-4-5`

### What it reads
- `client_approval_requests` — all pending approvals from all agents
- `client_roi_snapshots` — rolling 30-day, MTD, QTD per client
- `client_spend_entries` + `client_revenue_entries` — by channel per client
- `client_budget_envelopes` — per channel allocation
- `clients` — owner contact info, timezone
- `client_agent_activity` — all agent action logs
- `client_intelligence` — flagged items, urgent alerts

### What it does
1. **Approval routing:** Sends pending approvals to each client's owner via their configured channels (WhatsApp + email). Processes replies (APPROVE / EDIT / REJECT). Executes approved actions.
2. **Escalation:** 12h no-response → reminder. 20h → second channel. Expired → mark expired, pipeline continues.
3. **ROI analysis:** Per channel, per client. Detects underperforming channels and compounding channels.
4. **Budget reallocation proposals:** Based on ROI signals — owner approves before any reallocation.
5. **Platform cost management:** Throttles agent depth if a client's platform spend approaches their ceiling.
6. **Daily briefing (7:30 AM):** Sent per client in their timezone — pending items, recent agent work, ROI status, urgent flags.

### What it writes
- `client_approval_requests` — all approval items from all agents
- `client_agent_activity` — every agent action logged (action, result, duration_ms, error_message)
- `client_roi_snapshots` — per-channel breakdown, channels below ROI target, compounding channels
- `client_business_targets` — proposed targets, `status: pending_approval → approved`
- `client_budget_envelopes` — per channel: allocated, spent, remaining, roi_current, status
- `client_intelligence` — daily briefing summaries

### Guardrails
- **ROI law:** `(projected revenue) ÷ (cost) ≥ brand.roi_target_multiplier`. Value comes from config, not hardcoded.
- **ROI color system:** Green ≥ target, Yellow 50–99% of target (action within 30d), Red <50% of target (reallocate), Black <1x (pause)
- **Autonomous (no approval):** Intelligence gathering, metric calculation, briefing generation, escalation reminders, ROI analysis
- **Always requires approval:** External communication, content publishing, budget commitment, target proposals
- **Throttle order if over cost ceiling:** Reduce competitor intel depth → reduce SEO frequency → reduce social volume → batch notifications. Never throttle approvals.
- ROI benchmarks are stored per industry in `industry_roi_benchmarks` — not hardcoded. Orchestrator uses client's industry to pull relevant benchmarks.

### Claude receives (built from config)
```json
{
  "client_name": "...",
  "brands": [...],
  "roi_target": 20,
  "currency": "...",
  "pending_approvals": [...],
  "roi_by_channel": { "channel": { "roi": 0, "spend": 0, "revenue": 0 } },
  "industry_benchmarks": { "channel": { "typical_roi_min": 0, "typical_roi_max": 0 } }
}
```

### Claude Prompts Needed
- `prompts/orchestrator_core.txt` — Generic approval routing and ROI enforcement. ROI law, color system, escalation rules, autonomous vs approval-required actions.
- `prompts/orchestrator_roi.txt` — Generic ROI analysis. Reallocation triggers, compounding signal detection. Uses client's roi_target from config.
- `prompts/orchestrator_briefing.txt` — Generic daily briefing generator. Client context + pending items + ROI status in, briefing narrative out.
- `prompts/orchestrator_budget.txt` — Generic budget reallocation proposal. Channel performance + envelopes in, reallocation proposal out.

### New DB Tables
- `client_approval_requests`
- `client_agent_activity`
- `client_roi_snapshots`
- `client_business_targets`
- `client_budget_envelopes`
- `client_spend_entries`
- `client_revenue_entries`
- `client_intelligence`
- `industry_roi_benchmarks` (shared across all clients — benchmarks by industry + channel)

### New Env Vars
- `OWNER_WHATSAPP` — per client (stored in `clients` table, not env var)
- `OWNER_EMAIL` — per client (stored in `clients` table, not env var)
- `ROI_DEFAULT_TARGET` — global default if not set per brand (default: 20)

---

## All New DB Tables (Master List)

| Table | Owned By | Notes |
|-------|---------|-------|
| `clients` | Core config | One row per company |
| `brands` | Core config | One or many per client |
| `brand_channels` | Core config | Platform credentials per brand |
| `brand_keywords` | Core config / SEO | SEO keywords per brand |
| `brand_content_config` | Broadcast | Post frequency + pillars per brand |
| `brand_care_config` | Customer Care | At-risk keywords, retention offers per brand |
| `industry_roi_benchmarks` | Orchestrator | Shared benchmarks by industry + channel |
| `client_prospects` | Scout | Researched potential leads |
| `client_leads` | Scout | Qualified leads awaiting approval |
| `client_contracts` | Scout | Active + historical contracts (optional) |
| `client_intelligence` | Scout + Orchestrator | Alerts, insights, briefings |
| `client_outreach` | Pipeline | Multi-step outreach sequences |
| `client_nurture_messages` | Pipeline | Stage-based nurture messages |
| `client_social_posts` | Broadcast | Generated + published posts |
| `client_social_comments` | Broadcast | Comments + reply drafts |
| `client_seo_content` | SEO Engine | Articles + metadata |
| `client_feedback` | Customer Care | All inbound feedback |
| `client_testimonials` | Customer Care | Approved testimonials |
| `client_qr_codes` | Customer Care | Feedback collection codes |
| `client_competitors` | Customer Care | Competitor profiles |
| `client_competitor_snapshots` | Customer Care | Monthly competitor analysis |
| `client_strategic_reports` | Customer Care | Blue Ocean / strategic opportunities |
| `client_approval_requests` | Orchestrator | All approval items from all agents |
| `client_agent_activity` | Orchestrator | All agent action logs |
| `client_roi_snapshots` | Orchestrator | Per-channel ROI per period |
| `client_business_targets` | Orchestrator | Period targets |
| `client_budget_envelopes` | Orchestrator | Per-channel budget allocation |
| `client_spend_entries` | Orchestrator | Spend tracking |
| `client_revenue_entries` | Orchestrator | Revenue attribution |

## All New Environment Variables (Master List)

| Variable | Required | Notes |
|----------|----------|-------|
| `SERPAPI_KEY` | Optional | Scout + Customer Care (web research) |
| `APIFY_API_TOKEN` | Optional | Customer Care (social scraping) |
| `LINKEDIN_ACCESS_TOKEN` | Per brand | Stored in `brand_channels`, not global env |
| `WHATSAPP_PHONE_NUMBER_ID` | Per brand | Stored in `brand_channels`, not global env |
| `META_INSTAGRAM_ACCOUNT_ID` | Per brand | Stored in `brand_channels`, not global env |
| `META_ACCESS_TOKEN` | Per brand | Stored in `brand_channels`, not global env |
| `ROI_DEFAULT_TARGET` | No | Global fallback (default: 20) |

> Note: Per-brand credentials (LinkedIn, Meta, WhatsApp) are stored in the `brand_channels` DB table so each client can have their own without touching env vars.

## All Claude Prompts Needed (Master List)

| File | Agent | Generic? |
|------|-------|---------|
| `prompts/scout_qualify.txt` | Scout | Yes — brand config injected at runtime |
| `prompts/scout_research.txt` | Scout | Yes |
| `prompts/pipeline_sequence.txt` | Pipeline | Yes |
| `prompts/pipeline_nurture.txt` | Pipeline | Yes |
| `prompts/broadcast_post.txt` | Broadcast | Yes |
| `prompts/broadcast_comment.txt` | Broadcast | Yes |
| `prompts/seo_article.txt` | SEO Engine | Yes |
| `prompts/seo_keywords.txt` | SEO Engine | Yes |
| `prompts/care_classify.txt` | Customer Care | Yes |
| `prompts/care_respond.txt` | Customer Care | Yes |
| `prompts/care_competitor.txt` | Customer Care | Yes |
| `prompts/care_strategy.txt` | Customer Care | Yes |
| `prompts/orchestrator_core.txt` | Orchestrator | Yes |
| `prompts/orchestrator_roi.txt` | Orchestrator | Yes |
| `prompts/orchestrator_briefing.txt` | Orchestrator | Yes |
| `prompts/orchestrator_budget.txt` | Orchestrator | Yes |

## Recommended Build Order

1. **Core config tables** — `clients`, `brands`, `brand_channels` must exist before any agent runs
2. **Orchestrator** — approval routing and activity logging needed by all other agents
3. **Scout** — lead discovery feeds Pipeline
4. **Pipeline** — depends on approved leads from Scout
5. **Customer Care** — standalone, no agent dependencies
6. **Broadcast** — depends on brand_channels setup
7. **SEO Engine** — standalone, no agent dependencies

## Onboarding a New Client

1. Insert a row into `clients` (name, owner_email, owner_whatsapp, timezone, currency)
2. Insert rows into `brands` for each brand they operate (industry, tone, channels, target audience, deal values)
3. Insert rows into `brand_channels` with their social/messaging credentials
4. Insert seed keywords into `brand_keywords` to kick off SEO Engine
5. Insert competitor names into `client_competitors` to kick off Customer Care intel
6. That's it — all agents pick up the new client automatically on their next scheduled run
