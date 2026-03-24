# CaterOS — Complete Autonomous Business Operating System
# Final Build Guide v4.0 — 20x ROI Architecture
# For Cursor AI + Vercel Deployment

---

## EXECUTIVE SUMMARY

CaterOS is the autonomous operating system for two brands:
- **Mikana Food Service** — B2B catering: UAE/Lebanon schools + corporate clients
- **Boxed & Go** — D2C meal subscriptions: UAE households + professionals

**North Star: 20x ROI on ALL expenditure (marketing + platform costs combined)**

At Standard tier: AED 750 platform + AED 15,000 marketing = AED 15,750/month total cost.
To hit 20x: need AED 315,000 in attributed revenue per month minimum.

20x forces the system to prioritise: school renewals (50-100x), SEO inbound (30-80x),
referrals (infinite), and LinkedIn outreach (15-40x for large contracts).
Paid ads only justified where subscriber/contract LTV × 20 > CAC.

**Six AI agents run autonomously. You govern from your phone.**
Daily input: 3–7 WhatsApp replies. Under 5 minutes.

**Full stack:** Next.js 14 · Neon Postgres · Vercel · Anthropic Claude API (claude-sonnet-4-5)
Resend · Meta Graph API · LinkedIn API · WhatsApp Business API · SerpAPI · Apify · QRCode.js

---

## COMPLETE AGENT ROSTER

| Agent | Job | Runs | Your Approval Required |
|---|---|---|---|
| Scout | Find leads (schools, corporate, B&G audience) | Daily 7am | New leads score ≥ 6 |
| Pipeline | Draft outreach, advance sequences | Daily 9am | Every outreach message |
| Broadcast | Generate + publish social content | Every 30min | Every post before publish |
| SEO Engine | Write + optimise content, manage sitemaps | Monday 6am | Every article |
| Customer Care | Classify feedback, draft responses, competitive intel | Every 30min | Every complaint response |
| Orchestrator | Govern all agents, manage P&L, 20x ROI target | Continuous | Targets · Budgets · Tier changes · Product verdicts |

---

## PLATFORM COST TIERS

| Tier | AED/mo | USD/mo | Revenue Needed for 20x | When |
|---|---|---|---|---|
| Floor | 450 | 122 | AED 9,000+ | Launch/pre-revenue |
| Standard ← START | 750 | 205 | AED 15,000+ | Normal operations |
| Expanded | 1,200 | 327 | AED 24,000+ | Revenue > AED 200K/mo |
| Scale | 2,000 | 545 | AED 40,000+ | Revenue > AED 500K/mo |

---

## CRON SCHEDULE

| Time | Job | Agent |
|---|---|---|
| 7:00am weekdays | Morning Scout cycle | Scout |
| 7:30am weekdays | Morning briefing (WhatsApp + email) | Orchestrator |
| 9:00am weekdays | Morning Pipeline cycle | Pipeline |
| Every 30min | Social publish queue | Broadcast |
| Every 30min | Feedback processor | Customer Care |
| Every 2hrs | Engagement sync | Broadcast |
| Every 4hrs | Escalation + ROI signal check | Orchestrator |
| Monday 6am | Weekly content + SEO + financial batch | All agents |
| 1st of month 6am | Monthly competitive intelligence deep scan | Customer Care |

---
---

# PHASE 0 — PROJECT INITIALISATION

---

## PROMPT 0.1 — Scaffold Project

```
Create a new Next.js 14 app called "cateros" using the App Router.

STEP 1 — Run:
npx create-next-app@latest cateros --typescript --tailwind --app --src-dir --import-alias "@/*"

STEP 2 — Install all dependencies:
npm install @neondatabase/serverless drizzle-orm drizzle-kit @anthropic-ai/sdk resend date-fns zod @radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-tabs @radix-ui/react-dropdown-menu @radix-ui/react-popover lucide-react recharts clsx tailwind-merge @hello-pangea/dnd qrcode
npm install --save-dev @types/qrcode

STEP 3 — Create this exact folder structure:
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                        ← redirects to /briefing
│   ├── briefing/page.tsx               ← Owner morning briefing (homepage)
│   ├── approvals/
│   │   ├── page.tsx
│   │   ├── [id]/page.tsx
│   │   └── history/page.tsx
│   ├── activity/page.tsx
│   ├── pipeline/
│   │   ├── schools/page.tsx
│   │   ├── corporate/page.tsx
│   │   └── boxedgo/page.tsx
│   ├── broadcast/page.tsx
│   ├── seo/page.tsx
│   ├── scout/page.tsx
│   ├── financial/page.tsx
│   ├── care/page.tsx
│   ├── feedback/page.tsx               ← PUBLIC: QR code feedback form
│   └── api/
│       ├── approvals/
│       │   ├── route.ts
│       │   ├── [id]/route.ts
│       │   └── whatsapp/route.ts
│       ├── notifications/
│       │   ├── send/route.ts
│       │   └── briefing/route.ts
│       ├── scout/
│       │   ├── run/route.ts
│       │   ├── research/route.ts
│       │   └── audience/route.ts
│       ├── pipeline/
│       │   ├── schools/route.ts
│       │   ├── corporate/route.ts
│       │   └── boxedgo/route.ts
│       ├── broadcast/
│       │   ├── generate/route.ts
│       │   ├── publish/route.ts
│       │   ├── schedule/route.ts
│       │   └── webhooks/
│       │       └── instagram/route.ts
│       ├── seo/
│       │   ├── generate/route.ts
│       │   ├── keywords/route.ts
│       │   └── sitemap/route.ts
│       ├── care/
│       │   ├── feedback/route.ts
│       │   ├── classify/route.ts
│       │   ├── patterns/route.ts
│       │   ├── qrcodes/route.ts
│       │   └── testimonials/route.ts
│       ├── competitive/
│       │   ├── run/route.ts
│       │   └── competitors/route.ts
│       ├── financial/
│       │   ├── targets/route.ts
│       │   ├── spend/route.ts
│       │   ├── revenue/route.ts
│       │   ├── roi/route.ts
│       │   └── platform-costs/route.ts
│       ├── health/route.ts
│       └── cron/
│           ├── morning-scout/route.ts
│           ├── morning-briefing/route.ts
│           ├── morning-pipeline/route.ts
│           ├── social-publish/route.ts
│           ├── feedback-processor/route.ts
│           ├── engagement-sync/route.ts
│           ├── escalation-check/route.ts
│           ├── weekly-batch/route.ts
│           └── monthly-intel/route.ts
├── lib/
│   ├── db.ts
│   ├── schema.ts
│   ├── anthropic.ts
│   ├── constants.ts
│   ├── validate-env.ts
│   └── utils.ts
├── agents/
│   ├── orchestrator.ts
│   ├── scout.ts
│   ├── pipeline.ts
│   ├── broadcast.ts
│   ├── seo-engine.ts
│   └── customer-care.ts
├── integrations/
│   ├── meta.ts
│   ├── linkedin.ts
│   ├── whatsapp.ts
│   ├── resend.ts
│   └── scraping.ts
└── components/
    ├── ui/
    │   ├── Sidebar.tsx
    │   ├── ApprovalCard.tsx
    │   ├── MetricCard.tsx
    │   └── BrandBadge.tsx
    ├── briefing/
    ├── pipeline/
    ├── broadcast/
    ├── financial/
    └── care/

STEP 4 — Create .env.local:
# CORE
DATABASE_URL=
ANTHROPIC_API_KEY=
RESEND_API_KEY=
CRON_SECRET=generate_a_random_32_char_string
NEXT_PUBLIC_APP_URL=http://localhost:3000

# OWNER
OWNER_WHATSAPP=+971XXXXXXXXX
OWNER_EMAIL=your@email.com
OWNER_APPROVAL_TOKEN=generate_a_random_32_char_string

# WHATSAPP BUSINESS API
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=choose_any_string

# META / INSTAGRAM
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_WEBHOOK_VERIFY_TOKEN=choose_any_string

# LINKEDIN
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORGANIZATION_ID=

# SCRAPING
SERPAPI_KEY=
APIFY_API_TOKEN=

# FINANCIAL
USD_TO_AED_RATE=3.67
ROI_TARGET_MULTIPLIER=20
PLATFORM_STARTING_TIER=standard

STEP 5 — Create vercel.json:
{
  "crons": [
    { "path": "/api/cron/morning-scout",      "schedule": "0 7 * * 1-5"   },
    { "path": "/api/cron/morning-briefing",   "schedule": "30 7 * * 1-5"  },
    { "path": "/api/cron/morning-pipeline",   "schedule": "0 9 * * 1-5"   },
    { "path": "/api/cron/social-publish",     "schedule": "*/30 * * * *"   },
    { "path": "/api/cron/feedback-processor", "schedule": "*/30 * * * *"   },
    { "path": "/api/cron/engagement-sync",    "schedule": "0 */2 * * *"    },
    { "path": "/api/cron/escalation-check",   "schedule": "0 */4 * * *"    },
    { "path": "/api/cron/weekly-batch",       "schedule": "0 6 * * 1"      },
    { "path": "/api/cron/monthly-intel",      "schedule": "0 6 1 * *"      }
  ]
}

STEP 6 — Create src/lib/constants.ts:
export const ROI_TARGET = 20
export const USD_TO_AED = parseFloat(process.env.USD_TO_AED_RATE || '3.67')
export const CLAUDE_MODEL = 'claude-sonnet-4-5'

export const APPROVAL_EXPIRY_HOURS: Record<string, number> = {
  new_lead_school: 48,
  new_lead_corporate: 48,
  new_subscriber: 48,
  outreach_email: 24,
  social_post: 12,
  seo_article: 48,
  spending_decision: 24,
  tier_change: 48,
  product_verdict: 72,
  blue_ocean_report: 72
}

export const BRANDS = {
  mikana: { name: 'Mikana Food Service', color: '#E8490F', platform: 'linkedin' as const },
  boxedgo: { name: 'Boxed & Go', color: '#c2714f', platform: 'instagram' as const }
}

export const PLATFORM_TIERS = {
  floor:    { ceiling_aed: 450,  ceiling_usd: 122, competitors_per_industry: 5,  seo_per_month: 2,  posts_per_week: 4  },
  standard: { ceiling_aed: 750,  ceiling_usd: 205, competitors_per_industry: 10, seo_per_month: 4,  posts_per_week: 8  },
  expanded: { ceiling_aed: 1200, ceiling_usd: 327, competitors_per_industry: 15, seo_per_month: 8,  posts_per_week: 14 },
  scale:    { ceiling_aed: 2000, ceiling_usd: 545, competitors_per_industry: 25, seo_per_month: 16, posts_per_week: 20 }
}

export function cronGuard(request: Request): boolean {
  return request.headers.get('authorization') === `Bearer ${process.env.CRON_SECRET}`
}
```

---

## PROMPT 0.2 — Core Library Files

```
Create these three core library files exactly as written:

━━━ src/lib/db.ts ━━━
import { neon } from '@neondatabase/serverless'
import { drizzle } from 'drizzle-orm/neon-http'
import * as schema from './schema'

const sql = neon(process.env.DATABASE_URL!)
export const db = drizzle(sql, { schema })
export type DB = typeof db

━━━ src/lib/anthropic.ts ━━━
import Anthropic from '@anthropic-ai/sdk'
export const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
export const CLAUDE_MODEL = 'claude-sonnet-4-5'

export async function callClaude(params: {
  systemPrompt: string
  userMessage: string
  maxTokens?: number
  jsonMode?: boolean
}): Promise<string> {
  const { systemPrompt, userMessage, maxTokens = 2000, jsonMode = false } = params
  const response = await anthropic.messages.create({
    model: CLAUDE_MODEL,
    max_tokens: maxTokens,
    system: jsonMode
      ? systemPrompt + '\n\nCRITICAL: Respond ONLY with valid JSON. No preamble, no markdown. Raw JSON only.'
      : systemPrompt,
    messages: [{ role: 'user', content: userMessage }]
  })
  const text = response.content[0].type === 'text' ? response.content[0].text : ''
  return jsonMode ? text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim() : text
}

━━━ src/lib/utils.ts ━━━
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { USD_TO_AED, ROI_TARGET } from './constants'

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }

export function formatAED(amount: number): string {
  return `AED ${Math.round(amount).toLocaleString('en-AE')}`
}

export function formatROI(roi: number): string { return `${roi.toFixed(1)}x` }

export function usdToAed(usd: number): number {
  return Math.round(usd * USD_TO_AED * 100) / 100
}

export function calculateTrueNetROI(params: {
  revenueAed: number
  marketingSpendAed: number
  platformCostAed: number
}) {
  const { revenueAed, marketingSpendAed, platformCostAed } = params
  const totalCost = marketingSpendAed + platformCostAed
  return {
    grossROI: marketingSpendAed > 0 ? revenueAed / marketingSpendAed : 0,
    trueNetROI: totalCost > 0 ? (revenueAed - totalCost) / totalCost : 0,
    absoluteNetValue: revenueAed - totalCost,
    platformCostPct: revenueAed > 0 ? (platformCostAed / revenueAed) * 100 : 0,
    vsTargetGap: totalCost > 0 ? (revenueAed / totalCost) - ROI_TARGET : -ROI_TARGET,
    meetsTarget: totalCost > 0 && revenueAed >= totalCost * ROI_TARGET
  }
}

export function roiEmoji(roi: number): string {
  if (roi >= 20) return '🟢'
  if (roi >= 10) return '🟡'
  if (roi >= 1) return '🔴'
  return '⚫'
}

━━━ src/lib/validate-env.ts ━━━
const REQUIRED = [
  'DATABASE_URL', 'ANTHROPIC_API_KEY', 'RESEND_API_KEY', 'CRON_SECRET',
  'NEXT_PUBLIC_APP_URL', 'OWNER_WHATSAPP', 'OWNER_EMAIL',
  'WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_ACCESS_TOKEN',
  'META_APP_ID', 'META_ACCESS_TOKEN', 'META_INSTAGRAM_ACCOUNT_ID',
  'LINKEDIN_ACCESS_TOKEN', 'LINKEDIN_ORGANIZATION_ID'
]

export function validateEnv() {
  const missing = REQUIRED.filter(key => !process.env[key])
  if (missing.length > 0) {
    throw new Error(`CaterOS: Missing environment variables:\n${missing.map(k => `  - ${k}`).join('\n')}`)
  }
}

━━━ src/lib/drizzle.config.ts ━━━
import type { Config } from 'drizzle-kit'
export default {
  schema: './src/lib/schema.ts',
  out: './drizzle',
  driver: 'pg',
  dbCredentials: { connectionString: process.env.DATABASE_URL! }
} satisfies Config
```
# PHASE 0 CONTINUED — COMPLETE DATABASE SCHEMA

---

## PROMPT 0.3 — Complete Database Schema

```
Create the COMPLETE schema in src/lib/schema.ts

Import:
import { pgTable, uuid, text, integer, boolean, timestamp,
         date, numeric, jsonb } from 'drizzle-orm/pg-core'
import { sql } from 'drizzle-orm'

All tables use cateros_ prefix. Write all 14 sections below.

━━━ SECTION 1: SYSTEM ━━━

export const cateros_brands = pgTable('cateros_brands', {
  id: uuid('id').primaryKey().defaultRandom(),
  slug: text('slug').unique().notNull(),
  display_name: text('display_name'),
  brand_color: text('brand_color'),
  website_url: text('website_url'),
  instagram_account_id: text('instagram_account_id'),
  instagram_access_token: text('instagram_access_token'),
  linkedin_org_id: text('linkedin_org_id'),
  linkedin_access_token: text('linkedin_access_token'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_system_config = pgTable('cateros_system_config', {
  id: uuid('id').primaryKey().defaultRandom(),
  key: text('key').unique().notNull(),
  value: text('value'),
  reason: text('reason'),
  set_by: text('set_by').default('orchestrator'),
  expires_at: timestamp('expires_at'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 2: APPROVAL & NOTIFICATION SYSTEM ━━━

export const cateros_approval_requests = pgTable('cateros_approval_requests', {
  id: uuid('id').primaryKey().defaultRandom(),
  type: text('type').notNull(),
  brand: text('brand'),
  title: text('title'),
  summary: text('summary'),
  payload: jsonb('payload'),
  agent: text('agent'),
  entity_id: uuid('entity_id'),
  entity_type: text('entity_type'),
  status: text('status').default('pending'),
  priority: text('priority').default('normal'),
  owner_decision: text('owner_decision'),
  edited_payload: jsonb('edited_payload'),
  whatsapp_message_id: text('whatsapp_message_id'),
  notification_sent_at: timestamp('notification_sent_at'),
  whatsapp_sent_at: timestamp('whatsapp_sent_at'),
  email_sent_at: timestamp('email_sent_at'),
  first_escalation_at: timestamp('first_escalation_at'),
  second_escalation_at: timestamp('second_escalation_at'),
  responded_at: timestamp('responded_at'),
  expires_at: timestamp('expires_at'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_agent_activity = pgTable('cateros_agent_activity', {
  id: uuid('id').primaryKey().defaultRandom(),
  agent: text('agent').notNull(),
  action: text('action').notNull(),
  brand: text('brand'),
  entity_id: uuid('entity_id'),
  entity_type: text('entity_type'),
  result: text('result'),
  detail: text('detail'),
  approval_request_id: uuid('approval_request_id'),
  error_message: text('error_message'),
  duration_ms: integer('duration_ms'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_notifications = pgTable('cateros_notifications', {
  id: uuid('id').primaryKey().defaultRandom(),
  channel: text('channel'),
  type: text('type'),
  recipient: text('recipient'),
  subject: text('subject'),
  body: text('body'),
  approval_request_id: uuid('approval_request_id'),
  status: text('status').default('pending'),
  platform_message_id: text('platform_message_id'),
  sent_at: timestamp('sent_at'),
  delivered_at: timestamp('delivered_at'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 3: MIKANA SCHOOLS ━━━

export const cateros_schools = pgTable('cateros_schools', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  type: text('type'),
  curriculum: text('curriculum'),
  emirate: text('emirate'),
  area: text('area'),
  address: text('address'),
  website: text('website'),
  student_count: integer('student_count'),
  staff_count: integer('staff_count'),
  total_daily_covers: integer('total_daily_covers'),
  academic_year_start: text('academic_year_start'),
  academic_year_end: text('academic_year_end'),
  terms_per_year: integer('terms_per_year').default(3),
  current_contract_status: text('current_contract_status'),
  competitor_name: text('competitor_name'),
  contract_value_aed: integer('contract_value_aed'),
  contract_start_date: date('contract_start_date'),
  contract_end_date: date('contract_end_date'),
  renewal_notice_days: integer('renewal_notice_days').default(90),
  principal_name: text('principal_name'),
  principal_email: text('principal_email'),
  facilities_contact_name: text('facilities_contact_name'),
  facilities_contact_email: text('facilities_contact_email'),
  qualification_score: integer('qualification_score'),
  source: text('source').default('scout_agent'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_school_leads = pgTable('cateros_school_leads', {
  id: uuid('id').primaryKey().defaultRandom(),
  school_id: uuid('school_id'),
  lead_type: text('lead_type'),
  stage: text('stage').default('pending_approval'),
  priority: text('priority').default('medium'),
  estimated_value_aed: integer('estimated_value_aed'),
  academic_year_target: text('academic_year_target'),
  renewal_date: date('renewal_date'),
  outreach_sequence_step: integer('outreach_sequence_step').default(0),
  last_outreach_at: timestamp('last_outreach_at'),
  next_action: text('next_action'),
  next_action_date: date('next_action_date'),
  won_date: date('won_date'),
  lost_reason: text('lost_reason'),
  final_value_aed: integer('final_value_aed'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

━━━ SECTION 4: MIKANA CORPORATE ━━━

export const cateros_companies = pgTable('cateros_companies', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  industry: text('industry'),
  sub_industry: text('sub_industry'),
  website: text('website'),
  linkedin_url: text('linkedin_url'),
  address: text('address'),
  city: text('city').default('Dubai'),
  employee_count_estimate: integer('employee_count_estimate'),
  daily_meals_opportunity: integer('daily_meals_opportunity'),
  annual_value_estimate_aed: integer('annual_value_estimate_aed'),
  qualification_score: integer('qualification_score'),
  current_food_situation: text('current_food_situation'),
  competitor_name: text('competitor_name'),
  source: text('source').default('scout_agent'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_contacts = pgTable('cateros_contacts', {
  id: uuid('id').primaryKey().defaultRandom(),
  company_id: uuid('company_id'),
  school_id: uuid('school_id'),
  first_name: text('first_name'),
  last_name: text('last_name'),
  title: text('title'),
  email: text('email'),
  phone: text('phone'),
  whatsapp: text('whatsapp'),
  linkedin_url: text('linkedin_url'),
  is_primary: boolean('is_primary').default(false),
  language_preference: text('language_preference').default('en'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_corporate_leads = pgTable('cateros_corporate_leads', {
  id: uuid('id').primaryKey().defaultRandom(),
  company_id: uuid('company_id'),
  primary_contact_id: uuid('primary_contact_id'),
  stage: text('stage').default('pending_approval'),
  priority: text('priority').default('medium'),
  estimated_value_aed: integer('estimated_value_aed'),
  meals_per_day_estimate: integer('meals_per_day_estimate'),
  outreach_sequence_step: integer('outreach_sequence_step').default(0),
  last_outreach_at: timestamp('last_outreach_at'),
  next_action: text('next_action'),
  next_action_date: date('next_action_date'),
  won_date: date('won_date'),
  lost_reason: text('lost_reason'),
  final_contract_value_aed: integer('final_contract_value_aed'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_outreach = pgTable('cateros_outreach', {
  id: uuid('id').primaryKey().defaultRandom(),
  lead_type: text('lead_type'),
  lead_id: uuid('lead_id'),
  contact_id: uuid('contact_id'),
  channel: text('channel'),
  subject: text('subject'),
  body: text('body'),
  sequence_step: integer('sequence_step'),
  status: text('status').default('pending_approval'),
  approval_request_id: uuid('approval_request_id'),
  sent_at: timestamp('sent_at'),
  opened_at: timestamp('opened_at'),
  replied_at: timestamp('replied_at'),
  reply_content: text('reply_content'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 5: BOXED & GO ━━━

export const cateros_bg_plans = pgTable('cateros_bg_plans', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  category: text('category'),
  description: text('description'),
  description_arabic: text('description_arabic'),
  target_segment: text('target_segment'),
  meals_per_week: integer('meals_per_week'),
  price_aed_weekly: numeric('price_aed_weekly', { precision: 8, scale: 2 }),
  price_aed_monthly: numeric('price_aed_monthly', { precision: 8, scale: 2 }),
  price_lbp_monthly: integer('price_lbp_monthly'),
  is_active: boolean('is_active').default(true),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_bg_meals = pgTable('cateros_bg_meals', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  name_arabic: text('name_arabic'),
  category: text('category'),
  cuisine_theme: text('cuisine_theme'),
  day_of_week: text('day_of_week'),
  description: text('description'),
  description_arabic: text('description_arabic'),
  preparation_notes: text('preparation_notes'),
  finish_time_minutes: integer('finish_time_minutes'),
  video_url: text('video_url'),
  weight_grams: integer('weight_grams'),
  calories: integer('calories'),
  protein_grams: integer('protein_grams'),
  carbs_grams: integer('carbs_grams'),
  fat_grams: integer('fat_grams'),
  fibre_grams: integer('fibre_grams'),
  price_aed: numeric('price_aed', { precision: 8, scale: 2 }),
  price_lbp: integer('price_lbp'),
  allergens: text('allergens').array(),
  swap_compatible_ids: text('swap_compatible_ids').array(),
  is_active: boolean('is_active').default(true),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_bg_subscribers = pgTable('cateros_bg_subscribers', {
  id: uuid('id').primaryKey().defaultRandom(),
  first_name: text('first_name'),
  last_name: text('last_name'),
  email: text('email'),
  phone: text('phone'),
  whatsapp: text('whatsapp'),
  area: text('area'),
  city: text('city').default('Dubai'),
  country: text('country').default('UAE'),
  segment: text('segment'),
  plan_id: uuid('plan_id'),
  stage: text('stage').default('pending_approval'),
  source: text('source'),
  utm_campaign: text('utm_campaign'),
  referral_code: text('referral_code'),
  trial_start_date: date('trial_start_date'),
  subscription_start_date: date('subscription_start_date'),
  churn_reason: text('churn_reason'),
  churn_date: date('churn_date'),
  lifetime_value_aed: numeric('lifetime_value_aed', { precision: 10, scale: 2 }).default('0'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_bg_outreach = pgTable('cateros_bg_outreach', {
  id: uuid('id').primaryKey().defaultRandom(),
  subscriber_id: uuid('subscriber_id'),
  channel: text('channel'),
  message_type: text('message_type'),
  content: text('content'),
  content_arabic: text('content_arabic'),
  status: text('status').default('pending_approval'),
  approval_request_id: uuid('approval_request_id'),
  sent_at: timestamp('sent_at'),
  replied_at: timestamp('replied_at'),
  reply_content: text('reply_content'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 6: BROADCAST ━━━

export const cateros_social_accounts = pgTable('cateros_social_accounts', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  platform: text('platform'),
  account_handle: text('account_handle'),
  account_id: text('account_id'),
  access_token: text('access_token'),
  token_expires_at: timestamp('token_expires_at'),
  follower_count: integer('follower_count').default(0),
  last_synced_at: timestamp('last_synced_at'),
  is_active: boolean('is_active').default(true),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_social_posts = pgTable('cateros_social_posts', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  platform: text('platform'),
  content_type: text('content_type'),
  language: text('language').default('en'),
  caption: text('caption'),
  caption_arabic: text('caption_arabic'),
  hashtags: text('hashtags').array(),
  image_prompt: text('image_prompt'),
  image_url: text('image_url'),
  media_id: text('media_id'),
  platform_post_id: text('platform_post_id'),
  platform_post_url: text('platform_post_url'),
  status: text('status').default('pending_approval'),
  approval_request_id: uuid('approval_request_id'),
  scheduled_at: timestamp('scheduled_at'),
  published_at: timestamp('published_at'),
  failure_reason: text('failure_reason'),
  likes_count: integer('likes_count').default(0),
  comments_count: integer('comments_count').default(0),
  shares_count: integer('shares_count').default(0),
  reach: integer('reach').default(0),
  impressions: integer('impressions').default(0),
  saves_count: integer('saves_count').default(0),
  engagement_rate: numeric('engagement_rate', { precision: 5, scale: 4 }).default('0'),
  last_engagement_sync: timestamp('last_engagement_sync'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_social_comments = pgTable('cateros_social_comments', {
  id: uuid('id').primaryKey().defaultRandom(),
  post_id: uuid('post_id'),
  platform_comment_id: text('platform_comment_id'),
  author_username: text('author_username'),
  content: text('content'),
  sentiment: text('sentiment'),
  requires_reply: boolean('requires_reply').default(false),
  reply_content: text('reply_content'),
  replied_at: timestamp('replied_at'),
  auto_replied: boolean('auto_replied').default(false),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 7: SEO ━━━

export const cateros_seo_keywords = pgTable('cateros_seo_keywords', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand'),
  keyword: text('keyword').notNull(),
  search_volume_estimate: integer('search_volume_estimate'),
  difficulty_estimate: integer('difficulty_estimate'),
  intent: text('intent'),
  cluster_topic: text('cluster_topic'),
  current_ranking: integer('current_ranking'),
  target_page_slug: text('target_page_slug'),
  status: text('status').default('identified'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_seo_content = pgTable('cateros_seo_content', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  content_type: text('content_type'),
  title: text('title'),
  slug: text('slug').unique(),
  primary_keyword_id: uuid('primary_keyword_id'),
  secondary_keyword_ids: text('secondary_keyword_ids').array(),
  target_audience: text('target_audience'),
  content_markdown: text('content_markdown'),
  content_html: text('content_html'),
  meta_title: text('meta_title'),
  meta_description: text('meta_description'),
  schema_markup: text('schema_markup'),
  word_count: integer('word_count'),
  seo_score: integer('seo_score'),
  status: text('status').default('pending_approval'),
  approval_request_id: uuid('approval_request_id'),
  published_at: timestamp('published_at'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 8: FINANCIAL ━━━

export const cateros_business_targets = pgTable('cateros_business_targets', {
  id: uuid('id').primaryKey().defaultRandom(),
  period_type: text('period_type'),
  period_label: text('period_label'),
  period_start: date('period_start'),
  period_end: date('period_end'),
  brand: text('brand'),
  target_revenue_aed: integer('target_revenue_aed'),
  target_new_school_contracts: integer('target_new_school_contracts'),
  target_school_contract_value_aed: integer('target_school_contract_value_aed'),
  target_new_corporate_contracts: integer('target_new_corporate_contracts'),
  target_corporate_contract_value_aed: integer('target_corporate_contract_value_aed'),
  target_new_bg_subscribers: integer('target_new_bg_subscribers'),
  target_bg_mrr_aed: integer('target_bg_mrr_aed'),
  target_bg_churn_rate_pct: numeric('target_bg_churn_rate_pct', { precision: 5, scale: 2 }),
  target_cac_school_aed: integer('target_cac_school_aed'),
  target_cac_corporate_aed: integer('target_cac_corporate_aed'),
  target_cac_bg_subscriber_aed: integer('target_cac_bg_subscriber_aed'),
  target_roi_multiplier: numeric('target_roi_multiplier', { precision: 4, scale: 2 }).default('20'),
  actual_revenue_aed: integer('actual_revenue_aed').default(0),
  actual_new_school_contracts: integer('actual_new_school_contracts').default(0),
  actual_new_corporate_contracts: integer('actual_new_corporate_contracts').default(0),
  actual_new_bg_subscribers: integer('actual_new_bg_subscribers').default(0),
  actual_bg_mrr_aed: integer('actual_bg_mrr_aed').default(0),
  status: text('status').default('pending_approval'),
  approval_request_id: uuid('approval_request_id'),
  orchestrator_reasoning: text('orchestrator_reasoning'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_budget_envelopes = pgTable('cateros_budget_envelopes', {
  id: uuid('id').primaryKey().defaultRandom(),
  target_id: uuid('target_id'),
  brand: text('brand'),
  channel: text('channel'),
  channel_label: text('channel_label'),
  currency: text('currency').default('AED'),
  allocated_amount: numeric('allocated_amount', { precision: 10, scale: 2 }),
  allocated_amount_aed: numeric('allocated_amount_aed', { precision: 10, scale: 2 }),
  spent_amount_aed: numeric('spent_amount_aed', { precision: 10, scale: 2 }).default('0'),
  committed_amount_aed: numeric('committed_amount_aed', { precision: 10, scale: 2 }).default('0'),
  remaining_amount_aed: numeric('remaining_amount_aed', { precision: 10, scale: 2 }),
  roi_current: numeric('roi_current', { precision: 6, scale: 2 }).default('0'),
  roi_target: numeric('roi_target', { precision: 6, scale: 2 }).default('20'),
  status: text('status').default('active'),
  paused_reason: text('paused_reason'),
  consecutive_below_roi_months: integer('consecutive_below_roi_months').default(0),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_spend_entries = pgTable('cateros_spend_entries', {
  id: uuid('id').primaryKey().defaultRandom(),
  budget_envelope_id: uuid('budget_envelope_id'),
  brand: text('brand'),
  channel: text('channel'),
  description: text('description'),
  spend_type: text('spend_type'),
  amount: numeric('amount', { precision: 10, scale: 2 }),
  currency: text('currency').default('AED'),
  amount_aed: numeric('amount_aed', { precision: 10, scale: 2 }),
  usd_rate_used: numeric('usd_rate_used', { precision: 8, scale: 4 }),
  barter_market_value_aed: numeric('barter_market_value_aed', { precision: 10, scale: 2 }),
  barter_partner: text('barter_partner'),
  barter_what_we_gave: text('barter_what_we_gave'),
  barter_what_we_received: text('barter_what_we_received'),
  social_post_id: uuid('social_post_id'),
  invoice_reference: text('invoice_reference'),
  spend_date: date('spend_date'),
  entered_by: text('entered_by').default('manual'),
  verified: boolean('verified').default(false),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_revenue_entries = pgTable('cateros_revenue_entries', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  revenue_type: text('revenue_type'),
  entity_id: uuid('entity_id'),
  entity_type: text('entity_type'),
  description: text('description'),
  amount_aed: numeric('amount_aed', { precision: 10, scale: 2 }),
  is_recurring: boolean('is_recurring').default(false),
  recurring_period: text('recurring_period'),
  acquisition_channel: text('acquisition_channel'),
  acquisition_spend_aed: numeric('acquisition_spend_aed', { precision: 10, scale: 2 }),
  revenue_date: date('revenue_date'),
  contract_duration_months: integer('contract_duration_months'),
  total_contract_value_aed: numeric('total_contract_value_aed', { precision: 10, scale: 2 }),
  entered_by: text('entered_by').default('orchestrator'),
  source_detail: text('source_detail'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_roi_snapshots = pgTable('cateros_roi_snapshots', {
  id: uuid('id').primaryKey().defaultRandom(),
  snapshot_date: date('snapshot_date'),
  brand: text('brand'),
  period: text('period'),
  total_spend_aed: numeric('total_spend_aed', { precision: 10, scale: 2 }),
  spend_by_channel: jsonb('spend_by_channel'),
  total_revenue_aed: numeric('total_revenue_aed', { precision: 10, scale: 2 }),
  revenue_by_channel: jsonb('revenue_by_channel'),
  platform_cost_aed: numeric('platform_cost_aed', { precision: 10, scale: 2 }),
  gross_roi: numeric('gross_roi', { precision: 6, scale: 2 }),
  true_net_roi: numeric('true_net_roi', { precision: 6, scale: 2 }),
  roi_vs_20x_target: numeric('roi_vs_20x_target', { precision: 6, scale: 2 }),
  roi_by_channel: jsonb('roi_by_channel'),
  cac_school_aed: numeric('cac_school_aed', { precision: 10, scale: 2 }),
  cac_corporate_aed: numeric('cac_corporate_aed', { precision: 10, scale: 2 }),
  cac_bg_subscriber_aed: numeric('cac_bg_subscriber_aed', { precision: 10, scale: 2 }),
  ltv_school_aed: numeric('ltv_school_aed', { precision: 10, scale: 2 }),
  ltv_corporate_aed: numeric('ltv_corporate_aed', { precision: 10, scale: 2 }),
  ltv_bg_subscriber_aed: numeric('ltv_bg_subscriber_aed', { precision: 10, scale: 2 }),
  payback_period_school_months: numeric('payback_period_school_months', { precision: 5, scale: 2 }),
  payback_period_corporate_months: numeric('payback_period_corporate_months', { precision: 5, scale: 2 }),
  payback_period_bg_months: numeric('payback_period_bg_months', { precision: 5, scale: 2 }),
  bg_mrr_aed: numeric('bg_mrr_aed', { precision: 10, scale: 2 }),
  bg_mrr_growth_pct: numeric('bg_mrr_growth_pct', { precision: 5, scale: 2 }),
  bg_churn_rate_pct: numeric('bg_churn_rate_pct', { precision: 5, scale: 2 }),
  roi_trend: text('roi_trend'),
  compounding_channels: text('compounding_channels').array(),
  underperforming_channels: text('underperforming_channels').array(),
  channels_below_20x: text('channels_below_20x').array(),
  orchestrator_assessment: text('orchestrator_assessment'),
  reallocation_triggered: boolean('reallocation_triggered').default(false),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 9: PLATFORM COSTS ━━━

export const cateros_platform_cost_tiers = pgTable('cateros_platform_cost_tiers', {
  id: uuid('id').primaryKey().defaultRandom(),
  tier_name: text('tier_name').unique(),
  tier_label: text('tier_label'),
  monthly_ceiling_aed: numeric('monthly_ceiling_aed', { precision: 10, scale: 2 }),
  monthly_ceiling_usd: numeric('monthly_ceiling_usd', { precision: 10, scale: 2 }),
  agent_cycle_frequency: text('agent_cycle_frequency'),
  competitive_intel_frequency: text('competitive_intel_frequency'),
  competitors_per_industry: integer('competitors_per_industry'),
  instagram_scraping_depth: text('instagram_scraping_depth'),
  max_approvals_per_day: integer('max_approvals_per_day'),
  seo_articles_per_month: integer('seo_articles_per_month'),
  social_posts_per_week: integer('social_posts_per_week'),
  cost_breakdown: jsonb('cost_breakdown'),
  upgrade_trigger_revenue_aed: numeric('upgrade_trigger_revenue_aed', { precision: 10, scale: 2 }),
  upgrade_trigger_growth_pct: numeric('upgrade_trigger_growth_pct', { precision: 5, scale: 2 }),
  is_active: boolean('is_active').default(false),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_platform_cost_entries = pgTable('cateros_platform_cost_entries', {
  id: uuid('id').primaryKey().defaultRandom(),
  service: text('service').notNull(),
  service_label: text('service_label'),
  currency: text('currency').default('USD'),
  amount: numeric('amount', { precision: 10, scale: 2 }),
  amount_aed: numeric('amount_aed', { precision: 10, scale: 2 }),
  usd_rate_used: numeric('usd_rate_used', { precision: 8, scale: 4 }),
  billing_period: text('billing_period'),
  usage_description: text('usage_description'),
  invoice_url: text('invoice_url'),
  entered_by: text('entered_by').default('manual'),
  is_estimate: boolean('is_estimate').default(false),
  verified: boolean('verified').default(false),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_platform_cost_budgets = pgTable('cateros_platform_cost_budgets', {
  id: uuid('id').primaryKey().defaultRandom(),
  period: text('period').notNull(),
  active_tier: text('active_tier'),
  approved_ceiling_aed: numeric('approved_ceiling_aed', { precision: 10, scale: 2 }),
  approved_ceiling_usd: numeric('approved_ceiling_usd', { precision: 10, scale: 2 }),
  actual_spend_aed: numeric('actual_spend_aed', { precision: 10, scale: 2 }).default('0'),
  actual_spend_usd: numeric('actual_spend_usd', { precision: 10, scale: 2 }).default('0'),
  estimated_month_end_aed: numeric('estimated_month_end_aed', { precision: 10, scale: 2 }),
  days_elapsed: integer('days_elapsed'),
  days_in_month: integer('days_in_month'),
  spend_pace_pct: numeric('spend_pace_pct', { precision: 5, scale: 2 }),
  alert_80pct_sent: boolean('alert_80pct_sent').default(false),
  alert_90pct_sent: boolean('alert_90pct_sent').default(false),
  alert_100pct_sent: boolean('alert_100pct_sent').default(false),
  tier_upgrade_proposed: boolean('tier_upgrade_proposed').default(false),
  tier_upgrade_approval_id: uuid('tier_upgrade_approval_id'),
  marketing_revenue_attributed_aed: numeric('marketing_revenue_attributed_aed', { precision: 10, scale: 2 }).default('0'),
  gross_marketing_roi: numeric('gross_marketing_roi', { precision: 6, scale: 2 }).default('0'),
  platform_cost_deduction_aed: numeric('platform_cost_deduction_aed', { precision: 10, scale: 2 }),
  true_net_roi: numeric('true_net_roi', { precision: 6, scale: 2 }).default('0'),
  roi_vs_20x_gap: numeric('roi_vs_20x_gap', { precision: 6, scale: 2 }).default('0'),
  status: text('status').default('active'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

━━━ SECTION 10: CUSTOMER FEEDBACK ━━━

export const cateros_feedback = pgTable('cateros_feedback', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  feedback_type: text('feedback_type'),
  channel: text('channel'),
  customer_type: text('customer_type'),
  customer_id: uuid('customer_id'),
  customer_name: text('customer_name'),
  customer_email: text('customer_email'),
  customer_whatsapp: text('customer_whatsapp'),
  school_id: uuid('school_id'),
  company_id: uuid('company_id'),
  raw_text: text('raw_text').notNull(),
  subject: text('subject'),
  rating: integer('rating'),
  sentiment_score: integer('sentiment_score'),
  complaint_categories: text('complaint_categories').array(),
  meal_ids_mentioned: uuid('meal_ids_mentioned').array(),
  plan_ids_mentioned: uuid('plan_ids_mentioned').array(),
  urgency: text('urgency').default('normal'),
  is_at_risk_flag: boolean('is_at_risk_flag').default(false),
  status: text('status').default('new'),
  response_draft: text('response_draft'),
  response_draft_arabic: text('response_draft_arabic'),
  response_channel: text('response_channel'),
  approval_request_id: uuid('approval_request_id'),
  responded_at: timestamp('responded_at'),
  response_sent: text('response_sent'),
  resolved_at: timestamp('resolved_at'),
  resolution_notes: text('resolution_notes'),
  flagged_for_product_review: boolean('flagged_for_product_review').default(false),
  product_review_actioned: boolean('product_review_actioned').default(false),
  qr_code_id: text('qr_code_id'),
  qr_scan_location: text('qr_scan_location'),
  source_url: text('source_url'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_qr_codes = pgTable('cateros_qr_codes', {
  id: uuid('id').primaryKey().defaultRandom(),
  code: text('code').unique().notNull(),
  brand: text('brand').notNull(),
  purpose: text('purpose'),
  linked_entity_type: text('linked_entity_type'),
  linked_entity_id: uuid('linked_entity_id'),
  linked_entity_label: text('linked_entity_label'),
  destination_url: text('destination_url'),
  scan_count: integer('scan_count').default(0),
  feedback_count: integer('feedback_count').default(0),
  is_active: boolean('is_active').default(true),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_testimonials = pgTable('cateros_testimonials', {
  id: uuid('id').primaryKey().defaultRandom(),
  feedback_id: uuid('feedback_id'),
  brand: text('brand').notNull(),
  customer_name: text('customer_name'),
  customer_title: text('customer_title'),
  customer_type: text('customer_type'),
  quote_original: text('quote_original'),
  quote_edited: text('quote_edited'),
  quote_arabic: text('quote_arabic'),
  rating: integer('rating'),
  permission_to_use: boolean('permission_to_use').default(false),
  permission_requested_at: timestamp('permission_requested_at'),
  permission_granted_at: timestamp('permission_granted_at'),
  status: text('status').default('raw'),
  used_in_posts: uuid('used_in_posts').array(),
  used_in_seo: uuid('used_in_seo').array(),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 11: PRODUCT INTELLIGENCE ━━━

export const cateros_product_performance = pgTable('cateros_product_performance', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  product_type: text('product_type'),
  product_id: uuid('product_id'),
  product_name: text('product_name'),
  order_count_mtd: integer('order_count_mtd').default(0),
  order_count_prev_month: integer('order_count_prev_month').default(0),
  order_trend_pct: numeric('order_trend_pct', { precision: 5, scale: 2 }),
  reorder_rate_pct: numeric('reorder_rate_pct', { precision: 5, scale: 2 }),
  customer_rating_avg: numeric('customer_rating_avg', { precision: 3, scale: 2 }),
  complaint_count_mtd: integer('complaint_count_mtd').default(0),
  revenue_mtd_aed: numeric('revenue_mtd_aed', { precision: 10, scale: 2 }),
  cogs_mtd_aed: numeric('cogs_mtd_aed', { precision: 10, scale: 2 }),
  gross_margin_pct: numeric('gross_margin_pct', { precision: 5, scale: 2 }),
  contribution_to_total_revenue_pct: numeric('contribution_to_total_revenue_pct', { precision: 5, scale: 2 }),
  marketing_spend_attributed_aed: numeric('marketing_spend_attributed_aed', { precision: 10, scale: 2 }),
  cac_this_product_aed: numeric('cac_this_product_aed', { precision: 10, scale: 2 }),
  roi_this_product: numeric('roi_this_product', { precision: 6, scale: 2 }),
  roi_vs_20x_target: numeric('roi_vs_20x_target', { precision: 6, scale: 2 }),
  status_recommendation: text('status_recommendation'),
  recommendation_detail: text('recommendation_detail'),
  recommendation_reasoning: text('recommendation_reasoning'),
  recommendation_date: date('recommendation_date'),
  recommendation_approved: boolean('recommendation_approved').default(false),
  recommendation_approval_id: uuid('recommendation_approval_id'),
  snapshot_month: text('snapshot_month'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

━━━ SECTION 12: COMPETITIVE INTELLIGENCE ━━━

export const cateros_competitors = pgTable('cateros_competitors', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  industry: text('industry').notNull(),
  country: text('country').default('UAE'),
  website_url: text('website_url'),
  instagram_handle: text('instagram_handle'),
  google_maps_place_id: text('google_maps_place_id'),
  google_maps_url: text('google_maps_url'),
  brand: text('brand'),
  direct_competitor: boolean('direct_competitor').default(true),
  tagline: text('tagline'),
  price_range: text('price_range'),
  key_products: text('key_products').array(),
  stated_differentiators: text('stated_differentiators').array(),
  google_rating: numeric('google_rating', { precision: 3, scale: 2 }),
  google_review_count: integer('google_review_count'),
  instagram_follower_count: integer('instagram_follower_count'),
  instagram_avg_engagement_rate: numeric('instagram_avg_engagement_rate', { precision: 5, scale: 4 }),
  is_active: boolean('is_active').default(true),
  added_by: text('added_by').default('manual'),
  last_scraped_at: timestamp('last_scraped_at'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

export const cateros_competitor_snapshots = pgTable('cateros_competitor_snapshots', {
  id: uuid('id').primaryKey().defaultRandom(),
  competitor_id: uuid('competitor_id'),
  snapshot_month: text('snapshot_month'),
  snapshot_type: text('snapshot_type').default('full'),
  website_content_summary: text('website_content_summary'),
  menu_items: jsonb('menu_items'),
  pricing_data: jsonb('pricing_data'),
  recent_announcements: text('recent_announcements').array(),
  google_rating: numeric('google_rating', { precision: 3, scale: 2 }),
  google_review_count: integer('google_review_count'),
  google_reviews_sample: jsonb('google_reviews_sample'),
  google_common_complaints: text('google_common_complaints').array(),
  google_common_praises: text('google_common_praises').array(),
  google_sentiment_summary: text('google_sentiment_summary'),
  instagram_follower_count: integer('instagram_follower_count'),
  instagram_post_count_mtd: integer('instagram_post_count_mtd'),
  instagram_avg_likes: integer('instagram_avg_likes'),
  instagram_avg_comments: integer('instagram_avg_comments'),
  instagram_engagement_rate: numeric('instagram_engagement_rate', { precision: 5, scale: 4 }),
  instagram_top_posts: jsonb('instagram_top_posts'),
  instagram_content_themes: text('instagram_content_themes').array(),
  instagram_comment_complaints: text('instagram_comment_complaints').array(),
  instagram_comment_praises: text('instagram_comment_praises').array(),
  positioning_summary: text('positioning_summary'),
  actual_strengths: text('actual_strengths').array(),
  actual_weaknesses: text('actual_weaknesses').array(),
  pricing_position: text('pricing_position'),
  content_strategy_summary: text('content_strategy_summary'),
  raw_scrape_data: jsonb('raw_scrape_data'),
  created_at: timestamp('created_at').defaultNow()
})

export const cateros_blue_ocean_reports = pgTable('cateros_blue_ocean_reports', {
  id: uuid('id').primaryKey().defaultRandom(),
  report_month: text('report_month'),
  industry: text('industry'),
  brand: text('brand'),
  competitors_analysed: integer('competitors_analysed'),
  landscape_summary: text('landscape_summary'),
  universal_complaints: jsonb('universal_complaints'),
  unserved_needs: jsonb('unserved_needs'),
  competitor_blind_spots: jsonb('competitor_blind_spots'),
  blue_ocean_opportunities: jsonb('blue_ocean_opportunities'),
  product_innovations: jsonb('product_innovations'),
  messaging_opportunities: jsonb('messaging_opportunities'),
  scout_briefing: text('scout_briefing'),
  pipeline_briefing: text('pipeline_briefing'),
  broadcast_briefing: text('broadcast_briefing'),
  product_flags: text('product_flags').array(),
  executive_summary: text('executive_summary'),
  status: text('status').default('pending_approval'),
  approval_request_id: uuid('approval_request_id'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ SECTION 13: PARTNERSHIPS ━━━

export const cateros_partnerships = pgTable('cateros_partnerships', {
  id: uuid('id').primaryKey().defaultRandom(),
  partner_name: text('partner_name').notNull(),
  partner_type: text('partner_type'),
  brand: text('brand'),
  deal_type: text('deal_type'),
  our_commitment: text('our_commitment'),
  our_commitment_value_aed: numeric('our_commitment_value_aed', { precision: 10, scale: 2 }),
  their_commitment: text('their_commitment'),
  their_commitment_value_aed: numeric('their_commitment_value_aed', { precision: 10, scale: 2 }),
  net_value_to_us_aed: numeric('net_value_to_us_aed', { precision: 10, scale: 2 }),
  start_date: date('start_date'),
  end_date: date('end_date'),
  auto_renew: boolean('auto_renew').default(false),
  status: text('status').default('proposed'),
  approval_request_id: uuid('approval_request_id'),
  leads_attributed: integer('leads_attributed').default(0),
  revenue_attributed_aed: numeric('revenue_attributed_aed', { precision: 10, scale: 2 }).default('0'),
  actual_roi: numeric('actual_roi', { precision: 6, scale: 2 }).default('0'),
  contact_name: text('contact_name'),
  contact_email: text('contact_email'),
  notes: text('notes'),
  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

━━━ SECTION 14: INTELLIGENCE ━━━

export const cateros_intelligence = pgTable('cateros_intelligence', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand'),
  report_type: text('report_type'),
  title: text('title'),
  summary: text('summary'),
  full_report: text('full_report'),
  sources: text('sources').array(),
  entity_id: uuid('entity_id'),
  action_recommended: text('action_recommended'),
  urgency: text('urgency').default('normal'),
  status: text('status').default('new'),
  created_at: timestamp('created_at').defaultNow()
})

━━━ AFTER WRITING ALL SECTIONS ━━━
Run these commands in terminal:
npx drizzle-kit generate:pg
npx drizzle-kit push:pg
```
# PHASE 1 — ORCHESTRATOR AGENT

---

## PROMPT 1.1 — Orchestrator System Prompts

```
Create src/agents/orchestrator.ts and add these exported system prompt constants at the top.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const ORCHESTRATOR_CORE_PROMPT = `
You are the Orchestrator — the governing intelligence of CaterOS.
You coordinate five specialist agents for two brands:

MIKANA FOOD SERVICE: UAE/Lebanon B2B catering — schools + corporate campuses.
8+ years. HACCP-certified. 1,000+ daily covers. Nutritionist-designed menus.

BOXED & GO: UAE D2C meal subscription — households + professionals.
Heat & Eat (3min reheat) · Build Your Plate (13min finish, 1,500 combos)
Social Table (family 3-4 people) · Nutritionist Plan (macro-counted).

THE 20x ROI LAW:
Every AED spent on marketing AND platform operating costs combined must generate
20 AED in attributed revenue. This is not a guideline. It is the governing constraint
of every single decision, recommendation, allocation, and approval you process.

APPROVAL DECISION FRAMEWORK:
Before queuing any action that involves spend, ask:
(projected revenue from this action) ÷ (cost of action + fair share of platform overhead) ≥ 20?
If NO → downgrade the action (cheaper channel, smaller spend) or do not queue it.
If YES → queue for approval with the ROI justification clearly stated.

CHANNEL ROI BENCHMARKS (UAE food service market):
School renewals:     50–100x  (near-zero CAC, AED 400K+ lifetime value)
SEO inbound:         30–80x   (compounds; content costs amortise over years)
Referral programs:   ∞        (zero acquisition cost — maximise always)
LinkedIn outreach:   15–40x   (only justified for contracts > AED 200K)
Instagram organic:   8–25x    (depends on subscriber retention rate)
Paid Meta ads:       5–15x    (only run if subscriber LTV × 20 > projected CAC)
Influencer:          3–12x    (manage carefully; one partnership at a time)

ROI COLOUR SYSTEM (use in all reports and briefings):
🟢 ≥ 20x — target met
🟡 10–19x — approaching target, action needed within 30 days
🔴 < 10x — below threshold, reallocate immediately
⚫ < 1x — spending to lose money, pause this instant

ESCALATION RULES:
No response within 12 hours → first WhatsApp reminder
No response within 20 hours → second reminder + email
Expired without response → mark expired, log it, pipeline continues unblocked
CRITICAL items (food safety, legal, contract loss risk, budget overrun) → immediate WhatsApp regardless of hour

AUTONOMOUS ACTIONS (no approval needed):
Intelligence gathering, metric calculation, pattern recognition, briefing generation,
escalation reminders, engagement syncing, lead research, ROI analysis.

APPROVAL REQUIRED:
Sending any external communication, publishing any content, committing any budget,
making any product recommendation, proposing any targets, changing any cost tier.
`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const ORCHESTRATOR_ROI_PROMPT = `
You are running the 20x ROI analysis for CaterOS.

THE 20x STANDARD:
Total combined spend (marketing + platform operating costs) × 20 = minimum revenue required.
Report against this for every channel, every product type, and overall.

TRUE NET ROI FORMULA:
true_net_roi = (total_revenue - total_marketing_spend - platform_cost) / (total_marketing_spend + platform_cost)
gross_roi = total_revenue / total_marketing_spend  ← also report this for comparison

REALLOCATION TRIGGERS (propose immediately when detected):
- Channel ROI < 10x for 30 consecutive days → propose 30% budget reduction
- Channel ROI < 1x for 14 consecutive days → propose immediate pause + full reallocation
- Channel ROI > 30x for 30 consecutive days → propose 25% budget increase (40% max per channel)
- Overall ROI < 20x → emergency reallocation analysis required, alert owner

COMPOUNDING SIGNAL DETECTION:
Flag channels where ALL THREE are true simultaneously:
1. ROI is above 20x AND
2. ROI is increasing month-over-month AND
3. CAC is declining while volume is holding or growing
These are compounding channels — they deserve priority budget increases.

OUTPUT — valid JSON matching cateros_roi_snapshots table structure.
channels_below_20x array is mandatory — drives immediate reallocation actions.
Executive summary must open with: current overall ROI vs 20x target,
the revenue gap in AED if below target, and the top 3 actions to close any gap.
`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const ORCHESTRATOR_TARGET_PROMPT = `
You are proposing quarterly business targets and marketing budget allocations for CaterOS.

THE 20x CONSTRAINT ON TARGET SETTING:
Revenue target = (total marketing budget + platform costs) × 20 minimum.
Budget allocation = revenue target ÷ 20, then subtract platform costs = max marketing spend.
Never set a revenue target that does not cover the 20x cost multiple.

UAE SEASONALITY:
Q1 (Jan-Mar): School Term 2 strong. Corporate steady. B&G New Year health push.
Q2 (Apr-Jun): School renewal season — most critical quarter. B&G pre-summer push.
Q3 (Jul-Sep): Schools closed — near-zero school revenue. B&G summer challenge.
Q4 (Oct-Dec): School Term 1 energy. National Day promotions. B&G festive push.

CHANNEL BUDGET ALLOCATION RULES (20x-enforcing):
1. Channels with proven > 20x ROI get budget first (cap 40% per channel)
2. Channels with 10–20x ROI: maintain allocation
3. Channels with < 10x ROI for 2+ months: reduce 50%
4. Channels with < 1x ROI for 1 month: pause, reallocate immediately
5. Always reserve 15% of budget for new channel experiments
6. SEO + referral = near-zero cost → maximise their revenue share always

For each budget allocation, include:
projected_roi_multiple: number
rationale: why this channel justifies spend at the 20x standard
reallocation_trigger: the exact condition that would trigger a reduction

OUTPUT — valid JSON with targets, budget_allocations array, and orchestrator_reasoning.
`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const ORCHESTRATOR_PRODUCT_PROMPT = `
You are evaluating individual product performance against the 20x ROI target.

VERDICT FRAMEWORK:
PROMOTE_AGGRESSIVELY: ROI > 20x + reorder rate > 60% + complaint rate < 3%
MAINTAIN:             ROI > 20x, metrics stable
REDUCE_PROMOTION:     ROI 10–20x — optimise before spending more
REPRICE_UP:           Demand inelastic, ROI < 20x — price is the lever
REPRICE_DOWN:         Volume too low due to price barrier — volume gain will restore ROI
MODIFY_RECIPE:        Good demand, poor reorder/high complaints — quality issue
MODIFY_PROCESS:       Good product, margins too thin — kitchen efficiency problem
BUNDLE_WITH:          Solo ROI weak but bundle ROI strong
SEASONAL_ONLY:        Strong 6–8 weeks/year, not worth year-round production
PHASE_OUT:            ROI < 5x after 3 months of optimisation attempts

roi_vs_20x_target = product_roi - 20
Positive = exceeding target. Negative = how far below target.

OUTPUT — valid JSON array, one object per product with full reasoning.
`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const ORCHESTRATOR_COST_PROMPT = `
You are managing CaterOS platform operating costs.
Current situation is provided in each call.

COST OPTIMISATION PRIORITY (throttle in this order when approaching ceiling):
1. NEVER THROTTLE: owner approval notifications, CRITICAL alerts, renewal warnings
2. First throttle: competitive intelligence scraping depth (reduce competitors per run)
3. Second throttle: SEO article generation frequency (reduce articles per batch)
4. Third throttle: social post generation rate (fewer drafts per cycle)
5. Last resort: batch approval notifications hourly instead of real-time

TIER UPGRADE RULES (all three must be true):
1. Utilisation > 90% for 2 consecutive months
2. Revenue has crossed the tier's upgrade_trigger_revenue_aed threshold
3. ROI of additional capability > 20x (extra monthly cost × 20 ≤ expected extra revenue)

TIER DOWNGRADE RULES (all three must be true):
1. Utilisation < 50% for 2 consecutive months
2. Revenue below current tier's threshold
3. No capability degradation in 30 days

PLATFORM COST HEALTH TARGETS:
Green: platform cost < 2% of monthly attributed revenue
Amber: 2–5% of revenue
Red: > 5% of revenue — flag immediately in next briefing

OUTPUT — valid JSON with cost status, throttling_actions[], tier_change_recommendation,
and executive_summary (2–3 sentences, plain English for owner).
`
```

---

## PROMPT 1.2 — Orchestrator Core Functions

```
Continue building src/agents/orchestrator.ts

Add all imports at the top:
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { calculateTrueNetROI, usdToAed, formatAED, formatROI, roiEmoji } from '@/lib/utils'
import { APPROVAL_EXPIRY_HOURS, ROI_TARGET, PLATFORM_TIERS } from '@/lib/constants'
import * as schema from '@/lib/schema'
import { eq, lte, gte, and, desc, sql, isNull } from 'drizzle-orm'
import { sendWhatsApp } from '@/integrations/whatsapp'
import { sendEmail, sendApprovalEmail } from '@/integrations/resend'

Then implement ALL of the following functions. Write each completely — no TODOs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 1: logActivity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function logActivity(
  agent: string, action: string, brand: string,
  entityId: string | null, entityType: string | null,
  result: string, approvalRequestId?: string, errorMessage?: string
): Promise<void> {
  await db.insert(schema.cateros_agent_activity).values({
    agent, action, brand, entity_id: entityId, entity_type: entityType,
    result, approval_request_id: approvalRequestId, error_message: errorMessage
  })
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 2: queueForApproval
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function queueForApproval(params: {
  type: string; brand: string; title: string; summary: string;
  payload: Record<string, unknown>; agent: string;
  entityId: string; entityType: string; priority?: string
}): Promise<typeof schema.cateros_approval_requests.$inferSelect> {

  const expiresAt = new Date()
  expiresAt.setHours(expiresAt.getHours() + (APPROVAL_EXPIRY_HOURS[params.type] ?? 24))

  const [request] = await db.insert(schema.cateros_approval_requests).values({
    type: params.type, brand: params.brand, title: params.title,
    summary: params.summary, payload: params.payload, agent: params.agent,
    entity_id: params.entityId, entity_type: params.entityType,
    priority: params.priority ?? 'normal', status: 'pending', expires_at: expiresAt
  }).returning()

  // Send WhatsApp notification
  const agentEmojis: Record<string, string> = {
    scout: '🔍', pipeline: '📋', broadcast: '📡',
    seo_engine: '🔎', customer_care: '💬', orchestrator: '🧠'
  }
  const brandEmojis: Record<string, string> = { mikana: '🍽️', boxedgo: '📦', both: '🏢' }
  const expiryHours = APPROVAL_EXPIRY_HOURS[params.type] ?? 24
  const shortId = request.id.substring(0, 8).toUpperCase()

  const msg = `${agentEmojis[params.agent] ?? '🤖'} *CaterOS — Action Required*

*${params.title}* ${brandEmojis[params.brand] ?? ''}

${params.summary}

Reply:
✅ *APPROVE*
✏️ *EDIT: [your changes]*
❌ *REJECT: [reason]*

_ID: ${shortId} · Expires ${expiryHours}h_`

  try {
    const result = await sendWhatsApp(process.env.OWNER_WHATSAPP!, msg)
    await db.update(schema.cateros_approval_requests).set({
      whatsapp_message_id: result.messageId,
      whatsapp_sent_at: new Date(),
      notification_sent_at: new Date()
    }).where(eq(schema.cateros_approval_requests.id, request.id))
  } catch (e) {
    console.error('[ORCHESTRATOR] WhatsApp notification failed:', e)
  }

  try {
    await sendApprovalEmail(request)
  } catch (e) {
    console.error('[ORCHESTRATOR] Email notification failed:', e)
  }

  await logActivity(params.agent, `Queued for approval: ${params.title}`,
    params.brand, params.entityId, params.entityType, 'queued_for_approval', request.id)

  return request
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 3: processOwnerReply
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function processOwnerReply(
  messageBody: string, fromNumber: string
): Promise<void> {
  const ownerNumber = process.env.OWNER_WHATSAPP!.replace('+', '')
  const senderNumber = fromNumber.replace('+', '').replace('whatsapp:', '')
  if (senderNumber !== ownerNumber) return

  const body = messageBody.trim()
  const bodyUpper = body.toUpperCase()

  // Handle ALL APPROVE batch
  if (bodyUpper === 'ALL APPROVE') {
    await approveAllPending()
    await sendWhatsApp(process.env.OWNER_WHATSAPP!, '✅ All pending approvals approved and queued for execution.')
    return
  }

  // Find which approval this refers to
  // First try shortId in message, then fall back to most recent pending
  let request: typeof schema.cateros_approval_requests.$inferSelect | undefined
  const shortIdMatch = body.match(/ID:\s*([A-F0-9]{8})/i)

  if (shortIdMatch) {
    const prefix = shortIdMatch[1].toLowerCase()
    const all = await db.query.cateros_approval_requests.findMany({
      where: eq(schema.cateros_approval_requests.status, 'pending')
    })
    request = all.find(r => r.id.replace(/-/g, '').startsWith(prefix.replace(/-/g, '')))
  }

  if (!request) {
    request = await db.query.cateros_approval_requests.findFirst({
      where: eq(schema.cateros_approval_requests.status, 'pending'),
      orderBy: [desc(schema.cateros_approval_requests.created_at)]
    })
  }

  if (!request) {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!, '⚠️ No pending approvals found. Check CaterOS for any waiting items.')
    return
  }

  let decision = ''
  let editedContent: string | null = null

  if (bodyUpper.startsWith('APPROVE') || body === '✅') {
    decision = 'approved'
  } else if (bodyUpper.startsWith('EDIT:')) {
    decision = 'edited'
    editedContent = body.substring(5).trim()
  } else if (bodyUpper.startsWith('REJECT')) {
    decision = 'rejected'
  } else {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `❓ Reply: APPROVE / EDIT: [changes] / REJECT: [reason]\nFor: "${request.title}"`)
    return
  }

  await db.update(schema.cateros_approval_requests).set({
    status: decision,
    owner_decision: body,
    edited_payload: editedContent ? { content: editedContent } : null,
    responded_at: new Date()
  }).where(eq(schema.cateros_approval_requests.id, request.id))

  if (decision === 'approved' || decision === 'edited') {
    await executeApprovedAction(request, editedContent)
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `✅ Done — "${request.title}" approved and queued for execution.`)
  } else {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `❌ Noted — "${request.title}" declined. Agents have moved on.`)
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 4: approveAllPending
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async function approveAllPending(): Promise<void> {
  const pending = await db.query.cateros_approval_requests.findMany({
    where: eq(schema.cateros_approval_requests.status, 'pending')
  })
  for (const request of pending) {
    await db.update(schema.cateros_approval_requests).set({
      status: 'approved', owner_decision: 'ALL APPROVE', responded_at: new Date()
    }).where(eq(schema.cateros_approval_requests.id, request.id))
    await executeApprovedAction(request, null)
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 5: executeApprovedAction
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function executeApprovedAction(
  request: typeof schema.cateros_approval_requests.$inferSelect,
  editedContent: string | null
): Promise<void> {
  const payload = (request.payload ?? {}) as Record<string, unknown>

  try {
    switch (request.type) {
      case 'new_lead_school':
        await db.update(schema.cateros_school_leads)
          .set({ stage: 'identified', updated_at: new Date() })
          .where(eq(schema.cateros_school_leads.id, payload.leadId as string))
        const { generateSchoolOutreach } = await import('./pipeline')
        await generateSchoolOutreach(payload.leadId as string)
        break

      case 'new_lead_corporate':
        await db.update(schema.cateros_corporate_leads)
          .set({ stage: 'identified', updated_at: new Date() })
          .where(eq(schema.cateros_corporate_leads.id, payload.leadId as string))
        const { generateCorporateOutreach } = await import('./pipeline')
        await generateCorporateOutreach(payload.leadId as string)
        break

      case 'new_subscriber':
        await db.update(schema.cateros_bg_subscribers)
          .set({ stage: 'awareness', updated_at: new Date() })
          .where(eq(schema.cateros_bg_subscribers.id, payload.subscriberId as string))
        break

      case 'outreach_email': {
        const body = editedContent ?? (payload.body as string)
        await db.update(schema.cateros_outreach)
          .set({ status: 'approved', body })
          .where(eq(schema.cateros_outreach.id, payload.outreachId as string))
        const { sendOutreachEmail } = await import('@/integrations/resend')
        await sendOutreachEmail({
          to: payload.contactEmail as string,
          subject: payload.subject as string,
          body
        })
        await db.update(schema.cateros_outreach)
          .set({ status: 'sent', sent_at: new Date() })
          .where(eq(schema.cateros_outreach.id, payload.outreachId as string))
        break
      }

      case 'social_post':
        await db.update(schema.cateros_social_posts).set({
          status: 'approved',
          caption: editedContent ?? undefined
        }).where(eq(schema.cateros_social_posts.id, payload.postId as string))
        break

      case 'seo_article':
        await db.update(schema.cateros_seo_content).set({
          status: 'approved',
          content_markdown: editedContent ?? undefined
        }).where(eq(schema.cateros_seo_content.id, payload.contentId as string))
        break

      case 'spending_decision':
        if ((payload.subtype as string) === 'tier_change') {
          await applyTierChange(payload.proposedTier as string)
        } else if ((payload.subtype as string) === 'quarterly_targets') {
          await db.update(schema.cateros_business_targets)
            .set({ status: 'approved', updated_at: new Date() })
            .where(eq(schema.cateros_business_targets.id, payload.targetsId as string))
        } else if ((payload.subtype as string) === 'budget_reallocation') {
          await reallocateBudget(
            payload.fromEnvelopeId as string,
            payload.toEnvelopeId as string,
            parseFloat(payload.amountAed as string)
          )
        }
        break

      case 'blue_ocean_report':
        await db.update(schema.cateros_blue_ocean_reports)
          .set({ status: 'approved' })
          .where(eq(schema.cateros_blue_ocean_reports.id, payload.reportId as string))
        break
    }

    await logActivity('orchestrator', `Executed: ${request.title}`,
      request.brand ?? 'both', request.entity_id, request.entity_type, 'executed', request.id)

  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error)
    await logActivity('orchestrator', `Execution failed: ${request.title}`,
      request.brand ?? 'both', request.entity_id, request.entity_type, 'failed',
      request.id, msg)
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 6: generateMorningBriefing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function generateMorningBriefing(): Promise<void> {
  const now = new Date()
  const yesterday = new Date(now.getTime() - 86400000)
  const isMonday = now.getDay() === 1

  const [pending, urgentIntel, recentActivity, latestROI, platformCost] = await Promise.all([
    db.query.cateros_approval_requests.findMany({
      where: eq(schema.cateros_approval_requests.status, 'pending'),
      orderBy: [desc(schema.cateros_approval_requests.priority)]
    }),
    db.query.cateros_intelligence.findMany({
      where: and(
        eq(schema.cateros_intelligence.urgency, 'urgent'),
        eq(schema.cateros_intelligence.status, 'new')
      )
    }),
    db.query.cateros_agent_activity.findMany({
      where: gte(schema.cateros_agent_activity.created_at, yesterday),
      orderBy: [desc(schema.cateros_agent_activity.created_at)]
    }),
    db.query.cateros_roi_snapshots.findFirst({
      orderBy: [desc(schema.cateros_roi_snapshots.created_at)]
    }),
    getCurrentMonthPlatformCost()
  ])

  const agentCounts: Record<string, number> = {}
  recentActivity.forEach(a => { agentCounts[a.agent] = (agentCounts[a.agent] ?? 0) + 1 })

  let msg = `☀️ *CaterOS Daily Briefing*
${now.toLocaleDateString('en-AE', { weekday: 'long', day: 'numeric', month: 'long' })}

`

  if (pending.length === 0) {
    msg += `✅ *Nothing needs your attention*\n`
  } else {
    msg += `*📋 Needs your input (${pending.length} item${pending.length > 1 ? 's' : ''}):*\n`
    pending.slice(0, 6).forEach((a, i) => {
      const hoursLeft = Math.max(0, Math.round(
        (new Date(a.expires_at!).getTime() - now.getTime()) / 3600000
      ))
      const urgentFlag = hoursLeft < 3 ? ' ⚠️' : ''
      msg += `${i + 1}. ${a.title}${urgentFlag} _(${hoursLeft}h left)_\n`
    })
    if (pending.length > 6) msg += `_...and ${pending.length - 6} more in CaterOS_\n`
  }

  msg += `
*🤖 Agents worked last 24h:*`
  const agents = ['scout', 'pipeline', 'broadcast', 'customer_care', 'seo_engine']
  agents.forEach(a => {
    if (agentCounts[a]) msg += `\n• ${a.replace('_', ' ')}: ${agentCounts[a]} actions`
  })

  if (isMonday && latestROI) {
    const roi = parseFloat(String(latestROI.true_net_roi ?? '0'))
    const rev = parseFloat(String(latestROI.total_revenue_aed ?? '0'))
    const costs = parseFloat(String(latestROI.total_spend_aed ?? '0')) +
                  parseFloat(String(latestROI.platform_cost_aed ?? '0'))
    const gap = roi < 20 ? formatAED((20 - roi) * costs) : null

    msg += `

*${roiEmoji(roi)} Weekly ROI (rolling 30 days):*
Overall: *${formatROI(roi)}* vs 20x target
${gap ? `Revenue gap: ${gap} needed to hit 20x` : '✅ 20x target achieved'}
Platform cost: ${formatAED(platformCost)} (${rev > 0 ? ((platformCost / rev) * 100).toFixed(1) : '0'}% of revenue)
${(latestROI.channels_below_20x as string[] ?? []).length > 0 
  ? `⚠️ Below 20x: ${(latestROI.channels_below_20x as string[]).join(', ')}` 
  : '✅ All channels at target'}`
  }

  if (urgentIntel.length > 0) {
    msg += `\n\n*⚡ Urgent intelligence (${urgentIntel.length}):*`
    urgentIntel.slice(0, 3).forEach(i => { msg += `\n• ${i.title}` })
  }

  msg += `\n\n_Open CaterOS for full details_`

  await sendWhatsApp(process.env.OWNER_WHATSAPP!, msg)

  // Save briefing to intelligence log
  await db.insert(schema.cateros_intelligence).values({
    brand: 'both',
    report_type: 'daily_summary',
    title: `Daily Briefing — ${now.toLocaleDateString('en-AE')}`,
    summary: msg,
    urgency: 'low',
    status: 'new'
  })
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 7: runEscalationCheck
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function runEscalationCheck(): Promise<void> {
  const now = new Date()
  const pending = await db.query.cateros_approval_requests.findMany({
    where: eq(schema.cateros_approval_requests.status, 'pending')
  })

  for (const req of pending) {
    const ageHours = req.notification_sent_at
      ? (now.getTime() - new Date(req.notification_sent_at).getTime()) / 3600000
      : 999

    const hoursLeft = req.expires_at
      ? (new Date(req.expires_at).getTime() - now.getTime()) / 3600000
      : 0

    // Expired
    if (hoursLeft <= 0) {
      await db.update(schema.cateros_approval_requests)
        .set({ status: 'expired' })
        .where(eq(schema.cateros_approval_requests.id, req.id))
      await sendWhatsApp(process.env.OWNER_WHATSAPP!,
        `⏱️ Approval expired: *"${req.title}"* — agents have moved on.`)
      continue
    }

    // First escalation at 12h
    if (ageHours > 12 && !req.first_escalation_at) {
      await sendWhatsApp(process.env.OWNER_WHATSAPP!,
        `⚠️ *Reminder:* "${req.title}" still needs your decision. ${Math.round(hoursLeft)}h remaining.`)
      await db.update(schema.cateros_approval_requests)
        .set({ first_escalation_at: now })
        .where(eq(schema.cateros_approval_requests.id, req.id))
    }

    // Second escalation at 20h (8h after first)
    if (req.first_escalation_at) {
      const sinceFirst = (now.getTime() - new Date(req.first_escalation_at).getTime()) / 3600000
      if (sinceFirst > 8 && !req.second_escalation_at) {
        await sendWhatsApp(process.env.OWNER_WHATSAPP!,
          `🚨 *Final reminder:* "${req.title}" expires in ${Math.round(hoursLeft)}h. Please action in CaterOS.`)
        await sendEmail({
          to: process.env.OWNER_EMAIL!,
          subject: `[CaterOS] Action required: "${req.title}" expires in ${Math.round(hoursLeft)}h`,
          body: `This CaterOS approval request expires soon and requires your decision.\n\nTitle: ${req.title}\nSummary: ${req.summary}\n\nOpen CaterOS to review.`
        })
        await db.update(schema.cateros_approval_requests)
          .set({ second_escalation_at: now })
          .where(eq(schema.cateros_approval_requests.id, req.id))
      }
    }
  }

  // Also run ROI signal check
  await checkROISignals()
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 8: runROIAnalysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function runROIAnalysis(period = 'rolling_30'): Promise<unknown> {
  const periodStart = new Date()
  if (period === 'rolling_30') periodStart.setDate(periodStart.getDate() - 30)
  else if (period === 'mtd') periodStart.setDate(1)
  else if (period === 'qtd') periodStart.setMonth(Math.floor(periodStart.getMonth() / 3) * 3, 1)

  const [spendEntries, revenueEntries, platformCost] = await Promise.all([
    db.query.cateros_spend_entries.findMany({
      where: gte(schema.cateros_spend_entries.spend_date, periodStart.toISOString().slice(0, 10))
    }),
    db.query.cateros_revenue_entries.findMany({
      where: gte(schema.cateros_revenue_entries.revenue_date, periodStart.toISOString().slice(0, 10))
    }),
    getCurrentMonthPlatformCost()
  ])

  const totalSpend = spendEntries.reduce((sum, e) => sum + parseFloat(String(e.amount_aed ?? '0')), 0)
  const totalRevenue = revenueEntries.reduce((sum, e) => sum + parseFloat(String(e.amount_aed ?? '0')), 0)

  const spendByChannel: Record<string, number> = {}
  spendEntries.forEach(e => {
    spendByChannel[e.channel ?? 'unknown'] = (spendByChannel[e.channel ?? 'unknown'] ?? 0) +
      parseFloat(String(e.amount_aed ?? '0'))
  })

  const revenueByChannel: Record<string, number> = {}
  revenueEntries.forEach(e => {
    revenueByChannel[e.acquisition_channel ?? 'unknown'] = (revenueByChannel[e.acquisition_channel ?? 'unknown'] ?? 0) +
      parseFloat(String(e.amount_aed ?? '0'))
  })

  const roiCalc = calculateTrueNetROI({
    revenueAed: totalRevenue,
    marketingSpendAed: totalSpend,
    platformCostAed: platformCost
  })

  const analysis = await callClaude({
    systemPrompt: ORCHESTRATOR_ROI_PROMPT,
    userMessage: JSON.stringify({
      period, period_start: periodStart.toISOString(),
      total_spend_aed: totalSpend,
      total_revenue_aed: totalRevenue,
      platform_cost_aed: platformCost,
      spend_by_channel: spendByChannel,
      revenue_by_channel: revenueByChannel,
      roi_calculations: roiCalc,
      roi_target: ROI_TARGET
    }),
    maxTokens: 2500,
    jsonMode: true
  })

  const parsed = JSON.parse(analysis)

  const [snapshot] = await db.insert(schema.cateros_roi_snapshots).values({
    snapshot_date: new Date().toISOString().slice(0, 10),
    brand: 'both', period,
    total_spend_aed: String(totalSpend),
    total_revenue_aed: String(totalRevenue),
    platform_cost_aed: String(platformCost),
    gross_roi: String(roiCalc.grossROI),
    true_net_roi: String(roiCalc.trueNetROI),
    roi_vs_20x_target: String(roiCalc.vsTargetGap),
    spend_by_channel: spendByChannel,
    revenue_by_channel: revenueByChannel,
    channels_below_20x: parsed.channels_below_20x ?? [],
    orchestrator_assessment: parsed.executive_summary,
    ...parsed
  }).returning()

  // Alert if below 20x
  if (roiCalc.trueNetROI < ROI_TARGET) {
    const totalCost = totalSpend + platformCost
    const gap = formatAED((ROI_TARGET - roiCalc.trueNetROI) * totalCost)
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `🔴 *ROI Alert — Below 20x Target*
Current: ${formatROI(roiCalc.trueNetROI)} vs 20x target
Revenue gap: ${gap} needed to reach target
${(parsed.channels_below_20x ?? []).length} channels below threshold

Open CaterOS → Financial for full analysis.`)
  }

  // Propose reallocation for channels severely below target
  for (const ch of parsed.underperforming_channels ?? []) {
    if (ch.current_roi < 10) {
      await proposeReallocation(ch.channel, ch.recommended_action, ch.suggested_reduction_aed)
    }
  }

  return snapshot
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 9: checkROISignals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function checkROISignals(): Promise<void> {
  const envelopes = await db.query.cateros_budget_envelopes.findMany({
    where: eq(schema.cateros_budget_envelopes.status, 'active')
  })

  for (const env of envelopes) {
    const roi = parseFloat(String(env.roi_current ?? '0'))
    const months = env.consecutive_below_roi_months ?? 0

    if (roi < 1) {
      // Below 1x — propose immediate pause
      await proposeReallocation(
        env.channel_label ?? env.channel ?? 'unknown',
        'immediate_pause',
        parseFloat(String(env.remaining_amount_aed ?? '0'))
      )
    } else if (roi < 10 && months >= 1) {
      // Below 10x for 2+ months — propose 50% reduction
      await proposeReallocation(
        env.channel_label ?? env.channel ?? 'unknown',
        'reduce_50pct',
        parseFloat(String(env.allocated_amount_aed ?? '0')) * 0.5
      )
    }
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 10: proposeReallocation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function proposeReallocation(
  channel: string, action: string, amountAed: number
): Promise<void> {
  const actionLabels: Record<string, string> = {
    immediate_pause: 'Pause immediately — ROI below 1x',
    reduce_50pct: 'Reduce budget by 50% — ROI below 10x for 2+ months',
    reduce_30pct: 'Reduce budget by 30% — ROI declining',
    increase_25pct: 'Increase budget by 25% — ROI above 30x and compounding'
  }

  await queueForApproval({
    type: 'spending_decision',
    brand: 'both',
    title: `Budget Reallocation — ${channel}`,
    summary: `${actionLabels[action] ?? action}\nChannel: ${channel}\nAmount affected: ${formatAED(amountAed)}\n\nThis reallocation protects the 20x ROI target by reducing spend on underperforming channels.`,
    payload: { subtype: 'budget_reallocation', channel, action, amountAed },
    agent: 'orchestrator',
    entityId: crypto.randomUUID(),
    entityType: 'budget_envelope',
    priority: action === 'immediate_pause' ? 'urgent' : 'normal'
  })
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 11: reallocateBudget
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function reallocateBudget(
  fromEnvelopeId: string, toEnvelopeId: string, amountAed: number
): Promise<void> {
  await db.update(schema.cateros_budget_envelopes).set({
    allocated_amount_aed: sql`allocated_amount_aed - ${amountAed}`,
    remaining_amount_aed: sql`remaining_amount_aed - ${amountAed}`,
    updated_at: new Date()
  }).where(eq(schema.cateros_budget_envelopes.id, fromEnvelopeId))

  await db.update(schema.cateros_budget_envelopes).set({
    allocated_amount_aed: sql`allocated_amount_aed + ${amountAed}`,
    remaining_amount_aed: sql`remaining_amount_aed + ${amountAed}`,
    updated_at: new Date()
  }).where(eq(schema.cateros_budget_envelopes.id, toEnvelopeId))
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 12: applyTierChange
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function applyTierChange(newTierName: string): Promise<void> {
  await db.update(schema.cateros_platform_cost_tiers)
    .set({ is_active: false })

  await db.update(schema.cateros_platform_cost_tiers)
    .set({ is_active: true })
    .where(eq(schema.cateros_platform_cost_tiers.tier_name, newTierName))

  const tier = PLATFORM_TIERS[newTierName as keyof typeof PLATFORM_TIERS]
  if (tier) {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `⚙️ CaterOS platform tier changed to *${newTierName.toUpperCase()}*.\nNew monthly ceiling: ${formatAED(tier.ceiling_aed)}/month.`)
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 13: getCurrentMonthPlatformCost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function getCurrentMonthPlatformCost(): Promise<number> {
  const period = new Date().toISOString().slice(0, 7)
  const budget = await db.query.cateros_platform_cost_budgets.findFirst({
    where: eq(schema.cateros_platform_cost_budgets.period, period)
  })
  return parseFloat(String(budget?.actual_spend_aed ?? '0'))
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 14: logPlatformCost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function logPlatformCost(params: {
  service: string; serviceLabel: string;
  amount: number; currency: 'USD' | 'AED';
  billingPeriod: string; usageDescription: string; isEstimate: boolean
}): Promise<void> {
  const amountAed = params.currency === 'USD' ? usdToAed(params.amount) : params.amount
  const rate = parseFloat(process.env.USD_TO_AED_RATE ?? '3.67')

  await db.insert(schema.cateros_platform_cost_entries).values({
    service: params.service, service_label: params.serviceLabel,
    currency: params.currency, amount: String(params.amount),
    amount_aed: String(amountAed),
    usd_rate_used: params.currency === 'USD' ? String(rate) : null,
    billing_period: params.billingPeriod,
    usage_description: params.usageDescription,
    is_estimate: params.isEstimate
  })

  // Update budget record
  const period = params.billingPeriod
  const existing = await db.query.cateros_platform_cost_budgets.findFirst({
    where: eq(schema.cateros_platform_cost_budgets.period, period)
  })

  if (existing) {
    const newSpend = parseFloat(String(existing.actual_spend_aed ?? '0')) + amountAed
    const ceiling = parseFloat(String(existing.approved_ceiling_aed ?? '999'))
    const pct = (newSpend / ceiling) * 100

    await db.update(schema.cateros_platform_cost_budgets).set({
      actual_spend_aed: String(newSpend),
      updated_at: new Date()
    }).where(eq(schema.cateros_platform_cost_budgets.id, existing.id))

    // Alert thresholds
    if (pct >= 80 && !existing.alert_80pct_sent) {
      await sendWhatsApp(process.env.OWNER_WHATSAPP!,
        `📊 *Platform Cost Alert — 80%*\n${formatAED(newSpend)} spent of ${formatAED(ceiling)} ceiling.\nProjected month-end: ${formatAED(newSpend * (30 / new Date().getDate()))}.`)
      await db.update(schema.cateros_platform_cost_budgets)
        .set({ alert_80pct_sent: true })
        .where(eq(schema.cateros_platform_cost_budgets.id, existing.id))
    }
    if (pct >= 100 && !existing.alert_100pct_sent) {
      await sendWhatsApp(process.env.OWNER_WHATSAPP!,
        `🚨 *Platform Cost OVERRUN*\n${formatAED(newSpend)} spent — ceiling of ${formatAED(ceiling)} exceeded.\nAuto-throttling non-critical operations.`)
      await db.update(schema.cateros_platform_cost_budgets)
        .set({ alert_100pct_sent: true })
        .where(eq(schema.cateros_platform_cost_budgets.id, existing.id))
    }
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 15: proposeQuarterlyTargets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function proposeQuarterlyTargets(): Promise<void> {
  const latestROI = await db.query.cateros_roi_snapshots.findFirst({
    orderBy: [desc(schema.cateros_roi_snapshots.created_at)]
  })

  const currentTargets = await db.query.cateros_business_targets.findFirst({
    where: eq(schema.cateros_business_targets.status, 'approved'),
    orderBy: [desc(schema.cateros_business_targets.created_at)]
  })

  const proposal = await callClaude({
    systemPrompt: ORCHESTRATOR_TARGET_PROMPT,
    userMessage: JSON.stringify({
      latest_roi: latestROI,
      current_targets: currentTargets,
      current_date: new Date().toISOString(),
      roi_target: ROI_TARGET
    }),
    maxTokens: 3000,
    jsonMode: true
  })

  const data = JSON.parse(proposal)

  const [targets] = await db.insert(schema.cateros_business_targets).values({
    ...data.targets,
    target_roi_multiplier: String(ROI_TARGET),
    status: 'pending_approval',
    orchestrator_reasoning: data.reasoning
  }).returning()

  await queueForApproval({
    type: 'spending_decision',
    brand: 'both',
    title: `Quarterly Targets & Budget — ${data.targets.period_label ?? 'Next Quarter'}`,
    summary: `Revenue target: ${formatAED(data.targets.target_revenue_aed)}.\nMarketing budget: ${formatAED(data.total_marketing_budget_aed)}.\n20x required: ${formatAED(data.total_marketing_budget_aed * ROI_TARGET)} minimum revenue.\n${data.reasoning?.slice(0, 200) ?? ''}`,
    payload: { subtype: 'quarterly_targets', targetsId: targets.id, ...data },
    agent: 'orchestrator',
    entityId: targets.id,
    entityType: 'business_targets'
  })
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNCTION 16: runWeeklyFinancialReview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export async function runWeeklyFinancialReview(): Promise<void> {
  await runROIAnalysis('rolling_30')
  await runROIAnalysis('mtd')
  await checkROISignals()
}

export { ORCHESTRATOR_CORE_PROMPT, ORCHESTRATOR_ROI_PROMPT,
  ORCHESTRATOR_TARGET_PROMPT, ORCHESTRATOR_PRODUCT_PROMPT, ORCHESTRATOR_COST_PROMPT }
```
# PHASE 2 — SCOUT AGENT

---

## PROMPT 2.1 — Scout Agent

```
Create src/agents/scout.ts — fully autonomous market intelligence agent.

Add these imports:
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { queueForApproval, logActivity } from './orchestrator'
import * as schema from '@/lib/schema'
import { eq, isNull, lte, and } from 'drizzle-orm'
import { formatAED } from '@/lib/utils'

━━━ SYSTEM PROMPTS ━━━

export const SCOUT_SCHOOLS_PROMPT = `
You are Scout — market intelligence agent for Mikana Food Service school catering.

MIKANA: Premium UAE/Lebanon caterer. HACCP-certified (KHDA/MOE audit-ready).
Nutritionist-designed rotating menus. Allergen management. Arabic/English bilingual.
8+ years school food service. 1,000+ daily covers experience.

ROI REALITY: School contracts = 50-100x ROI. Near-zero CAC once relationship starts.
Average contract: AED 400K-800K/year. Renewal window (90 days before expiry) is
the highest-value moment in the entire sales calendar.

UAE SCHOOL DECISION MAKERS:
Small (< 500 students): Principal makes food decisions
Medium (500-1,500): Head of Operations / Facilities Director
Large groups (GEMS, Taaleem, Bloom, Nord Anglia): Procurement Committee

PRICING: AED 12-22/meal (Mikana targets AED 15-20 — quality premium tier)
Daily covers = students × 0.7 (not all students buy every day) + staff

QUALIFY A SCHOOL AS HIGH PRIORITY IF:
- Student count > 800
- Competitor contract is 6-12 months from typical renewal (usually academic year end: June)
- Current provider has poor Google/social reviews
- School fees are premium tier (correlates with F&B budget willingness)
- No current provider (in-house or none) — immediate opportunity

OUTPUT — valid JSON ONLY:
{
  "school_overview": "string",
  "student_count_estimate": number,
  "total_daily_covers": number,
  "estimated_annual_value_aed": number,
  "current_contract_status": "active_mikana|active_competitor|in_house|no_service|unknown",
  "competitor_name": "string or null",
  "estimated_contract_renewal_window": "string",
  "qualification_score": number (1-10),
  "qualification_reasoning": "string",
  "decision_maker_likely_title": "string",
  "key_pain_points": ["string"],
  "recommended_outreach_angle": "string",
  "personalisation_hooks": ["string", "string", "string"],
  "best_outreach_timing": "string",
  "action": "outreach_now|monitor_for_renewal|research_more|skip",
  "projected_roi_multiple": number
}
`

export const SCOUT_CORPORATE_PROMPT = `
You are Scout — market intelligence agent for Mikana Food Service corporate catering.

TARGET ZONES PHASE 1:
Free zones: DIFC, Dubai Internet City, Dubai Design District, Dubai South,
twofour54, Masdar City, Abu Dhabi Global Market, Expo City Dubai.
These zones have captive workforces that cannot easily leave for lunch.
That captivity = pricing power for the caterer.

FUTURE PHASES: Private hospitals and day surgery centres (HACCP compliance = natural fit).
Construction labour camps (volume efficiency = Mikana strength).

ROI REALITY: Corporate contracts = 15-40x ROI. High deal value (AED 200K-1M+/year).
LinkedIn outreach at AED 50/message: even 1% response rate on a AED 500K deal = 100x.
Only worth LinkedIn spend for deals > AED 200K.

MIKANA EDGE FOR CORPORATE:
HACCP compliance stricter than most corporate caterers.
Cost-per-head transparency (no hidden fees).
Nutritionist-designed menus for diverse workforces (70+ nationalities in Dubai).
Arabic/English bilingual team.

PRICING: AED 22-35/meal × 250 working days/year.

OUTPUT — valid JSON ONLY:
{
  "company_overview": "string",
  "employee_count_estimate": number,
  "daily_meals_opportunity": number,
  "annual_value_estimate_aed": number,
  "current_food_situation": "no_service|in_house|outsourced_competitor|unknown",
  "competitor_name": "string or null",
  "qualification_score": number (1-10),
  "qualification_reasoning": "string",
  "decision_maker_likely_title": "string",
  "pain_points_to_address": ["string"],
  "recommended_outreach_angle": "string",
  "personalisation_hooks": ["string", "string", "string"],
  "projected_roi_multiple": number,
  "action": "outreach_now|research_more|monitor|skip"
}
`

export const SCOUT_BOXEDGO_PROMPT = `
You are Scout doing audience and market research for Boxed & Go UAE meal subscription brand.

PRODUCTS:
Heat & Eat: Fully cooked, reheat 3 minutes. Zero effort.
Build Your Plate: 3-part system — protein (80% cooked, finish 8-13 min) × side × sauce.
  Generates 1,500 combinations from a rotating menu. Maximum variety, controlled effort.
Social Table: Family-style for 3-4 people, semi-prepared, big serving dishes.
Nutritionist Plan: Macro-counted, calorie-tracked, portion-controlled.

TARGET SEGMENTS:
UAE households: Dual-income expat/Emirati families. Cooking time scarce. Quality matters.
Individual professionals: Time-poor 25-40s. Health-conscious. Delivery app fatigued.
  Delivery apps = overpriced, unhealthy, inconsistent. We are the structured alternative.

CAC DISCIPLINE (20x ROI):
Average plan: AED 1,150/month × average retention 8 months = AED 9,200 LTV.
At 20x ROI: max acceptable CAC = AED 9,200 ÷ 20 = AED 460.
But first-month-only metric: AED 1,150 ÷ 20 = AED 57.50 max CAC per first sale.
Best acquisition: referral (AED 0), SEO inbound (near zero), Instagram organic (low).
Paid Meta only justified if subscriber converts and retains 3+ months.

OUTPUT — valid JSON ONLY:
{
  "geographic_opportunity": "string",
  "audience_segment_insights": {
    "households": "string",
    "professionals": "string"
  },
  "competitor_gaps": ["string"],
  "low_cac_acquisition_opportunities": ["string"],
  "high_roi_campaign_angles": ["string"],
  "influencer_profile_targets": ["string"],
  "content_themes_for_organic": ["string"],
  "zero_cac_partnership_ideas": ["string"],
  "recommended_immediate_actions": ["string"]
}
`

━━━ FUNCTIONS ━━━

export async function researchSchool(
  schoolName: string, emirate: string, type: string, additionalContext?: string
): Promise<void> {
  const response = await callClaude({
    systemPrompt: SCOUT_SCHOOLS_PROMPT,
    userMessage: `Research this school for Mikana Food Service catering opportunity:
School name: ${schoolName}
Emirate: ${emirate}
Type/curriculum: ${type}
Additional context: ${additionalContext ?? 'none provided'}

Provide thorough qualification assessment.`,
    maxTokens: 1500,
    jsonMode: true
  })

  const data = JSON.parse(response)

  // Upsert school
  const [school] = await db.insert(schema.cateros_schools).values({
    name: schoolName, emirate, type,
    student_count: data.student_count_estimate,
    total_daily_covers: data.total_daily_covers,
    current_contract_status: data.current_contract_status,
    competitor_name: data.competitor_name,
    qualification_score: data.qualification_score,
    source: 'scout_agent',
    notes: data.qualification_reasoning
  }).returning()

  await logActivity('scout', `Researched school: ${schoolName}`,
    'mikana', school.id, 'school', 'executed')

  // Queue for approval if score qualifies
  if (data.qualification_score >= 6 && data.action !== 'skip') {
    const [lead] = await db.insert(schema.cateros_school_leads).values({
      school_id: school.id,
      lead_type: 'new_acquisition',
      stage: 'pending_approval',
      estimated_value_aed: data.estimated_annual_value_aed,
      next_action: data.recommended_outreach_angle
    }).returning()

    await queueForApproval({
      type: 'new_lead_school',
      brand: 'mikana',
      title: `New School Lead: ${schoolName}`,
      summary: `Score: ${data.qualification_score}/10 · Est. value: ${formatAED(data.estimated_annual_value_aed)}/year · ${data.current_contract_status}\n\nAngle: ${data.recommended_outreach_angle}\n\nHooks: ${data.personalisation_hooks?.join(' · ')}\n\nProjected ROI: ${data.projected_roi_multiple}x`,
      payload: {
        leadId: lead.id, schoolId: school.id, schoolName,
        estimatedValue: data.estimated_annual_value_aed,
        outreachAngle: data.recommended_outreach_angle,
        hooks: data.personalisation_hooks,
        roiMultiple: data.projected_roi_multiple
      },
      agent: 'scout',
      entityId: lead.id,
      entityType: 'school_lead'
    })
  }
}

export async function researchCorporate(
  companyName: string, industry: string, city = 'Dubai', additionalContext?: string
): Promise<void> {
  const response = await callClaude({
    systemPrompt: SCOUT_CORPORATE_PROMPT,
    userMessage: `Research this company for Mikana Food Service corporate catering:
Company: ${companyName}
Industry: ${industry}
City: ${city}
Additional context: ${additionalContext ?? 'none provided'}`,
    maxTokens: 1500,
    jsonMode: true
  })

  const data = JSON.parse(response)

  const [company] = await db.insert(schema.cateros_companies).values({
    name: companyName, industry, city,
    employee_count_estimate: data.employee_count_estimate,
    daily_meals_opportunity: data.daily_meals_opportunity,
    annual_value_estimate_aed: data.annual_value_estimate_aed,
    qualification_score: data.qualification_score,
    current_food_situation: data.current_food_situation,
    competitor_name: data.competitor_name,
    source: 'scout_agent',
    notes: data.qualification_reasoning
  }).returning()

  await logActivity('scout', `Researched company: ${companyName}`,
    'mikana', company.id, 'company', 'executed')

  if (data.qualification_score >= 6 && data.action !== 'skip') {
    const [lead] = await db.insert(schema.cateros_corporate_leads).values({
      company_id: company.id,
      stage: 'pending_approval',
      estimated_value_aed: data.annual_value_estimate_aed,
      meals_per_day_estimate: data.daily_meals_opportunity,
      next_action: data.recommended_outreach_angle
    }).returning()

    await queueForApproval({
      type: 'new_lead_corporate',
      brand: 'mikana',
      title: `New Corporate Lead: ${companyName}`,
      summary: `Score: ${data.qualification_score}/10 · Est. value: ${formatAED(data.annual_value_estimate_aed)}/year · ${data.current_food_situation}\n\nAngle: ${data.recommended_outreach_angle}\n\nProjected ROI: ${data.projected_roi_multiple}x`,
      payload: {
        leadId: lead.id, companyId: company.id, companyName,
        estimatedValue: data.annual_value_estimate_aed,
        outreachAngle: data.recommended_outreach_angle,
        hooks: data.personalisation_hooks,
        roiMultiple: data.projected_roi_multiple
      },
      agent: 'scout',
      entityId: lead.id,
      entityType: 'corporate_lead'
    })
  }
}

export async function runBoxedGoAudienceResearch(focus: string): Promise<void> {
  const response = await callClaude({
    systemPrompt: SCOUT_BOXEDGO_PROMPT,
    userMessage: `Conduct audience and market research for Boxed & Go UAE.
Focus: ${focus}
Current date context: ${new Date().toLocaleDateString('en-AE', { month: 'long', year: 'numeric' })}`,
    maxTokens: 1500,
    jsonMode: true
  })

  const data = JSON.parse(response)

  await db.insert(schema.cateros_intelligence).values({
    brand: 'boxedgo',
    report_type: 'audience_insight',
    title: `B&G Audience Research — ${focus}`,
    summary: data.recommended_immediate_actions?.join(' · ') ?? '',
    full_report: response,
    urgency: 'low',
    status: 'new'
  })

  await logActivity('scout', `B&G audience research: ${focus}`,
    'boxedgo', null, 'intelligence', 'executed')
}

export async function runMorningScoutCycle(): Promise<Record<string, number>> {
  let schoolsResearched = 0, companiesResearched = 0, renewalAlerts = 0

  // 1. Research unscored schools (max 3 per cycle to control API cost)
  const unscoredSchools = await db.query.cateros_schools.findMany({
    where: isNull(schema.cateros_schools.qualification_score),
    limit: 3
  })
  for (const s of unscoredSchools) {
    await researchSchool(s.name, s.emirate ?? 'Dubai', s.type ?? 'unknown')
    schoolsResearched++
  }

  // 2. Research unscored companies (max 3)
  const unscoredCompanies = await db.query.cateros_companies.findMany({
    where: isNull(schema.cateros_companies.qualification_score),
    limit: 3
  })
  for (const c of unscoredCompanies) {
    await researchCorporate(c.name, c.industry ?? 'free_zone', c.city ?? 'Dubai')
    companiesResearched++
  }

  // 3. Renewal alerts — contracts expiring in 120 days
  const renewalDate = new Date()
  renewalDate.setDate(renewalDate.getDate() + 120)

  const upcomingRenewals = await db.query.cateros_schools.findMany({
    where: and(
      eq(schema.cateros_schools.current_contract_status, 'active_mikana'),
      lte(schema.cateros_schools.contract_end_date, renewalDate.toISOString().slice(0, 10))
    )
  })

  for (const school of upcomingRenewals) {
    const daysLeft = school.contract_end_date
      ? Math.round((new Date(school.contract_end_date).getTime() - Date.now()) / 86400000)
      : 0

    const urgency = daysLeft < 30 ? '🚨' : daysLeft < 60 ? '⚠️' : '📅'

    await db.insert(schema.cateros_intelligence).values({
      brand: 'mikana',
      report_type: 'renewal_alert',
      title: `Contract Renewal: ${school.name} — ${daysLeft} days`,
      summary: `${urgency} ${school.name} contract expires in ${daysLeft} days.\nValue: ${formatAED(school.contract_value_aed ?? 0)}/year.\nContact: ${school.facilities_contact_name ?? 'unknown'}`,
      entity_id: school.id,
      urgency: daysLeft < 30 ? 'critical' : daysLeft < 60 ? 'urgent' : 'normal',
      action_recommended: 'initiate_renewal_sequence',
      status: 'new'
    })
    renewalAlerts++
  }

  // 4. B&G audience pulse (autonomous, no approval needed)
  await runBoxedGoAudienceResearch('weekly market pulse')

  return { schoolsResearched, companiesResearched, renewalAlerts, timestamp: Date.now() }
}
```

---
---

# PHASE 3 — PIPELINE AGENT

---

## PROMPT 3.1 — Pipeline Agent

```
Create src/agents/pipeline.ts

Imports:
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { queueForApproval, logActivity } from './orchestrator'
import * as schema from '@/lib/schema'
import { eq, and, lte, isNull } from 'drizzle-orm'

━━━ SYSTEM PROMPTS ━━━

export const PIPELINE_SCHOOLS_PROMPT = `
You are Pipeline — outreach agent for Mikana Food Service school contracts.

MIKANA USPs: HACCP-certified (KHDA/MOE compliant), nutritionist-designed rotating menus,
allergen management with parent-facing transparency, Arabic/English bilingual teams,
transparent cost-per-head (no hidden fees), proven at 1,000+ covers/day.

TONE: Senior operator talking to another senior professional. No hype. Direct respect.
Lead with compliance and safety — these reduce the headmaster's risk, not just preference.
Second with quality. Third with operations. Never lead with price.

NEW SCHOOL ACQUISITION SEQUENCE (5 steps):
Step 1 (Day 1): One specific hook about their school + who we are in one line + one fact + 15-min call CTA. Max 130 words.
Step 2 (Day 5): Reference step 1 + new value point specific to their curriculum/parent community. Max 100 words.
Step 3 (Day 12): Value-add — genuine insight on school food safety or menu planning (give without asking). Max 130 words.
Step 4 (Day 20): Direct and honest final ask. Easy for them to defer gracefully. Max 80 words.
Step 5 (Day 35): Soft seasonal check-in. No ask. Just presence. Max 60 words.

RENEWAL SEQUENCE (3 steps):
Step 1 (90 days before): Performance review framing + next year improvements + early-bird incentive.
Step 2 (60 days before): Formal renewal proposal. Clear numbers. Academic year framing.
Step 3 (30 days before): Final negotiation move. Urgent but respectful.

OUTPUT — valid JSON ONLY:
{
  "lead_type": "new_acquisition|renewal",
  "step": number,
  "channel": "email|linkedin|whatsapp",
  "subject": "string (email) or null",
  "body": "string",
  "body_arabic": "string or null",
  "follow_up_in_days": number,
  "next_action_suggestion": "string",
  "confidence_score": number (1-10),
  "roi_justification": "string"
}
`

export const PIPELINE_CORPORATE_PROMPT = `
You are Pipeline — outreach agent for Mikana Food Service corporate catering contracts.

5-step sequence. Day 1, 4, 9, 16, 30.
Each message: specific company hook → one clear value point → one CTA. Max 150 words.
Professional, direct, human. Not a template. Not a newsletter.

WHAT TO LEAD WITH PER INDUSTRY:
Free zones (tech/media): menu diversity (70+ nationalities in Dubai = varied palates)
Healthcare: HACCP compliance + allergen management + clinical nutrition options
Corporate HQ: cost transparency + no hidden fees + nutritionist menus
Construction: volume efficiency + cost-per-head discipline + Arabic-speaking team

20x ROI NOTE: Corporate contracts AED 200K-1M+/year.
LinkedIn outreach at AED 50/message with 250 working days: even 1 meeting from 200 messages
on a AED 500K contract = 1,000x ROI. Always justify why this contact is worth the outreach spend.

OUTPUT — same JSON structure as schools prompt.
`

export const PIPELINE_BOXEDGO_PROMPT = `
You are Pipeline — subscriber acquisition agent for Boxed & Go.

BRAND VOICE: Warm, real, lifestyle-forward. A friend who found the solution.
Never a brand. Never corporate. Real language people actually use.

CAC DISCIPLINE:
20x ROI standard: max AED 57.50 CAC on first-month revenue (AED 1,150 avg plan ÷ 20).
WhatsApp messages cost near zero. Keep outreach personal and efficient.
Every message must earn its right to exist.

CHANNELS: WhatsApp (primary), Instagram DM (secondary), Email (B&G website leads)
WhatsApp: max 100 words, conversational, 1-2 emojis max, ends with soft question.

STAGE-SPECIFIC MESSAGING:
awareness→interest: pure curiosity hook, zero selling, make them want to know more
interest→trial_offered: the 3-day sample pack offer (AED 99 for 3 meals, refunded on subscription)
trial_offered→trial_active: excited welcome + the Sizzle Moment tip (box open → pouch tear → protein on hot pan)
trial_active→subscribed: simple, direct ask. What's working? Here's how to subscribe.
churned→win_back: acknowledge the gap honestly. No guilt. Simple come back offer with small incentive.

LEBANON: Use: "Your teta's recipes, done the hard part for you."
Lebanon content = emotional anchoring in family food memory + modern convenience.

OUTPUT — valid JSON ONLY:
{
  "stage_transition": "string",
  "channel": "whatsapp|instagram_dm|email",
  "content": "string",
  "content_arabic": "string or null",
  "follow_up_in_days": number,
  "suggested_offer": "string or null",
  "estimated_cac_aed": number,
  "roi_multiple_at_avg_ltv": number
}
`

━━━ FUNCTIONS ━━━

export async function generateSchoolOutreach(schoolLeadId: string): Promise<void> {
  const lead = await db.query.cateros_school_leads.findFirst({
    where: eq(schema.cateros_school_leads.id, schoolLeadId)
  })
  if (!lead) return

  const school = await db.query.cateros_schools.findFirst({
    where: eq(schema.cateros_schools.id, lead.school_id!)
  })
  if (!school) return

  const contact = await db.query.cateros_contacts.findFirst({
    where: eq(schema.cateros_contacts.school_id, school.id)
  })

  const totalSteps = lead.lead_type === 'renewal' ? 3 : 5
  const sequences = []

  for (let step = 1; step <= totalSteps; step++) {
    const response = await callClaude({
      systemPrompt: PIPELINE_SCHOOLS_PROMPT,
      userMessage: `Generate outreach for:
School: ${school.name}
Curriculum: ${school.type}
Emirate: ${school.emirate}
Student count: ${school.student_count ?? 'unknown'}
Current provider: ${school.current_contract_status} ${school.competitor_name ? '(' + school.competitor_name + ')' : ''}
Lead type: ${lead.lead_type}
Step: ${step} of ${totalSteps}
Contact title: ${contact?.title ?? 'Head of Operations'}
Pain points: ${school.notes ?? 'not yet identified'}
Personalisation hooks from Scout: ${JSON.stringify(lead.notes ?? '')}`,
      maxTokens: 1000,
      jsonMode: true
    })

    const data = JSON.parse(response)
    const dayDelay = step === 1 ? 0 : [0, 5, 12, 20, 35][step - 1]
    const scheduledDate = new Date()
    scheduledDate.setDate(scheduledDate.getDate() + dayDelay)

    const [outreach] = await db.insert(schema.cateros_outreach).values({
      lead_type: 'school',
      lead_id: lead.id,
      contact_id: contact?.id ?? undefined,
      channel: data.channel,
      subject: data.subject,
      body: data.body,
      sequence_step: step,
      status: step === 1 ? 'pending_approval' : 'draft'
    }).returning()

    sequences.push({ outreach, data, scheduledDate })
  }

  // Queue step 1 for approval
  const first = sequences[0]
  if (first) {
    await queueForApproval({
      type: 'outreach_email',
      brand: 'mikana',
      title: `School Outreach Step 1: ${school.name}`,
      summary: `To: ${contact?.title ?? 'Head of Operations'} at ${school.name}\nSubject: ${first.data.subject}\n\n${first.data.body.slice(0, 300)}...\n\nROI: ${first.data.roi_justification}`,
      payload: {
        outreachId: first.outreach.id,
        subject: first.data.subject,
        body: first.data.body,
        contactEmail: contact?.email ?? '',
        schoolName: school.name,
        leadId: lead.id
      },
      agent: 'pipeline',
      entityId: first.outreach.id,
      entityType: 'outreach'
    })
  }

  await logActivity('pipeline', `Generated ${totalSteps}-step sequence for ${school.name}`,
    'mikana', lead.id, 'school_lead', 'executed')
}

export async function generateCorporateOutreach(corporateLeadId: string): Promise<void> {
  const lead = await db.query.cateros_corporate_leads.findFirst({
    where: eq(schema.cateros_corporate_leads.id, corporateLeadId)
  })
  if (!lead) return

  const company = await db.query.cateros_companies.findFirst({
    where: eq(schema.cateros_companies.id, lead.company_id!)
  })
  if (!company) return

  const contact = await db.query.cateros_contacts.findFirst({
    where: eq(schema.cateros_contacts.company_id, company.id)
  })

  for (let step = 1; step <= 5; step++) {
    const response = await callClaude({
      systemPrompt: PIPELINE_CORPORATE_PROMPT,
      userMessage: `Generate outreach for:
Company: ${company.name}
Industry: ${company.industry}
City: ${company.city}
Employees: ${company.employee_count_estimate ?? 'unknown'}
Daily meals opportunity: ${company.daily_meals_opportunity ?? 'unknown'}
Current food situation: ${company.current_food_situation}
Annual value estimate: ${company.annual_value_estimate_aed}
Step: ${step} of 5
Contact title: ${contact?.title ?? 'Head of Operations'}`,
      maxTokens: 1000,
      jsonMode: true
    })

    const data = JSON.parse(response)

    const [outreach] = await db.insert(schema.cateros_outreach).values({
      lead_type: 'corporate',
      lead_id: lead.id,
      contact_id: contact?.id ?? undefined,
      channel: data.channel,
      subject: data.subject,
      body: data.body,
      sequence_step: step,
      status: step === 1 ? 'pending_approval' : 'draft'
    }).returning()

    if (step === 1) {
      await queueForApproval({
        type: 'outreach_email',
        brand: 'mikana',
        title: `Corporate Outreach Step 1: ${company.name}`,
        summary: `To: ${contact?.title ?? 'Operations'} at ${company.name}\nEst. value: ${company.annual_value_estimate_aed ? company.annual_value_estimate_aed.toLocaleString() + ' AED/year' : 'TBD'}\n\n${data.body.slice(0, 300)}...`,
        payload: {
          outreachId: outreach.id, subject: data.subject, body: data.body,
          contactEmail: contact?.email ?? '', companyName: company.name, leadId: lead.id
        },
        agent: 'pipeline',
        entityId: outreach.id,
        entityType: 'outreach'
      })
    }
  }
}

export async function generateBoxedGoMessage(
  subscriberId: string, targetStage: string
): Promise<void> {
  const subscriber = await db.query.cateros_bg_subscribers.findFirst({
    where: eq(schema.cateros_bg_subscribers.id, subscriberId)
  })
  if (!subscriber) return

  const plan = subscriber.plan_id
    ? await db.query.cateros_bg_plans.findFirst({
        where: eq(schema.cateros_bg_plans.id, subscriber.plan_id)
      })
    : null

  const response = await callClaude({
    systemPrompt: PIPELINE_BOXEDGO_PROMPT,
    userMessage: `Generate message for:
Subscriber stage: ${subscriber.stage} → targeting: ${targetStage}
Segment: ${subscriber.segment ?? 'unknown'}
City: ${subscriber.city}
Country: ${subscriber.country}
Current plan: ${plan?.name ?? 'none yet'}
Source: ${subscriber.source ?? 'unknown'}
Days since last contact: unknown`,
    maxTokens: 800,
    jsonMode: true
  })

  const data = JSON.parse(response)

  const [outreach] = await db.insert(schema.cateros_bg_outreach).values({
    subscriber_id: subscriberId,
    channel: data.channel,
    message_type: data.stage_transition,
    content: data.content,
    content_arabic: data.content_arabic,
    status: 'pending_approval'
  }).returning()

  await queueForApproval({
    type: 'outreach_email',
    brand: 'boxedgo',
    title: `B&G Message: ${data.stage_transition}`,
    summary: `To: ${subscriber.first_name ?? 'Subscriber'} (${subscriber.city}) via ${data.channel}\n\n${data.content.slice(0, 250)}...\n\nEst. CAC: AED ${data.estimated_cac_aed} · ROI multiple at avg LTV: ${data.roi_multiple_at_avg_ltv}x`,
    payload: {
      outreachId: outreach.id, subscriberId,
      content: data.content, channel: data.channel,
      whatsapp: subscriber.whatsapp, email: subscriber.email,
      estimatedCac: data.estimated_cac_aed
    },
    agent: 'pipeline',
    entityId: outreach.id,
    entityType: 'bg_outreach'
  })
}

export async function runMorningPipelineCycle(): Promise<Record<string, number>> {
  let schoolSequences = 0, corporateSequences = 0, bgMessages = 0

  // 1. Newly approved school leads — generate sequences
  const approvedSchoolLeads = await db.query.cateros_school_leads.findMany({
    where: eq(schema.cateros_school_leads.stage, 'identified'),
  })
  for (const lead of approvedSchoolLeads.slice(0, 3)) {
    const hasOutreach = await db.query.cateros_outreach.findFirst({
      where: and(eq(schema.cateros_outreach.lead_id, lead.id), eq(schema.cateros_outreach.lead_type, 'school'))
    })
    if (!hasOutreach) {
      await generateSchoolOutreach(lead.id)
      schoolSequences++
    }
  }

  // 2. Newly approved corporate leads
  const approvedCorporateLeads = await db.query.cateros_corporate_leads.findMany({
    where: eq(schema.cateros_corporate_leads.stage, 'identified')
  })
  for (const lead of approvedCorporateLeads.slice(0, 3)) {
    const hasOutreach = await db.query.cateros_outreach.findFirst({
      where: and(eq(schema.cateros_outreach.lead_id, lead.id), eq(schema.cateros_outreach.lead_type, 'corporate'))
    })
    if (!hasOutreach) {
      await generateCorporateOutreach(lead.id)
      corporateSequences++
    }
  }

  // 3. B&G subscribers needing next stage push
  const staleSubscribers = await db.query.cateros_bg_subscribers.findMany({
    where: and(
      eq(schema.cateros_bg_subscribers.stage, 'interest'),
    ),
    limit: 5
  })
  for (const sub of staleSubscribers) {
    await generateBoxedGoMessage(sub.id, 'trial_offered')
    bgMessages++
  }

  return { schoolSequences, corporateSequences, bgMessages }
}

export { generateSchoolOutreach, generateCorporateOutreach,
  generateBoxedGoMessage, runMorningPipelineCycle }
```

---
---

# PHASE 4 — INTEGRATIONS + BROADCAST

---

## PROMPT 4.1 — Platform Integrations

```
Create all four integration files:

━━━ src/integrations/meta.ts ━━━

const BASE = 'https://graph.facebook.com/v18.0'

async function apiFetch(url: string, options: RequestInit = {}, retries = 3): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options)
      if (res.ok) return res
      if (res.status === 429) {
        await new Promise(r => setTimeout(r, Math.pow(2, i) * 2000))
        continue
      }
      const text = await res.text()
      throw new Error(`Meta API ${res.status}: ${text}`)
    } catch (e) {
      if (i === retries - 1) throw e
      await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000))
    }
  }
  throw new Error('Max retries exceeded')
}

export async function createMediaContainer(imageUrl: string, caption: string): Promise<string> {
  const res = await apiFetch(`${BASE}/${process.env.META_INSTAGRAM_ACCOUNT_ID}/media`, {
    method: 'POST',
    body: new URLSearchParams({ image_url: imageUrl, caption, access_token: process.env.META_ACCESS_TOKEN! })
  })
  return (await res.json()).id
}

export async function publishMediaContainer(containerId: string): Promise<string> {
  await new Promise(r => setTimeout(r, 8000)) // Let container process
  const res = await apiFetch(`${BASE}/${process.env.META_INSTAGRAM_ACCOUNT_ID}/media_publish`, {
    method: 'POST',
    body: new URLSearchParams({ creation_id: containerId, access_token: process.env.META_ACCESS_TOKEN! })
  })
  return (await res.json()).id
}

export async function getMediaInsights(mediaId: string): Promise<Record<string, number>> {
  const fields = 'like_count,comments_count,reach,impressions,saved'
  const res = await apiFetch(`${BASE}/${mediaId}?fields=${fields}&access_token=${process.env.META_ACCESS_TOKEN}`)
  return res.json()
}

export async function getMediaComments(mediaId: string): Promise<Array<Record<string, string>>> {
  const res = await apiFetch(`${BASE}/${mediaId}/comments?access_token=${process.env.META_ACCESS_TOKEN}`)
  const data = await res.json()
  return data.data ?? []
}

export async function replyToComment(commentId: string, message: string): Promise<void> {
  await apiFetch(`${BASE}/${commentId}/replies`, {
    method: 'POST',
    body: new URLSearchParams({ message, access_token: process.env.META_ACCESS_TOKEN! })
  })
}

━━━ src/integrations/linkedin.ts ━━━

const LI_BASE = 'https://api.linkedin.com/v2'

async function liRequest(path: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${LI_BASE}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${process.env.LINKEDIN_ACCESS_TOKEN}`,
      'Content-Type': 'application/json',
      'X-Restli-Protocol-Version': '2.0.0',
      ...options.headers
    }
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`LinkedIn API ${res.status}: ${text}`)
  }
  return res
}

export async function createLinkedInPost(text: string): Promise<string> {
  const orgId = process.env.LINKEDIN_ORGANIZATION_ID
  const res = await liRequest('/ugcPosts', {
    method: 'POST',
    body: JSON.stringify({
      author: `urn:li:organization:${orgId}`,
      lifecycleState: 'PUBLISHED',
      specificContent: {
        'com.linkedin.ugc.ShareContent': {
          shareCommentary: { text },
          shareMediaCategory: 'NONE'
        }
      },
      visibility: { 'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC' }
    })
  })
  const data = await res.json()
  return data.id
}

export async function getLinkedInPostStats(postUrn: string): Promise<Record<string, unknown>> {
  const encoded = encodeURIComponent(postUrn)
  const res = await liRequest(`/socialActions/${encoded}`)
  return res.json()
}

━━━ src/integrations/whatsapp.ts ━━━

export async function sendWhatsApp(to: string, message: string): Promise<{ messageId: string }> {
  const phoneId = process.env.WHATSAPP_PHONE_NUMBER_ID
  const token = process.env.WHATSAPP_ACCESS_TOKEN
  const toNumber = to.replace('+', '').replace('whatsapp:', '')

  const res = await fetch(`https://graph.facebook.com/v18.0/${phoneId}/messages`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      messaging_product: 'whatsapp',
      to: toNumber,
      type: 'text',
      text: { body: message }
    })
  })

  if (!res.ok) {
    const err = await res.text()
    console.error('[WHATSAPP] Send failed:', err)
    // Do not throw — notification failures must not block the pipeline
    return { messageId: 'failed' }
  }

  const data = await res.json()
  return { messageId: data.messages?.[0]?.id ?? 'unknown' }
}

━━━ src/integrations/resend.ts ━━━

import { Resend } from 'resend'
const resend = new Resend(process.env.RESEND_API_KEY)

export async function sendEmail(params: {
  to: string; subject: string; body: string; html?: string
}): Promise<void> {
  try {
    await resend.emails.send({
      from: 'CaterOS <noreply@cateros.app>',
      to: params.to,
      subject: params.subject,
      html: params.html ?? `<div style="font-family: Arial; padding: 20px; white-space: pre-wrap">${params.body}</div>`
    })
  } catch (e) {
    console.error('[RESEND] Email failed:', e)
  }
}

export async function sendOutreachEmail(params: {
  to: string; subject: string; body: string
}): Promise<void> {
  await resend.emails.send({
    from: 'Mikana Food Service <hello@mikanafoodservice.com>',
    to: params.to,
    subject: params.subject,
    html: `<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; line-height: 1.6; color: #1a1a1a">
      ${params.body.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('')}
      <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0">
      <p style="color: #6b7280; font-size: 13px">
        Mikana Food Service · Dubai, UAE<br>
        <a href="https://mikanafoodservice.com" style="color: #E8490F">mikanafoodservice.com</a>
      </p>
    </div>`
  })
}

export async function sendApprovalEmail(request: {
  id: string; title: string | null; summary: string | null;
  type: string; brand: string | null; agent: string | null;
  expires_at: Date | null
}): Promise<void> {
  const shortId = request.id.substring(0, 8).toUpperCase()
  const appUrl = process.env.NEXT_PUBLIC_APP_URL
  await sendEmail({
    to: process.env.OWNER_EMAIL!,
    subject: `[CaterOS] Action required: ${request.title ?? 'New approval'}`,
    html: `<div style="font-family: Arial; max-width: 600px; margin: 0 auto; padding: 30px">
      <h2 style="color: #0f172a">CaterOS — Action Required</h2>
      <h3 style="color: #E8490F">${request.title}</h3>
      <p style="background: #f8fafc; padding: 16px; border-radius: 8px; white-space: pre-wrap">${request.summary}</p>
      <p>
        <a href="${appUrl}/approvals" style="background: #0f172a; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; display: inline-block">
          Open in CaterOS
        </a>
      </p>
      <p style="color: #6b7280; font-size: 13px">
        ID: ${shortId} · Agent: ${request.agent} · Brand: ${request.brand}<br>
        You can also reply APPROVE / REJECT on WhatsApp.
      </p>
    </div>`
  })
}

━━━ src/integrations/scraping.ts ━━━

const CACHE = new Map<string, { data: unknown; timestamp: number }>()
const CACHE_TTL = 30 * 24 * 3600 * 1000 // 30 days

async function cachedFetch<T>(key: string, fn: () => Promise<T>): Promise<T | null> {
  const cached = CACHE.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) return cached.data as T
  try {
    const fresh = await fn()
    CACHE.set(key, { data: fresh, timestamp: Date.now() })
    return fresh
  } catch (e) {
    console.error('[SCRAPING] Fetch failed:', key, e)
    return null
  }
}

export async function scrapeGoogleReviews(placeId: string, maxResults = 20): Promise<unknown> {
  if (!process.env.SERPAPI_KEY) return null
  return cachedFetch(`reviews_${placeId}`, async () => {
    const params = new URLSearchParams({
      engine: 'google_maps_reviews',
      place_id: placeId,
      api_key: process.env.SERPAPI_KEY!,
      num: String(maxResults),
      sort_by: 'newestFirst'
    })
    const res = await fetch(`https://serpapi.com/search.json?${params}`)
    if (!res.ok) throw new Error(`SerpAPI ${res.status}`)
    return res.json()
  })
}

export async function scrapeWebsite(url: string): Promise<unknown> {
  return cachedFetch(`website_${url}`, async () => {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; CaterOS/1.0; market research)' },
      signal: AbortSignal.timeout(12000)
    })
    if (!res.ok) return { blocked: true, url, status: res.status }
    const html = await res.text()
    const bodyText = html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().substring(0, 5000)
    const title = html.match(/<title[^>]*>([^<]+)<\/title>/i)?.[1]?.trim() ?? ''
    return { url, title, bodyText, scraped_at: new Date().toISOString() }
  })
}

export async function scrapeInstagramProfile(handle: string): Promise<unknown> {
  if (!process.env.APIFY_API_TOKEN) return null
  return cachedFetch(`instagram_${handle}`, async () => {
    const res = await fetch(
      'https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items',
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.APIFY_API_TOKEN}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ usernames: [handle], resultsLimit: 12 }),
        signal: AbortSignal.timeout(90000)
      }
    )
    if (!res.ok) throw new Error(`Apify ${res.status}`)
    return res.json()
  })
}
```

---

## PROMPT 4.2 — Broadcast Agent

```
Create src/agents/broadcast.ts

Imports:
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { queueForApproval, logActivity } from './orchestrator'
import { publishMediaContainer, createMediaContainer, getMediaInsights,
         getMediaComments, replyToComment } from '@/integrations/meta'
import { createLinkedInPost } from '@/integrations/linkedin'
import { sendWhatsApp } from '@/integrations/whatsapp'
import * as schema from '@/lib/schema'
import { eq, lte, gte, and, desc } from 'drizzle-orm'

━━━ SYSTEM PROMPTS ━━━

export const BROADCAST_MIKANA_PROMPT = `
You are Broadcast managing LinkedIn content for Mikana Food Service.

BRAND VOICE: Authoritative, expert, grounded. 8 years feeding thousands of schoolchildren
under HACCP standards earns respect, not hype. Write like a confident senior operator
sharing genuine hard-earned insight. Never salesy. Never obvious.

CONTENT PILLARS (rotate across posts — tag which pillar):
1. thought_leadership — food safety insights, school nutrition research, UAE corporate wellness trends
2. operational_excellence — our kitchens, our HACCP process, how we manage 1,000+ covers
3. industry_insight — UAE food service data, regulatory changes, market observations
4. social_proof — client outcomes, milestones, menu launches (anonymise clients initially)
5. school_season — back to school, Ramadan, term transitions, National Day

LINKEDIN POST STRUCTURE:
Line 1-2: Hook that earns the click BEFORE "see more" — specific, surprising, or counter-intuitive
Body: 3-5 tight paragraphs. No filler words. No "I'm excited to share..."
Insight line: one truth that stays with the reader
Soft CTA: "What's your experience with this?" not "Contact us"
Hashtags: 3-5 max. Always #FoodService #UAE plus one specific.
Length: 200-300 words.

ROI: Every LinkedIn post is near-zero-cost and can generate AED 500K+ inbound inquiries.
Write every post as if a GEMS procurement officer might read it and think "I should speak to them."

OUTPUT — valid JSON ONLY:
{
  "brand": "mikana",
  "platform": "linkedin",
  "content_type": "pillar_name",
  "caption": "full post text",
  "hashtags": ["tag1", "tag2"],
  "image_prompt": "detailed visual description for image generation",
  "best_publish_day": "Tuesday|Wednesday|Thursday",
  "best_publish_time": "7:30|12:00|18:00",
  "engagement_hypothesis": "why this post will generate response",
  "target_reader": "who we're really writing this for"
}
`

export const BROADCAST_BOXEDGO_PROMPT = `
You are Broadcast managing Instagram content for Boxed & Go.

BRAND VOICE: Warm, confident, slightly playful. A friend who solved the meal problem.
Not corporate. Not a nutrition lecture. Real food, consistently delivered. Life made easier.

BILINGUAL RULE: Every post has English + Arabic. Arabic must be Gulf-colloquial (not formal MSA).
Think how a Dubai family actually speaks, not a textbook.

THE SIZZLE MOMENT (mandatory in all video/reel briefs):
Box opens → pouch tears → PROTEIN HITS HOT PAN (loud satisfying sizzle) → plate assembled → first bite.
This is Boxed & Go's signature visual. Every video content brief must include it.

CONTENT PILLARS:
1. product_showcase — specific dish or protein+side+sauce combo, finish time, sizzle moment
2. behind_scenes — kitchen, fresh sourcing, vacuum sealing, packaging care
3. customer_reality — relatable Dubai moments: busy Monday, delivery app price shock, tired after work
4. seasonal_cultural — Ramadan suhoor ideas, Eid gatherings, National Day, summer, back to school
5. education — how Build Your Plate works, macro counts, allergen transparency

CAPTION STRUCTURE:
Line 1-2: Visual hook or relatable problem
Short punchy paragraphs (2-3 lines max each)
2 emojis max, purposeful placement
CTA: save this / tag someone / link in bio / DM us
Hashtags: 10-14 (mix: broad + UAE-niche + food-niche)

OUTPUT — valid JSON ONLY:
{
  "brand": "boxedgo",
  "platform": "instagram|instagram_story|instagram_reel",
  "content_type": "pillar_name",
  "language": "bilingual",
  "caption": "English caption",
  "caption_arabic": "Arabic — Gulf colloquial",
  "hashtags": ["tag"],
  "image_prompt": "detailed visual description",
  "story_elements": "any stickers/polls if story — null if not",
  "best_publish_day": "string",
  "best_publish_time": "string UAE",
  "target_segment": "household_family|individual_professional|both",
  "product_featured": "heat_and_eat|build_your_plate|social_table|nutritionist|general"
}
`

export const BROADCAST_COMMENT_PROMPT = `
You are managing comment replies for Mikana (LinkedIn) and Boxed & Go (Instagram).

MIKANA: Professional, warm, specific. Answer questions directly. Never defensive. Max 3 sentences.
BOXED & GO: Match warm casual energy. Quick and human. Emoji if appropriate. Max 2-3 sentences.
BOTH: Never ignore a direct question. If complaint in comment: acknowledge + offer DM.

OUTPUT — valid JSON ONLY:
{
  "sentiment": "positive|neutral|negative|question|spam",
  "requires_reply": boolean,
  "reply": "string or null",
  "reply_arabic": "string or null",
  "escalate_to_human": boolean,
  "escalation_reason": "string or null"
}
`

━━━ FUNCTIONS ━━━

export async function generateAndQueuePost(params: {
  brand: string; platform: string; contentType: string;
  topic?: string; productFocus?: string
}): Promise<void> {
  const isBoxedGo = params.brand === 'boxedgo'
  const prompt = isBoxedGo ? BROADCAST_BOXEDGO_PROMPT : BROADCAST_MIKANA_PROMPT

  let context = `Generate a ${params.platform} ${params.contentType} post for ${params.brand}.`
  if (params.topic) context += `\nTopic/angle: ${params.topic}`
  if (params.productFocus) context += `\nProduct focus: ${params.productFocus}`
  context += `\nCurrent date context: ${new Date().toLocaleDateString('en-AE', { month: 'long', year: 'numeric' })}`

  // If build_your_plate, fetch a random active meal combo for authenticity
  if (params.productFocus === 'build_your_plate') {
    const meals = await db.query.cateros_bg_meals.findMany({
      where: eq(schema.cateros_bg_meals.is_active, true),
      limit: 50
    })
    const proteins = meals.filter(m => m.category === 'build_protein')
    const sides = meals.filter(m => m.category === 'build_side')
    const sauces = meals.filter(m => m.category === 'build_sauce')
    if (proteins.length && sides.length && sauces.length) {
      const p = proteins[Math.floor(Math.random() * proteins.length)]
      const s = sides[Math.floor(Math.random() * sides.length)]
      const sa = sauces[Math.floor(Math.random() * sauces.length)]
      context += `\nFeatured combo: ${p.name} + ${s.name} + ${sa.name}\nFinish time: ${(p.finish_time_minutes ?? 0) + (s.finish_time_minutes ?? 0)}min\nCalories: ~${(p.calories ?? 0) + (s.calories ?? 0)} kcal\nProtein: ~${(p.protein_grams ?? 0) + (s.protein_grams ?? 0)}g`
    }
  }

  const response = await callClaude({
    systemPrompt: prompt,
    userMessage: context,
    maxTokens: 1500,
    jsonMode: true
  })

  const data = JSON.parse(response)

  const scheduledAt = new Date()
  // Schedule for next relevant time slot
  const hour = scheduledAt.getHours()
  if (hour < 7) scheduledAt.setHours(7, 30, 0)
  else if (hour < 12) scheduledAt.setHours(12, 0, 0)
  else scheduledAt.setHours(18, 0, 0)

  const [post] = await db.insert(schema.cateros_social_posts).values({
    brand: params.brand,
    platform: data.platform ?? params.platform,
    content_type: data.content_type,
    language: data.language ?? 'en',
    caption: data.caption,
    caption_arabic: data.caption_arabic ?? null,
    hashtags: data.hashtags ?? [],
    image_prompt: data.image_prompt,
    status: 'pending_approval',
    scheduled_at: scheduledAt
  }).returning()

  const preview = data.caption?.slice(0, 200) ?? ''

  await queueForApproval({
    type: 'social_post',
    brand: params.brand,
    title: `${params.brand === 'mikana' ? 'LinkedIn' : 'Instagram'} Post: ${data.content_type}`,
    summary: `Platform: ${data.platform}\nBest time: ${data.best_publish_day} ${data.best_publish_time}\n\n${preview}...\n\nHashtags: ${data.hashtags?.slice(0, 5).join(' ')}`,
    payload: { postId: post.id, caption: data.caption, platform: data.platform, brand: params.brand },
    agent: 'broadcast',
    entityId: post.id,
    entityType: 'social_post'
  })
}

export async function runPublishQueue(): Promise<{ published: number; failed: number }> {
  const now = new Date()
  let published = 0, failed = 0

  const duePosts = await db.query.cateros_social_posts.findMany({
    where: and(
      eq(schema.cateros_social_posts.status, 'approved'),
      lte(schema.cateros_social_posts.scheduled_at, now)
    )
  })

  for (const post of duePosts) {
    try {
      await db.update(schema.cateros_social_posts)
        .set({ status: 'publishing' })
        .where(eq(schema.cateros_social_posts.id, post.id))

      if (post.platform?.includes('instagram')) {
        const caption = [post.caption, (post.hashtags as string[] ?? []).map(h => `#${h}`).join(' ')]
          .filter(Boolean).join('\n\n')
        const imageUrl = post.image_url ?? 'https://via.placeholder.com/1080x1080'
        const containerId = await createMediaContainer(imageUrl, caption)
        const mediaId = await publishMediaContainer(containerId)

        await db.update(schema.cateros_social_posts).set({
          status: 'published', platform_post_id: mediaId,
          platform_post_url: `https://instagram.com/p/${mediaId}`,
          published_at: new Date(), media_id: containerId
        }).where(eq(schema.cateros_social_posts.id, post.id))

      } else if (post.platform === 'linkedin') {
        const postId = await createLinkedInPost(post.caption ?? '')
        await db.update(schema.cateros_social_posts).set({
          status: 'published', platform_post_id: postId,
          published_at: new Date()
        }).where(eq(schema.cateros_social_posts.id, post.id))
      }

      published++
      await logActivity('broadcast', `Published ${post.platform} post`, post.brand,
        post.id, 'social_post', 'executed')

    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error)
      await db.update(schema.cateros_social_posts).set({
        status: 'failed', failure_reason: msg
      }).where(eq(schema.cateros_social_posts.id, post.id))
      failed++
      await sendWhatsApp(process.env.OWNER_WHATSAPP!,
        `⚠️ CaterOS: Post failed to publish.\nBrand: ${post.brand} · Platform: ${post.platform}\nError: ${msg.slice(0, 200)}\nCheck CaterOS → Broadcast.`)
    }
  }

  return { published, failed }
}

export async function runEngagementSync(): Promise<void> {
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  const publishedPosts = await db.query.cateros_social_posts.findMany({
    where: and(
      eq(schema.cateros_social_posts.status, 'published'),
      gte(schema.cateros_social_posts.published_at, thirtyDaysAgo)
    )
  })

  for (const post of publishedPosts) {
    if (!post.platform_post_id) continue
    try {
      if (post.platform?.includes('instagram')) {
        const insights = await getMediaInsights(post.platform_post_id)
        await db.update(schema.cateros_social_posts).set({
          likes_count: (insights.like_count as number) ?? post.likes_count,
          comments_count: (insights.comments_count as number) ?? post.comments_count,
          reach: (insights.reach as number) ?? post.reach,
          impressions: (insights.impressions as number) ?? post.impressions,
          saves_count: (insights.saved as number) ?? post.saves_count,
          last_engagement_sync: new Date()
        }).where(eq(schema.cateros_social_posts.id, post.id))

        // Process new comments
        const comments = await getMediaComments(post.platform_post_id)
        for (const comment of comments) {
          const exists = await db.query.cateros_social_comments.findFirst({
            where: eq(schema.cateros_social_comments.platform_comment_id, comment.id as string)
          })
          if (!exists) await processComment(post.id, comment, post.brand)
        }
      }
    } catch (e) {
      console.error(`[BROADCAST] Engagement sync failed for post ${post.id}:`, e)
    }
  }
}

export async function processComment(
  postId: string,
  comment: Record<string, unknown>,
  brand: string
): Promise<void> {
  const response = await callClaude({
    systemPrompt: BROADCAST_COMMENT_PROMPT,
    userMessage: `Brand: ${brand}
Comment from @${comment.username}: "${comment.text}"
Classify and draft reply if needed.`,
    maxTokens: 500,
    jsonMode: true
  })

  const data = JSON.parse(response)

  await db.insert(schema.cateros_social_comments).values({
    post_id: postId,
    platform_comment_id: comment.id as string,
    author_username: comment.username as string,
    content: comment.text as string,
    sentiment: data.sentiment,
    requires_reply: data.requires_reply,
    reply_content: data.reply
  })

  if (data.escalate_to_human) {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `💬 *Comment needs your attention*\n@${comment.username}: "${comment.text}"\nReason: ${data.escalation_reason}`)
  }
}

export async function runWeeklyContentBatch(): Promise<void> {
  // Mikana: 3 LinkedIn posts (Tue/Wed/Thu)
  const mikaanaPillars = ['thought_leadership', 'operational_excellence', 'industry_insight']
  for (const pillar of mikaanaPillars) {
    await generateAndQueuePost({ brand: 'mikana', platform: 'linkedin', contentType: pillar })
  }

  // Boxed & Go: 5 Instagram feed + 2 Stories
  const bgPillars = ['product_showcase', 'customer_reality', 'behind_scenes', 'education', 'seasonal_cultural']
  for (const pillar of bgPillars) {
    await generateAndQueuePost({ brand: 'boxedgo', platform: 'instagram', contentType: pillar })
  }
  await generateAndQueuePost({ brand: 'boxedgo', platform: 'instagram_story', contentType: 'product_showcase' })
  await generateAndQueuePost({ brand: 'boxedgo', platform: 'instagram_story', contentType: 'customer_reality' })
}

export { generateAndQueuePost, runPublishQueue, runEngagementSync, runWeeklyContentBatch }
```
# PHASE 5 — SEO ENGINE

---

## PROMPT 5.1 — SEO Engine Agent

```
Create src/agents/seo-engine.ts

Imports:
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { queueForApproval, logActivity } from './orchestrator'
import * as schema from '@/lib/schema'
import { eq } from 'drizzle-orm'

━━━ SYSTEM PROMPT ━━━

export const SEO_ENGINE_PROMPT = `
You are the SEO Engine for Mikana Food Service and Boxed & Go.

ROI REALITY: SEO content that ranks generates inbound leads at near-zero CAC indefinitely.
A single article ranking #1 for "corporate catering Dubai" (~500 searches/month) generates
5-10 inquiries/month. At AED 500K average contract: that is AED 2.5M-5M/month in pipeline
at effectively infinite ROI once the content costs are amortised.
SEO is the highest long-term ROI channel in CaterOS. Prioritise quality over quantity.

MIKANA TARGET KEYWORDS:
Primary: "school catering UAE", "corporate catering Dubai", "school canteen management Dubai"
Secondary: "HACCP catering UAE", "office catering Abu Dhabi", "halal corporate catering Dubai",
"school food contractor UAE", "corporate meal service Dubai"

BOXED & GO TARGET KEYWORDS:
Primary: "meal subscription Dubai", "meal delivery subscription UAE"
Secondary: "healthy meal plan Dubai", "meal box delivery Dubai",
"build your plate meal kit UAE", "ready meal subscription UAE"

ARTICLE REQUIREMENTS:
- Primary keyword in: H1 title, first 80 words, one H2, meta description
- Length: 950-1,400 words
- UAE-specific: Dubai, Abu Dhabi, KHDA, HACCP where genuinely relevant
- FAQ section at end (minimum 4 questions — improves featured snippet ranking)
- JSON-LD schema: LocalBusiness + FAQPage, always
- Natural keyword density: 1-2% primary, 0.5-1% secondary
- Internal link suggestions: 2-3 hypothetical links to other Mikana/B&G content

OUTPUT — valid JSON ONLY:
{
  "brand": "mikana|boxedgo",
  "content_type": "article|landing_page|guide",
  "title": "string (60 chars max)",
  "slug": "kebab-case-slug",
  "primary_keyword": "string",
  "secondary_keywords": ["string"],
  "target_audience": "string",
  "meta_title": "string (60 chars max)",
  "meta_description": "string (155 chars max)",
  "content_markdown": "full article in markdown",
  "schema_markup": "valid JSON-LD as string",
  "word_count": number,
  "seo_score": number (1-100),
  "seo_score_reasoning": "string"
}
`

━━━ FUNCTIONS ━━━

export async function generateSEOArticle(
  brand: string, keyword: string, audience: string
): Promise<void> {
  const response = await callClaude({
    systemPrompt: SEO_ENGINE_PROMPT,
    userMessage: `Generate a high-ranking SEO article for:
Brand: ${brand}
Target keyword: ${keyword}
Primary audience: ${audience}
Current date context: ${new Date().toLocaleDateString('en-AE', { month: 'long', year: 'numeric' })}

Write the complete article ready to publish. Include all fields.`,
    maxTokens: 3500,
    jsonMode: true
  })

  const data = JSON.parse(response)

  const [content] = await db.insert(schema.cateros_seo_content).values({
    brand,
    content_type: data.content_type,
    title: data.title,
    slug: data.slug,
    target_audience: data.target_audience,
    content_markdown: data.content_markdown,
    meta_title: data.meta_title,
    meta_description: data.meta_description,
    schema_markup: data.schema_markup,
    word_count: data.word_count,
    seo_score: data.seo_score,
    status: 'pending_approval'
  }).returning()

  await queueForApproval({
    type: 'seo_article',
    brand,
    title: `SEO Article: ${data.title}`,
    summary: `Keyword: ${data.primary_keyword}\nSEO Score: ${data.seo_score}/100\nWords: ${data.word_count}\nSlug: /${data.slug}\n\nMeta: ${data.meta_description}`,
    payload: { contentId: content.id, title: data.title, slug: data.slug, keyword },
    agent: 'seo_engine',
    entityId: content.id,
    entityType: 'seo_content'
  })

  await logActivity('seo_engine', `Generated article: ${data.title}`, brand,
    content.id, 'seo_content', 'queued_for_approval')
}

export async function generateKeywordCluster(brand: string, topic: string): Promise<void> {
  const response = await callClaude({
    systemPrompt: SEO_ENGINE_PROMPT,
    userMessage: `Generate a keyword cluster for: Brand: ${brand}, Topic: ${topic}

Return JSON with a keywords array: [{ "keyword": string, "search_volume_estimate": number,
"difficulty_estimate": number, "intent": "informational|commercial|transactional",
"cluster_topic": string, "priority": "high|medium|low" }]
Generate 10-15 keywords.`,
    maxTokens: 1000,
    jsonMode: true
  })

  const data = JSON.parse(response)
  const keywords = Array.isArray(data) ? data : data.keywords ?? []

  for (const kw of keywords) {
    await db.insert(schema.cateros_seo_keywords).values({
      brand,
      keyword: kw.keyword,
      search_volume_estimate: kw.search_volume_estimate,
      difficulty_estimate: kw.difficulty_estimate,
      intent: kw.intent,
      cluster_topic: kw.cluster_topic,
      status: 'identified'
    }).onConflictDoNothing()
  }
}

export async function runWeeklySEOBatch(): Promise<void> {
  // 2 articles for Mikana + 2 for Boxed & Go
  const mikanaTargets = [
    { keyword: 'school catering UAE', audience: 'school principals and operations managers' },
    { keyword: 'corporate catering Dubai', audience: 'facilities managers and HR directors' }
  ]
  for (const t of mikanaTargets) {
    await generateSEOArticle('mikana', t.keyword, t.audience)
  }

  const bgTargets = [
    { keyword: 'meal subscription Dubai', audience: 'busy Dubai professionals and families' },
    { keyword: 'build your plate meal kit UAE', audience: 'health-conscious UAE residents' }
  ]
  for (const t of bgTargets) {
    await generateSEOArticle('boxedgo', t.keyword, t.audience)
  }
}

export { generateSEOArticle, generateKeywordCluster, runWeeklySEOBatch }
```

---
---

# PHASE 6 — CUSTOMER CARE AGENT

---

## PROMPT 6.1 — Customer Care Agent

```
Create src/agents/customer-care.ts

Imports:
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { queueForApproval, logActivity } from './orchestrator'
import { scrapeGoogleReviews, scrapeWebsite, scrapeInstagramProfile } from '@/integrations/scraping'
import { sendWhatsApp } from '@/integrations/whatsapp'
import * as schema from '@/lib/schema'
import { eq, and, gte, desc } from 'drizzle-orm'
import QRCode from 'qrcode'

━━━ SYSTEM PROMPTS ━━━

export const CARE_CLASSIFICATION_PROMPT = `
You are the Customer Care intelligence agent for CaterOS.

URGENCY CLASSIFICATION:
CRITICAL (alert within 1hr): Allergen reaction, food safety incident, illness report,
  legal threat, senior decision-maker expressing urgent anger
URGENT (respond within 4hrs): Strong negative from paying client, explicit churn threat,
  full missed delivery, school contact unhappy during contract renewal window
NORMAL (respond within 24hrs): General quality feedback, suggestions, mild complaints
LOW (acknowledge within 48hrs): Vague feedback, positive suggestions, general praise

AT-RISK FLAG — Set is_at_risk_flag = true if ANY of these:
- Boxed & Go trial subscriber complaining (trial = fragile, high churn risk)
- Any subscriber mentions a competitor positively by name
- School client complaining AND contract renewal is within 90 days
- Any mention of "cancel", "switch", "thinking of leaving", "disappointing"
- Corporate client complaint with multiple people cc'd (signals escalation risk)

ROI LENS ON AT-RISK:
BG subscriber at-risk = AED 9,200 average LTV at risk (8 months average retention × AED 1,150)
School renewal at-risk = AED 400K-800K contract at risk
Treat every at-risk flag as a direct financial threat requiring immediate attention.

OUTPUT — valid JSON ONLY:
{
  "feedback_type": "complaint|testimonial|suggestion|neutral",
  "sentiment_score": number (1-10, 1=very negative, 10=very positive),
  "complaint_categories": ["meal_quality|delivery_temperature|portion_size|price_value|packaging|service|other"],
  "meals_mentioned": ["string"],
  "urgency": "critical|urgent|normal|low",
  "is_at_risk_flag": boolean,
  "at_risk_reason": "string or null",
  "key_issue_summary": "string (1 sentence)",
  "product_flag": boolean,
  "product_flag_reason": "string or null",
  "testimonial_candidate": boolean
}
`

export const CARE_RESPONSE_PROMPT = `
You are drafting customer responses for Mikana Food Service and Boxed & Go.

MIKANA RESPONSE STYLE: Professional, warm, specific, accountable. 100-180 words.
Never generic "sorry for the inconvenience" — name the actual issue.
Always state a concrete resolution. Sign: "The Mikana Team"

BOXED & GO RESPONSE STYLE: Warm, direct, genuine. 60-120 words.
Match the customer's energy level. Bilingual if customer wrote in Arabic.
Always offer something tangible for any complaint. Sign: "The Boxed & Go Team"

FOR COMPLAINTS: Acknowledge specifically → own it → state resolution in same message.
FOR CRITICAL COMPLAINTS: Open with "Our [food safety/operations] team is reviewing this immediately."
FOR AT-RISK CUSTOMERS: Include a retention offer — replacement meal, account credit, or free week.
FOR TESTIMONIALS: Thank genuinely → ask permission to share their experience.

OUTPUT — valid JSON ONLY:
{
  "response_draft": "string",
  "response_draft_arabic": "string or null",
  "response_channel": "email|whatsapp|form_reply",
  "retention_offer": "string or null",
  "permission_requested": boolean,
  "internal_note": "string",
  "resolution_suggestion": "string"
}
`

export const COMPETITIVE_PROFILING_PROMPT = `
You are analysing scraped competitor data for CaterOS competitive intelligence.

KEY ANALYSIS FOCUS:
What competitors CLAIM vs what customers ACTUALLY EXPERIENCE.
The gap between marketing promise and customer reality is where we win.

ANALYSE EACH DATA SOURCE:
Google reviews: What do customers actually complain about? What do they praise?
  Look for patterns — 3+ mentions of same issue = a real weakness, not a one-off.
Website: What is their positioning? What do they emphasise? What do they avoid saying?
Instagram: What content performs well? What topics generate complaints in comments?

OUTPUT — valid JSON matching cateros_competitor_snapshots shape.
actual_weaknesses is the most valuable field — be specific and evidence-based.
`

export const BLUE_OCEAN_PROMPT = `
You are synthesising competitive intelligence into Blue Ocean strategy for CaterOS.

20x ROI FILTER ON ALL INNOVATIONS:
Every Blue Ocean opportunity must pass this test before inclusion:
(projected additional annual revenue from innovation) ÷ (cost to implement) ≥ 20
Only include opportunities where this ratio is achievable.

BLUE OCEAN FOUR ACTIONS FRAMEWORK:
ELIMINATE: What does every competitor offer that customers DON'T actually value?
  (Eliminating this reduces cost while increasing value to target customer)
REDUCE: What are competitors over-investing in that delivers diminishing returns?
RAISE: What do ALL competitors consistently under-deliver that customers clearly want more of?
  (These are premium-justifying improvements)
CREATE: What does NO competitor currently offer that a clear segment of customers genuinely needs?
  (This is your whitespace — the actual Blue Ocean)

Rank all opportunities by: revenue_potential_aed ÷ implementation_effort × time_to_market_months
Only propose opportunities where projected ROI > 20x.

OUTPUT — valid JSON with:
- landscape_summary (objective, 200 words)
- universal_complaints (array of {complaint, frequency, severity})
- unserved_needs (array of {need, evidence, segment})
- blue_ocean_opportunities (array of {opportunity, framework_action, evidence,
    revenue_potential_aed, implementation_cost_aed, roi_multiple, time_to_market_months})
- product_flags (array of flags to pass to Product Intelligence)
- executive_summary (plain English, 150 words)
`

━━━ FUNCTIONS ━━━

export async function classifyFeedback(feedbackId: string): Promise<void> {
  const feedback = await db.query.cateros_feedback.findFirst({
    where: eq(schema.cateros_feedback.id, feedbackId)
  })
  if (!feedback) return

  const response = await callClaude({
    systemPrompt: CARE_CLASSIFICATION_PROMPT,
    userMessage: `Classify this feedback:
Brand: ${feedback.brand}
Customer type: ${feedback.customer_type ?? 'unknown'}
Channel: ${feedback.channel}
Rating: ${feedback.rating ?? 'not provided'}
Feedback text: "${feedback.raw_text}"`,
    maxTokens: 800,
    jsonMode: true
  })

  const data = JSON.parse(response)

  await db.update(schema.cateros_feedback).set({
    feedback_type: data.feedback_type,
    sentiment_score: data.sentiment_score,
    complaint_categories: data.complaint_categories,
    urgency: data.urgency,
    is_at_risk_flag: data.is_at_risk_flag,
    status: 'classified',
    flagged_for_product_review: data.product_flag,
    updated_at: new Date()
  }).where(eq(schema.cateros_feedback.id, feedbackId))

  // Escalate CRITICAL immediately
  if (data.urgency === 'critical') {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `🚨 *CRITICAL — Immediate Attention Required*
Brand: ${feedback.brand.toUpperCase()}
Issue: ${data.key_issue_summary}
Customer: ${feedback.customer_name ?? 'unknown'}
Action: Draft response now in CaterOS → Customer Care`)
  }

  // Queue at-risk for urgent attention
  if (data.is_at_risk_flag) {
    await sendWhatsApp(process.env.OWNER_WHATSAPP!,
      `⚠️ *At-Risk Customer Flagged*
${data.at_risk_reason}
Open CaterOS → Customer Care to respond before they churn.`)
  }

  // Auto-draft response
  await draftResponse(feedbackId)
}

export async function draftResponse(feedbackId: string): Promise<void> {
  const feedback = await db.query.cateros_feedback.findFirst({
    where: eq(schema.cateros_feedback.id, feedbackId)
  })
  if (!feedback) return

  const response = await callClaude({
    systemPrompt: CARE_RESPONSE_PROMPT,
    userMessage: `Draft response for:
Brand: ${feedback.brand}
Urgency: ${feedback.urgency}
At-risk: ${feedback.is_at_risk_flag}
Customer name: ${feedback.customer_name ?? 'not provided'}
Original feedback: "${feedback.raw_text}"
Complaint categories: ${JSON.stringify(feedback.complaint_categories)}
Rating: ${feedback.rating}`,
    maxTokens: 1000,
    jsonMode: true
  })

  const data = JSON.parse(response)

  await db.update(schema.cateros_feedback).set({
    response_draft: data.response_draft,
    response_draft_arabic: data.response_draft_arabic,
    response_channel: data.response_channel,
    status: 'pending_approval',
    updated_at: new Date()
  }).where(eq(schema.cateros_feedback.id, feedbackId))

  // Queue for approval (complaints + at-risk)
  if (feedback.feedback_type !== 'testimonial' || feedback.is_at_risk_flag) {
    await queueForApproval({
      type: 'outreach_email',
      brand: feedback.brand,
      title: `Customer Response: ${feedback.urgency?.toUpperCase()} — ${feedback.customer_name ?? 'Anonymous'}`,
      summary: `Issue: ${feedback.raw_text?.slice(0, 200)}\n\nDraft response:\n${data.response_draft?.slice(0, 300)}...\n\n${data.retention_offer ? 'Retention offer: ' + data.retention_offer : ''}`,
      payload: {
        feedbackId, responseDraft: data.response_draft,
        channel: data.response_channel, retentionOffer: data.retention_offer
      },
      agent: 'customer_care',
      entityId: feedbackId,
      entityType: 'feedback',
      priority: feedback.urgency === 'critical' ? 'urgent' : 'normal'
    })
  }

  // Testimonial handling
  if (data.permission_requested && feedback.sentiment_score && feedback.sentiment_score >= 8) {
    await db.insert(schema.cateros_testimonials).values({
      feedback_id: feedbackId,
      brand: feedback.brand,
      customer_name: feedback.customer_name,
      customer_type: feedback.customer_type,
      quote_original: feedback.raw_text,
      rating: feedback.rating,
      permission_to_use: false,
      permission_requested_at: new Date(),
      status: 'pending_permission'
    })
  }
}

export async function processFeedbackBatch(): Promise<void> {
  const newFeedback = await db.query.cateros_feedback.findMany({
    where: eq(schema.cateros_feedback.status, 'new'),
    limit: 20
  })
  for (const f of newFeedback) {
    await classifyFeedback(f.id)
  }
}

export async function generateQRCode(params: {
  brand: string; purpose: string; linkedEntityType: string;
  linkedEntityId: string; linkedEntityLabel: string
}): Promise<{ code: string; qrDataUrl: string; destinationUrl: string }> {
  const code = `${params.brand.slice(0, 2).toUpperCase()}-${Date.now().toString(36).toUpperCase()}`
  const destinationUrl = `${process.env.NEXT_PUBLIC_APP_URL}/feedback?code=${code}&brand=${params.brand}`

  await db.insert(schema.cateros_qr_codes).values({
    code, brand: params.brand, purpose: params.purpose,
    linked_entity_type: params.linkedEntityType,
    linked_entity_id: params.linkedEntityId,
    linked_entity_label: params.linkedEntityLabel,
    destination_url: destinationUrl
  })

  const qrDataUrl = await QRCode.toDataURL(destinationUrl, {
    width: 400, margin: 2,
    color: { dark: params.brand === 'mikana' ? '#E8490F' : '#c2714f', light: '#FFFFFF' }
  })

  return { code, qrDataUrl, destinationUrl }
}

export async function runCompetitiveIntelligence(industry: string): Promise<void> {
  const competitors = await db.query.cateros_competitors.findMany({
    where: and(
      eq(schema.cateros_competitors.industry, industry),
      eq(schema.cateros_competitors.is_active, true)
    )
  })

  const snapshots = []

  for (const competitor of competitors) {
    const [websiteData, googleReviews, instagramData] = await Promise.allSettled([
      competitor.website_url ? scrapeWebsite(competitor.website_url) : Promise.resolve(null),
      competitor.google_maps_place_id ? scrapeGoogleReviews(competitor.google_maps_place_id) : Promise.resolve(null),
      competitor.instagram_handle ? scrapeInstagramProfile(competitor.instagram_handle) : Promise.resolve(null)
    ])

    const profile = await callClaude({
      systemPrompt: COMPETITIVE_PROFILING_PROMPT,
      userMessage: JSON.stringify({
        competitor_name: competitor.name,
        industry,
        website_data: websiteData.status === 'fulfilled' ? websiteData.value : null,
        google_reviews: googleReviews.status === 'fulfilled' ? googleReviews.value : null,
        instagram_data: instagramData.status === 'fulfilled' ? instagramData.value : null
      }),
      maxTokens: 2000,
      jsonMode: true
    })

    const profileData = JSON.parse(profile)
    const month = new Date().toISOString().slice(0, 7)

    const [snapshot] = await db.insert(schema.cateros_competitor_snapshots).values({
      competitor_id: competitor.id,
      snapshot_month: month,
      website_content_summary: profileData.website_content_summary,
      google_rating: profileData.google_rating ? String(profileData.google_rating) : null,
      google_common_complaints: profileData.google_common_complaints ?? [],
      google_common_praises: profileData.google_common_praises ?? [],
      google_sentiment_summary: profileData.google_sentiment_summary,
      instagram_content_themes: profileData.instagram_content_themes ?? [],
      instagram_comment_complaints: profileData.instagram_comment_complaints ?? [],
      positioning_summary: profileData.positioning_summary,
      actual_strengths: profileData.actual_strengths ?? [],
      actual_weaknesses: profileData.actual_weaknesses ?? [],
      raw_scrape_data: profileData
    }).returning()

    snapshots.push(snapshot)

    // Update last scraped
    await db.update(schema.cateros_competitors)
      .set({ last_scraped_at: new Date() })
      .where(eq(schema.cateros_competitors.id, competitor.id))
  }

  // Run Blue Ocean synthesis if we have enough snapshots
  if (snapshots.length >= 3) {
    await runBlueOceanSynthesis(industry)
  }
}

export async function runBlueOceanSynthesis(industry: string): Promise<void> {
  const month = new Date().toISOString().slice(0, 7)

  const snapshots = await db.query.cateros_competitor_snapshots.findMany({
    where: eq(schema.cateros_competitor_snapshots.snapshot_month, month)
  })

  const ownComplaints = await db.query.cateros_feedback.findMany({
    where: and(
      eq(schema.cateros_feedback.feedback_type, 'complaint'),
      gte(schema.cateros_feedback.created_at, new Date(Date.now() - 90 * 86400000))
    ),
    limit: 50
  })

  const synthesis = await callClaude({
    systemPrompt: BLUE_OCEAN_PROMPT,
    userMessage: JSON.stringify({
      industry, month,
      competitor_snapshots: snapshots.slice(0, 10),
      own_complaint_patterns: ownComplaints.map(f => ({
        categories: f.complaint_categories,
        text: f.raw_text?.slice(0, 200)
      })),
      roi_target: 20
    }),
    maxTokens: 3000,
    jsonMode: true
  })

  const data = JSON.parse(synthesis)

  const [report] = await db.insert(schema.cateros_blue_ocean_reports).values({
    report_month: month,
    industry,
    brand: 'both',
    competitors_analysed: snapshots.length,
    landscape_summary: data.landscape_summary,
    universal_complaints: data.universal_complaints,
    unserved_needs: data.unserved_needs,
    competitor_blind_spots: data.competitor_blind_spots,
    blue_ocean_opportunities: data.blue_ocean_opportunities,
    product_innovations: data.product_innovations,
    messaging_opportunities: data.messaging_opportunities,
    product_flags: data.product_flags ?? [],
    executive_summary: data.executive_summary,
    status: 'pending_approval'
  }).returning()

  await queueForApproval({
    type: 'blue_ocean_report',
    brand: 'both',
    title: `Blue Ocean Report — ${industry} — ${month}`,
    summary: `${snapshots.length} competitors analysed.\n\n${data.executive_summary?.slice(0, 400)}`,
    payload: { reportId: report.id, industry, month },
    agent: 'customer_care',
    entityId: report.id,
    entityType: 'blue_ocean_report',
    priority: 'low'
  })
}

export { classifyFeedback, draftResponse, processFeedbackBatch,
  generateQRCode, runCompetitiveIntelligence, runBlueOceanSynthesis }
```

---
---

# PHASE 7 — ALL API ROUTES

---

## PROMPT 7.1 — All Cron Routes

```
Create ALL cron routes. Each follows the same pattern — copy exactly.
Add export const dynamic = 'force-dynamic' to every route file.

━━━ /api/cron/morning-scout/route.ts ━━━
import { cronGuard } from '@/lib/constants'
import { runMorningScoutCycle } from '@/agents/scout'
export const dynamic = 'force-dynamic'
export async function GET(request: Request) {
  if (!cronGuard(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })
  try {
    const report = await runMorningScoutCycle()
    return Response.json({ success: true, report })
  } catch (error) {
    console.error('[CRON] morning-scout failed:', error)
    return Response.json({ error: String(error) }, { status: 500 })
  }
}

━━━ /api/cron/morning-briefing/route.ts ━━━
Same pattern, calls: generateMorningBriefing from '@/agents/orchestrator'

━━━ /api/cron/morning-pipeline/route.ts ━━━
Same pattern, calls: runMorningPipelineCycle from '@/agents/pipeline'

━━━ /api/cron/social-publish/route.ts ━━━
Same pattern, calls: runPublishQueue from '@/agents/broadcast'

━━━ /api/cron/feedback-processor/route.ts ━━━
Same pattern, calls: processFeedbackBatch from '@/agents/customer-care'

━━━ /api/cron/engagement-sync/route.ts ━━━
Same pattern, calls: runEngagementSync from '@/agents/broadcast'

━━━ /api/cron/escalation-check/route.ts ━━━
Same pattern, calls: runEscalationCheck from '@/agents/orchestrator'

━━━ /api/cron/weekly-batch/route.ts ━━━
Calls THREE functions in sequence:
import { runWeeklyContentBatch } from '@/agents/broadcast'
import { runWeeklySEOBatch } from '@/agents/seo-engine'
import { runWeeklyFinancialReview } from '@/agents/orchestrator'

export async function GET(request: Request) {
  if (!cronGuard(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })
  const [content, seo, financial] = await Promise.allSettled([
    runWeeklyContentBatch(),
    runWeeklySEOBatch(),
    runWeeklyFinancialReview()
  ])
  return Response.json({
    success: true,
    content: content.status,
    seo: seo.status,
    financial: financial.status
  })
}

━━━ /api/cron/monthly-intel/route.ts ━━━
import { runCompetitiveIntelligence } from '@/agents/customer-care'
const INDUSTRIES = [
  'school_food_uae', 'corporate_catering_uae', 'meal_subscription_uae'
]
export async function GET(request: Request) {
  if (!cronGuard(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })
  const results = []
  for (const industry of INDUSTRIES) {
    try {
      await runCompetitiveIntelligence(industry)
      results.push({ industry, status: 'completed' })
    } catch (e) {
      results.push({ industry, status: 'failed', error: String(e) })
    }
  }
  return Response.json({ success: true, results })
}
```

---

## PROMPT 7.2 — Approval + WhatsApp Webhook Routes

```
Create these approval routes:

━━━ /api/approvals/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_approval_requests } from '@/lib/schema'
import { eq, desc } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const status = searchParams.get('status') ?? 'pending'
  const brand = searchParams.get('brand')
  const limit = parseInt(searchParams.get('limit') ?? '50')

  const conditions = status !== 'all' ? [eq(cateros_approval_requests.status, status)] : []
  if (brand) conditions.push(eq(cateros_approval_requests.brand, brand))

  const items = await db.query.cateros_approval_requests.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_approval_requests.created_at)],
    limit
  })

  const pending = await db.query.cateros_approval_requests.findMany({
    where: eq(cateros_approval_requests.status, 'pending')
  })

  return Response.json({ items, pendingCount: pending.length })
}

━━━ /api/approvals/[id]/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_approval_requests } from '@/lib/schema'
import { eq } from 'drizzle-orm'
import { executeApprovedAction } from '@/agents/orchestrator'
export const dynamic = 'force-dynamic'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const item = await db.query.cateros_approval_requests.findFirst({
    where: eq(cateros_approval_requests.id, params.id)
  })
  if (!item) return Response.json({ error: 'Not found' }, { status: 404 })
  return Response.json(item)
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  const { decision, editedContent, reason } = body

  await db.update(cateros_approval_requests).set({
    status: decision,
    owner_decision: reason ?? decision,
    edited_payload: editedContent ? { content: editedContent } : null,
    responded_at: new Date()
  }).where(eq(cateros_approval_requests.id, params.id))

  if (decision === 'approved' || decision === 'edited') {
    const request_record = await db.query.cateros_approval_requests.findFirst({
      where: eq(cateros_approval_requests.id, params.id)
    })
    if (request_record) await executeApprovedAction(request_record, editedContent ?? null)
  }

  return Response.json({ success: true, decision })
}

━━━ /api/approvals/whatsapp/route.ts ━━━
import { processOwnerReply } from '@/agents/orchestrator'
import crypto from 'crypto'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const mode = searchParams.get('hub.mode')
  const token = searchParams.get('hub.verify_token')
  const challenge = searchParams.get('hub.challenge')
  if (mode === 'subscribe' && token === process.env.WHATSAPP_WEBHOOK_VERIFY_TOKEN) {
    return new Response(challenge, { status: 200 })
  }
  return new Response('Forbidden', { status: 403 })
}

export async function POST(request: Request) {
  // Verify signature
  const body = await request.text()
  const signature = request.headers.get('x-hub-signature-256') ?? ''
  const expected = 'sha256=' + crypto
    .createHmac('sha256', process.env.META_APP_SECRET!)
    .update(body)
    .digest('hex')

  if (signature !== expected) {
    return new Response('Signature mismatch', { status: 401 })
  }

  // Process asynchronously — must return 200 immediately
  const data = JSON.parse(body)
  setTimeout(async () => {
    try {
      const entry = data.entry?.[0]?.changes?.[0]?.value
      const message = entry?.messages?.[0]
      if (message?.type === 'text') {
        const from = message.from
        const text = message.text.body
        await processOwnerReply(text, from)
      }
    } catch (e) {
      console.error('[WEBHOOK] WhatsApp processing error:', e)
    }
  }, 0)

  return Response.json({ status: 'received' })
}
```

---

## PROMPT 7.3 — All Remaining API Routes

```
Create all remaining API routes. Each must include export const dynamic = 'force-dynamic'.

━━━ /api/financial/roi/route.ts ━━━
GET: runs runROIAnalysis('rolling_30') and returns latest snapshot
POST: body { period } — runs analysis for that period

━━━ /api/financial/spend/route.ts ━━━
GET: returns recent spend entries
POST: body matches cateros_spend_entries shape — calls logSpend from orchestrator

━━━ /api/financial/revenue/route.ts ━━━
GET: returns recent revenue entries
POST: body matches cateros_revenue_entries — calls logRevenue

━━━ /api/financial/targets/route.ts ━━━
GET: returns current approved targets
POST: calls proposeQuarterlyTargets from orchestrator

━━━ /api/financial/platform-costs/route.ts ━━━
GET: returns current month cateros_platform_cost_budgets record + all entries
POST: logs a platform cost entry via logPlatformCost

━━━ /api/pipeline/schools/route.ts ━━━
GET: returns school_leads joined with school data, ordered by next_action_date
  Filters: stage?, lead_type?, overdue (next_action_date < today)
PATCH /[id]: update stage, next_action, notes

━━━ /api/pipeline/corporate/route.ts ━━━
GET: returns corporate_leads joined with company + contact
PATCH /[id]: update stage

━━━ /api/pipeline/boxedgo/route.ts ━━━
GET: returns bg_subscribers with filters (stage, segment, at_risk)
POST: create subscriber → generate awareness message
PATCH /[id]: update stage → auto-generate appropriate next message

━━━ /api/broadcast/schedule/route.ts ━━━
GET: returns social_posts with filters (brand, status, platform, date range)
PATCH /[id]: update status, scheduled_at, caption
DELETE /[id]: archive post

━━━ /api/broadcast/generate/route.ts ━━━
POST: body { brand, platform, contentType, topic?, productFocus? }
Calls generateAndQueuePost from broadcast agent

━━━ /api/broadcast/webhooks/instagram/route.ts ━━━
GET: verify challenge — check hub.verify_token === META_WEBHOOK_VERIFY_TOKEN, return hub.challenge
POST: verify x-hub-signature-256, parse comments, call processComment for each, return 200 immediately

━━━ /api/seo/generate/route.ts ━━━
POST: body { brand, keyword, audience } — calls generateSEOArticle

━━━ /api/seo/content/route.ts ━━━
GET: returns seo_content with filters (brand, status)
PATCH /[id]: update status or content

━━━ /api/care/feedback/route.ts ━━━
GET: returns feedback inbox with filters (urgency, status, brand)
POST (public route — NO auth): receives QR form submissions
  Creates cateros_feedback record, runs classifyFeedback asynchronously
  Returns immediately with { success: true, message: "Thank you for your feedback" }

━━━ /api/care/qrcodes/route.ts ━━━
GET: returns all QR codes with scan/feedback stats
POST: body { brand, purpose, linkedEntityType, linkedEntityId, linkedEntityLabel }
  Calls generateQRCode, returns { code, qrDataUrl, destinationUrl }

━━━ /api/care/testimonials/route.ts ━━━
GET: returns testimonials filtered by status, brand
PATCH /[id]: grant permission, edit quote, update status

━━━ /api/competitive/competitors/route.ts ━━━
GET: returns all competitors grouped by industry
POST: add competitor — body matches cateros_competitors shape
PATCH /[id]: update competitor details

━━━ /api/competitive/run/route.ts ━━━
POST: body { industry } — calls runCompetitiveIntelligence

━━━ /api/health/route.ts ━━━
export const dynamic = 'force-dynamic'
export async function GET() {
  const { db } = await import('@/lib/db')
  const { cateros_approval_requests } = await import('@/lib/schema')
  const { eq } = await import('drizzle-orm')
  const pending = await db.query.cateros_approval_requests.findMany({
    where: eq(cateros_approval_requests.status, 'pending')
  })
  return Response.json({
    status: 'ok',
    version: '4.0.0',
    timestamp: new Date().toISOString(),
    roiTarget: '20x',
    brands: ['mikana', 'boxedgo'],
    agents: ['scout', 'pipeline', 'broadcast', 'seo_engine', 'customer_care', 'orchestrator'],
    pendingApprovals: pending.length,
    urgentApprovals: pending.filter(p => p.priority === 'urgent').length
  })
}

━━━ /api/dev/seed/route.ts ━━━
export async function POST() {
  if (process.env.NODE_ENV !== 'development') {
    return Response.json({ error: 'Development only' }, { status: 403 })
  }
  const { runSeed } = await import('@/lib/seed')
  await runSeed()
  return Response.json({ success: true, message: 'Database seeded' })
}

For ALL routes: import { and } from 'drizzle-orm' where needed for multiple where conditions.
All GET routes with filtering: parse query params with new URL(request.url).searchParams
```
# PHASE 8 — OWNER INTERFACE

---

## PROMPT 8.1 — App Layout, Navigation & Global Styles

```
Update src/app/layout.tsx:

import { validateEnv } from '@/lib/validate-env'
import Sidebar from '@/components/ui/Sidebar'
import './globals.css'

if (process.env.NODE_ENV === 'production') {
  try { validateEnv() } catch (e) { console.error(e) }
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </body>
    </html>
  )
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add to src/app/globals.css (after Tailwind directives):

:root {
  --mikana: #E8490F;
  --mikana-dark: #c23a0c;
  --boxedgo: #c2714f;
  --boxedgo-light: #fef3e2;
  --green-roi: #22c55e;
  --amber-roi: #f59e0b;
  --red-roi: #ef4444;
  --black-roi: #1e293b;
  --card: #1e293b;
  --surface: #0f172a;
}

.roi-green  { color: #22c55e; }
.roi-amber  { color: #f59e0b; }
.roi-red    { color: #ef4444; }
.roi-black  { color: #94a3b8; }
.badge-mikana   { background: #E8490F; color: white; }
.badge-boxedgo  { background: #c2714f; color: white; }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create src/components/ui/Sidebar.tsx:

'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import {
  Sun, Bell, Activity, School, Building2, Package,
  Radio, Search, Radar, MessageSquare, TrendingUp, Settings
} from 'lucide-react'

const NAV = [
  { href: '/briefing',          icon: Sun,           label: 'Morning Briefing', badgeKey: 'pending' },
  { href: '/approvals',         icon: Bell,          label: 'Approvals',        badgeKey: 'approvals' },
  { href: '/activity',          icon: Activity,      label: 'Activity Log' },
  { href: '/pipeline/schools',  icon: School,        label: 'Schools',          badgeKey: 'renewals' },
  { href: '/pipeline/corporate',icon: Building2,     label: 'Corporate' },
  { href: '/pipeline/boxedgo',  icon: Package,       label: 'Boxed & Go',       badgeKey: 'atrisk' },
  { href: '/broadcast',         icon: Radio,         label: 'Broadcast',        badgeKey: 'comments' },
  { href: '/seo',               icon: Search,        label: 'SEO Engine' },
  { href: '/scout',             icon: Radar,         label: 'Scout' },
  { href: '/care',              icon: MessageSquare, label: 'Customer Care',    badgeKey: 'urgent' },
  { href: '/financial',         icon: TrendingUp,    label: 'Financial' },
  { href: '/settings',          icon: Settings,      label: 'Settings' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [expanded, setExpanded] = useState(true)
  const [badges, setBadges] = useState<Record<string, number>>({})

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(data => {
      setBadges({
        pending: data.pendingApprovals || 0,
        approvals: data.pendingApprovals || 0,
        urgent: data.urgentApprovals || 0,
      })
    }).catch(() => {})
    const interval = setInterval(() => {
      fetch('/api/health').then(r => r.json()).then(data => {
        setBadges({
          pending: data.pendingApprovals || 0,
          approvals: data.pendingApprovals || 0,
          urgent: data.urgentApprovals || 0,
        })
      }).catch(() => {})
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  return (
    <aside className={`${expanded ? 'w-56' : 'w-16'} bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-200 shrink-0`}>
      <div className="p-4 flex items-center justify-between border-b border-slate-800">
        {expanded && <span className="font-bold text-sm tracking-wider text-white">CATEROS</span>}
        <button onClick={() => setExpanded(!expanded)} className="text-slate-400 hover:text-white ml-auto">
          {expanded ? '←' : '→'}
        </button>
      </div>

      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label, badgeKey }) => {
          const active = pathname.startsWith(href)
          const count = badgeKey ? badges[badgeKey] : 0
          return (
            <Link key={href} href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors relative
                ${active ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}>
              <Icon size={18} className="shrink-0" />
              {expanded && <span>{label}</span>}
              {count > 0 && (
                <span className="absolute right-2 top-1.5 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {count > 9 ? '9+' : count}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      <div className="p-3 border-t border-slate-800">
        {expanded && <p className="text-xs text-slate-500 mb-2">Agent Status</p>}
        <div className="flex gap-1.5 flex-wrap">
          {['S', 'P', 'B', 'SEO', 'C'].map(a => (
            <span key={a} className="w-2 h-2 rounded-full bg-green-500" title={a} />
          ))}
        </div>
      </div>
    </aside>
  )
}
```

---

## PROMPT 8.2 — Morning Briefing Page

```
Build src/app/briefing/page.tsx

This is the owner's homepage — the daily command centre.
Answers: "What needs my attention right now?"
Designed for mobile (read on phone at breakfast). Fast. Actionable.

'use client'
import { useState, useEffect } from 'react'
import { CheckCircle, Edit2, XCircle, Clock, TrendingUp, AlertTriangle } from 'lucide-react'
import { formatAED, roiEmoji } from '@/lib/utils'

type Approval = {
  id: string; type: string; brand: string; title: string; summary: string;
  priority: string; expires_at: string; agent: string; payload: any
}

export default function BriefingPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [roiData, setRoiData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [actioning, setActioning] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')

  const isMonday = new Date().getDay() === 1

  useEffect(() => {
    Promise.all([
      fetch('/api/approvals?status=pending&limit=20').then(r => r.json()),
      isMonday ? fetch('/api/financial/roi').then(r => r.json()) : Promise.resolve(null)
    ]).then(([appr, roi]) => {
      setApprovals(appr.data || [])
      setRoiData(roi)
      setLoading(false)
    })
    const interval = setInterval(() => {
      fetch('/api/approvals?status=pending&limit=20').then(r => r.json())
        .then(data => setApprovals(data.data || []))
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  async function decide(id: string, decision: 'approved' | 'rejected' | 'edited', editContent?: string) {
    setActioning(id)
    await fetch(`/api/approvals/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, editedPayload: editContent ? { content: editContent } : undefined })
    })
    setApprovals(prev => prev.filter(a => a.id !== id))
    setActioning(null)
    setEditingId(null)
  }

  function hoursLeft(expires: string) {
    return Math.max(0, Math.round((new Date(expires).getTime() - Date.now()) / 3600000))
  }

  const brandColor = (b: string) => b === 'mikana' ? 'bg-orange-600' : 'bg-amber-700'
  const agentLabel: Record<string, string> = {
    scout: '🔍 Scout', pipeline: '📋 Pipeline', broadcast: '📡 Broadcast',
    seo_engine: '🔎 SEO', customer_care: '💬 Care', orchestrator: '🧠 Orchestrator'
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-slate-400 text-sm">Loading briefing…</div>
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Good morning ☀️</h1>
          <p className="text-slate-400 text-sm">
            {new Date().toLocaleDateString('en-AE', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </div>
        {approvals.length > 0 && (
          <span className="bg-red-500 text-white text-sm font-bold px-3 py-1 rounded-full">
            {approvals.length} pending
          </span>
        )}
      </div>

      {/* SECTION 1: APPROVAL QUEUE */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Needs Your Input
        </h2>

        {approvals.length === 0 ? (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <CheckCircle className="text-green-500 mx-auto mb-2" size={32} />
            <p className="text-white font-medium">All clear — agents are working</p>
            <p className="text-slate-400 text-sm mt-1">No items need your attention right now</p>
          </div>
        ) : (
          <div className="space-y-3">
            {approvals.map(a => {
              const hours = hoursLeft(a.expires_at)
              const isEditing = editingId === a.id
              return (
                <div key={a.id}
                  className={`bg-slate-800 rounded-xl p-4 border-l-4 ${a.priority === 'urgent' ? 'border-red-500' : 'border-slate-600'}`}>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded-full text-white font-medium ${brandColor(a.brand)}`}>
                        {a.brand === 'mikana' ? 'Mikana' : 'Boxed & Go'}
                      </span>
                      <span className="text-xs text-slate-400">{agentLabel[a.agent] || a.agent}</span>
                    </div>
                    <div className={`flex items-center gap-1 text-xs shrink-0 ${hours < 4 ? 'text-red-400' : 'text-slate-400'}`}>
                      <Clock size={12} />
                      {hours}h left
                    </div>
                  </div>

                  <p className="text-white font-medium text-sm mb-1">{a.title}</p>
                  <p className="text-slate-400 text-sm leading-relaxed mb-3">{a.summary}</p>

                  {isEditing ? (
                    <div className="space-y-2">
                      <textarea
                        className="w-full bg-slate-700 text-white rounded-lg p-3 text-sm resize-none border border-slate-600 focus:border-orange-500 focus:outline-none"
                        rows={5} value={editText}
                        onChange={e => setEditText(e.target.value)}
                        placeholder="Make your changes here…"
                      />
                      <div className="flex gap-2">
                        <button onClick={() => decide(a.id, 'edited', editText)}
                          className="flex-1 bg-orange-600 hover:bg-orange-700 text-white text-sm py-2 rounded-lg font-medium transition-colors">
                          Submit Edit
                        </button>
                        <button onClick={() => setEditingId(null)}
                          className="px-4 bg-slate-700 hover:bg-slate-600 text-white text-sm py-2 rounded-lg transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        disabled={actioning === a.id}
                        onClick={() => decide(a.id, 'approved')}
                        className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm py-2 rounded-lg font-medium flex items-center justify-center gap-1.5 transition-colors">
                        <CheckCircle size={15} /> Approve
                      </button>
                      <button
                        onClick={() => { setEditingId(a.id); setEditText(a.payload?.body || a.payload?.caption || a.summary || '') }}
                        className="px-3 bg-slate-700 hover:bg-slate-600 text-white text-sm py-2 rounded-lg transition-colors">
                        <Edit2 size={15} />
                      </button>
                      <button
                        disabled={actioning === a.id}
                        onClick={() => decide(a.id, 'rejected')}
                        className="px-3 bg-slate-700 hover:bg-red-900 disabled:opacity-50 text-white text-sm py-2 rounded-lg transition-colors">
                        <XCircle size={15} />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* SECTION 2: ROI STATUS (Mondays only) */}
      {isMonday && roiData && (
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Weekly ROI Review
          </h2>
          <div className="bg-slate-800 rounded-xl p-5">
            <div className="flex items-baseline gap-3 mb-1">
              <span className="text-4xl font-bold text-white">{roiData.true_net_roi?.toFixed(1)}x</span>
              <span className="text-2xl">{roiEmoji(roiData.true_net_roi)}</span>
              <span className="text-slate-400 text-sm">vs 20x target</span>
            </div>
            {roiData.true_net_roi < 20 && (
              <div className="flex items-center gap-2 text-amber-400 text-sm mt-2">
                <AlertTriangle size={14} />
                {formatAED((20 - roiData.true_net_roi) * (roiData.total_spend_aed || 0))} more revenue needed this month
              </div>
            )}
            {roiData.channels_below_20x?.length > 0 && (
              <p className="text-sm text-slate-400 mt-2">
                Below 20x: {roiData.channels_below_20x.join(', ')}
              </p>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
```

---

## PROMPT 8.3 — Approvals Inbox

```
Build src/app/approvals/page.tsx — Full approval management interface.

'use client'
import { useState, useEffect, useCallback } from 'react'
import { formatDistanceToNow } from 'date-fns'

type Approval = {
  id: string; type: string; brand: string; title: string; summary: string;
  payload: any; priority: string; expires_at: string; agent: string; status: string; created_at: string
}

const TYPE_ICONS: Record<string, string> = {
  new_lead_school: '🏫', new_lead_corporate: '🏢', new_subscriber: '📦',
  outreach_email: '📧', social_post: '📱', seo_article: '📝',
  spending_decision: '💰', tier_change: '⚙️', product_verdict: '🎯', blue_ocean_report: '🌊'
}
const AGENT_LABELS: Record<string, string> = {
  scout: 'Scout', pipeline: 'Pipeline', broadcast: 'Broadcast',
  seo_engine: 'SEO Engine', customer_care: 'Customer Care', orchestrator: 'Orchestrator'
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [selected, setSelected] = useState<Approval | null>(null)
  const [tab, setTab] = useState<'pending' | 'history'>('pending')
  const [filterAgent, setFilterAgent] = useState('all')
  const [loading, setLoading] = useState(true)
  const [editContent, setEditContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadApprovals = useCallback(() => {
    const status = tab === 'pending' ? 'pending' : 'all'
    fetch(`/api/approvals?status=${status}&limit=50`)
      .then(r => r.json())
      .then(data => { setApprovals(data.data || []); setLoading(false) })
  }, [tab])

  useEffect(() => { loadApprovals() }, [loadApprovals])

  useEffect(() => {
    if (selected) {
      const content = selected.payload?.body || selected.payload?.caption || selected.payload?.content || selected.summary || ''
      setEditContent(content)
    }
  }, [selected])

  async function decide(id: string, decision: 'approved' | 'rejected' | 'edited') {
    setSubmitting(true)
    await fetch(`/api/approvals/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        decision,
        editedPayload: decision === 'edited' ? { content: editContent } : undefined
      })
    })
    setApprovals(prev => prev.filter(a => a.id !== id))
    setSelected(null)
    setSubmitting(false)
  }

  const filtered = filterAgent === 'all' ? approvals : approvals.filter(a => a.agent === filterAgent)

  const brandStyle = (brand: string) =>
    brand === 'mikana' ? 'bg-orange-600' : brand === 'boxedgo' ? 'bg-amber-700' : 'bg-slate-600'

  return (
    <div className="flex h-full">
      {/* LEFT: List */}
      <div className="w-80 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-lg font-bold text-white mb-3">Approvals</h1>
          <div className="flex gap-1 mb-3">
            {(['pending', 'history'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`flex-1 text-sm py-1.5 rounded-lg capitalize ${tab === t ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
                {t}
              </button>
            ))}
          </div>
          <select value={filterAgent} onChange={e => setFilterAgent(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg text-sm text-white px-3 py-2">
            <option value="all">All agents</option>
            {Object.entries(AGENT_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-slate-400 text-sm">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-sm">
              {tab === 'pending' ? 'No pending approvals ✅' : 'No history found'}
            </div>
          ) : (
            filtered.map(a => (
              <button key={a.id} onClick={() => setSelected(a)}
                className={`w-full text-left p-4 border-b border-slate-800 hover:bg-slate-800 transition-colors ${selected?.id === a.id ? 'bg-slate-800' : ''}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${a.priority === 'urgent' ? 'bg-red-500' : 'bg-slate-500'}`} />
                  <span className="text-base">{TYPE_ICONS[a.type] || '📋'}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded text-white ${brandStyle(a.brand)}`}>
                    {a.brand === 'boxedgo' ? 'B&G' : a.brand === 'mikana' ? 'Mik' : 'Both'}
                  </span>
                </div>
                <p className="text-sm text-white font-medium truncate">{a.title}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {AGENT_LABELS[a.agent]} · {formatDistanceToNow(new Date(a.expires_at), { addSuffix: true })}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* RIGHT: Detail */}
      <div className="flex-1 flex flex-col">
        {!selected ? (
          <div className="flex-1 flex items-center justify-center text-slate-600">
            <p>Select an item to review</p>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">{TYPE_ICONS[selected.type] || '📋'}</span>
                <div>
                  <h2 className="text-xl font-bold text-white">{selected.title}</h2>
                  <p className="text-sm text-slate-400">
                    {AGENT_LABELS[selected.agent]} · {selected.type.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>

              <div className="bg-slate-800 rounded-xl p-4 mb-4">
                <p className="text-slate-300 text-sm leading-relaxed">{selected.summary}</p>
              </div>

              {/* Outreach email preview */}
              {(selected.type === 'outreach_email') && selected.payload && (
                <div className="bg-slate-800 rounded-xl p-4 mb-4 border border-slate-700">
                  <p className="text-xs text-slate-500 mb-1">To: {selected.payload.contactEmail}</p>
                  <p className="text-sm font-medium text-white mb-3">Subject: {selected.payload.subject}</p>
                  <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap border-t border-slate-700 pt-3">
                    {selected.payload.body}
                  </div>
                </div>
              )}

              {/* Social post preview */}
              {selected.type === 'social_post' && selected.payload && (
                <div className="bg-slate-800 rounded-xl p-4 mb-4 border border-slate-700">
                  <p className="text-xs text-slate-500 mb-2 capitalize">{selected.payload.platform}</p>
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{selected.payload.caption}</p>
                  {selected.payload.hashtags?.length > 0 && (
                    <p className="text-xs text-blue-400 mt-2">{selected.payload.hashtags.map((h: string) => `#${h}`).join(' ')}</p>
                  )}
                  {selected.payload.caption_arabic && (
                    <p className="text-sm text-slate-400 leading-relaxed mt-3 pt-3 border-t border-slate-700 text-right" dir="rtl">
                      {selected.payload.caption_arabic}
                    </p>
                  )}
                </div>
              )}

              {/* Edit area */}
              <div className="mb-4">
                <label className="text-xs text-slate-500 block mb-2">Edit content (used if you click "Edit & Approve"):</label>
                <textarea
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-sm text-white resize-none focus:border-orange-500 focus:outline-none leading-relaxed"
                  rows={8}
                />
              </div>

              {/* Payload detail */}
              {selected.payload && (
                <details className="mb-4">
                  <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300">Full payload data</summary>
                  <pre className="text-xs text-slate-400 bg-slate-900 rounded-xl p-4 mt-2 overflow-auto">
                    {JSON.stringify(selected.payload, null, 2)}
                  </pre>
                </details>
              )}
            </div>

            {/* Action bar */}
            <div className="border-t border-slate-800 p-4 flex gap-3">
              <button disabled={submitting} onClick={() => decide(selected.id, 'approved')}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold text-sm transition-colors">
                ✅ Approve
              </button>
              <button disabled={submitting} onClick={() => decide(selected.id, 'edited')}
                className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold text-sm transition-colors">
                ✏️ Edit & Approve
              </button>
              <button disabled={submitting} onClick={() => decide(selected.id, 'rejected')}
                className="flex-1 bg-slate-700 hover:bg-red-900 disabled:opacity-50 text-white py-3 rounded-xl font-semibold text-sm transition-colors">
                ❌ Reject
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

---

## PROMPT 8.4 — Financial Dashboard

```
Build src/app/financial/page.tsx — 20x ROI Command Centre.

'use client'
import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { formatAED, formatROI, roiEmoji } from '@/lib/utils'

export default function FinancialPage() {
  const [roi, setRoi] = useState<any>(null)
  const [targets, setTargets] = useState<any>(null)
  const [envelopes, setEnvelopes] = useState<any[]>([])
  const [platformCost, setPlatformCost] = useState<any>(null)
  const [products, setProducts] = useState<any[]>([])
  const [period, setPeriod] = useState('rolling_30')
  const [loading, setLoading] = useState(true)
  const [logSpendOpen, setLogSpendOpen] = useState<string | null>(null)
  const [spendAmount, setSpendAmount] = useState('')

  useEffect(() => {
    Promise.all([
      fetch(`/api/financial/roi?period=${period}`).then(r => r.json()),
      fetch('/api/financial/targets').then(r => r.json()),
      fetch('/api/financial/spend').then(r => r.json()),
      fetch('/api/financial/platform-costs').then(r => r.json()),
    ]).then(([r, t, s, p]) => {
      setRoi(r.data)
      setTargets(t.data)
      setEnvelopes(s.envelopes || [])
      setPlatformCost(p.data)
      setLoading(false)
    })
  }, [period])

  async function proposeTargets() {
    await fetch('/api/financial/targets/propose', { method: 'POST' })
    alert('Quarterly targets proposal queued — check your WhatsApp.')
  }

  async function logSpend(envelopeId: string) {
    await fetch('/api/financial/spend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budget_envelope_id: envelopeId, amount: parseFloat(spendAmount), currency: 'AED', description: 'Manual entry', spend_date: new Date().toISOString().split('T')[0] })
    })
    setLogSpendOpen(null); setSpendAmount('')
  }

  if (loading) return <div className="flex items-center justify-center h-full text-slate-400 text-sm">Loading financial data…</div>

  const trueROI = parseFloat(roi?.true_net_roi || '0')
  const grossROI = parseFloat(roi?.gross_roi || '0')
  const roiColor = trueROI >= 20 ? '#22c55e' : trueROI >= 10 ? '#f59e0b' : '#ef4444'

  const channelData = Object.entries(roi?.roi_by_channel || {}).map(([channel, roiVal]) => ({
    channel: channel.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    roi: parseFloat(roiVal as string)
  })).sort((a, b) => b.roi - a.roi)

  const revenueData = Object.entries(roi?.revenue_by_channel || {}).map(([name, value]) => ({
    name: name.replace(/_/g, ' '), value: parseFloat(value as string), color: '#' + Math.floor(Math.random() * 0xffffff).toString(16)
  }))

  const tierColors: Record<string, string> = { floor: '#64748b', standard: '#3b82f6', expanded: '#8b5cf6', scale: '#f59e0b' }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Financial Dashboard</h1>
        <div className="flex gap-2">
          {['mtd', 'rolling_30', 'qtd', 'ytd'].map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`text-sm px-3 py-1.5 rounded-lg ${period === p ? 'bg-slate-600 text-white' : 'text-slate-400 hover:text-white'}`}>
              {p.toUpperCase().replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* ROI HERO */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-2xl p-6">
          <p className="text-slate-400 text-sm mb-2">True Net ROI (marketing + platform costs)</p>
          <div className="flex items-baseline gap-3 mb-1">
            <span className="text-6xl font-bold" style={{ color: roiColor }}>{trueROI.toFixed(1)}x</span>
            <span className="text-3xl">{roiEmoji(trueROI)}</span>
          </div>
          <p className="text-slate-400 text-sm">vs <strong className="text-white">20x</strong> target</p>
          {trueROI < 20 && (
            <div className="mt-3 bg-red-900/30 border border-red-800 rounded-xl p-3">
              <p className="text-red-400 text-sm">
                Gap: {formatAED((20 - trueROI) * parseFloat(roi?.total_spend_aed || '0'))} more revenue needed
              </p>
            </div>
          )}
          <div className="mt-3 pt-3 border-t border-slate-700">
            <p className="text-sm text-slate-400">Gross ROI (marketing only): <span className="text-white">{grossROI.toFixed(1)}x</span></p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 space-y-3">
          <p className="text-slate-400 text-sm">Revenue Breakdown</p>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Total Revenue</span>
            <span className="text-white font-semibold">{formatAED(parseFloat(roi?.total_revenue_aed || '0'))}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Marketing Spend</span>
            <span className="text-red-400">- {formatAED(parseFloat(roi?.total_spend_aed || '0'))}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Platform Costs</span>
            <span className="text-red-400">- {formatAED(parseFloat(roi?.platform_cost_aed || '0'))}</span>
          </div>
          <div className="flex justify-between text-sm font-semibold border-t border-slate-700 pt-2">
            <span className="text-white">Net Value</span>
            <span style={{ color: roiColor }}>{formatAED(
              parseFloat(roi?.total_revenue_aed || '0') -
              parseFloat(roi?.total_spend_aed || '0') -
              parseFloat(roi?.platform_cost_aed || '0')
            )}</span>
          </div>
        </div>
      </div>

      {/* ROI BY CHANNEL CHART */}
      {channelData.length > 0 && (
        <div className="bg-slate-800 rounded-2xl p-6">
          <h2 className="text-white font-semibold mb-4">ROI by Channel vs 20x Target</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={channelData} layout="vertical" margin={{ left: 20 }}>
              <XAxis type="number" stroke="#64748b" tickFormatter={v => `${v}x`} />
              <YAxis type="category" dataKey="channel" stroke="#64748b" width={140} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => [`${v.toFixed(1)}x ROI`, 'ROI']} contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px' }} />
              <ReferenceLine x={20} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: '20x target', fill: '#f59e0b', fontSize: 11, position: 'top' }} />
              <Bar dataKey="roi" radius={[0, 4, 4, 0]}>
                {channelData.map((entry, i) => (
                  <Cell key={i} fill={entry.roi >= 20 ? '#22c55e' : entry.roi >= 10 ? '#f59e0b' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {roi?.channels_below_20x?.length > 0 && (
            <div className="mt-3 p-3 bg-amber-900/30 border border-amber-800 rounded-xl">
              <p className="text-amber-400 text-sm">⚠️ Below 20x target: {roi.channels_below_20x.join(' · ')}</p>
            </div>
          )}
        </div>
      )}

      {/* BUDGET ENVELOPES */}
      <div className="bg-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-700">
          <h2 className="text-white font-semibold">Marketing Budget</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-xs">
              <th className="text-left p-4">Channel</th>
              <th className="text-right p-4">Allocated</th>
              <th className="text-right p-4">Spent</th>
              <th className="text-right p-4">Remaining</th>
              <th className="text-right p-4">ROI</th>
              <th className="text-right p-4">Action</th>
            </tr>
          </thead>
          <tbody>
            {envelopes.map(e => {
              const roi_val = parseFloat(e.roi_current || '0')
              const roiCol = roi_val >= 20 ? 'text-green-400' : roi_val >= 10 ? 'text-amber-400' : 'text-red-400'
              return (
                <tr key={e.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="p-4 text-white">{e.channel_label}</td>
                  <td className="p-4 text-right text-slate-300">{formatAED(parseFloat(e.allocated_amount_aed || '0'))}</td>
                  <td className="p-4 text-right text-slate-300">{formatAED(parseFloat(e.spent_amount_aed || '0'))}</td>
                  <td className="p-4 text-right text-slate-300">{formatAED(parseFloat(e.remaining_amount_aed || '0'))}</td>
                  <td className={`p-4 text-right font-semibold ${roiCol}`}>{roi_val.toFixed(1)}x</td>
                  <td className="p-4 text-right">
                    {logSpendOpen === e.id ? (
                      <div className="flex gap-2 justify-end">
                        <input type="number" placeholder="AED" value={spendAmount} onChange={ev => setSpendAmount(ev.target.value)}
                          className="w-24 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-white text-xs" />
                        <button onClick={() => logSpend(e.id)} className="text-xs bg-green-700 text-white px-2 py-1 rounded">Log</button>
                        <button onClick={() => setLogSpendOpen(null)} className="text-xs text-slate-400">✕</button>
                      </div>
                    ) : (
                      <button onClick={() => setLogSpendOpen(e.id)} className="text-xs text-slate-400 hover:text-white">Log Spend</button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* PLATFORM COSTS */}
      {platformCost && (
        <div className="bg-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-semibold">Platform Operating Costs</h2>
            <span className={`text-xs px-2 py-1 rounded-full text-white`}
              style={{ background: tierColors[platformCost.active_tier] || '#64748b' }}>
              {platformCost.active_tier?.toUpperCase()} TIER
            </span>
          </div>
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1 bg-slate-700 rounded-full h-3">
              <div className="h-full rounded-full bg-blue-500 transition-all"
                style={{ width: `${Math.min(100, (parseFloat(platformCost.actual_spend_aed) / parseFloat(platformCost.approved_ceiling_aed)) * 100)}%` }} />
            </div>
            <p className="text-sm text-white whitespace-nowrap">
              {formatAED(parseFloat(platformCost.actual_spend_aed || '0'))} / {formatAED(parseFloat(platformCost.approved_ceiling_aed || '0'))}
            </p>
          </div>
          <p className="text-sm text-slate-400">
            Platform cost as % of revenue:{' '}
            <span className={parseFloat(platformCost.platform_cost_pct || '0') < 2 ? 'text-green-400' : 'text-amber-400'}>
              {parseFloat(platformCost.platform_cost_pct || '0').toFixed(1)}%
            </span>
            <span className="text-slate-600 ml-2">(target: &lt;2%)</span>
          </p>
        </div>
      )}

      {/* CTA */}
      <div className="flex gap-3">
        <button onClick={proposeTargets}
          className="bg-orange-600 hover:bg-orange-700 text-white px-5 py-3 rounded-xl text-sm font-semibold transition-colors">
          Propose New Quarter Targets
        </button>
        <button onClick={() => fetch('/api/financial/roi', { method: 'POST' }).then(() => window.location.reload())}
          className="bg-slate-700 hover:bg-slate-600 text-white px-5 py-3 rounded-xl text-sm transition-colors">
          Refresh ROI Analysis
        </button>
      </div>

      {roi?.orchestrator_assessment && (
        <div className="bg-slate-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">Orchestrator Assessment</h3>
          <p className="text-slate-300 text-sm leading-relaxed">{roi.orchestrator_assessment}</p>
        </div>
      )}
    </div>
  )
}
```

---

## PROMPT 8.5 — Customer Care Page

```
Build src/app/care/page.tsx — Feedback inbox with AI-assisted responses.

'use client'
import { useState, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'

const URGENCY_COLORS: Record<string, string> = {
  critical: 'border-red-500 bg-red-900/20',
  urgent: 'border-amber-500 bg-amber-900/20',
  normal: 'border-slate-700 bg-slate-800',
  low: 'border-slate-800 bg-slate-800/50'
}
const URGENCY_DOT: Record<string, string> = {
  critical: 'bg-red-500', urgent: 'bg-amber-500', normal: 'bg-slate-500', low: 'bg-slate-700'
}

export default function CarePage() {
  const [feedback, setFeedback] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [urgencyFilter, setUrgencyFilter] = useState('all')
  const [responseText, setResponseText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [tab, setTab] = useState<'inbox' | 'patterns' | 'testimonials' | 'qrcodes'>('inbox')
  const [qrCodes, setQrCodes] = useState<any[]>([])
  const [testimonials, setTestimonials] = useState<any[]>([])
  const [newQrForm, setNewQrForm] = useState(false)

  useEffect(() => {
    fetch('/api/care/feedback/inbox?limit=50')
      .then(r => r.json()).then(d => setFeedback(d.data || []))
    fetch('/api/care/qrcodes').then(r => r.json()).then(d => setQrCodes(d.data || []))
    fetch('/api/care/testimonials').then(r => r.json()).then(d => setTestimonials(d.data || []))
  }, [])

  useEffect(() => {
    if (selected) setResponseText(selected.response_draft || '')
  }, [selected])

  async function submitResponse() {
    if (!selected) return
    setSubmitting(true)
    await fetch(`/api/care/feedback/${selected.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'approved', response_sent: responseText })
    })
    setFeedback(prev => prev.filter(f => f.id !== selected.id))
    setSelected(null)
    setSubmitting(false)
  }

  const filtered = urgencyFilter === 'all' ? feedback : feedback.filter(f => f.urgency === urgencyFilter)
  const criticalCount = feedback.filter(f => f.urgency === 'critical').length
  const urgentCount = feedback.filter(f => f.urgency === 'urgent').length
  const atRiskCount = feedback.filter(f => f.is_at_risk_flag).length

  return (
    <div className="flex flex-col h-full">
      {/* Header Metrics */}
      <div className="border-b border-slate-800 px-6 py-4 flex items-center gap-6">
        <h1 className="text-lg font-bold text-white">Customer Care</h1>
        <div className="flex gap-4 text-sm">
          {criticalCount > 0 && <span className="text-red-400 font-semibold">🔴 {criticalCount} critical</span>}
          {urgentCount > 0 && <span className="text-amber-400">🟡 {urgentCount} urgent</span>}
          {atRiskCount > 0 && <span className="text-orange-400">⚠️ {atRiskCount} at-risk</span>}
        </div>
        <div className="flex gap-1 ml-auto">
          {(['inbox', 'patterns', 'testimonials', 'qrcodes'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`text-sm px-3 py-1.5 rounded-lg capitalize ${tab === t ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === 'inbox' && (
        <div className="flex flex-1 overflow-hidden">
          {/* List */}
          <div className="w-80 border-r border-slate-800 overflow-y-auto">
            <div className="p-3 border-b border-slate-800">
              <select value={urgencyFilter} onChange={e => setUrgencyFilter(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-2">
                <option value="all">All urgency</option>
                <option value="critical">Critical</option>
                <option value="urgent">Urgent</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
            {filtered.map(f => (
              <button key={f.id} onClick={() => setSelected(f)}
                className={`w-full text-left p-4 border-b border-slate-800 border-l-4 hover:bg-slate-800/50 ${URGENCY_COLORS[f.urgency]} ${selected?.id === f.id ? 'bg-slate-800' : ''}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-2 h-2 rounded-full ${URGENCY_DOT[f.urgency]}`} />
                  <span className="text-xs text-slate-400 capitalize">{f.brand}</span>
                  {f.is_at_risk_flag && <span className="text-xs bg-orange-600 text-white px-1.5 rounded">AT-RISK</span>}
                </div>
                <p className="text-sm text-white font-medium truncate">{f.raw_text?.substring(0, 60)}…</p>
                <p className="text-xs text-slate-500 mt-0.5">{formatDistanceToNow(new Date(f.created_at), { addSuffix: true })}</p>
              </button>
            ))}
          </div>

          {/* Detail */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {!selected ? (
              <div className="flex-1 flex items-center justify-center text-slate-600">Select a feedback item</div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <span className={`w-3 h-3 rounded-full ${URGENCY_DOT[selected.urgency]}`} />
                    <span className="text-white font-semibold capitalize">{selected.urgency}</span>
                    <span className="text-slate-400 text-sm capitalize">{selected.feedback_type}</span>
                    {selected.is_at_risk_flag && <span className="bg-orange-600 text-white text-xs px-2 py-0.5 rounded-full">⚠️ At-Risk</span>}
                  </div>

                  <div className="bg-slate-800 rounded-xl p-4">
                    <p className="text-xs text-slate-500 mb-2">Customer feedback:</p>
                    <p className="text-slate-200 text-sm leading-relaxed">{selected.raw_text}</p>
                    {selected.rating && <p className="text-amber-400 mt-2">{'★'.repeat(selected.rating)}{'☆'.repeat(5 - selected.rating)}</p>}
                  </div>

                  {selected.complaint_categories?.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {selected.complaint_categories.map((c: string) => (
                        <span key={c} className="bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded-full">{c}</span>
                      ))}
                    </div>
                  )}

                  <div>
                    <label className="text-xs text-slate-500 block mb-2">Draft response (approve to send):</label>
                    <textarea value={responseText} onChange={e => setResponseText(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-sm text-white resize-none focus:border-orange-500 focus:outline-none"
                      rows={6} />
                  </div>
                </div>
                <div className="border-t border-slate-800 p-4 flex gap-3">
                  <button disabled={submitting} onClick={submitResponse}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold text-sm transition-colors">
                    ✅ Approve & Send
                  </button>
                  <button className="px-4 bg-slate-700 hover:bg-slate-600 text-white py-3 rounded-xl text-sm transition-colors">
                    Escalate
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {tab === 'qrcodes' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-semibold">QR Codes</h2>
            <button onClick={() => setNewQrForm(!newQrForm)}
              className="bg-orange-600 hover:bg-orange-700 text-white text-sm px-4 py-2 rounded-lg transition-colors">
              + Generate QR Code
            </button>
          </div>
          {newQrForm && (
            <NewQRCodeForm onDone={() => { setNewQrForm(false); fetch('/api/care/qrcodes').then(r => r.json()).then(d => setQrCodes(d.data || [])) }} />
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {qrCodes.map(qr => (
              <div key={qr.id} className="bg-slate-800 rounded-xl p-4">
                <p className="text-white font-medium text-sm">{qr.linked_entity_label || qr.purpose}</p>
                <p className="text-xs text-slate-400 mb-3 capitalize">{qr.brand} · {qr.purpose}</p>
                <div className="flex gap-4 text-sm">
                  <div><span className="text-slate-400">Scans:</span> <span className="text-white">{qr.scan_count}</span></div>
                  <div><span className="text-slate-400">Feedback:</span> <span className="text-white">{qr.feedback_count}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'testimonials' && (
        <div className="flex-1 overflow-y-auto p-6">
          <h2 className="text-white font-semibold mb-4">Testimonials ({testimonials.length})</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {testimonials.map(t => (
              <div key={t.id} className="bg-slate-800 rounded-xl p-5">
                <p className="text-slate-200 text-sm italic mb-3">"{t.quote_original}"</p>
                <p className="text-slate-400 text-xs">{t.customer_name} · {t.customer_type}</p>
                <div className="mt-3 flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${t.permission_to_use ? 'bg-green-900 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
                    {t.permission_to_use ? 'Permission granted' : 'Pending permission'}
                  </span>
                  {t.permission_to_use && (
                    <button className="text-xs text-orange-400 hover:text-orange-300">Send to Broadcast →</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function NewQRCodeForm({ onDone }: { onDone: () => void }) {
  const [form, setForm] = useState({ brand: 'boxedgo', purpose: 'meal_packaging', label: '' })
  async function submit() {
    await fetch('/api/care/qrcodes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand: form.brand, purpose: form.purpose, linkedEntityLabel: form.label })
    })
    onDone()
  }
  return (
    <div className="bg-slate-700 rounded-xl p-4 mb-4 space-y-3">
      <select value={form.brand} onChange={e => setForm({...form, brand: e.target.value})}
        className="w-full bg-slate-800 border border-slate-600 text-white text-sm rounded-lg px-3 py-2">
        <option value="boxedgo">Boxed & Go</option>
        <option value="mikana">Mikana</option>
      </select>
      <input placeholder="Label (e.g. 'Chicken Box — Week 14')" value={form.label}
        onChange={e => setForm({...form, label: e.target.value})}
        className="w-full bg-slate-800 border border-slate-600 text-white text-sm rounded-lg px-3 py-2" />
      <button onClick={submit} className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-lg">Generate</button>
    </div>
  )
}
```

---

## PROMPT 8.6 — Pipeline Pages

```
Build src/app/pipeline/schools/page.tsx:

'use client'
import { useState, useEffect } from 'react'
import { formatAED } from '@/lib/utils'

const STAGES = ['identified','researched','outreach_sent','meeting_booked','proposal_sent','negotiating','won','lost']
const RENEWAL_STAGES = ['upcoming','renewal_outreach','negotiating','renewed','lost_renewal']

export default function SchoolsPage() {
  const [leads, setLeads] = useState<any[]>([])
  const [view, setView] = useState<'kanban' | 'renewals'>('renewals')

  useEffect(() => {
    fetch('/api/pipeline/schools').then(r => r.json()).then(d => setLeads(d.data || []))
  }, [])

  const renewals = leads.filter(l => l.lead_type === 'renewal').sort((a, b) =>
    new Date(a.renewal_date).getTime() - new Date(b.renewal_date).getTime()
  )
  const newAcq = leads.filter(l => l.lead_type === 'new_acquisition')

  const daysUntil = (date: string) => Math.round((new Date(date).getTime() - Date.now()) / 86400000)

  const totalPipeline = leads.reduce((s, l) => s + (l.estimated_value_aed || 0), 0)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Schools Pipeline</h1>
          <p className="text-slate-400 text-sm">{formatAED(totalPipeline)} total pipeline value</p>
        </div>
        <div className="flex gap-2">
          {(['renewals', 'kanban'] as const).map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`text-sm px-3 py-2 rounded-lg capitalize ${view === v ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Renewals < 90 days', value: renewals.filter(r => daysUntil(r.renewal_date) < 90).length, color: 'text-amber-400' },
          { label: 'Renewals < 30 days', value: renewals.filter(r => daysUntil(r.renewal_date) < 30).length, color: 'text-red-400' },
          { label: 'New acquisition', value: newAcq.length, color: 'text-white' },
          { label: 'Won this quarter', value: leads.filter(l => l.stage === 'won').length, color: 'text-green-400' },
        ].map(s => (
          <div key={s.label} className="bg-slate-800 rounded-xl p-4">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-slate-400 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {view === 'renewals' ? (
        <div className="bg-slate-800 rounded-2xl overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-white font-semibold">Contract Renewals — Sorted by Urgency</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 text-xs">
                <th className="text-left p-4">School</th>
                <th className="text-left p-4">Days to Renewal</th>
                <th className="text-right p-4">Contract Value</th>
                <th className="text-left p-4">Stage</th>
                <th className="text-right p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {renewals.map(r => {
                const days = daysUntil(r.renewal_date)
                const urgencyColor = days < 30 ? 'text-red-400' : days < 90 ? 'text-amber-400' : 'text-green-400'
                return (
                  <tr key={r.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="p-4 text-white font-medium">{r.school_name || r.school_id}</td>
                    <td className={`p-4 font-semibold ${urgencyColor}`}>{days} days</td>
                    <td className="p-4 text-right text-slate-300">{formatAED(r.estimated_value_aed || 0)}</td>
                    <td className="p-4">
                      <span className="bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded-full capitalize">
                        {r.stage?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => fetch(`/api/pipeline/schools/${r.id}/generate-outreach`, { method: 'POST' })}
                        className="text-xs bg-orange-600 hover:bg-orange-700 text-white px-3 py-1.5 rounded-lg transition-colors">
                        Generate Renewal
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="flex gap-3 min-w-max">
            {STAGES.map(stage => {
              const stageLeads = newAcq.filter(l => l.stage === stage)
              return (
                <div key={stage} className="w-56">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400 uppercase tracking-wider">{stage.replace(/_/g, ' ')}</p>
                    <span className="text-xs bg-slate-700 text-slate-400 px-1.5 rounded">{stageLeads.length}</span>
                  </div>
                  <div className="space-y-2">
                    {stageLeads.map(l => (
                      <div key={l.id} className="bg-slate-800 rounded-xl p-3 border border-slate-700">
                        <p className="text-white text-sm font-medium truncate">{l.school_name || 'School'}</p>
                        <p className="text-slate-400 text-xs">{formatAED(l.estimated_value_aed || 0)}</p>
                        <div className="mt-2">
                          <span className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">
                            Score: {l.qualification_score || '—'}
                          </span>
                        </div>
                      </div>
                    ))}
                    {stageLeads.length === 0 && (
                      <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 border-dashed text-center">
                        <p className="text-slate-700 text-xs">Empty</p>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build src/app/pipeline/boxedgo/page.tsx:

'use client'
import { useState, useEffect } from 'react'
import { formatAED } from '@/lib/utils'

const STAGES = ['awareness','interest','trial_offered','trial_active','subscribed','paused','churned']
const STAGE_COLORS: Record<string, string> = {
  awareness: 'bg-slate-700', interest: 'bg-blue-900', trial_offered: 'bg-amber-900',
  trial_active: 'bg-amber-700', subscribed: 'bg-green-800', paused: 'bg-slate-600', churned: 'bg-red-900'
}

export default function BoxedGoPage() {
  const [subscribers, setSubscribers] = useState<any[]>([])

  useEffect(() => {
    fetch('/api/pipeline/boxedgo').then(r => r.json()).then(d => setSubscribers(d.data || []))
  }, [])

  const byStage = STAGES.reduce((acc, s) => {
    acc[s] = subscribers.filter(sub => sub.stage === s)
    return acc
  }, {} as Record<string, any[]>)

  const subscribed = byStage['subscribed'] || []
  const avgPlanValue = 1150
  const mrr = subscribed.length * avgPlanValue
  const atRisk = subscribers.filter(s => s.is_at_risk_flag)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Boxed & Go</h1>
          <p className="text-slate-400 text-sm">Subscriber Funnel</p>
        </div>
      </div>

      {/* MRR + Funnel stats */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Active MRR', value: formatAED(mrr), sub: `${subscribed.length} subscribers` },
          { label: 'In Trial', value: byStage['trial_active']?.length || 0, sub: 'converting' },
          { label: 'Interested', value: byStage['interest']?.length || 0, sub: 'nurturing' },
          { label: 'Churned MTD', value: byStage['churned']?.length || 0, sub: 'review reasons' },
          { label: 'At-Risk', value: atRisk.length, sub: atRisk.length > 0 ? '⚠️ needs attention' : 'all clear' },
        ].map(s => (
          <div key={s.label} className="bg-slate-800 rounded-xl p-4">
            <p className="text-xl font-bold text-white">{s.value}</p>
            <p className="text-slate-400 text-xs mt-1">{s.label}</p>
            <p className="text-slate-600 text-xs">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Funnel visualisation */}
      <div className="bg-slate-800 rounded-2xl p-6">
        <h2 className="text-white font-semibold mb-4">Subscriber Funnel</h2>
        <div className="space-y-2">
          {STAGES.map(stage => {
            const count = byStage[stage]?.length || 0
            const maxCount = Math.max(...STAGES.map(s => byStage[s]?.length || 0), 1)
            const pct = (count / maxCount) * 100
            return (
              <div key={stage} className="flex items-center gap-3">
                <span className="text-slate-400 text-xs w-24 capitalize">{stage.replace(/_/g, ' ')}</span>
                <div className="flex-1 bg-slate-900 rounded-full h-6 overflow-hidden">
                  <div className={`h-full ${STAGE_COLORS[stage]} flex items-center justify-end pr-2 transition-all`}
                    style={{ width: `${Math.max(pct, 5)}%` }}>
                    <span className="text-white text-xs font-semibold">{count}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

---

## PROMPT 8.7 — Broadcast Page

```
Build src/app/broadcast/page.tsx — Content Studio with brand-split design.

'use client'
import { useState, useEffect } from 'react'

const MIKANA_PILLARS = ['Thought Leadership', 'Operational Excellence', 'Industry Insight', 'Social Proof', 'School Season']
const BOXEDGO_PILLARS = ['Product Showcase', 'Behind the Scenes', 'Customer Reality', 'Seasonal/Cultural', 'Education']
const PLATFORMS = { mikana: ['linkedin'], boxedgo: ['instagram', 'instagram_story', 'instagram_reel'] }

export default function BroadcastPage() {
  const [activeBrand, setActiveBrand] = useState<'mikana' | 'boxedgo'>('boxedgo')
  const [pillar, setPillar] = useState('')
  const [topic, setTopic] = useState('')
  const [platform, setPlatform] = useState('instagram')
  const [generating, setGenerating] = useState(false)
  const [preview, setPreview] = useState<any>(null)
  const [queue, setQueue] = useState<any[]>([])

  useEffect(() => {
    fetch('/api/broadcast/schedule?status=pending_approval,approved,scheduled&limit=20')
      .then(r => r.json()).then(d => setQueue(d.data || []))
  }, [])

  async function generate() {
    setGenerating(true)
    const res = await fetch('/api/broadcast/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand: activeBrand, platform, contentType: pillar, topic })
    })
    const data = await res.json()
    setPreview(data.post)
    setGenerating(false)
  }

  async function generateWeeklyBatch() {
    await fetch('/api/cron/weekly-batch', {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${process.env.NEXT_PUBLIC_CRON_SECRET || ''}` }
    })
    alert('Weekly content batch generating — check approvals inbox shortly.')
  }

  const pillars = activeBrand === 'mikana' ? MIKANA_PILLARS : BOXEDGO_PILLARS
  const brandColor = activeBrand === 'mikana' ? '#E8490F' : '#c2714f'

  return (
    <div className="h-full flex flex-col">
      {/* Brand Switcher */}
      <div className="flex border-b border-slate-800">
        <button onClick={() => { setActiveBrand('mikana'); setPlatform('linkedin'); setPreview(null) }}
          className={`flex-1 py-4 text-sm font-semibold transition-colors ${activeBrand === 'mikana' ? 'text-white border-b-2' : 'text-slate-400'}`}
          style={activeBrand === 'mikana' ? { borderColor: '#E8490F' } : {}}>
          Mikana Food Service — LinkedIn
        </button>
        <button onClick={() => { setActiveBrand('boxedgo'); setPlatform('instagram'); setPreview(null) }}
          className={`flex-1 py-4 text-sm font-semibold transition-colors ${activeBrand === 'boxedgo' ? 'text-white border-b-2' : 'text-slate-400'}`}
          style={activeBrand === 'boxedgo' ? { borderColor: '#c2714f' } : {}}>
          Boxed & Go — Instagram
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Generator panel */}
        <div className="w-80 border-r border-slate-800 p-5 space-y-4 overflow-y-auto">
          <h2 className="text-white font-semibold text-sm">Generate Content</h2>

          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Platform</label>
            <select value={platform} onChange={e => setPlatform(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-2">
              {PLATFORMS[activeBrand].map(p => (
                <option key={p} value={p}>{p.replace(/_/g, ' ').toUpperCase()}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Content Pillar</label>
            <div className="space-y-1">
              {pillars.map(p => (
                <button key={p} onClick={() => setPillar(p)}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors ${pillar === p ? 'text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
                  style={pillar === p ? { background: brandColor + '33', border: `1px solid ${brandColor}` } : {}}>
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Topic (optional)</label>
            <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Specific angle or hook…"
              className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-2 focus:border-orange-500 focus:outline-none" />
          </div>

          <button onClick={generate} disabled={generating || !pillar}
            className="w-full py-3 rounded-xl font-semibold text-sm text-white disabled:opacity-50 transition-colors"
            style={{ background: brandColor }}>
            {generating ? 'Generating…' : 'Generate Post'}
          </button>

          <button onClick={generateWeeklyBatch}
            className="w-full py-3 rounded-xl font-semibold text-sm text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors">
            Auto-fill Week (batch)
          </button>
        </div>

        {/* Preview */}
        <div className="flex-1 overflow-y-auto p-6">
          {preview ? (
            <div className="max-w-lg mx-auto space-y-4">
              <div className="bg-slate-800 rounded-2xl p-5 border border-slate-700">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                    style={{ background: brandColor }}>
                    {activeBrand === 'mikana' ? 'M' : 'B'}
                  </div>
                  <div>
                    <p className="text-white text-sm font-medium">{activeBrand === 'mikana' ? 'Mikana Food Service' : 'Boxed & Go'}</p>
                    <p className="text-slate-500 text-xs capitalize">{platform.replace(/_/g, ' ')}</p>
                  </div>
                </div>
                {preview.image_prompt && (
                  <div className="bg-slate-700 rounded-xl p-3 mb-3 text-xs text-slate-400 italic">
                    📷 Image prompt: {preview.image_prompt}
                  </div>
                )}
                <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">{preview.caption}</p>
                {preview.caption_arabic && (
                  <p className="text-slate-400 text-sm leading-relaxed mt-3 pt-3 border-t border-slate-700 text-right" dir="rtl">
                    {preview.caption_arabic}
                  </p>
                )}
                {preview.hashtags?.length > 0 && (
                  <p className="text-blue-400 text-xs mt-3">{preview.hashtags.map((h: string) => `#${h}`).join(' ')}</p>
                )}
              </div>
              <div className="flex gap-3">
                <button className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2.5 rounded-xl text-sm font-semibold">
                  Send for Approval
                </button>
                <button onClick={generate} className="px-4 bg-slate-700 hover:bg-slate-600 text-white py-2.5 rounded-xl text-sm">
                  Regenerate
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-600">
              <div className="text-center">
                <p className="text-4xl mb-3">📡</p>
                <p>Select a pillar and generate content</p>
              </div>
            </div>
          )}
        </div>

        {/* Publish Queue */}
        <div className="w-72 border-l border-slate-800 overflow-y-auto">
          <div className="p-4 border-b border-slate-700">
            <h3 className="text-white font-semibold text-sm">Publish Queue ({queue.length})</h3>
          </div>
          {queue.map(post => (
            <div key={post.id} className="p-4 border-b border-slate-800">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-1.5 py-0.5 rounded text-white ${post.brand === 'mikana' ? 'bg-orange-600' : 'bg-amber-700'}`}>
                  {post.brand === 'mikana' ? 'M' : 'B&G'}
                </span>
                <span className="text-xs text-slate-500 capitalize">{post.platform}</span>
                <span className={`ml-auto text-xs ${post.status === 'pending_approval' ? 'text-amber-400' : post.status === 'published' ? 'text-green-400' : 'text-slate-400'}`}>
                  {post.status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-slate-300 text-xs line-clamp-2">{post.caption?.substring(0, 80)}…</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

---

## PROMPT 8.8 — Public Feedback Form

```
Build src/app/feedback/page.tsx — PUBLIC, no authentication required.

Add to next.config.js:
module.exports = {
  async headers() {
    return [{ source: '/feedback', headers: [{ key: 'Cache-Control', value: 'no-store' }] }]
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

function FeedbackFormInner() {
  const params = useSearchParams()
  const code = params.get('code')
  const brandParam = params.get('brand')

  const [brand, setBrand] = useState(brandParam || 'boxedgo')
  const [qrData, setQrData] = useState<any>(null)
  const [rating, setRating] = useState(0)
  const [hoverRating, setHoverRating] = useState(0)
  const [text, setText] = useState('')
  const [name, setName] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (code) {
      fetch(`/api/care/qrcodes?code=${code}`)
        .then(r => r.json())
        .then(d => {
          if (d.data) {
            setQrData(d.data)
            setBrand(d.data.brand)
          }
        })
    }
  }, [code])

  async function submit() {
    if (!rating || !text.trim()) return
    setSubmitting(true)
    await fetch('/api/care/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brand, rating, raw_text: text, customer_name: name || null,
        customer_whatsapp: whatsapp || null,
        qr_code_id: code || null, channel: code ? 'qr_code' : 'website_form'
      })
    })
    setDone(true)
    setSubmitting(false)
  }

  const isMikana = brand === 'mikana'
  const primaryColor = isMikana ? '#E8490F' : '#c2714f'
  const bgGradient = isMikana
    ? 'bg-gradient-to-br from-slate-950 via-slate-900 to-orange-950'
    : 'bg-gradient-to-br from-slate-950 via-slate-900 to-amber-950'

  if (done) return (
    <div className={`min-h-screen ${bgGradient} flex items-center justify-center p-4`}>
      <div className="max-w-sm w-full text-center space-y-4">
        <div className="text-5xl">{'★'.repeat(rating)}</div>
        <h2 className="text-2xl font-bold text-white">
          {rating === 5 ? 'Thank you! 🎉' : 'Thank you for the honest feedback'}
        </h2>
        <p className="text-slate-300 text-sm">
          {isMikana
            ? 'A member of our team will be in touch within 24 hours.'
            : 'We read every message. Expect to hear from us within 24 hours.'}
        </p>
        {rating === 5 && (
          <div className="mt-4 space-y-2">
            <p className="text-slate-400 text-sm">Share with others?</p>
            <button className="w-full py-3 rounded-xl text-white text-sm font-semibold"
              style={{ background: primaryColor }}>
              Share on WhatsApp
            </button>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className={`min-h-screen ${bgGradient} flex items-center justify-center p-4`}>
      <div className="max-w-sm w-full space-y-6">
        {/* Brand header */}
        <div className="text-center">
          <div className="w-12 h-12 rounded-2xl mx-auto mb-3 flex items-center justify-center text-white font-bold text-xl"
            style={{ background: primaryColor }}>
            {isMikana ? 'M' : 'B'}
          </div>
          <h1 className="text-xl font-bold text-white">
            {isMikana ? 'Mikana Food Service' : 'Boxed & Go'}
          </h1>
          {qrData?.linked_entity_label && (
            <p className="text-slate-400 text-sm mt-1">{qrData.linked_entity_label}</p>
          )}
        </div>

        {/* Star rating */}
        <div className="text-center">
          <p className="text-slate-400 text-sm mb-3">
            {isMikana ? 'How was your experience?' : 'How was your meal?'}
          </p>
          <div className="flex justify-center gap-2">
            {[1,2,3,4,5].map(s => (
              <button key={s}
                onMouseEnter={() => setHoverRating(s)}
                onMouseLeave={() => setHoverRating(0)}
                onClick={() => setRating(s)}
                className="text-4xl transition-transform hover:scale-110">
                <span style={{ color: s <= (hoverRating || rating) ? '#f59e0b' : '#334155' }}>★</span>
              </button>
            ))}
          </div>
          {rating > 0 && (
            <p className="text-slate-400 text-xs mt-2">
              {['', 'Needs improvement', 'Below expectations', 'Acceptable', 'Good', 'Excellent!'][rating]}
            </p>
          )}
        </div>

        {/* Text feedback */}
        <div>
          <textarea value={text} onChange={e => setText(e.target.value)}
            placeholder={isMikana
              ? 'Tell us about your experience — honestly. We use every piece of feedback to improve.'
              : 'Tell us honestly. What was great? What can we improve?'}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white text-sm resize-none focus:outline-none"
            style={{ '--tw-ring-color': primaryColor } as any}
            rows={4} />
        </div>

        {/* Optional name/contact */}
        <div className="space-y-3">
          <input value={name} onChange={e => setName(e.target.value)}
            placeholder="Your name (optional)"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none" />
          <input value={whatsapp} onChange={e => setWhatsapp(e.target.value)}
            placeholder="WhatsApp number (optional — to follow up)"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none" />
        </div>

        <button onClick={submit} disabled={!rating || !text.trim() || submitting}
          className="w-full py-4 rounded-xl text-white font-bold text-sm disabled:opacity-50 transition-all"
          style={{ background: primaryColor }}>
          {submitting ? 'Sending…' : 'Send Feedback'}
        </button>

        <p className="text-center text-slate-600 text-xs">Your feedback goes directly to our team.</p>
      </div>
    </div>
  )
}

export default function FeedbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <FeedbackFormInner />
    </Suspense>
  )
}
```
# PHASE 8 CONTINUED — REMAINING UI PAGES

---

## PROMPT 8.9 — Root Redirect + Activity Log + Scout + SEO Pages

```
Create src/app/page.tsx — root redirect:
import { redirect } from 'next/navigation'
export default function Home() { redirect('/briefing') }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build src/app/activity/page.tsx — Agent Activity Log:

'use client'
import { useState, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'

const AGENT_EMOJI: Record<string, string> = {
  scout: '🔍', pipeline: '📋', broadcast: '📡',
  seo_engine: '🔎', customer_care: '💬', orchestrator: '🧠'
}
const RESULT_COLORS: Record<string, string> = {
  queued_for_approval: 'text-amber-400',
  executed: 'text-green-400',
  skipped: 'text-slate-400',
  failed: 'text-red-400'
}

export default function ActivityPage() {
  const [activities, setActivities] = useState<any[]>([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const url = filter === 'all'
      ? '/api/activity?limit=100'
      : `/api/activity?agent=${filter}&limit=100`
    fetch(url).then(r => r.json()).then(d => {
      setActivities(d.data || [])
      setLoading(false)
    })
  }, [filter])

  const agents = ['all', 'scout', 'pipeline', 'broadcast', 'seo_engine', 'customer_care', 'orchestrator']

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Agent Activity Log</h1>
        <div className="flex gap-1 flex-wrap">
          {agents.map(a => (
            <button key={a} onClick={() => setFilter(a)}
              className={`text-xs px-3 py-1.5 rounded-lg capitalize ${filter === a ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
              {a === 'all' ? 'All' : (AGENT_EMOJI[a] || '') + ' ' + a.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Loading…</div>
      ) : (
        <div className="space-y-1">
          {activities.length === 0 && (
            <div className="text-center py-12 text-slate-600">No activity yet</div>
          )}
          {activities.map(a => (
            <div key={a.id} className="bg-slate-800/50 hover:bg-slate-800 rounded-xl px-4 py-3 flex items-start gap-3 transition-colors">
              <span className="text-lg shrink-0 mt-0.5">{AGENT_EMOJI[a.agent] || '🤖'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-slate-300 text-sm font-medium">{a.action}</span>
                  <span className={`text-xs ${RESULT_COLORS[a.result] || 'text-slate-500'}`}>
                    {a.result?.replace(/_/g, ' ')}
                  </span>
                  {a.brand && (
                    <span className={`text-xs px-1.5 py-0.5 rounded text-white ${a.brand === 'mikana' ? 'bg-orange-700' : 'bg-amber-700'}`}>
                      {a.brand === 'mikana' ? 'M' : 'B&G'}
                    </span>
                  )}
                </div>
                {a.detail && <p className="text-slate-500 text-xs mt-0.5 truncate">{a.detail}</p>}
                {a.error_message && <p className="text-red-400 text-xs mt-0.5">{a.error_message}</p>}
              </div>
              <span className="text-slate-600 text-xs shrink-0">
                {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

Also create src/app/api/activity/route.ts:
import { db } from '@/lib/db'
import { cateros_agent_activity } from '@/lib/schema'
import { eq, desc } from 'drizzle-orm'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const agent = searchParams.get('agent')
  const limit = parseInt(searchParams.get('limit') || '50')

  const where = agent ? eq(cateros_agent_activity.agent, agent) : undefined
  const data = await db.query.cateros_agent_activity.findMany({
    where, orderBy: [desc(cateros_agent_activity.created_at)], limit
  })
  return Response.json({ data })
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build src/app/scout/page.tsx — Scout Intelligence Dashboard:

'use client'
import { useState, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { formatAED } from '@/lib/utils'

export default function ScoutPage() {
  const [intelligence, setIntelligence] = useState<any[]>([])
  const [schools, setSchools] = useState<any[]>([])
  const [companies, setCompanies] = useState<any[]>([])
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState<'intel' | 'schools' | 'companies'>('intel')

  useEffect(() => {
    Promise.all([
      fetch('/api/scout/intelligence?limit=30').then(r => r.json()),
      fetch('/api/pipeline/schools?unscored=true&limit=20').then(r => r.json()),
      fetch('/api/pipeline/corporate?unscored=true&limit=20').then(r => r.json()),
    ]).then(([intel, sch, comp]) => {
      setIntelligence(intel.data || [])
      setSchools(sch.data || [])
      setCompanies(comp.data || [])
    })
  }, [])

  async function runScout() {
    setRunning(true)
    await fetch('/api/scout/run', { method: 'POST' })
    setRunning(false)
    alert('Scout cycle complete — check approvals inbox for new leads.')
  }

  const urgencyColor: Record<string, string> = {
    urgent: 'text-red-400', normal: 'text-slate-300', low: 'text-slate-500'
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">🔍 Scout</h1>
          <p className="text-slate-400 text-sm">Market intelligence · Lead discovery · Renewal radar</p>
        </div>
        <button onClick={runScout} disabled={running}
          className="bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors">
          {running ? 'Scanning…' : 'Run Scout Now'}
        </button>
      </div>

      <div className="flex gap-1">
        {(['intel', 'schools', 'companies'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`text-sm px-4 py-2 rounded-lg capitalize ${tab === t ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
            {t === 'intel' ? '📊 Intelligence' : t === 'schools' ? `🏫 Schools (${schools.length})` : `🏢 Companies (${companies.length})`}
          </button>
        ))}
      </div>

      {tab === 'intel' && (
        <div className="space-y-3">
          {intelligence.length === 0 && (
            <div className="text-center py-12 text-slate-600">
              <p className="text-4xl mb-3">🔍</p>
              <p>No intelligence yet. Run Scout to start gathering.</p>
            </div>
          )}
          {intelligence.map(item => (
            <div key={item.id} className="bg-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <span className={`text-sm font-semibold ${urgencyColor[item.urgency] || 'text-white'}`}>
                    {item.urgency === 'urgent' ? '🚨 ' : ''}{item.title}
                  </span>
                </div>
                <span className="text-xs text-slate-500 shrink-0">
                  {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                </span>
              </div>
              <p className="text-slate-400 text-sm leading-relaxed">{item.summary}</p>
              {item.action_recommended && (
                <p className="text-orange-400 text-xs mt-2">→ {item.action_recommended}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'schools' && (
        <div className="space-y-3">
          {schools.map(s => (
            <div key={s.id} className="bg-slate-800 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="text-white font-medium">{s.name}</p>
                <p className="text-slate-400 text-sm">{s.emirate} · {s.curriculum} · {s.student_count?.toLocaleString()} students</p>
              </div>
              <div className="text-right">
                <p className="text-white font-semibold">{formatAED((s.total_daily_covers || 0) * 16 * 180)}/yr</p>
                <span className={`text-xs ${s.qualification_score >= 8 ? 'text-green-400' : 'text-slate-400'}`}>
                  Score: {s.qualification_score}/10
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'companies' && (
        <div className="space-y-3">
          {companies.map(c => (
            <div key={c.id} className="bg-slate-800 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="text-white font-medium">{c.name}</p>
                <p className="text-slate-400 text-sm">{c.city} · {c.industry?.replace(/_/g, ' ')} · {c.employee_count_estimate?.toLocaleString()} employees</p>
              </div>
              <div className="text-right">
                <p className="text-white font-semibold">{formatAED(c.annual_value_estimate_aed || 0)}/yr</p>
                <span className={`text-xs ${c.qualification_score >= 8 ? 'text-green-400' : 'text-slate-400'}`}>
                  Score: {c.qualification_score}/10
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

Also create src/app/api/scout/intelligence/route.ts:
import { db } from '@/lib/db'
import { cateros_intelligence } from '@/lib/schema'
import { desc } from 'drizzle-orm'
export const dynamic = 'force-dynamic'
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') || '20')
  const data = await db.query.cateros_intelligence.findMany({
    orderBy: [desc(cateros_intelligence.created_at)], limit
  })
  return Response.json({ data })
}

Also create src/app/api/scout/run/route.ts:
import { runMorningScoutCycle } from '@/agents/scout'
export const dynamic = 'force-dynamic'
export async function POST() {
  const report = await runMorningScoutCycle()
  return Response.json({ success: true, report })
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build src/app/seo/page.tsx — SEO Engine Dashboard:

'use client'
import { useState, useEffect } from 'react'

export default function SEOPage() {
  const [articles, setArticles] = useState<any[]>([])
  const [brand, setBrand] = useState('both')
  const [generating, setGenerating] = useState(false)
  const [form, setForm] = useState({ brand: 'mikana', keyword: '', audience: '' })

  useEffect(() => {
    const url = brand === 'both' ? '/api/seo/content?limit=50' : `/api/seo/content?brand=${brand}&limit=50`
    fetch(url).then(r => r.json()).then(d => setArticles(d.data || []))
  }, [brand])

  async function generate() {
    if (!form.keyword) return
    setGenerating(true)
    await fetch('/api/seo/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form)
    })
    setGenerating(false)
    alert('Article generating — check approvals inbox shortly.')
  }

  async function runWeeklyBatch() {
    setGenerating(true)
    await fetch('/api/cron/weekly-batch', { method: 'GET', headers: { 'Authorization': `Bearer ${process.env.NEXT_PUBLIC_CRON_SECRET || ''}` } })
    setGenerating(false)
    alert('Weekly SEO batch triggered — 4 articles queued for approval.')
  }

  const statusColor: Record<string, string> = {
    pending_approval: 'text-amber-400',
    approved: 'text-blue-400',
    published: 'text-green-400',
    rejected: 'text-red-400'
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">🔎 SEO Engine</h1>
          <p className="text-slate-400 text-sm">Near-zero CAC inbound channel · Highest long-term ROI</p>
        </div>
        <button onClick={runWeeklyBatch} disabled={generating}
          className="bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors">
          Run Weekly Batch (4 articles)
        </button>
      </div>

      {/* Generator */}
      <div className="bg-slate-800 rounded-2xl p-5">
        <h2 className="text-white font-semibold mb-4">Generate Single Article</h2>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Brand</label>
            <select value={form.brand} onChange={e => setForm({...form, brand: e.target.value})}
              className="w-full bg-slate-700 border border-slate-600 text-white text-sm rounded-lg px-3 py-2">
              <option value="mikana">Mikana Food Service</option>
              <option value="boxedgo">Boxed & Go</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Primary Keyword</label>
            <input value={form.keyword} onChange={e => setForm({...form, keyword: e.target.value})}
              placeholder="e.g. school catering UAE"
              className="w-full bg-slate-700 border border-slate-600 text-white text-sm rounded-lg px-3 py-2 focus:border-orange-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Target Audience</label>
            <input value={form.audience} onChange={e => setForm({...form, audience: e.target.value})}
              placeholder="e.g. school principals UAE"
              className="w-full bg-slate-700 border border-slate-600 text-white text-sm rounded-lg px-3 py-2 focus:border-orange-500 focus:outline-none" />
          </div>
        </div>
        <button onClick={generate} disabled={generating || !form.keyword}
          className="mt-3 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm transition-colors">
          {generating ? 'Generating…' : 'Generate Article'}
        </button>
      </div>

      {/* Filter + Article list */}
      <div className="flex gap-2 items-center">
        <span className="text-slate-400 text-sm">Filter:</span>
        {['both', 'mikana', 'boxedgo'].map(b => (
          <button key={b} onClick={() => setBrand(b)}
            className={`text-sm px-3 py-1.5 rounded-lg capitalize ${brand === b ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
            {b === 'both' ? 'All' : b === 'mikana' ? 'Mikana' : 'Boxed & Go'}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {articles.length === 0 && (
          <div className="text-center py-12 text-slate-600">
            <p className="text-4xl mb-3">📝</p>
            <p>No articles yet. Generate one above or run the weekly batch.</p>
          </div>
        )}
        {articles.map(a => (
          <div key={a.id} className="bg-slate-800 rounded-xl p-5 flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-1.5 py-0.5 rounded text-white ${a.brand === 'mikana' ? 'bg-orange-700' : 'bg-amber-700'}`}>
                  {a.brand === 'mikana' ? 'Mikana' : 'B&G'}
                </span>
                <span className={`text-xs ${statusColor[a.status] || 'text-slate-400'}`}>
                  {a.status?.replace(/_/g, ' ')}
                </span>
                {a.seo_score && (
                  <span className={`text-xs font-semibold ${a.seo_score >= 70 ? 'text-green-400' : a.seo_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                    SEO: {a.seo_score}/100
                  </span>
                )}
              </div>
              <p className="text-white font-medium">{a.title || 'Untitled'}</p>
              <p className="text-slate-400 text-sm mt-0.5 truncate">{a.meta_description}</p>
              <p className="text-slate-600 text-xs mt-1">{a.word_count} words · /{a.slug}</p>
            </div>
            <div className="flex gap-2 shrink-0">
              {a.status === 'pending_approval' && (
                <button className="text-xs bg-green-700 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg">
                  Review
                </button>
              )}
              {a.status === 'approved' && (
                <button className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg">
                  Publish
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## PROMPT 8.10 — Corporate Pipeline Page + Settings Page

```
Build src/app/pipeline/corporate/page.tsx:

'use client'
import { useState, useEffect } from 'react'
import { formatAED } from '@/lib/utils'

const STAGES = [
  'pending_approval', 'discovered', 'researched', 'outreach_sent',
  'meeting_booked', 'proposal_sent', 'negotiating', 'won', 'lost'
]

export default function CorporatePage() {
  const [leads, setLeads] = useState<any[]>([])
  const [selectedLead, setSelectedLead] = useState<any>(null)

  useEffect(() => {
    fetch('/api/pipeline/corporate').then(r => r.json()).then(d => setLeads(d.data || []))
  }, [])

  const totalPipeline = leads.filter(l => !['won','lost'].includes(l.stage))
    .reduce((s, l) => s + (l.estimated_value_aed || 0), 0)
  const wonValue = leads.filter(l => l.stage === 'won')
    .reduce((s, l) => s + (l.final_contract_value_aed || l.estimated_value_aed || 0), 0)

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Corporate Pipeline</h1>
          <p className="text-slate-400 text-sm">Free zones · Corporate campuses · Future: healthcare + construction</p>
        </div>
        <button onClick={() => fetch('/api/scout/run', { method: 'POST' })}
          className="bg-orange-600 hover:bg-orange-700 text-white text-sm px-4 py-2 rounded-xl transition-colors">
          Scout New Targets
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Active Pipeline', value: formatAED(totalPipeline), color: 'text-white' },
          { label: 'Won This Quarter', value: formatAED(wonValue), color: 'text-green-400' },
          { label: 'In Negotiation', value: leads.filter(l => l.stage === 'negotiating').length, color: 'text-amber-400' },
          { label: 'Pending Approval', value: leads.filter(l => l.stage === 'pending_approval').length, color: 'text-orange-400' },
        ].map(s => (
          <div key={s.label} className="bg-slate-800 rounded-xl p-4">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-slate-400 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Kanban */}
      <div className="overflow-x-auto pb-4">
        <div className="flex gap-3 min-w-max">
          {STAGES.map(stage => {
            const stageLeads = leads.filter(l => l.stage === stage)
            const stageValue = stageLeads.reduce((s, l) => s + (l.estimated_value_aed || 0), 0)
            return (
              <div key={stage} className="w-56 shrink-0">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-slate-400 uppercase tracking-wider truncate">
                    {stage.replace(/_/g, ' ')}
                  </p>
                  <span className="text-xs bg-slate-700 text-slate-400 px-1.5 rounded ml-1">
                    {stageLeads.length}
                  </span>
                </div>
                {stageValue > 0 && (
                  <p className="text-xs text-slate-500 mb-2">{formatAED(stageValue)}</p>
                )}
                <div className="space-y-2">
                  {stageLeads.map(l => (
                    <button key={l.id} onClick={() => setSelectedLead(l === selectedLead ? null : l)}
                      className={`w-full text-left bg-slate-800 hover:bg-slate-700 rounded-xl p-3 border transition-colors ${selectedLead?.id === l.id ? 'border-orange-500' : 'border-slate-700'}`}>
                      <p className="text-white text-sm font-medium truncate">{l.company_name || l.company_id}</p>
                      <p className="text-slate-400 text-xs">{formatAED(l.estimated_value_aed || 0)}/yr</p>
                      <p className="text-slate-500 text-xs">{l.meals_per_day_estimate?.toLocaleString()} meals/day</p>
                    </button>
                  ))}
                  {stageLeads.length === 0 && (
                    <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 border-dashed text-center">
                      <p className="text-slate-700 text-xs">Empty</p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Lead detail slide-over */}
      {selectedLead && (
        <div className="fixed inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-800 p-6 overflow-y-auto shadow-2xl z-50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-bold">{selectedLead.company_name || 'Company'}</h2>
            <button onClick={() => setSelectedLead(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          <div className="space-y-4">
            <div className="bg-slate-800 rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">Stage</span><span className="text-white capitalize">{selectedLead.stage?.replace(/_/g, ' ')}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Est. Value</span><span className="text-white font-semibold">{formatAED(selectedLead.estimated_value_aed || 0)}/yr</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Meals/day</span><span className="text-white">{selectedLead.meals_per_day_estimate?.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Priority</span><span className="text-white capitalize">{selectedLead.priority}</span></div>
            </div>
            {selectedLead.next_action && (
              <div className="bg-slate-800 rounded-xl p-4">
                <p className="text-slate-400 text-xs mb-1">Next Action</p>
                <p className="text-white text-sm">{selectedLead.next_action}</p>
                {selectedLead.next_action_date && (
                  <p className="text-slate-500 text-xs mt-1">{selectedLead.next_action_date}</p>
                )}
              </div>
            )}
            <button
              onClick={() => fetch(`/api/pipeline/corporate/${selectedLead.id}/generate-outreach`, { method: 'POST' })}
              className="w-full bg-orange-600 hover:bg-orange-700 text-white py-3 rounded-xl text-sm font-semibold transition-colors">
              Generate Outreach Sequence
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build src/app/settings/page.tsx — placeholder with environment status:

'use client'
import { useState, useEffect } from 'react'

export default function SettingsPage() {
  const [health, setHealth] = useState<any>(null)

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(setHealth)
  }, [])

  const ENV_CHECKS = [
    { key: 'WhatsApp API', env: 'WHATSAPP_PHONE_NUMBER_ID' },
    { key: 'Instagram / Meta', env: 'META_INSTAGRAM_ACCOUNT_ID' },
    { key: 'LinkedIn', env: 'LINKEDIN_ORGANIZATION_ID' },
    { key: 'SerpAPI', env: 'SERPAPI_KEY' },
    { key: 'Apify', env: 'APIFY_API_TOKEN' },
    { key: 'Resend Email', env: 'RESEND_API_KEY' },
  ]

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 text-sm">System status and configuration</p>
      </div>

      {/* System Health */}
      {health && (
        <div className="bg-slate-800 rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-4">System Status</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex justify-between"><span className="text-slate-400">Version</span><span className="text-white">{health.version}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">ROI Target</span><span className="text-green-400 font-bold">{health.roiTarget}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Pending Approvals</span><span className={health.pendingApprovals > 0 ? 'text-amber-400' : 'text-green-400'}>{health.pendingApprovals}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Agents</span><span className="text-white">{health.agents?.length}</span></div>
          </div>
        </div>
      )}

      {/* Integration Status */}
      <div className="bg-slate-800 rounded-2xl p-5">
        <h2 className="text-white font-semibold mb-4">Integrations</h2>
        <p className="text-slate-500 text-xs mb-4">
          Set these in Vercel → Settings → Environment Variables
        </p>
        <div className="space-y-2">
          {ENV_CHECKS.map(({ key }) => (
            <div key={key} className="flex items-center justify-between py-2 border-b border-slate-700">
              <span className="text-slate-300 text-sm">{key}</span>
              <span className="text-xs text-slate-500">Check Vercel env vars</span>
            </div>
          ))}
        </div>
      </div>

      {/* Agents */}
      <div className="bg-slate-800 rounded-2xl p-5">
        <h2 className="text-white font-semibold mb-4">Agents</h2>
        <div className="space-y-2">
          {['Scout (7:00am weekdays)', 'Pipeline (9:00am weekdays)', 'Broadcast (every 30min)', 'Feedback Processor (every 30min)', 'Engagement Sync (every 2hrs)', 'Escalation Check (every 4hrs)', 'Weekly Batch (Monday 6am)', 'Monthly Intel (1st of month)'].map(a => (
            <div key={a} className="flex items-center gap-3 py-2 border-b border-slate-700">
              <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
              <span className="text-slate-300 text-sm">{a}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800 rounded-2xl p-5">
        <h2 className="text-white font-semibold mb-2">WhatsApp Commands</h2>
        <div className="space-y-1 text-sm font-mono">
          {[['APPROVE', 'Approve most recent item'], ['EDIT: [text]', 'Approve with your changes'], ['REJECT', 'Decline item'], ['ALL APPROVE', 'Approve entire batch'], ['STATUS', 'Get ROI + pipeline snapshot']].map(([cmd, desc]) => (
            <div key={cmd} className="flex gap-3">
              <span className="text-orange-400 w-40 shrink-0">{cmd}</span>
              <span className="text-slate-400">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

---

## PROMPT 8.11 — Fix drizzle.config.ts Location

```
Move drizzle config to project root.

DELETE src/lib/drizzle.config.ts if it exists.

CREATE drizzle.config.ts at project ROOT (same level as package.json):

import type { Config } from 'drizzle-kit'
export default {
  schema: './src/lib/schema.ts',
  out: './drizzle',
  driver: 'pg',
  dbCredentials: {
    connectionString: process.env.DATABASE_URL!
  }
} satisfies Config

Then run:
npx drizzle-kit push:pg
```
# PHASE 9 — SEED DATABASE

---

## PROMPT 9.1 — Seed Data

```
Create src/lib/seed.ts and implement the runSeed() function.

Import:
import { db } from './db'
import * as schema from './schema'

export async function runSeed() {

  // 1. BRANDS
  await db.insert(schema.cateros_brands).values([
    { slug: 'mikana', display_name: 'Mikana Food Service', brand_color: '#E8490F', website_url: 'https://mikanafoodservice.com' },
    { slug: 'boxedgo', display_name: 'Boxed & Go', brand_color: '#c2714f', website_url: 'https://boxedandgo.com' }
  ]).onConflictDoNothing()

  // 2. PLATFORM COST TIERS
  await db.insert(schema.cateros_platform_cost_tiers).values([
    {
      tier_name: 'floor', tier_label: 'Minimum Viable',
      monthly_ceiling_aed: '450', monthly_ceiling_usd: '122',
      agent_cycle_frequency: 'Daily — reduced token budget',
      competitive_intel_frequency: 'Monthly — 5 competitors/industry',
      competitors_per_industry: 5, seo_articles_per_month: 2, social_posts_per_week: 4,
      upgrade_trigger_revenue_aed: '50000', upgrade_trigger_growth_pct: '0',
      is_active: false,
      cost_breakdown: { claude_api_usd: 50, vercel_usd: 20, resend_usd: 0, whatsapp_api_usd: 8, serpapi_usd: 0, apify_usd: 5, neon_usd: 0 }
    },
    {
      tier_name: 'standard', tier_label: 'Full Operation',
      monthly_ceiling_aed: '750', monthly_ceiling_usd: '205',
      agent_cycle_frequency: 'Daily — full capacity',
      competitive_intel_frequency: 'Monthly — 10 competitors/industry',
      competitors_per_industry: 10, seo_articles_per_month: 4, social_posts_per_week: 8,
      upgrade_trigger_revenue_aed: '200000', upgrade_trigger_growth_pct: '30',
      is_active: true,
      cost_breakdown: { claude_api_usd: 100, vercel_usd: 20, resend_usd: 20, whatsapp_api_usd: 12, serpapi_usd: 30, apify_usd: 15, neon_usd: 0 }
    },
    {
      tier_name: 'expanded', tier_label: 'High Growth',
      monthly_ceiling_aed: '1200', monthly_ceiling_usd: '327',
      agent_cycle_frequency: 'Daily — high frequency',
      competitive_intel_frequency: 'Weekly scan + monthly deep analysis',
      competitors_per_industry: 15, seo_articles_per_month: 8, social_posts_per_week: 14,
      upgrade_trigger_revenue_aed: '500000', upgrade_trigger_growth_pct: '50',
      is_active: false,
      cost_breakdown: { claude_api_usd: 180, vercel_usd: 20, resend_usd: 20, whatsapp_api_usd: 20, serpapi_usd: 50, apify_usd: 30, neon_usd: 19 }
    },
    {
      tier_name: 'scale', tier_label: 'Enterprise',
      monthly_ceiling_aed: '2000', monthly_ceiling_usd: '545',
      agent_cycle_frequency: 'Continuous — real-time where applicable',
      competitive_intel_frequency: 'Weekly deep analysis — all industries',
      competitors_per_industry: 25, seo_articles_per_month: 16, social_posts_per_week: 20,
      upgrade_trigger_revenue_aed: '1000000', upgrade_trigger_growth_pct: '100',
      is_active: false,
      cost_breakdown: { claude_api_usd: 300, vercel_usd: 20, resend_usd: 40, whatsapp_api_usd: 35, serpapi_usd: 75, apify_usd: 50, neon_usd: 19 }
    }
  ]).onConflictDoNothing()

  // 3. PLATFORM COST BUDGET (current month)
  const now = new Date()
  const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  await db.insert(schema.cateros_platform_cost_budgets).values({
    period, active_tier: 'standard',
    approved_ceiling_aed: '750', approved_ceiling_usd: '205',
    actual_spend_aed: '0', days_elapsed: now.getDate(), days_in_month: daysInMonth,
    spend_pace_pct: '0', status: 'active'
  }).onConflictDoNothing()

  // 4. BOXED & GO PLANS
  await db.insert(schema.cateros_bg_plans).values([
    {
      name: 'Daily Essentials', category: 'heat_and_eat',
      description: 'Fully cooked, reheat in 3 minutes. 5 meals per week.',
      description_arabic: 'وجبات مطبوخة بالكامل، أعيدي تسخينها في 3 دقائق.',
      target_segment: 'individual_professional', meals_per_week: 5,
      price_aed_weekly: '265', price_aed_monthly: '950'
    },
    {
      name: 'Builder Box', category: 'build_your_plate',
      description: 'Protein + side + sauce pouches. 80% cooked, finish in 13 minutes. 5 sets per week.',
      description_arabic: 'بروتين + طبق جانبي + صوص. مطبوخ ٨٠٪، أكمل الطهي في ١٣ دقيقة.',
      target_segment: 'individual_professional', meals_per_week: 5,
      price_aed_weekly: '325', price_aed_monthly: '1150'
    },
    {
      name: 'Family Social Table', category: 'social_table',
      description: 'Family-style meals for 3–4 people. Semi-prepared, finish together.',
      description_arabic: 'وجبات عائلية لـ ٣-٤ أشخاص.',
      target_segment: 'household_family', meals_per_week: 4,
      price_aed_weekly: '420', price_aed_monthly: '1480'
    },
    {
      name: 'Nutritionist Plan', category: 'nutritionist',
      description: 'Macro-counted, calorie-tracked. 7 meals per week. Dietitian-approved.',
      description_arabic: 'خطة التغذية المحسوبة، مع تتبع السعرات الحرارية.',
      target_segment: 'fitness', meals_per_week: 7,
      price_aed_weekly: '385', price_aed_monthly: '1350'
    },
    {
      name: 'Full Week Mix', category: 'heat_and_eat',
      description: 'Mix of Heat & Eat and Build Your Plate. 7 meals per week. Maximum variety.',
      description_arabic: 'مزيج متنوع. ٧ وجبات أسبوعياً.',
      target_segment: 'household_family', meals_per_week: 7,
      price_aed_weekly: '495', price_aed_monthly: '1750'
    }
  ]).onConflictDoNothing()

  // 5. SCHOOLS (6 target schools)
  const schools = [
    { name: 'GEMS Wellington International School', type: 'private', curriculum: 'British', emirate: 'Dubai', area: 'Dubai Marina', student_count: 2400, total_daily_covers: 1800, current_contract_status: 'active_competitor', qualification_score: 9 },
    { name: 'Repton School Dubai', type: 'private', curriculum: 'British', emirate: 'Dubai', area: 'Nad Al Sheba', student_count: 1800, total_daily_covers: 1350, current_contract_status: 'active_competitor', qualification_score: 8 },
    { name: 'Dubai American Academy', type: 'private', curriculum: 'American', emirate: 'Dubai', area: 'Al Barsha', student_count: 1200, total_daily_covers: 900, current_contract_status: 'no_service', qualification_score: 7 },
    { name: 'Abu Dhabi Grammar School', type: 'private', curriculum: 'British', emirate: 'Abu Dhabi', area: 'Abu Dhabi City', student_count: 1600, total_daily_covers: 1200, current_contract_status: 'active_competitor', qualification_score: 9 },
    { name: 'The British School Al Khubairat', type: 'private', curriculum: 'British', emirate: 'Abu Dhabi', area: 'Al Khubairat', student_count: 1100, total_daily_covers: 825, current_contract_status: 'in_house', qualification_score: 8 },
    { name: 'Nord Anglia International School', type: 'private', curriculum: 'IB', emirate: 'Dubai', area: 'Dubai Hills', student_count: 1400, total_daily_covers: 1050, current_contract_status: 'active_competitor', qualification_score: 8 }
  ]

  for (const school of schools) {
    const [s] = await db.insert(schema.cateros_schools).values({
      ...school, source: 'seed', renewal_notice_days: 90
    }).returning()

    await db.insert(schema.cateros_contacts).values({
      school_id: s.id,
      first_name: 'Head of', last_name: 'Operations',
      title: 'Head of Operations',
      is_primary: true, language_preference: 'en'
    })

    const [lead] = await db.insert(schema.cateros_school_leads).values({
      school_id: s.id,
      lead_type: 'new_acquisition',
      stage: 'pending_approval',
      priority: school.qualification_score >= 9 ? 'high' : 'medium',
      estimated_value_aed: school.total_daily_covers * 16 * 180
    }).returning()

    await db.insert(schema.cateros_approval_requests).values({
      type: 'new_lead_school',
      brand: 'mikana',
      title: `New School Lead: ${school.name}`,
      summary: `${school.curriculum} curriculum · ${school.student_count} students · ${school.total_daily_covers} daily covers. Score: ${school.qualification_score}/10. Estimated annual value: AED ${(school.total_daily_covers * 16 * 180).toLocaleString()}. Status: ${school.current_contract_status.replace(/_/g, ' ')}.`,
      payload: { leadId: lead.id, schoolId: s.id, score: school.qualification_score },
      agent: 'scout',
      entity_id: lead.id,
      entity_type: 'school_lead',
      status: 'pending',
      priority: school.qualification_score >= 9 ? 'urgent' : 'normal',
      expires_at: new Date(Date.now() + 48 * 3600 * 1000)
    })
  }

  // 6. COMPANIES (5 corporate targets)
  const companies = [
    { name: 'Dubai Internet City', industry: 'free_zone', city: 'Dubai', employee_count_estimate: 70000, daily_meals_opportunity: 35000, annual_value_estimate_aed: 4500000, qualification_score: 9 },
    { name: 'DIFC', industry: 'free_zone', city: 'Dubai', employee_count_estimate: 25000, daily_meals_opportunity: 12500, annual_value_estimate_aed: 2200000, qualification_score: 8 },
    { name: 'Masdar City', industry: 'corporate_campus', city: 'Abu Dhabi', employee_count_estimate: 7000, daily_meals_opportunity: 3500, annual_value_estimate_aed: 770000, qualification_score: 7 },
    { name: 'Dubai South', industry: 'free_zone', city: 'Dubai', employee_count_estimate: 35000, daily_meals_opportunity: 17500, annual_value_estimate_aed: 2800000, qualification_score: 8 },
    { name: 'twofour54', industry: 'free_zone', city: 'Abu Dhabi', employee_count_estimate: 6500, daily_meals_opportunity: 3250, annual_value_estimate_aed: 715000, qualification_score: 7 }
  ]

  for (const company of companies) {
    const [c] = await db.insert(schema.cateros_companies).values({
      ...company, source: 'seed', current_food_situation: 'unknown'
    }).returning()

    const [contact] = await db.insert(schema.cateros_contacts).values({
      company_id: c.id,
      first_name: 'Head of', last_name: 'Facilities',
      title: 'Head of Facilities & Operations',
      is_primary: true
    }).returning()

    const [lead] = await db.insert(schema.cateros_corporate_leads).values({
      company_id: c.id,
      primary_contact_id: contact.id,
      stage: 'pending_approval',
      priority: company.qualification_score >= 9 ? 'high' : 'medium',
      estimated_value_aed: company.annual_value_estimate_aed,
      meals_per_day_estimate: company.daily_meals_opportunity
    }).returning()

    await db.insert(schema.cateros_approval_requests).values({
      type: 'new_lead_corporate',
      brand: 'mikana',
      title: `New Corporate Lead: ${company.name}`,
      summary: `${company.industry.replace(/_/g, ' ')} · ${company.employee_count_estimate.toLocaleString()} employees · ${company.daily_meals_opportunity.toLocaleString()} daily meals opportunity. Estimated annual value: AED ${company.annual_value_estimate_aed.toLocaleString()}. Score: ${company.qualification_score}/10.`,
      payload: { leadId: lead.id, companyId: c.id, score: company.qualification_score },
      agent: 'scout',
      entity_id: lead.id,
      entity_type: 'corporate_lead',
      status: 'pending',
      priority: 'normal',
      expires_at: new Date(Date.now() + 48 * 3600 * 1000)
    })
  }

  // 7. BOXED & GO SUBSCRIBERS (8 test subscribers)
  const subscriberSeeds = [
    { first_name: 'Layla', last_name: 'Al Mansouri', city: 'Dubai', area: 'JLT', segment: 'household_family', stage: 'trial_active', source: 'instagram_organic' },
    { first_name: 'James', last_name: 'Thompson', city: 'Dubai', area: 'DIFC', segment: 'individual_professional', stage: 'subscribed', source: 'instagram_organic' },
    { first_name: 'Noor', last_name: 'Al Rashidi', city: 'Abu Dhabi', area: 'Khalidiyah', segment: 'household_family', stage: 'awareness', source: 'instagram_organic' },
    { first_name: 'Sarah', last_name: 'Mitchell', city: 'Dubai', area: 'Dubai Marina', segment: 'individual_professional', stage: 'interest', source: 'seo_inbound' },
    { first_name: 'Ahmed', last_name: 'Khalil', city: 'Dubai', area: 'Business Bay', segment: 'couple', stage: 'trial_offered', source: 'linkedin_outreach' },
    { first_name: 'Emma', last_name: 'Davies', city: 'Dubai', area: 'Springs', segment: 'household_family', stage: 'awareness', source: 'referral' },
    { first_name: 'Fatima', last_name: 'Al Zaabi', city: 'Dubai', area: 'Arabian Ranches', segment: 'household_family', stage: 'trial_active', source: 'instagram_organic' },
    { first_name: 'Ryan', last_name: 'Park', city: 'Dubai', area: 'Downtown', segment: 'individual_professional', stage: 'churned', source: 'instagram_organic', churn_reason: 'price_too_high' }
  ]

  for (const sub of subscriberSeeds) {
    await db.insert(schema.cateros_bg_subscribers).values({
      ...sub,
      email: `${sub.first_name.toLowerCase()}.${sub.last_name.toLowerCase()}@example.com`,
      country: 'UAE'
    })
  }

  // 8. COMPETITORS (10 across 3 industries)
  await db.insert(schema.cateros_competitors).values([
    { name: 'National Food Company UAE', industry: 'school_food_uae', country: 'UAE', brand: 'mikana', direct_competitor: true },
    { name: 'Compass Group UAE', industry: 'school_food_uae', country: 'UAE', brand: 'mikana', direct_competitor: true },
    { name: 'Emirates Flight Catering Schools', industry: 'school_food_uae', country: 'UAE', brand: 'mikana', direct_competitor: true },
    { name: 'Sodexo UAE', industry: 'corporate_catering_uae', country: 'UAE', brand: 'mikana', direct_competitor: true },
    { name: 'Catering Alliance UAE', industry: 'corporate_catering_uae', country: 'UAE', brand: 'mikana', direct_competitor: true },
    { name: 'Compass Group Corporate', industry: 'corporate_catering_uae', country: 'UAE', brand: 'mikana', direct_competitor: false },
    { name: 'Kcal', industry: 'meal_subscription_uae', country: 'UAE', brand: 'boxedgo', direct_competitor: true, instagram_handle: 'kcaluae' },
    { name: 'Fuel Your Life', industry: 'meal_subscription_uae', country: 'UAE', brand: 'boxedgo', direct_competitor: true, instagram_handle: 'fuelyourlifeuae' },
    { name: 'EatClean UAE', industry: 'meal_subscription_uae', country: 'UAE', brand: 'boxedgo', direct_competitor: true, instagram_handle: 'eatcleanuae' },
    { name: 'HelloFresh UAE', industry: 'meal_subscription_uae', country: 'UAE', brand: 'boxedgo', direct_competitor: true, instagram_handle: 'hellofreshuae' }
  ]).onConflictDoNothing()

  console.log('✅ CaterOS database seeded successfully')
  console.log('📋 Check your WhatsApp — approval requests have been created')
  console.log('🎯 Note: Notifications will send when real WhatsApp credentials are configured')
}
```

---
---

# PHASE 10 — DEPLOYMENT

---

## PROMPT 10.1 — Production Deployment

```
Prepare CaterOS for Vercel production deployment. Follow every step in order.

━━━ STEP 1: Update next.config.js ━━━
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['@neondatabase/serverless']
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' }
        ]
      },
      {
        source: '/feedback',
        headers: [{ key: 'Cache-Control', value: 'no-store' }]
      }
    ]
  }
}
module.exports = nextConfig

━━━ STEP 2: Add export const dynamic = 'force-dynamic' ━━━
Add this line to the top of EVERY file in src/app/api/ that fetches live data.
This prevents Vercel from statically caching API responses.

━━━ STEP 3: Push schema to Neon ━━━
npx drizzle-kit push:pg

━━━ STEP 4: Seed database (development only) ━━━
POST http://localhost:3000/api/dev/seed
Verify in Neon console that tables have rows.

━━━ STEP 5: Deploy to Vercel ━━━
1. Push code to GitHub
2. Connect repository in Vercel dashboard
3. Add ALL environment variables (from .env.local) in Vercel → Settings → Environment Variables
4. Deploy

━━━ STEP 6: Configure WhatsApp Webhook ━━━
After deployment, register this webhook in Meta Developer Console:
  URL: https://your-cateros-domain.vercel.app/api/approvals/whatsapp
  Verify token: value of WHATSAPP_WEBHOOK_VERIFY_TOKEN
  Events: messages

Test: Send "STATUS" to your WhatsApp Business number. Should get a reply.

━━━ STEP 7: Configure Instagram Webhook ━━━
Register in Meta Developer Console:
  URL: https://your-cateros-domain.vercel.app/api/broadcast/webhooks/instagram
  Verify token: value of META_WEBHOOK_VERIFY_TOKEN
  Events: comments, mentions

━━━ STEP 8: Verify Cron Jobs ━━━
Go to Vercel Dashboard → Settings → Cron Jobs
All 9 crons from vercel.json should appear.
Enable each one.

━━━ STEP 9: First Run Tests ━━━
Run these manual tests in order:

TEST 1 — Health check:
GET https://your-domain.vercel.app/api/health
Expected: { status: 'ok', pendingApprovals: 11, agents: [...] }

TEST 2 — Morning briefing:
GET https://your-domain.vercel.app/api/cron/morning-briefing
Header: Authorization: Bearer {CRON_SECRET}
Expected: WhatsApp message arrives on your phone within 60 seconds

TEST 3 — WhatsApp approval:
Reply APPROVE to the WhatsApp message from TEST 2
Expected: Confirmation reply from CaterOS

TEST 4 — Social publish queue:
GET https://your-domain.vercel.app/api/cron/social-publish
Header: Authorization: Bearer {CRON_SECRET}
Expected: { success: true, published: 0, failed: 0 } (no posts approved yet)

TEST 5 — Feedback form (public):
Open https://your-domain.vercel.app/feedback?brand=boxedgo in incognito browser
Submit a test rating + feedback
Verify: record appears in /api/care/feedback/inbox

━━━ STEP 10: Go Live ━━━
1. Enable all crons in Vercel
2. Approve the 11 pending seed leads from your phone (reply APPROVE to each WhatsApp)
3. Monitor first morning briefing at 7:30am UAE time
4. Approve your first week of social content via batch approval

━━━ MAINTENANCE CALENDAR ━━━
Monthly: Refresh LinkedIn + Instagram access tokens (expire every 60 days)
Monthly: Review platform cost report in financial dashboard
Monthly: Approve competitive intelligence + Blue Ocean report
Quarterly: Approve new quarterly targets (Orchestrator proposes automatically)
```

---
---

# QUICK REFERENCE

---

## WHATSAPP COMMAND GUIDE

| You reply | What happens |
|---|---|
| `APPROVE` | Approves most recent pending item |
| `EDIT: [your text]` | Approves with your content replacing the draft |
| `REJECT` | Declines, agent moves on |
| `REJECT: [reason]` | Declines and logs your reason |
| `ALL APPROVE` | Approves entire pending batch at once |
| `STATUS` | Returns current ROI + pending count snapshot |
| `PAUSE [channel]` | Emergency pause a marketing channel spend |

---

## 20x ROI GOVERNANCE

```
EVERY DECISION PASSES THIS TEST:
(Projected Revenue Attribution) ÷ (Marketing Spend + Platform Costs) ≥ 20

CHANNEL BENCHMARKS — UAE food service:
School renewals:    50–100x  ← best channel ever, near-zero CAC
SEO inbound:        30–80x   ← compounds over years, always invest
Referral:           ∞        ← zero cost, never cap this
LinkedIn outreach:  15–40x   ← only works for contracts > AED 200K
Instagram organic:  8–25x    ← depends on subscriber retention
Paid Meta ads:      5–15x    ← only run if LTV × 20 > projected CAC
Influencer:         3–12x    ← one at a time, manage tightly

AUTOMATIC ORCHESTRATOR ACTIONS (propose, you approve):
Channel < 20x for 30 days → Propose 30% budget reduction
Channel < 10x for 30 days → Propose 50% budget reduction
Channel < 1x for 14 days  → Propose immediate pause
Channel > 30x for 30 days → Propose 25% budget increase
Overall ROI < 20x         → Emergency WhatsApp alert + analysis

ROI COLOUR CODES in all reports:
🟢 ≥ 20x  Target met
🟡 10–19x  Approaching target — action within 30 days
🔴 < 10x   Below threshold — reallocate immediately
⚫ < 1x    Burning money — pause this instant
```

---

## COMPLETE BUILD ORDER

```
Phase 0:  Prompts 0.1–0.3   Scaffold + schema + core libs
Phase 1:  Prompts 1.1–1.2   Orchestrator (run FIRST — all agents depend on it)
Phase 2:  Prompt  2.1       Scout agent
Phase 3:  Prompt  3.1       Pipeline agent
Phase 4:  Prompts 4.1–4.2   Integrations + Broadcast agent
Phase 5:  Prompt  5.1       SEO Engine agent
Phase 6:  Prompt  6.1       Customer Care agent
Phase 7:  Prompts 7.1–7.4   All API routes (crons + approvals + domain routes)
Phase 8:  Prompts 8.1–8.8   Owner UI (layout, briefing, approvals, financial, care, pipeline, broadcast, feedback)
Phase 9:  Prompt  9.1       Seed database
Phase 10: Prompt  10.1      Deploy to Vercel

TOTAL: 25 prompts. Build in order. Schema before agents. Agents before routes. Routes before UI.
```

---

## ENVIRONMENT VARIABLES — WHERE TO GET EACH ONE

```
DATABASE_URL           Neon console → Connection string (pooled)
ANTHROPIC_API_KEY      console.anthropic.com → API keys
RESEND_API_KEY         resend.com → API Keys
CRON_SECRET            Generate: openssl rand -hex 32
NEXT_PUBLIC_APP_URL    Your Vercel deployment URL
OWNER_WHATSAPP         Your number: +971XXXXXXXXX
OWNER_EMAIL            Your email address
OWNER_APPROVAL_TOKEN   Generate: openssl rand -hex 32

WHATSAPP_PHONE_NUMBER_ID    Meta Business Suite → WhatsApp → Phone numbers
WHATSAPP_BUSINESS_ACCOUNT_ID  Meta Business Suite → Account ID
WHATSAPP_ACCESS_TOKEN       Meta Business Suite → System User permanent token
WHATSAPP_WEBHOOK_VERIFY_TOKEN  Any string you choose — set same in Meta webhook config

META_APP_ID             developers.facebook.com → Your App → Settings
META_APP_SECRET         developers.facebook.com → Your App → Settings → Show
META_ACCESS_TOKEN       Graph API Explorer → Generate with instagram_basic,instagram_content_publish perms
META_INSTAGRAM_ACCOUNT_ID  GET /me/accounts via Graph API Explorer, find your Instagram account
META_WEBHOOK_VERIFY_TOKEN  Any string you choose — set same in Meta webhook config

LINKEDIN_CLIENT_ID     developer.linkedin.com → Your App → Auth
LINKEDIN_CLIENT_SECRET developer.linkedin.com → Your App → Auth → Show
LINKEDIN_ACCESS_TOKEN  OAuth 2.0 flow with w_organization_social scope
LINKEDIN_ORGANIZATION_ID  Your Company Page URL: linkedin.com/company/[THIS_NUMBER]

SERPAPI_KEY            serpapi.com → Dashboard → API Key (free: 100/month)
APIFY_API_TOKEN        console.apify.com → Settings → Integrations → API token

USD_TO_AED_RATE        3.67 (fixed, update if rate changes significantly)
ROI_TARGET_MULTIPLIER  20 (do not change)
PLATFORM_STARTING_TIER standard
```
# PHASE C — CREATIVE AGENT
## Visual Design, Art Direction & Asset Production
## Addendum to CaterOS v4 Build Guide

---

## OVERVIEW

The Creative Agent sits between Broadcast and publication.
Broadcast generates caption + copy + creative brief.
Creative generates the actual visual asset — photorealistic food image,
brand-overlaid graphic, platform-sized final file.
Owner approves the real finished post, not a description of one.

NEW DEPENDENCY — Install before running these prompts:
npm install openai sharp @vercel/blob uuid
npm install --save-dev @types/sharp

Add to .env.local:
OPENAI_API_KEY=                    ← platform.openai.com → API keys
VERCEL_BLOB_READ_WRITE_TOKEN=      ← Vercel dashboard → Storage → Blob → Token
IDEOGRAM_API_KEY=                  ← ideogram.ai → API (optional, better for text-on-image)
IMAGE_GENERATION_MODEL=dall-e-3    ← 'dall-e-3' | 'ideogram' | 'stability'

---
---

## PROMPT C.1 — Schema: Brand Identity + Creative Assets

```
Add these two tables to src/lib/schema.ts AFTER the existing tables.
Run npx drizzle-kit push:pg after adding.

━━━ cateros_brand_identity ━━━

export const cateros_brand_identity = pgTable('cateros_brand_identity', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').unique().notNull(),

  -- COLOUR PALETTE
  primary_color: text('primary_color'),       -- hex e.g. '#E8490F'
  secondary_color: text('secondary_color'),
  accent_color: text('accent_color'),
  background_color: text('background_color').default('#FFFFFF'),

  -- TYPOGRAPHY
  font_primary: text('font_primary'),         -- e.g. 'Playfair Display'
  font_secondary: text('font_secondary'),     -- e.g. 'Inter'
  font_color_on_primary: text('font_color_on_primary').default('#FFFFFF'),

  -- LOGO
  logo_url: text('logo_url'),
  logo_white_url: text('logo_white_url'),
  logo_dark_url: text('logo_dark_url'),
  logo_position: text('logo_position').default('bottom_right'),
  -- 'bottom_right'|'bottom_left'|'top_right'|'top_left'|'center'

  -- PHOTOGRAPHY STYLE
  photography_style: text('photography_style'),
  -- 'warm_natural'|'dark_moody'|'bright_clean'|'rustic'|'minimalist'
  photography_keywords: text('photography_keywords').array(),
  -- e.g. ['steam rising','close-up texture','marble surface','hands in frame']
  photography_avoid: text('photography_avoid').array(),
  -- e.g. ['plastic containers','neon lighting','cluttered backgrounds']
  hero_shot_description: text('hero_shot_description'),
  -- The Sizzle Moment or equivalent brand hero visual

  -- INSTAGRAM GRID
  instagram_grid_style: text('instagram_grid_style').default('consistent_filter'),
  -- 'alternating'|'consistent_filter'|'color_blocked'|'row_by_row'
  feed_aspect_ratio: text('feed_aspect_ratio').default('4:5'),
  -- '1:1'|'4:5'

  -- SEASONAL PALETTES (hex overrides)
  palette_ramadan: jsonb('palette_ramadan'),
  -- { primary: '#D4A017', accent: '#8B0000', mood: 'warm golden iftar' }
  palette_eid: jsonb('palette_eid'),
  palette_uae_national_day: jsonb('palette_uae_national_day'),
  palette_lebanese_independence: jsonb('palette_lebanese_independence'),
  palette_christmas: jsonb('palette_christmas'),

  -- BRAND VOICE (for text overlays)
  tagline: text('tagline'),
  brand_voice_adjectives: text('brand_voice_adjectives').array(),

  -- LEARNING: approved post URLs used as style reference
  approved_reference_urls: text('approved_reference_urls').array(),
  -- Updated whenever owner approves a generated post

  -- PLATFORM DIMENSIONS (auto-populated)
  dimensions_feed: text('dimensions_feed').default('1080x1080'),
  dimensions_story: text('dimensions_story').default('1080x1920'),
  dimensions_reel_thumbnail: text('dimensions_reel_thumbnail').default('1080x1920'),
  dimensions_linkedin: text('dimensions_linkedin').default('1200x627'),

  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

━━━ cateros_creative_assets ━━━

export const cateros_creative_assets = pgTable('cateros_creative_assets', {
  id: uuid('id').primaryKey().defaultRandom(),
  brand: text('brand').notNull(),
  post_id: uuid('post_id'),              -- references cateros_social_posts

  -- GENERATION INPUT
  content_brief: text('content_brief'),  -- what Broadcast handed over
  visual_concept: text('visual_concept'),
  dalle_prompt: text('dalle_prompt'),
  generation_model: text('generation_model').default('dall-e-3'),
  -- 'dall-e-3'|'ideogram'|'stability'

  -- RAW GENERATION OUTPUT
  raw_image_url: text('raw_image_url'),  -- direct from generation API
  raw_image_blob_key: text('raw_image_blob_key'),

  -- PROCESSED ASSETS (after brand overlay + resize)
  asset_feed_url: text('asset_feed_url'),        -- 1080x1080 or 1080x1350
  asset_story_url: text('asset_story_url'),      -- 1080x1920
  asset_linkedin_url: text('asset_linkedin_url'), -- 1200x627
  asset_thumbnail_url: text('asset_thumbnail_url'),

  -- TEXT OVERLAY
  has_text_overlay: boolean('has_text_overlay').default(false),
  text_overlay_headline: text('text_overlay_headline'),
  text_overlay_subtext: text('text_overlay_subtext'),
  text_overlay_data: jsonb('text_overlay_data'),

  -- QUALITY
  generation_attempts: integer('generation_attempts').default(1),
  rejected_reason: text('rejected_reason'),
  estimated_engagement_potential: text('estimated_engagement_potential'),
  -- 'high'|'medium'|'low'

  -- APPROVAL
  status: text('status').default('generating'),
  -- 'generating'|'ready'|'approved'|'rejected'|'regenerating'
  approval_request_id: uuid('approval_request_id'),
  approved_at: timestamp('approved_at'),
  added_to_brand_references: boolean('added_to_brand_references').default(false),

  created_at: timestamp('created_at').defaultNow(),
  updated_at: timestamp('updated_at').defaultNow()
})

Run: npx drizzle-kit push:pg
```

---

## PROMPT C.2 — Brand Identity Seed Data

```
Add brand identity records to src/lib/seed.ts inside the runSeed() function,
AFTER the brands section.

await db.insert(schema.cateros_brand_identity).values([
  {
    brand: 'mikana',
    primary_color: '#E8490F',
    secondary_color: '#1e293b',
    accent_color: '#f97316',
    background_color: '#FFFFFF',
    font_primary: 'Playfair Display',
    font_secondary: 'Inter',
    font_color_on_primary: '#FFFFFF',
    photography_style: 'bright_clean',
    photography_keywords: [
      'professional kitchen environment',
      'HACCP certified workspace',
      'fresh ingredients close-up',
      'chef hands plating',
      'steam rising from hot food',
      'vibrant colourful vegetables',
      'UAE school canteen setting',
      'corporate dining environment',
      'natural daylight food photography',
      'marble or stainless steel surface'
    ],
    photography_avoid: [
      'plastic disposable containers',
      'fast food aesthetic',
      'neon lighting',
      'cluttered backgrounds',
      'cartoon or illustrated style',
      'dark moody filter',
      'overly saturated colours'
    ],
    hero_shot_description: 'Chef hands carefully plating a nutritionist-designed meal in a professional kitchen, steam rising, natural light, clean stainless steel background',
    instagram_grid_style: 'consistent_filter',
    feed_aspect_ratio: '4:5',
    tagline: 'Feeding ambition. One plate at a time.',
    brand_voice_adjectives: ['authoritative', 'warm', 'expert', 'trustworthy', 'professional'],
    palette_ramadan: { primary: '#D4A574', accent: '#8B4513', mood: 'warm golden iftar setting, lanterns, family table' },
    palette_eid: { primary: '#2E8B57', accent: '#FFD700', mood: 'celebratory, rich, festive' },
    palette_uae_national_day: { primary: '#00732F', accent: '#FF0000', secondary: '#FFFFFF', mood: 'patriotic, proud, national colours' },
    dimensions_feed: '1080x1350',
    dimensions_story: '1080x1920',
    dimensions_linkedin: '1200x627'
  },
  {
    brand: 'boxedgo',
    primary_color: '#c2714f',
    secondary_color: '#fef3e2',
    accent_color: '#e85d26',
    background_color: '#fef9f5',
    font_primary: 'Fraunces',
    font_secondary: 'DM Sans',
    font_color_on_primary: '#FFFFFF',
    photography_style: 'warm_natural',
    photography_keywords: [
      'home kitchen countertop',
      'warm terracotta and cream tones',
      'protein hitting hot pan with loud sizzle',
      'steam rising dramatically',
      'hands opening vacuum pouch',
      'sauce being drizzled artfully',
      'colourful protein and vegetable combinations',
      'real home environment not studio',
      'wooden chopping board',
      'morning or evening golden hour light',
      'Dubai apartment kitchen aesthetic',
      'Lebanese grandmother kitchen warmth'
    ],
    photography_avoid: [
      'clinical white studio background',
      'professional restaurant plating',
      'paper bags or takeaway containers',
      'sad desk lunch aesthetic',
      'overly posed or staged',
      'cold blue tones',
      'empty plate or half eaten food'
    ],
    hero_shot_description: 'THE SIZZLE MOMENT: vacuum pouch protein being released into a very hot pan, dramatic steam explosion, golden-brown sear beginning, warm home kitchen background, terracotta and cream tones, cinematic close-up',
    instagram_grid_style: 'alternating',
    feed_aspect_ratio: '4:5',
    tagline: 'Done the hard part for you.',
    brand_voice_adjectives: ['warm', 'real', 'confident', 'playful', 'honest'],
    palette_ramadan: { primary: '#8B4513', accent: '#D4A574', mood: 'iftar family gathering, dates, warm lantern light, breaking fast together' },
    palette_eid: { primary: '#c2714f', accent: '#FFD700', mood: 'Eid feast, family social table, celebration, abundance' },
    palette_uae_national_day: { primary: '#00732F', accent: '#c2714f', mood: 'UAE pride with Boxed & Go warmth, national day feast' },
    palette_lebanese_independence: { primary: '#CC0000', accent: '#FFFFFF', mood: 'Lebanese heritage, teta recipes, cedar pride, home cooking' },
    dimensions_feed: '1080x1350',
    dimensions_story: '1080x1920',
    dimensions_linkedin: '1200x627'
  }
]).onConflictDoNothing()
```

---

## PROMPT C.3 — Creative Agent Core

```
Create src/agents/creative.ts — full implementation.

import OpenAI from 'openai'
import sharp from 'sharp'
import { put } from '@vercel/blob'
import { db } from '@/lib/db'
import { callClaude } from '@/lib/anthropic'
import { logActivity } from './orchestrator'
import * as schema from '@/lib/schema'
import { eq } from 'drizzle-orm'

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })

━━━ SYSTEM PROMPT ━━━

export const CREATIVE_DIRECTION_PROMPT = `
You are the Creative Agent for CaterOS — a senior creative director
and graphic designer specialising in F&B visual identity for UAE and Lebanon.

You receive a content brief from the Broadcast Agent and produce a precise
visual concept + image generation prompt that will create a photorealistic,
commercially viable, on-brand image ready for Instagram or LinkedIn.

BRAND IDENTITY PROVIDED TO YOU:
Photography style: [STYLE]
Visual keywords to include: [KEYWORDS]
Visual elements to avoid: [AVOID]
Hero shot description: [HERO]
Current season/moment: [SEASON]
Seasonal palette note: [SEASONAL_PALETTE]

F&B VISUAL PRINCIPLES — ALWAYS APPLY:
1. Food must look genuinely appetising above all else
2. Steam, texture, glistening, and colour contrast are your primary tools
3. Human hands in frame increase engagement — include where natural
4. The Sizzle Moment (Boxed & Go only): protein hitting very hot pan,
   dramatic steam explosion, beginning of golden sear, cinematic close-up.
   This is the brand's hero visual — include it whenever brief allows.
5. Negative space beats cluttered compositions every time
6. Natural or warm artificial light always — never cold studio flash
7. Real environments over studio sets — home kitchen, professional kitchen,
   outdoor terrace, family dining table
8. Imperfect beauty — a drip of sauce, a slight steam wisp — feels more real

PLATFORM NOTES:
Instagram feed (4:5): Hero food shot, product feature, lifestyle scene
Instagram story (9:16): Bold, immediate, text-friendly, swipe-up energy
LinkedIn (1.91:1): Professional, clean, thought-leadership compatible
Reels thumbnail (9:16): Must work as static — clear subject, bold colour

DALL-E 3 PROMPT FORMULA:
[Shot type], [subject in detail], [action if any], [surface/environment],
[lighting description], [colour palette], [mood], [camera angle],
[what makes it appetising], photorealistic food photography,
commercial quality, [avoid instructions]

OUTPUT — valid JSON only:
{
  "visual_concept": "one sentence — what the image shows and why it works",
  "dalle_prompt": "complete DALL-E 3 generation prompt, minimum 80 words",
  "alternative_prompt": "backup prompt if first generation fails quality check",
  "text_overlay": {
    "required": boolean,
    "headline": "string or null — max 5 words",
    "subtext": "string or null — max 8 words",
    "position": "bottom_third|top_third|center|none"
  },
  "platform_sizes_needed": ["feed", "story", "linkedin"],
  "estimated_engagement_potential": "high|medium|low",
  "engagement_reasoning": "why this visual will perform",
  "brand_consistency_note": "string or null — flag anything off-brand",
  "sizzle_moment_used": boolean
}
`

━━━ FUNCTIONS ━━━

1. async function getBrandIdentity(brand: string): Promise<BrandIdentity>
   -- Pull from cateros_brand_identity where brand = param
   -- If not found: throw new Error('Brand identity not configured for ' + brand)
   -- Return the full record

2. async function buildCreativeDirectionPrompt(
     brandIdentity: BrandIdentity,
     season: string
   ): Promise<string>
   -- Replace all template variables in CREATIVE_DIRECTION_PROMPT
   -- Detect season from current date:
     const month = new Date().getMonth() + 1
     const day = new Date().getDate()
     if (month === 3 || month === 4) season = 'Ramadan season — iftar and suhoor moments'
     else if (month === 12 && day >= 1 && day <= 3) season = 'UAE National Day'
     else if (month === 11 && day === 22) season = 'Lebanese Independence Day'
     else season = 'Regular season'
   -- Pull seasonal palette if season matches
   -- Return filled prompt string

3. async function generateVisualConcept(params: {
     brand: string
     contentBrief: string
     platform: string
     contentType: string
   }): Promise<VisualConcept>
   -- getBrandIdentity(params.brand)
   -- buildCreativeDirectionPrompt(identity, currentSeason)
   -- callClaude with prompt + userMessage = JSON.stringify({
        content_brief: params.contentBrief,
        platform: params.platform,
        content_type: params.contentType,
        brand_name: identity.brand,
        tagline: identity.tagline
      })
   -- Parse JSON response
   -- Return visual concept object

4. async function generateImage(dallePrompt: string): Promise<string>
   -- Call OpenAI Images API:
   const response = await openai.images.generate({
     model: 'dall-e-3',
     prompt: dallePrompt,
     n: 1,
     size: '1024x1024',
     quality: 'hd',
     style: 'natural'        -- 'natural' gives photorealistic, not illustrated
   })
   -- Return response.data[0].url
   -- If API error: throw with detailed message for retry logic

5. async function downloadImage(url: string): Promise<Buffer>
   -- fetch(url) with 30 second timeout
   -- Return buffer
   -- Used to download the generated image before processing

6. async function processAssets(params: {
     rawImageBuffer: Buffer
     brandIdentity: BrandIdentity
     textOverlay: TextOverlay
     sizesNeeded: string[]
   }): Promise<ProcessedAssets>

   Use sharp for all processing. For each requested size:

   FEED (1080x1350 — 4:5):
   let img = sharp(rawImageBuffer).resize(1080, 1350, { fit: 'cover', position: 'centre' })

   STORY (1080x1920 — 9:16):
   let img = sharp(rawImageBuffer).resize(1080, 1920, { fit: 'cover', position: 'centre' })

   LINKEDIN (1200x627 — 1.91:1):
   let img = sharp(rawImageBuffer).resize(1200, 627, { fit: 'cover', position: 'centre' })

   For EACH size, after resize:

   STEP 1 — Apply brand colour grade (subtle warm tint matching brand):
   -- If brand === 'boxedgo': apply warm tint
     .modulate({ brightness: 1.05, saturation: 1.1 })
     .tint({ r: 220, g: 180, b: 150 })  -- warm terracotta tint, low opacity effect
   -- If brand === 'mikana': apply clean bright grade
     .modulate({ brightness: 1.02, saturation: 1.05 })

   STEP 2 — Add logo watermark if logo_url is set:
   -- Download logo to buffer
   -- Resize logo to 120x120 (or appropriate size for image dimensions)
   -- Composite onto image at logo_position:
     bottom_right: { left: imageWidth - 140, top: imageHeight - 140 }
     bottom_left: { left: 20, top: imageHeight - 140 }
   -- logo opacity: 0.85

   STEP 3 — Add text overlay if required:
   -- Use sharp composite with SVG text overlay:
   const svgText = `
     <svg width="${width}" height="${height}">
       <defs>
         <linearGradient id="grad" x1="0" y1="0.7" x2="0" y2="1">
           <stop offset="0%" style="stop-color:rgb(0,0,0);stop-opacity:0" />
           <stop offset="100%" style="stop-color:rgb(0,0,0);stop-opacity:0.65" />
         </linearGradient>
       </defs>
       ${overlay.required ? `
         <rect width="${width}" height="${height * 0.35}"
           y="${height * 0.65}" fill="url(#grad)" />
         <text x="${width / 2}" y="${height * 0.82}"
           font-family="${identity.font_primary}, serif"
           font-size="${width * 0.045}px" font-weight="700"
           fill="white" text-anchor="middle"
           style="text-shadow: 0 2px 8px rgba(0,0,0,0.5)">
           ${overlay.headline || ''}
         </text>
         ${overlay.subtext ? `
         <text x="${width / 2}" y="${height * 0.89}"
           font-family="${identity.font_secondary}, sans-serif"
           font-size="${width * 0.03}px" font-weight="400"
           fill="rgba(255,255,255,0.85)" text-anchor="middle">
           ${overlay.subtext}
         </text>` : ''}
       ` : ''}
     </svg>
   `
   .composite([{ input: Buffer.from(svgText), blend: 'over' }])

   STEP 4 — Convert to JPEG at 90% quality:
   .jpeg({ quality: 90, mozjpeg: true })

   STEP 5 — Upload to Vercel Blob:
   const blobKey = `cateros/${brand}/posts/${Date.now()}_${size}.jpg`
   const { url } = await put(blobKey, processedBuffer, {
     access: 'public',
     contentType: 'image/jpeg'
   })

   Return: { feedUrl, storyUrl, linkedinUrl, thumbnailUrl }

7. export async function generateCreativeAsset(params: {
     postId: string
     brand: string
     platform: string
     contentType: string
     caption: string
     captionArabic?: string
   }): Promise<CreativeAsset>

   FULL PIPELINE:

   STEP 1 — Load brand identity
   const identity = await getBrandIdentity(params.brand)

   STEP 2 — Build content brief for Creative Direction
   const brief = `
     Platform: ${params.platform}
     Content type: ${params.contentType}
     Caption: ${params.caption}
     ${params.captionArabic ? 'Arabic caption: ' + params.captionArabic : ''}
   `

   STEP 3 — Generate visual concept via Claude
   const concept = await generateVisualConcept({
     brand: params.brand,
     contentBrief: brief,
     platform: params.platform,
     contentType: params.contentType
   })

   STEP 4 — Create DB record in 'generating' status
   const [asset] = await db.insert(schema.cateros_creative_assets).values({
     brand: params.brand,
     post_id: params.postId,
     content_brief: brief,
     visual_concept: concept.visual_concept,
     dalle_prompt: concept.dalle_prompt,
     generation_model: process.env.IMAGE_GENERATION_MODEL || 'dall-e-3',
     has_text_overlay: concept.text_overlay?.required || false,
     text_overlay_headline: concept.text_overlay?.headline || null,
     text_overlay_subtext: concept.text_overlay?.subtext || null,
     text_overlay_data: concept.text_overlay || null,
     estimated_engagement_potential: concept.estimated_engagement_potential,
     status: 'generating'
   }).returning()

   STEP 5 — Generate image (with retry on failure)
   let rawImageUrl: string
   let attempts = 0
   const prompts = [concept.dalle_prompt, concept.alternative_prompt]

   for (const prompt of prompts) {
     try {
       attempts++
       rawImageUrl = await generateImage(prompt)
       break
     } catch (e) {
       console.error(`[CREATIVE] Generation attempt ${attempts} failed:`, e)
       if (attempts >= 2) throw e
     }
   }

   STEP 6 — Download raw image
   const rawBuffer = await downloadImage(rawImageUrl)

   STEP 7 — Upload raw to blob
   const rawBlob = await put(
     `cateros/${params.brand}/raw/${Date.now()}.jpg`,
     rawBuffer,
     { access: 'public', contentType: 'image/jpeg' }
   )

   STEP 8 — Process all sizes with brand overlays
   const sizesNeeded = params.platform === 'linkedin'
     ? ['linkedin']
     : params.platform === 'instagram_story'
     ? ['story']
     : ['feed', 'story']

   const processed = await processAssets({
     rawImageBuffer: rawBuffer,
     brandIdentity: identity,
     textOverlay: concept.text_overlay,
     sizesNeeded
   })

   STEP 9 — Update DB record with all URLs
   await db.update(schema.cateros_creative_assets)
     .set({
       raw_image_url: rawBlob.url,
       asset_feed_url: processed.feedUrl || null,
       asset_story_url: processed.storyUrl || null,
       asset_linkedin_url: processed.linkedinUrl || null,
       generation_attempts: attempts,
       status: 'ready'
     })
     .where(eq(schema.cateros_creative_assets.id, asset.id))

   STEP 10 — Update social post with the primary image URL
   const primaryImageUrl = processed.feedUrl || processed.linkedinUrl || processed.storyUrl
   await db.update(schema.cateros_social_posts)
     .set({ image_url: primaryImageUrl })
     .where(eq(schema.cateros_social_posts.id, params.postId))

   STEP 11 — Log activity
   await logActivity(
     'creative', `Generated visual asset for ${params.brand} ${params.contentType}`,
     params.brand, params.postId, 'social_post', 'executed'
   )

   return { ...asset, ...processed }

8. export async function regenerateAsset(assetId: string, feedback?: string): Promise<void>
   -- Pull asset from DB
   -- If feedback provided: append to dalle_prompt as negative instruction
   -- Re-run from STEP 5 of generateCreativeAsset
   -- Mark old asset as 'regenerating', replace on completion

9. export async function addToReferenceLibrary(assetId: string): Promise<void>
   -- Pull asset + brand
   -- Add asset_feed_url to cateros_brand_identity.approved_reference_urls array
   -- This builds the brand's visual reference library over time
   -- Called automatically when owner approves a post

Export: {
  generateCreativeAsset,
  regenerateAsset,
  addToReferenceLibrary,
  getBrandIdentity,
  CREATIVE_DIRECTION_PROMPT
}
```

---

## PROMPT C.4 — Update Broadcast Agent to Call Creative

```
Update src/agents/broadcast.ts — generateAndQueuePost function.

Find the section after the Claude response is parsed and the post is saved to DB.
It currently looks like:

  const [post] = await db.insert(schema.cateros_social_posts).values({
    ...
    image_prompt: data.image_prompt,
    status: 'pending_approval',
    ...
  }).returning()

  await queueForApproval({ ... })

REPLACE the queueForApproval call with this new flow:

  // Step 1: Save post with 'generating_visual' status while Creative works
  await db.update(schema.cateros_social_posts)
    .set({ status: 'generating_visual' })
    .where(eq(schema.cateros_social_posts.id, post.id))

  // Step 2: Call Creative Agent to generate the actual visual
  let creativeAsset: any = null
  try {
    const { generateCreativeAsset } = await import('./creative')
    creativeAsset = await generateCreativeAsset({
      postId: post.id,
      brand: params.brand,
      platform: data.platform ?? params.platform,
      contentType: data.content_type,
      caption: data.caption,
      captionArabic: data.caption_arabic ?? undefined
    })
  } catch (e) {
    console.error('[BROADCAST] Creative generation failed, queuing without image:', e)
    // Fail gracefully — still queue for approval, owner will see image is missing
  }

  // Step 3: Queue for approval — now with real image URL in payload
  await queueForApproval({
    type: 'social_post',
    brand: params.brand,
    title: `${params.brand === 'mikana' ? 'LinkedIn' : 'Instagram'} Post: ${data.content_type}`,
    summary: `Platform: ${data.platform}
Best time: ${data.best_publish_day} ${data.best_publish_time}

${data.caption?.slice(0, 200)}...

Hashtags: ${data.hashtags?.slice(0, 5).join(' ')}
${creativeAsset ? '✅ Visual generated' : '⚠️ Visual generation failed — review before publishing'}`,
    payload: {
      postId: post.id,
      caption: data.caption,
      captionArabic: data.caption_arabic,
      platform: data.platform,
      brand: params.brand,
      hashtags: data.hashtags,
      imageUrl: creativeAsset?.asset_feed_url || null,
      storyUrl: creativeAsset?.asset_story_url || null,
      linkedinUrl: creativeAsset?.asset_linkedin_url || null,
      assetId: creativeAsset?.id || null,
      visualConcept: creativeAsset?.visual_concept || null,
      hasImage: !!creativeAsset?.asset_feed_url
    },
    agent: 'broadcast',
    entityId: post.id,
    entityType: 'social_post'
  })

Also update executeApprovedAction in orchestrator.ts:
When a social_post is approved, call addToReferenceLibrary:

  case 'social_post':
    await db.update(cateros_social_posts)
      .set({ status: 'approved', caption: editedContent || undefined })
      .where(eq(cateros_social_posts.id, payload.postId))

    // NEW: Add to brand reference library for future style consistency
    if (payload.assetId) {
      const { addToReferenceLibrary } = await import('@/agents/creative')
      await addToReferenceLibrary(payload.assetId)
    }
    break
```

---

## PROMPT C.5 — Update Approval Cards to Show Real Images

```
Update src/app/briefing/page.tsx and src/app/approvals/page.tsx.

In briefing/page.tsx — inside the approval card map, find the social_post section.
Currently shows: summary text only.

REPLACE the social post card section with:

{a.type === 'social_post' && (
  <div className="mb-3">
    {/* Show real generated image if available */}
    {a.payload?.imageUrl ? (
      <div className="relative rounded-xl overflow-hidden mb-3">
        <img
          src={a.payload.imageUrl}
          alt="Generated visual"
          className="w-full object-cover rounded-xl"
          style={{ maxHeight: '320px' }}
        />
        {/* Platform badge */}
        <div className="absolute top-2 left-2">
          <span className="bg-black/60 text-white text-xs px-2 py-1 rounded-full capitalize">
            {a.payload?.platform?.replace(/_/g, ' ')}
          </span>
        </div>
        {/* Regenerate button */}
        {a.payload?.assetId && (
          <button
            onClick={async (e) => {
              e.stopPropagation()
              await fetch(`/api/creative/regenerate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assetId: a.payload.assetId })
              })
              // Reload approvals after regeneration
              window.location.reload()
            }}
            className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white text-xs px-2 py-1 rounded-full transition-colors"
          >
            🔄 Regenerate
          </button>
        )}
      </div>
    ) : (
      <div className="bg-slate-700 rounded-xl h-32 flex items-center justify-center mb-3">
        <p className="text-slate-500 text-sm">⚠️ No image generated</p>
      </div>
    )}

    {/* Caption */}
    <p className="text-slate-300 text-sm leading-relaxed line-clamp-3">
      {a.payload?.caption}
    </p>

    {/* Visual concept note */}
    {a.payload?.visualConcept && (
      <p className="text-slate-500 text-xs mt-1 italic">
        🎨 {a.payload.visualConcept}
      </p>
    )}

    {/* Hashtags */}
    {a.payload?.hashtags?.length > 0 && (
      <p className="text-blue-400 text-xs mt-1">
        {a.payload.hashtags.slice(0, 6).map((h: string) => `#${h}`).join(' ')}
      </p>
    )}
  </div>
)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In src/app/approvals/page.tsx — find the social_post detail panel section.
Currently shows: caption + hashtags + arabic toggle.

UPDATE it to show the full image preview at the top:

{selected.type === 'social_post' && selected.payload && (
  <div className="bg-slate-800 rounded-xl overflow-hidden mb-4 border border-slate-700">

    {/* Image preview */}
    {selected.payload.imageUrl ? (
      <div className="relative">
        <img
          src={selected.payload.imageUrl}
          alt="Generated visual"
          className="w-full object-cover"
          style={{ maxHeight: '400px' }}
        />
        <div className="absolute top-3 left-3 flex gap-2">
          <span className="bg-black/70 text-white text-xs px-2 py-1 rounded-full capitalize">
            {selected.payload.platform?.replace(/_/g, ' ')}
          </span>
          <span className="bg-green-600/80 text-white text-xs px-2 py-1 rounded-full">
            ✓ Visual ready
          </span>
        </div>
        {selected.payload.assetId && (
          <button
            onClick={() => fetch('/api/creative/regenerate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ assetId: selected.payload.assetId })
            }).then(() => window.location.reload())}
            className="absolute top-3 right-3 bg-black/70 hover:bg-black/90 text-white text-xs px-3 py-1.5 rounded-full transition-colors"
          >
            🔄 Regenerate Image
          </button>
        )}
        {/* Show all sizes as small thumbnails if available */}
        {(selected.payload.storyUrl || selected.payload.linkedinUrl) && (
          <div className="absolute bottom-3 right-3 flex gap-1">
            {selected.payload.storyUrl && (
              <a href={selected.payload.storyUrl} target="_blank"
                className="bg-black/70 text-white text-xs px-2 py-1 rounded-full">
                Story ↗
              </a>
            )}
            {selected.payload.linkedinUrl && (
              <a href={selected.payload.linkedinUrl} target="_blank"
                className="bg-black/70 text-white text-xs px-2 py-1 rounded-full">
                LinkedIn ↗
              </a>
            )}
          </div>
        )}
      </div>
    ) : (
      <div className="h-48 flex items-center justify-center bg-slate-700">
        <div className="text-center">
          <p className="text-4xl mb-2">🎨</p>
          <p className="text-slate-400 text-sm">Image not generated</p>
          <button
            onClick={() => fetch('/api/creative/generate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ postId: selected.payload.postId, brand: selected.brand })
            }).then(() => window.location.reload())}
            className="mt-2 text-xs bg-orange-600 hover:bg-orange-700 text-white px-3 py-1.5 rounded-lg">
            Generate Now
          </button>
        </div>
      </div>
    )}

    {/* Visual concept */}
    {selected.payload.visualConcept && (
      <div className="px-4 py-3 bg-slate-700/50 border-t border-slate-700">
        <p className="text-xs text-slate-400 italic">🎨 {selected.payload.visualConcept}</p>
      </div>
    )}

    <div className="p-4">
      <p className="text-xs text-slate-500 mb-2 capitalize">
        {selected.payload.platform?.replace(/_/g, ' ')}
      </p>
      <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
        {selected.payload.caption}
      </p>
      {selected.payload.hashtags?.length > 0 && (
        <p className="text-xs text-blue-400 mt-2">
          {selected.payload.hashtags.map((h: string) => `#${h}`).join(' ')}
        </p>
      )}
      {selected.payload.captionArabic && (
        <p className="text-sm text-slate-400 leading-relaxed mt-3 pt-3 border-t
          border-slate-700 text-right" dir="rtl">
          {selected.payload.captionArabic}
        </p>
      )}
    </div>
  </div>
)}
```

---

## PROMPT C.6 — Creative API Routes

```
Create these API routes:

━━━ src/app/api/creative/generate/route.ts ━━━
Manually trigger creative generation for a post that has no image.

import { generateCreativeAsset } from '@/agents/creative'
import { db } from '@/lib/db'
import { cateros_social_posts } from '@/lib/schema'
import { eq } from 'drizzle-orm'

export const dynamic = 'force-dynamic'

export async function POST(request: Request) {
  const { postId, brand } = await request.json()

  const post = await db.query.cateros_social_posts.findFirst({
    where: eq(cateros_social_posts.id, postId)
  })
  if (!post) return Response.json({ error: 'Post not found' }, { status: 404 })

  const asset = await generateCreativeAsset({
    postId, brand,
    platform: post.platform || 'instagram',
    contentType: post.content_type || 'product_showcase',
    caption: post.caption || '',
    captionArabic: post.caption_arabic || undefined
  })

  return Response.json({ success: true, asset })
}

━━━ src/app/api/creative/regenerate/route.ts ━━━
Regenerate an asset with optional feedback.

import { regenerateAsset } from '@/agents/creative'
export const dynamic = 'force-dynamic'
export async function POST(request: Request) {
  const { assetId, feedback } = await request.json()
  await regenerateAsset(assetId, feedback)
  return Response.json({ success: true })
}

━━━ src/app/api/creative/assets/route.ts ━━━
List creative assets, optionally filtered by brand.

import { db } from '@/lib/db'
import { cateros_creative_assets } from '@/lib/schema'
import { eq, desc } from 'drizzle-orm'
export const dynamic = 'force-dynamic'
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const brand = searchParams.get('brand')
  const limit = parseInt(searchParams.get('limit') || '20')
  const where = brand ? eq(cateros_creative_assets.brand, brand) : undefined
  const data = await db.query.cateros_creative_assets.findMany({
    where, orderBy: [desc(cateros_creative_assets.created_at)], limit
  })
  return Response.json({ data })
}

━━━ src/app/api/creative/brand-identity/route.ts ━━━
GET and PATCH brand identity configuration.

import { db } from '@/lib/db'
import { cateros_brand_identity } from '@/lib/schema'
import { eq } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const brand = searchParams.get('brand')
  if (!brand) return Response.json({ error: 'brand required' }, { status: 400 })
  const data = await db.query.cateros_brand_identity.findFirst({
    where: eq(cateros_brand_identity.brand, brand)
  })
  return Response.json({ data })
}

export async function PATCH(request: Request) {
  const { brand, ...updates } = await request.json()
  if (!brand) return Response.json({ error: 'brand required' }, { status: 400 })
  await db.update(cateros_brand_identity)
    .set({ ...updates, updated_at: new Date() })
    .where(eq(cateros_brand_identity.brand, brand))
  return Response.json({ success: true })
}
```

---

## PROMPT C.7 — Creative Studio Page

```
Build src/app/creative/page.tsx — Brand identity config + asset library.

'use client'
import { useState, useEffect } from 'react'

export default function CreativePage() {
  const [brand, setBrand] = useState<'mikana' | 'boxedgo'>('boxedgo')
  const [identity, setIdentity] = useState<any>(null)
  const [assets, setAssets] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'library' | 'identity'>('library')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`/api/creative/brand-identity?brand=${brand}`)
      .then(r => r.json()).then(d => setIdentity(d.data))
    fetch(`/api/creative/assets?brand=${brand}&limit=30`)
      .then(r => r.json()).then(d => setAssets(d.data || []))
  }, [brand])

  async function saveIdentity() {
    setSaving(true)
    await fetch('/api/creative/brand-identity', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand, ...identity })
    })
    setSaving(false)
  }

  const brandColor = brand === 'mikana' ? '#E8490F' : '#c2714f'

  return (
    <div className="h-full flex flex-col">
      {/* Brand switcher */}
      <div className="flex border-b border-slate-800">
        {(['mikana', 'boxedgo'] as const).map(b => (
          <button key={b} onClick={() => setBrand(b)}
            className={`flex-1 py-4 text-sm font-semibold transition-colors ${brand === b ? 'text-white border-b-2' : 'text-slate-400'}`}
            style={brand === b ? { borderColor: brandColor } : {}}>
            {b === 'mikana' ? 'Mikana Food Service' : 'Boxed & Go'}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Tabs */}
        <div className="w-48 border-r border-slate-800 p-3 space-y-1">
          {([
            { key: 'library', label: '🖼️ Asset Library' },
            { key: 'identity', label: '🎨 Brand Identity' },
          ] as const).map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              className={`w-full text-left text-sm px-3 py-2 rounded-lg ${activeTab === t.key ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6">

          {/* ASSET LIBRARY */}
          {activeTab === 'library' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-semibold">Generated Assets ({assets.length})</h2>
              </div>
              {assets.length === 0 ? (
                <div className="text-center py-16 text-slate-600">
                  <p className="text-4xl mb-3">🎨</p>
                  <p>No assets yet. Approve a social post to generate visuals.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {assets.map(asset => (
                    <div key={asset.id} className="bg-slate-800 rounded-xl overflow-hidden group">
                      {asset.asset_feed_url ? (
                        <div className="relative">
                          <img src={asset.asset_feed_url} alt={asset.visual_concept}
                            className="w-full aspect-square object-cover" />
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <a href={asset.asset_feed_url} target="_blank"
                              className="text-xs bg-white text-black px-2 py-1 rounded">
                              Feed ↗
                            </a>
                            {asset.asset_story_url && (
                              <a href={asset.asset_story_url} target="_blank"
                                className="text-xs bg-white text-black px-2 py-1 rounded">
                                Story ↗
                              </a>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="aspect-square bg-slate-700 flex items-center justify-center">
                          <p className="text-slate-500 text-xs">No image</p>
                        </div>
                      )}
                      <div className="p-3">
                        <p className="text-slate-300 text-xs line-clamp-2">{asset.visual_concept}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs ${asset.estimated_engagement_potential === 'high' ? 'text-green-400' : asset.estimated_engagement_potential === 'medium' ? 'text-amber-400' : 'text-slate-400'}`}>
                            {asset.estimated_engagement_potential} engagement
                          </span>
                          {asset.added_to_brand_references && (
                            <span className="text-xs text-blue-400">📌 Reference</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* BRAND IDENTITY EDITOR */}
          {activeTab === 'identity' && identity && (
            <div className="max-w-xl space-y-5">
              <h2 className="text-white font-semibold">Brand Identity Configuration</h2>
              <p className="text-slate-400 text-sm">
                These settings govern every image the Creative Agent generates.
                Changes take effect on the next generation.
              </p>

              {/* Photography style */}
              <div>
                <label className="text-xs text-slate-400 block mb-2">Photography Style</label>
                <div className="grid grid-cols-2 gap-2">
                  {['warm_natural', 'dark_moody', 'bright_clean', 'rustic', 'minimalist'].map(s => (
                    <button key={s} onClick={() => setIdentity({...identity, photography_style: s})}
                      className={`text-sm px-3 py-2 rounded-lg capitalize ${identity.photography_style === s ? 'text-white' : 'text-slate-400 bg-slate-800 hover:text-white'}`}
                      style={identity.photography_style === s ? { background: brandColor } : {}}>
                      {s.replace(/_/g, ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Hero shot */}
              <div>
                <label className="text-xs text-slate-400 block mb-2">Hero Shot Description</label>
                <textarea value={identity.hero_shot_description || ''}
                  onChange={e => setIdentity({...identity, hero_shot_description: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-sm text-white resize-none focus:border-orange-500 focus:outline-none"
                  rows={3} />
              </div>

              {/* Tagline */}
              <div>
                <label className="text-xs text-slate-400 block mb-2">Brand Tagline</label>
                <input value={identity.tagline || ''}
                  onChange={e => setIdentity({...identity, tagline: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:border-orange-500 focus:outline-none" />
              </div>

              {/* Reference images */}
              {identity.approved_reference_urls?.length > 0 && (
                <div>
                  <label className="text-xs text-slate-400 block mb-2">
                    Approved Reference Images ({identity.approved_reference_urls.length})
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {identity.approved_reference_urls.slice(0, 8).map((url: string, i: number) => (
                      <img key={i} src={url} alt="Reference"
                        className="w-full aspect-square object-cover rounded-lg" />
                    ))}
                  </div>
                  <p className="text-slate-500 text-xs mt-1">
                    Added automatically when you approve posts. Used for style consistency.
                  </p>
                </div>
              )}

              <button onClick={saveIdentity} disabled={saving}
                className="w-full py-3 rounded-xl text-white font-semibold text-sm disabled:opacity-50 transition-colors"
                style={{ background: brandColor }}>
                {saving ? 'Saving…' : 'Save Brand Identity'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## PROMPT C.8 — Add Creative to Sidebar Navigation

```
Update src/components/ui/Sidebar.tsx

Add to the NAV array, after the Broadcast entry:

  { href: '/creative', icon: Palette, label: 'Creative Studio', badgeKey: 'creative' },

Add Palette to the lucide-react import:
  import { ..., Palette } from 'lucide-react'

The Creative Studio entry sits between Broadcast and SEO Engine in the nav.
```

---

## PROMPT C.9 — Update Seed to Generate Sample Assets

```
Add to the END of runSeed() in src/lib/seed.ts, after the competitors section:

  // Generate 3 sample creative briefs to test the Creative Agent
  // (only runs if OPENAI_API_KEY is set)
  if (process.env.OPENAI_API_KEY) {
    console.log('🎨 Generating sample creative assets...')
    try {
      const { generateCreativeAsset } = await import('../agents/creative')

      // Find the first approved or pending_approval post, or create a test post
      const [testPost] = await db.insert(schema.cateros_social_posts).values({
        brand: 'boxedgo',
        platform: 'instagram',
        content_type: 'product_showcase',
        caption: 'The Sizzle Moment. Your protein hitting the pan — 80% done, 13 minutes to perfect. This is Build Your Plate. 🔥',
        caption_arabic: 'لحظة الإشباع. البروتين الخاص بك على المقلاة — ٨٠٪ جاهز، ١٣ دقيقة للكمال.',
        hashtags: ['boxedandgo', 'mealprep', 'dubaifood', 'buildyourplate', 'healthydubai'],
        status: 'pending_approval',
        scheduled_at: new Date(Date.now() + 86400000)
      }).returning()

      await generateCreativeAsset({
        postId: testPost.id,
        brand: 'boxedgo',
        platform: 'instagram',
        contentType: 'product_showcase',
        caption: testPost.caption || '',
        captionArabic: testPost.caption_arabic || undefined
      })

      console.log('✅ Sample creative asset generated for Boxed & Go')
    } catch (e) {
      console.log('⚠️ Creative generation skipped (check OPENAI_API_KEY):', e)
    }
  }
```

---

## SYSTEM INTEGRATION SUMMARY

```
CREATIVE AGENT — WHERE IT FITS IN THE FULL FLOW:

Owner approves quarterly targets
  → Orchestrator allocates budget
    → Scout identifies leads + audience
      → Pipeline drafts outreach
        → Broadcast generates caption + content brief
          → *** CREATIVE AGENT generates actual visual ***
            → Approval card shows: real image + caption + hashtags
              → Owner approves (or clicks Regenerate)
                → Broadcast publishes to Instagram/LinkedIn
                  → Engagement Sync measures performance
                    → Approved image added to brand reference library
                      → Next generation uses it for style consistency

WHAT OWNER SEES IN APPROVAL (before vs after):

BEFORE:
  📱 Instagram Post: product_showcase
  "Platform: instagram · Best time: Wednesday 12:00pm
   The Sizzle Moment. Your protein hitting the pan...
   📷 Image prompt: warm close-up of chicken hitting sizzling pan..."

AFTER:
  📱 Instagram Post: product_showcase
  [ACTUAL PHOTOREALISTIC IMAGE OF THE SIZZLE MOMENT]
  [🔄 Regenerate button]
  "The Sizzle Moment. Your protein hitting the pan..."
  #boxedandgo #buildyourplate #dubaifood
  [Arabic caption]

COST PER CLIENT (added to platform operating costs):
  DALL-E 3 generations (8 posts/week × 4 weeks × $0.06):  ~$19/month
  Vercel Blob storage (~500MB/month at $0.02/GB):          ~$0.01/month
  Sharp processing (compute — included in Vercel):         $0/month
  Total additional cost per client:                        ~$20/month

Add $20 to platform cost estimates per client.
At $2,500–8,000/month retainer, this is negligible.
At 20 clients, total Creative Agent cost: ~$400/month.

PROMPT COUNT ADDED: 9 prompts (C.1 through C.9)
UPDATED TOTAL: 37 prompts across 11 phases
```
# PHASE F — FIXES & COMPLETIONS
## All corrections applied to CaterOS v4 + Creative Agent
## Apply these prompts AFTER completing Phases 0–C

---

## ISSUES FIXED IN THIS ADDENDUM

1. PROMPT 7.3 routes were prose stubs — all replaced with full implementation code
2. Customer Care missing: sendResponse, processQRScan, runPatternAnalysis
3. /api/care/feedback/[id] PATCH route was absent
4. Field name mismatch: UI sent editedPayload, PATCH route expected editedContent — unified
5. /api/financial/spend GET was missing envelope data needed by dashboard
6. /api/financial/targets/propose route was missing
7. /api/pipeline/schools/[id]/generate-outreach route was missing
8. /api/pipeline/corporate/[id]/generate-outreach route was missing
9. openai package missing from PROMPT 0.1 scaffold install
10. Creative Agent C.4 editedContent inconsistency corrected

---

## PROMPT F.1 — Fix Package Install (update PROMPT 0.1)

```
In the root package.json, ensure these packages are installed.
Run this command to add the missing ones:

npm install openai sharp @vercel/blob

Your full dependency list should now include:
@neondatabase/serverless drizzle-orm drizzle-kit @anthropic-ai/sdk
resend date-fns zod lucide-react recharts clsx tailwind-merge
@hello-pangea/dnd qrcode openai sharp @vercel/blob uuid
@radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-tabs
@radix-ui/react-dropdown-menu @radix-ui/react-popover

Dev dependencies:
@types/qrcode @types/sharp

Verify installation:
node -e "require('openai'); require('sharp'); console.log('OK')"
```

---

## PROMPT F.2 — Fix Approval Route Field Name Consistency

```
The approval system uses two field names inconsistently.
Apply this fix everywhere:

CANONICAL FIELD NAMES (use these everywhere):
  From UI to API:   { decision, editedPayload: { content: string } | undefined }
  From API to DB:   edited_payload (jsonb column)
  From DB to agent: request.edited_payload?.content

━━━ Fix src/app/api/approvals/[id]/route.ts ━━━
Replace the entire file with:

import { db } from '@/lib/db'
import { cateros_approval_requests } from '@/lib/schema'
import { eq } from 'drizzle-orm'
import { executeApprovedAction } from '@/agents/orchestrator'

export const dynamic = 'force-dynamic'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const item = await db.query.cateros_approval_requests.findFirst({
    where: eq(cateros_approval_requests.id, params.id)
  })
  if (!item) return Response.json({ error: 'Not found' }, { status: 404 })
  return Response.json({ data: item })
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  const { decision, editedPayload, reason } = body
  const editedContent = editedPayload?.content ?? null

  await db.update(cateros_approval_requests).set({
    status: decision,
    owner_decision: reason ?? decision,
    edited_payload: editedPayload ?? null,
    responded_at: new Date(),
    updated_at: new Date()
  }).where(eq(cateros_approval_requests.id, params.id))

  if (decision === 'approved' || decision === 'edited') {
    const record = await db.query.cateros_approval_requests.findFirst({
      where: eq(cateros_approval_requests.id, params.id)
    })
    if (record) await executeApprovedAction(record, editedContent)
  }

  return Response.json({ success: true, decision })
}

━━━ Fix src/app/api/approvals/route.ts ━━━
Replace with:

import { db } from '@/lib/db'
import { cateros_approval_requests } from '@/lib/schema'
import { eq, desc, and, or } from 'drizzle-orm'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const status = searchParams.get('status') || 'pending'
  const brand = searchParams.get('brand')
  const type = searchParams.get('type')
  const limit = parseInt(searchParams.get('limit') || '20')

  const conditions = []
  if (status !== 'all') conditions.push(eq(cateros_approval_requests.status, status))
  if (brand) conditions.push(eq(cateros_approval_requests.brand, brand))
  if (type) conditions.push(eq(cateros_approval_requests.type, type))

  const data = await db.query.cateros_approval_requests.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_approval_requests.created_at)],
    limit
  })

  return Response.json({ data, count: data.length })
}
```

---

## PROMPT F.3 — Complete Customer Care Agent (Missing Functions)

```
Add these three missing functions to src/agents/customer-care.ts,
BEFORE the final export statement.

━━━ FUNCTION: sendResponse ━━━

export async function sendResponse(
  feedbackId: string,
  approvedText: string,
  channel: string
): Promise<void> {
  const feedback = await db.query.cateros_feedback.findFirst({
    where: eq(schema.cateros_feedback.id, feedbackId)
  })
  if (!feedback) throw new Error('Feedback not found: ' + feedbackId)

  // Send via appropriate channel
  if (channel === 'whatsapp' && feedback.customer_whatsapp) {
    const { sendWhatsApp } = await import('@/integrations/whatsapp')
    await sendWhatsApp(feedback.customer_whatsapp, approvedText)
  } else if (channel === 'email' && feedback.customer_email) {
    const { sendEmail } = await import('@/integrations/resend')
    const brand = feedback.brand === 'mikana' ? 'Mikana Food Service' : 'Boxed & Go'
    await sendEmail({
      to: feedback.customer_email,
      subject: `Re: Your feedback — ${brand}`,
      body: approvedText
    })
  }

  // Update feedback record
  await db.update(schema.cateros_feedback).set({
    status: 'resolved',
    response_sent: approvedText,
    responded_at: new Date(),
    resolved_at: new Date(),
    updated_at: new Date()
  }).where(eq(schema.cateros_feedback.id, feedbackId))

  await logActivity(
    'customer_care', `Response sent for feedback ${feedbackId}`,
    feedback.brand, feedbackId, 'feedback', 'executed'
  )
}

━━━ FUNCTION: processQRScan ━━━

export async function processQRScan(
  code: string,
  formData: {
    rating?: number
    raw_text: string
    customer_name?: string
    customer_email?: string
    customer_whatsapp?: string
  }
): Promise<string> {
  // Find QR code record
  const qr = await db.query.cateros_qr_codes.findFirst({
    where: eq(schema.cateros_qr_codes.code, code)
  })
  if (!qr || !qr.is_active) throw new Error('Invalid or inactive QR code')

  // Increment scan + feedback counts
  await db.update(schema.cateros_qr_codes).set({
    scan_count: (qr.scan_count || 0) + 1,
    feedback_count: (qr.feedback_count || 0) + 1
  }).where(eq(schema.cateros_qr_codes.code, code))

  // Create feedback record
  const [feedback] = await db.insert(schema.cateros_feedback).values({
    brand: qr.brand,
    feedback_type: (formData.rating || 0) >= 4 ? 'testimonial' : 'complaint',
    channel: 'qr_code',
    raw_text: formData.raw_text,
    rating: formData.rating || null,
    customer_name: formData.customer_name || null,
    customer_email: formData.customer_email || null,
    customer_whatsapp: formData.customer_whatsapp || null,
    qr_code_id: code,
    qr_scan_location: qr.linked_entity_label || null,
    status: 'new',
    urgency: 'normal'
  }).returning()

  // Classify asynchronously (don't await — return fast for the form)
  classifyFeedback(feedback.id).catch(e =>
    console.error('[CARE] Background classification failed:', e)
  )

  return feedback.id
}

━━━ FUNCTION: runPatternAnalysis ━━━

export const CARE_PATTERN_PROMPT = `
You are analysing customer feedback patterns for CaterOS.

Identify patterns with ROI framing:
- Complaint clusters: 3+ complaints about the same issue in 7 days = pattern
- Product flags: >5% complaint rate on a specific meal/plan = flag for Orchestrator
- At-risk clusters: multiple at-risk flags in same segment or school
- Churn signals: trial subscribers complaining within first 3 deliveries
- Positive patterns: recurring praise themes = amplify in marketing

ROI LENS:
- Churned BG subscriber = lost AED 13,800 average LTV (12 months × AED 1,150)
- Lost school renewal = lost AED 400K-800K
- Resolved at-risk customer = retained LTV
Frame every pattern in financial terms.

OUTPUT — valid JSON:
{
  "complaint_patterns": [
    {
      "category": "string",
      "count": number,
      "example_quotes": ["string"],
      "product_ids_affected": ["string"],
      "revenue_at_risk_aed": number,
      "recommended_action": "string"
    }
  ],
  "product_flags": [
    {
      "product_name": "string",
      "complaint_rate_pct": number,
      "issue_summary": "string",
      "verdict_suggestion": "string"
    }
  ],
  "at_risk_summary": {
    "count": number,
    "total_ltv_at_risk_aed": number,
    "top_reasons": ["string"]
  },
  "positive_patterns": [
    { "theme": "string", "count": number, "marketing_angle": "string" }
  ],
  "testimonials_ready": number,
  "executive_summary": "string — 3 sentences max, financial impact first"
}
`

export async function runPatternAnalysis(): Promise<void> {
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000)

  const [recentFeedback, atRiskItems] = await Promise.all([
    db.query.cateros_feedback.findMany({
      where: and(
        gte(schema.cateros_feedback.created_at, sevenDaysAgo),
        eq(schema.cateros_feedback.status, 'new')
      ),
      orderBy: [desc(schema.cateros_feedback.created_at)]
    }),
    db.query.cateros_feedback.findMany({
      where: eq(schema.cateros_feedback.is_at_risk_flag, true)
    })
  ])

  if (recentFeedback.length === 0) return

  const response = await callClaude({
    systemPrompt: CARE_PATTERN_PROMPT,
    userMessage: JSON.stringify({
      feedback_items: recentFeedback.map(f => ({
        brand: f.brand,
        type: f.feedback_type,
        urgency: f.urgency,
        categories: f.complaint_categories,
        rating: f.rating,
        sentiment: f.sentiment_score,
        text_excerpt: f.raw_text?.substring(0, 200),
        is_at_risk: f.is_at_risk_flag
      })),
      at_risk_count: atRiskItems.length,
      period_days: 7
    }),
    maxTokens: 2000,
    jsonMode: true
  })

  const analysis = JSON.parse(response)

  // Save to intelligence
  await db.insert(schema.cateros_intelligence).values({
    brand: 'both',
    report_type: 'product_review',
    title: `Feedback Pattern Analysis — ${new Date().toLocaleDateString('en-AE')}`,
    summary: analysis.executive_summary,
    full_report: JSON.stringify(analysis),
    urgency: atRiskItems.length > 3 ? 'urgent' : 'normal',
    status: 'new'
  })

  // Flag products that need Orchestrator review
  for (const flag of analysis.product_flags || []) {
    if (flag.complaint_rate_pct > 10) {
      const { queueForApproval } = await import('./orchestrator')
      await queueForApproval({
        type: 'product_verdict',
        brand: 'both',
        title: `Product Flag: ${flag.product_name}`,
        summary: `${flag.complaint_rate_pct}% complaint rate. ${flag.issue_summary}. Suggested action: ${flag.verdict_suggestion}`,
        payload: flag,
        agent: 'customer_care',
        entityId: feedbackId,
        entityType: 'product_flag',
        priority: 'normal'
      })
    }
  }

  await logActivity('customer_care', 'Pattern analysis completed',
    'both', undefined, 'intelligence', 'executed')
}

━━━ UPDATE EXPORTS at bottom of customer-care.ts ━━━
Replace the current export line with:
export {
  classifyFeedback, draftResponse, sendResponse,
  processFeedbackBatch, processQRScan, runPatternAnalysis,
  generateQRCode, runCompetitiveIntelligence, runBlueOceanSynthesis,
  CARE_CLASSIFICATION_PROMPT, CARE_RESPONSE_PROMPT,
  CARE_PATTERN_PROMPT, COMPETITIVE_PROFILING_PROMPT, BLUE_OCEAN_SYNTHESIS_PROMPT
}
```

---

## PROMPT F.4 — Complete All Domain API Routes (Full Code)

```
Replace the prose stubs in PROMPT 7.3 with these full implementations.
Create each file exactly as written.

━━━ src/app/api/care/feedback/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_feedback } from '@/lib/schema'
import { eq, desc, and } from 'drizzle-orm'
import { classifyFeedback } from '@/agents/customer-care'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const urgency = searchParams.get('urgency')
  const status = searchParams.get('status') || 'new'
  const brand = searchParams.get('brand')
  const limit = parseInt(searchParams.get('limit') || '50')

  const conditions = [eq(cateros_feedback.status, status)]
  if (urgency) conditions.push(eq(cateros_feedback.urgency, urgency))
  if (brand) conditions.push(eq(cateros_feedback.brand, brand))

  const data = await db.query.cateros_feedback.findMany({
    where: and(...conditions),
    orderBy: [desc(cateros_feedback.created_at)],
    limit
  })
  return Response.json({ data })
}

export async function POST(request: Request) {
  // PUBLIC — no auth — receives QR form + website form submissions
  const body = await request.json()

  const [feedback] = await db.insert(cateros_feedback).values({
    brand: body.brand,
    feedback_type: body.feedback_type || 'neutral',
    channel: body.channel || 'website_form',
    raw_text: body.raw_text,
    rating: body.rating || null,
    customer_name: body.customer_name || null,
    customer_email: body.customer_email || null,
    customer_whatsapp: body.customer_whatsapp || null,
    qr_code_id: body.qr_code_id || null,
    status: 'new',
    urgency: 'normal'
  }).returning()

  // Classify asynchronously — don't block the response
  classifyFeedback(feedback.id).catch(e =>
    console.error('[CARE] Background classification failed:', e)
  )

  return Response.json({ success: true, message: 'Thank you for your feedback' })
}

━━━ src/app/api/care/feedback/[id]/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_feedback } from '@/lib/schema'
import { eq } from 'drizzle-orm'
import { sendResponse, draftResponse } from '@/agents/customer-care'

export const dynamic = 'force-dynamic'

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const data = await db.query.cateros_feedback.findFirst({
    where: eq(cateros_feedback.id, params.id)
  })
  if (!data) return Response.json({ error: 'Not found' }, { status: 404 })
  return Response.json({ data })
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  const { action, response_text, response_channel, status } = body

  if (action === 'approve_and_send' && response_text) {
    const feedback = await db.query.cateros_feedback.findFirst({
      where: eq(cateros_feedback.id, params.id)
    })
    if (!feedback) return Response.json({ error: 'Not found' }, { status: 404 })
    const channel = response_channel || feedback.response_channel || 'email'
    await sendResponse(params.id, response_text, channel)
    return Response.json({ success: true, action: 'sent' })
  }

  if (action === 'draft_response') {
    await draftResponse(params.id)
    const updated = await db.query.cateros_feedback.findFirst({
      where: eq(cateros_feedback.id, params.id)
    })
    return Response.json({ data: updated })
  }

  // Generic status/notes update
  await db.update(cateros_feedback).set({
    ...(status && { status }),
    ...(response_text && { response_draft: response_text }),
    updated_at: new Date()
  }).where(eq(cateros_feedback.id, params.id))

  return Response.json({ success: true })
}

━━━ src/app/api/care/feedback/inbox/route.ts ━━━
-- Alias route used by care page
import { db } from '@/lib/db'
import { cateros_feedback } from '@/lib/schema'
import { eq, desc, and, ne } from 'drizzle-orm'
export const dynamic = 'force-dynamic'
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const urgency = searchParams.get('urgency')
  const brand = searchParams.get('brand')
  const limit = parseInt(searchParams.get('limit') || '50')
  const conditions = [ne(cateros_feedback.status, 'resolved')]
  if (urgency && urgency !== 'all') conditions.push(eq(cateros_feedback.urgency, urgency))
  if (brand) conditions.push(eq(cateros_feedback.brand, brand))
  const data = await db.query.cateros_feedback.findMany({
    where: and(...conditions),
    orderBy: [desc(cateros_feedback.created_at)],
    limit
  })
  return Response.json({ data })
}

━━━ src/app/api/care/qrcodes/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_qr_codes } from '@/lib/schema'
import { eq, desc } from 'drizzle-orm'
import { generateQRCode } from '@/agents/customer-care'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  const brand = searchParams.get('brand')
  if (code) {
    const data = await db.query.cateros_qr_codes.findFirst({
      where: eq(cateros_qr_codes.code, code)
    })
    return Response.json({ data })
  }
  const conditions = brand ? [eq(cateros_qr_codes.brand, brand)] : []
  const data = await db.query.cateros_qr_codes.findMany({
    where: conditions.length > 0 ? conditions[0] : undefined,
    orderBy: [desc(cateros_qr_codes.created_at)]
  })
  return Response.json({ data })
}

export async function POST(request: Request) {
  const body = await request.json()
  const result = await generateQRCode({
    brand: body.brand,
    purpose: body.purpose || 'meal_packaging',
    linkedEntityType: body.linkedEntityType,
    linkedEntityId: body.linkedEntityId,
    linkedEntityLabel: body.linkedEntityLabel
  })
  return Response.json({ success: true, data: result })
}

━━━ src/app/api/care/testimonials/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_testimonials } from '@/lib/schema'
import { eq, desc, and } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const brand = searchParams.get('brand')
  const status = searchParams.get('status')
  const conditions = []
  if (brand) conditions.push(eq(cateros_testimonials.brand, brand))
  if (status) conditions.push(eq(cateros_testimonials.status, status))
  const data = await db.query.cateros_testimonials.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_testimonials.created_at)]
  })
  return Response.json({ data })
}

export async function PATCH(request: Request) {
  const { searchParams } = new URL(request.url)
  const id = searchParams.get('id')
  if (!id) return Response.json({ error: 'id required' }, { status: 400 })
  const body = await request.json()
  await db.update(cateros_testimonials).set({
    ...body, updated_at: new Date()
  }).where(eq(cateros_testimonials.id, id))
  return Response.json({ success: true })
}

━━━ src/app/api/financial/roi/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_roi_snapshots } from '@/lib/schema'
import { desc } from 'drizzle-orm'
import { runROIAnalysis } from '@/agents/orchestrator'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const period = searchParams.get('period') || 'rolling_30'
  const data = await db.query.cateros_roi_snapshots.findFirst({
    orderBy: [desc(cateros_roi_snapshots.created_at)]
  })
  return Response.json({ data })
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}))
  const period = body.period || 'rolling_30'
  const snapshot = await runROIAnalysis(period)
  return Response.json({ success: true, data: snapshot })
}

━━━ src/app/api/financial/spend/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_spend_entries, cateros_budget_envelopes } from '@/lib/schema'
import { desc } from 'drizzle-orm'
import { logSpend } from '@/agents/orchestrator'
export const dynamic = 'force-dynamic'

export async function GET() {
  const [entries, envelopes] = await Promise.all([
    db.query.cateros_spend_entries.findMany({
      orderBy: [desc(cateros_spend_entries.created_at)],
      limit: 50
    }),
    db.query.cateros_budget_envelopes.findMany()
  ])
  return Response.json({ data: entries, envelopes })
}

export async function POST(request: Request) {
  const body = await request.json()
  const entry = await logSpend(body)
  return Response.json({ success: true, data: entry })
}

━━━ src/app/api/financial/revenue/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_revenue_entries } from '@/lib/schema'
import { desc } from 'drizzle-orm'
import { logRevenue } from '@/agents/orchestrator'
export const dynamic = 'force-dynamic'

export async function GET() {
  const data = await db.query.cateros_revenue_entries.findMany({
    orderBy: [desc(cateros_revenue_entries.created_at)],
    limit: 100
  })
  return Response.json({ data })
}

export async function POST(request: Request) {
  const body = await request.json()
  const entry = await logRevenue(body)
  return Response.json({ success: true, data: entry })
}

━━━ src/app/api/financial/targets/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_business_targets } from '@/lib/schema'
import { desc, eq } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET() {
  const data = await db.query.cateros_business_targets.findFirst({
    where: eq(cateros_business_targets.status, 'approved'),
    orderBy: [desc(cateros_business_targets.created_at)]
  })
  return Response.json({ data })
}

━━━ src/app/api/financial/targets/propose/route.ts ━━━
import { proposeQuarterlyTargets } from '@/agents/orchestrator'
export const dynamic = 'force-dynamic'
export async function POST() {
  await proposeQuarterlyTargets()
  return Response.json({ success: true, message: 'Quarterly targets proposal queued — check your WhatsApp.' })
}

━━━ src/app/api/financial/platform-costs/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_platform_cost_budgets, cateros_platform_cost_entries } from '@/lib/schema'
import { eq, desc } from 'drizzle-orm'
import { logPlatformCost } from '@/agents/orchestrator'
export const dynamic = 'force-dynamic'

export async function GET() {
  const now = new Date()
  const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const [budget, entries] = await Promise.all([
    db.query.cateros_platform_cost_budgets.findFirst({
      where: eq(cateros_platform_cost_budgets.period, period)
    }),
    db.query.cateros_platform_cost_entries.findMany({
      where: eq(cateros_platform_cost_entries.billing_period, period),
      orderBy: [desc(cateros_platform_cost_entries.created_at)]
    })
  ])
  const pct = budget
    ? (parseFloat(String(budget.actual_spend_aed || '0')) /
       parseFloat(String(budget.approved_ceiling_aed || '1')) * 100).toFixed(1)
    : '0'
  return Response.json({ data: { ...budget, platform_cost_pct: pct }, entries })
}

export async function POST(request: Request) {
  const body = await request.json()
  const entry = await logPlatformCost(body)
  return Response.json({ success: true, data: entry })
}

━━━ src/app/api/pipeline/schools/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_school_leads, cateros_schools, cateros_contacts } from '@/lib/schema'
import { eq, desc, and, lte } from 'drizzle-orm'
import { sql } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const stage = searchParams.get('stage')
  const leadType = searchParams.get('lead_type')
  const overdue = searchParams.get('overdue') === 'true'

  const conditions = []
  if (stage) conditions.push(eq(cateros_school_leads.stage, stage))
  if (leadType) conditions.push(eq(cateros_school_leads.lead_type, leadType))
  if (overdue) conditions.push(lte(cateros_school_leads.next_action_date, new Date().toISOString().split('T')[0]))

  const leads = await db.query.cateros_school_leads.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_school_leads.updated_at)]
  })

  // Join school names
  const enriched = await Promise.all(leads.map(async lead => {
    const school = lead.school_id
      ? await db.query.cateros_schools.findFirst({ where: eq(cateros_schools.id, lead.school_id) })
      : null
    return { ...lead, school_name: school?.name, school_emirate: school?.emirate, qualification_score: school?.qualification_score }
  }))

  return Response.json({ data: enriched })
}

━━━ src/app/api/pipeline/schools/[id]/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_school_leads } from '@/lib/schema'
import { eq } from 'drizzle-orm'
export const dynamic = 'force-dynamic'
export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  await db.update(cateros_school_leads).set({ ...body, updated_at: new Date() })
    .where(eq(cateros_school_leads.id, params.id))
  return Response.json({ success: true })
}

━━━ src/app/api/pipeline/schools/[id]/generate-outreach/route.ts ━━━
import { generateSchoolOutreach } from '@/agents/pipeline'
export const dynamic = 'force-dynamic'
export async function POST(_: Request, { params }: { params: { id: string } }) {
  await generateSchoolOutreach(params.id)
  return Response.json({ success: true, message: 'Outreach sequence generating — check approvals inbox.' })
}

━━━ src/app/api/pipeline/corporate/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_corporate_leads, cateros_companies } from '@/lib/schema'
import { eq, desc, and } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const stage = searchParams.get('stage')
  const conditions = stage ? [eq(cateros_corporate_leads.stage, stage)] : []
  const leads = await db.query.cateros_corporate_leads.findMany({
    where: conditions.length > 0 ? conditions[0] : undefined,
    orderBy: [desc(cateros_corporate_leads.updated_at)]
  })
  const enriched = await Promise.all(leads.map(async lead => {
    const company = lead.company_id
      ? await db.query.cateros_companies.findFirst({ where: eq(cateros_companies.id, lead.company_id) })
      : null
    return { ...lead, company_name: company?.name, company_industry: company?.industry }
  }))
  return Response.json({ data: enriched })
}

━━━ src/app/api/pipeline/corporate/[id]/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_corporate_leads } from '@/lib/schema'
import { eq } from 'drizzle-orm'
export const dynamic = 'force-dynamic'
export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  await db.update(cateros_corporate_leads).set({ ...body, updated_at: new Date() })
    .where(eq(cateros_corporate_leads.id, params.id))
  return Response.json({ success: true })
}

━━━ src/app/api/pipeline/corporate/[id]/generate-outreach/route.ts ━━━
import { generateCorporateOutreach } from '@/agents/pipeline'
export const dynamic = 'force-dynamic'
export async function POST(_: Request, { params }: { params: { id: string } }) {
  await generateCorporateOutreach(params.id)
  return Response.json({ success: true, message: 'Outreach sequence generating — check approvals inbox.' })
}

━━━ src/app/api/pipeline/boxedgo/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_bg_subscribers } from '@/lib/schema'
import { eq, desc, and } from 'drizzle-orm'
import { generateBoxedGoMessage } from '@/agents/pipeline'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const stage = searchParams.get('stage')
  const segment = searchParams.get('segment')
  const atRisk = searchParams.get('at_risk') === 'true'
  const conditions = []
  if (stage) conditions.push(eq(cateros_bg_subscribers.stage, stage))
  if (segment) conditions.push(eq(cateros_bg_subscribers.segment, segment))
  const data = await db.query.cateros_bg_subscribers.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_bg_subscribers.created_at)]
  })
  return Response.json({ data })
}

export async function POST(request: Request) {
  const body = await request.json()
  const [subscriber] = await db.insert(cateros_bg_subscribers).values({
    ...body, stage: 'awareness'
  }).returning()
  await generateBoxedGoMessage(subscriber.id, 'interest')
  return Response.json({ success: true, data: subscriber })
}

━━━ src/app/api/pipeline/boxedgo/[id]/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_bg_subscribers } from '@/lib/schema'
import { eq } from 'drizzle-orm'
import { generateBoxedGoMessage } from '@/agents/pipeline'
export const dynamic = 'force-dynamic'
export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  await db.update(cateros_bg_subscribers).set({ ...body, updated_at: new Date() })
    .where(eq(cateros_bg_subscribers.id, params.id))
  if (body.stage) {
    await generateBoxedGoMessage(params.id, body.stage)
  }
  return Response.json({ success: true })
}

━━━ src/app/api/broadcast/schedule/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_social_posts } from '@/lib/schema'
import { eq, desc, and, inArray } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const brand = searchParams.get('brand')
  const platform = searchParams.get('platform')
  const statusParam = searchParams.get('status')
  const limit = parseInt(searchParams.get('limit') || '30')
  const conditions = []
  if (brand) conditions.push(eq(cateros_social_posts.brand, brand))
  if (platform) conditions.push(eq(cateros_social_posts.platform, platform))
  if (statusParam) {
    const statuses = statusParam.split(',')
    if (statuses.length === 1) conditions.push(eq(cateros_social_posts.status, statuses[0]))
    else conditions.push(inArray(cateros_social_posts.status, statuses))
  }
  const data = await db.query.cateros_social_posts.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_social_posts.created_at)],
    limit
  })
  return Response.json({ data })
}

export async function PATCH(request: Request) {
  const { searchParams } = new URL(request.url)
  const id = searchParams.get('id')
  if (!id) return Response.json({ error: 'id required' }, { status: 400 })
  const body = await request.json()
  await db.update(cateros_social_posts).set({ ...body, updated_at: new Date() })
    .where(eq(cateros_social_posts.id, id))
  return Response.json({ success: true })
}

━━━ src/app/api/broadcast/generate/route.ts ━━━
import { generateAndQueuePost } from '@/agents/broadcast'
export const dynamic = 'force-dynamic'
export async function POST(request: Request) {
  const body = await request.json()
  const post = await generateAndQueuePost(body)
  return Response.json({ success: true, post })
}

━━━ src/app/api/broadcast/webhooks/instagram/route.ts ━━━
import { processComment } from '@/agents/broadcast'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  if (searchParams.get('hub.verify_token') === process.env.META_WEBHOOK_VERIFY_TOKEN) {
    return new Response(searchParams.get('hub.challenge'), { status: 200 })
  }
  return new Response('Forbidden', { status: 403 })
}

export async function POST(request: Request) {
  const body = await request.json()
  const entries = body?.entry || []
  for (const entry of entries) {
    for (const change of entry?.changes || []) {
      if (change.field === 'comments' && change.value) {
        processComment(change.value).catch(e =>
          console.error('[WEBHOOK] Comment processing failed:', e)
        )
      }
    }
  }
  return new Response('OK', { status: 200 })
}

━━━ src/app/api/seo/generate/route.ts ━━━
import { generateSEOArticle } from '@/agents/seo-engine'
export const dynamic = 'force-dynamic'
export async function POST(request: Request) {
  const { brand, keyword, audience } = await request.json()
  await generateSEOArticle(brand, keyword, audience)
  return Response.json({ success: true, message: 'Article generating — check approvals inbox.' })
}

━━━ src/app/api/seo/content/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_seo_content } from '@/lib/schema'
import { eq, desc, and } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const brand = searchParams.get('brand')
  const status = searchParams.get('status')
  const limit = parseInt(searchParams.get('limit') || '20')
  const conditions = []
  if (brand) conditions.push(eq(cateros_seo_content.brand, brand))
  if (status) conditions.push(eq(cateros_seo_content.status, status))
  const data = await db.query.cateros_seo_content.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [desc(cateros_seo_content.created_at)],
    limit
  })
  return Response.json({ data })
}

export async function PATCH(request: Request) {
  const { searchParams } = new URL(request.url)
  const id = searchParams.get('id')
  if (!id) return Response.json({ error: 'id required' }, { status: 400 })
  const body = await request.json()
  await db.update(cateros_seo_content).set(body)
    .where(eq(cateros_seo_content.id, id))
  return Response.json({ success: true })
}

━━━ src/app/api/competitive/competitors/route.ts ━━━
import { db } from '@/lib/db'
import { cateros_competitors } from '@/lib/schema'
import { eq, desc } from 'drizzle-orm'
export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const industry = searchParams.get('industry')
  const data = await db.query.cateros_competitors.findMany({
    where: industry ? eq(cateros_competitors.industry, industry) : undefined,
    orderBy: [desc(cateros_competitors.created_at)]
  })
  return Response.json({ data })
}

export async function POST(request: Request) {
  const body = await request.json()
  const [competitor] = await db.insert(cateros_competitors).values(body).returning()
  return Response.json({ success: true, data: competitor })
}

export async function PATCH(request: Request) {
  const { searchParams } = new URL(request.url)
  const id = searchParams.get('id')
  if (!id) return Response.json({ error: 'id required' }, { status: 400 })
  const body = await request.json()
  await db.update(cateros_competitors).set({ ...body, updated_at: new Date() })
    .where(eq(cateros_competitors.id, id))
  return Response.json({ success: true })
}

━━━ src/app/api/competitive/run/route.ts ━━━
import { runCompetitiveIntelligence } from '@/agents/customer-care'
export const dynamic = 'force-dynamic'
export async function POST(request: Request) {
  const { industry } = await request.json()
  if (!industry) return Response.json({ error: 'industry required' }, { status: 400 })
  await runCompetitiveIntelligence(industry)
  return Response.json({ success: true })
}
```

---

## PROMPT F.5 — Fix Creative Agent C.4 (editedPayload Consistency)

```
In src/agents/orchestrator.ts, find the executeApprovedAction function,
specifically the 'social_post' case. Update it to use editedPayload correctly:

case 'social_post':
  // editedContent comes from edited_payload.content when owner edits via UI
  const captionOverride = editedContent ||
    (request.edited_payload as any)?.content || undefined

  await db.update(cateros_social_posts)
    .set({
      status: 'approved',
      ...(captionOverride && { caption: captionOverride }),
      updated_at: new Date()
    })
    .where(eq(cateros_social_posts.id, payload.postId))

  // Add approved image to brand reference library
  if (payload.assetId) {
    const { addToReferenceLibrary } = await import('@/agents/creative')
    await addToReferenceLibrary(payload.assetId).catch(e =>
      console.error('[ORCHESTRATOR] addToReferenceLibrary failed:', e)
    )
  }
  break
```

---

## PROMPT F.6 — Fix Missing Import in logActivity

```
In src/agents/customer-care.ts, the runPatternAnalysis function calls
logActivity and uses feedbackId in the queueForApproval call but it's
not in scope at that point.

Find this line in runPatternAnalysis:
  entityId: feedbackId,

Replace it with:
  entityId: undefined,

The entityId is optional — the pattern analysis doesn't relate to
a single feedback item, it's a batch report.
```

---

## PROMPT F.7 — Add Missing gte Import to Customer Care

```
At the top of src/agents/customer-care.ts, ensure the drizzle-orm
import includes gte and desc:

import { eq, and, desc, gte, lte } from 'drizzle-orm'

If the current import is missing any of these, add them.
```

---

## UPDATED COMPLETE BUILD ORDER (37 + 7 = total with fixes)

```
Build phases 0–C first, then run F prompts in order to fix and complete.

PHASE F PROMPTS — run after Phase C:

F.1  Fix package install (add openai, sharp, @vercel/blob)
F.2  Fix approval route field name consistency
F.3  Complete Customer Care (sendResponse, processQRScan, runPatternAnalysis)
F.4  Complete all domain API routes with full code
F.5  Fix Creative Agent editedPayload consistency
F.6  Fix feedbackId scope error in runPatternAnalysis
F.7  Add missing gte/desc imports to Customer Care

TOTAL PROMPTS: 44 across 12 phases (0, 1-7, 8, 9, 10, C, F)
```

---

## COMPLETE ENVIRONMENT VARIABLES (FINAL LIST)

```
# Core
DATABASE_URL=
ANTHROPIC_API_KEY=
RESEND_API_KEY=
CRON_SECRET=
NEXT_PUBLIC_APP_URL=

# Owner
OWNER_WHATSAPP=+971XXXXXXXXX
OWNER_EMAIL=
OWNER_APPROVAL_TOKEN=

# WhatsApp Business
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=

# Meta / Instagram
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_WEBHOOK_VERIFY_TOKEN=

# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORGANIZATION_ID=

# Scraping
SERPAPI_KEY=
APIFY_API_TOKEN=

# Creative Agent (NEW)
OPENAI_API_KEY=
VERCEL_BLOB_READ_WRITE_TOKEN=
IMAGE_GENERATION_MODEL=dall-e-3

# Financial
USD_TO_AED_RATE=3.67
ROI_TARGET_MULTIPLIER=20
PLATFORM_STARTING_TIER=standard
```
# PHASE R — RAILWAY DEPLOYMENT
## Replaces all Vercel references throughout the build guide
## Apply these prompts INSTEAD of PROMPT 10.1, and alongside F.1

---

## WHY RAILWAY OVER VERCEL FOR CATEROS

Vercel serverless functions have a hard 60-second execution timeout (300s on Enterprise).
CaterOS agents routinely exceed this:
- Competitive intelligence scraping: 3–8 minutes per industry
- Blue Ocean synthesis (6 competitors × Claude calls): 4–6 minutes
- Weekly content batch (8 posts × Creative Agent): 8–12 minutes
- Morning Scout cycle with 3 schools + 3 companies: 2–4 minutes

Railway runs a persistent Node.js process. No timeout. Agents run to completion.
Railway also costs less: ~$5/month for the Hobby plan vs Vercel Pro at $20/month.
Crons are handled by node-cron running inside the app process — no external scheduler needed.

---

## PROMPT R.1 — Update Package Install (replaces F.1 on this point)

```
Replace @vercel/blob with the AWS S3 SDK pointed at Cloudflare R2.
R2 is S3-compatible, has a free tier (10GB storage, 1M requests/month),
and works identically to Vercel Blob but is platform-independent.

Run:
npm uninstall @vercel/blob
npm install @aws-sdk/client-s3 @aws-sdk/lib-storage node-cron
npm install --save-dev @types/node-cron

Your full dependency list:
@neondatabase/serverless drizzle-orm drizzle-kit @anthropic-ai/sdk
resend date-fns zod lucide-react recharts clsx tailwind-merge
@hello-pangea/dnd qrcode openai sharp uuid node-cron
@aws-sdk/client-s3 @aws-sdk/lib-storage
@radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-tabs
@radix-ui/react-dropdown-menu @radix-ui/react-popover

Dev:
@types/qrcode @types/sharp @types/node-cron
```

---

## PROMPT R.2 — Create R2 Storage Client (replaces @vercel/blob)

```
Create src/lib/storage.ts — Cloudflare R2 via S3-compatible API.
This is a drop-in replacement for @vercel/blob.

import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3'

const R2 = new S3Client({
  region: 'auto',
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!
  }
})

const BUCKET = process.env.R2_BUCKET_NAME || 'cateros'
const PUBLIC_URL = process.env.R2_PUBLIC_URL || ''
-- R2_PUBLIC_URL is your R2 bucket's public domain
-- e.g. https://pub-abc123.r2.dev or your custom domain

export async function uploadFile(params: {
  key: string          -- e.g. 'cateros/boxedgo/posts/1234_feed.jpg'
  body: Buffer
  contentType: string  -- e.g. 'image/jpeg'
}): Promise<string> {
  await R2.send(new PutObjectCommand({
    Bucket: BUCKET,
    Key: params.key,
    Body: params.body,
    ContentType: params.contentType,
    -- Make publicly readable
    ACL: 'public-read'
  }))
  return `${PUBLIC_URL}/${params.key}`
}

export async function uploadJSON(key: string, data: object): Promise<string> {
  return uploadFile({
    key,
    body: Buffer.from(JSON.stringify(data)),
    contentType: 'application/json'
  })
}

-- Export a put() function matching @vercel/blob's API shape
-- so Creative Agent needs minimal changes
export async function put(
  key: string,
  body: Buffer,
  options: { access: string; contentType: string }
): Promise<{ url: string }> {
  const url = await uploadFile({ key, body, contentType: options.contentType })
  return { url }
}
```

---

## PROMPT R.3 — Update Creative Agent to Use R2 (replaces @vercel/blob import)

```
In src/agents/creative.ts, replace the @vercel/blob import with R2:

FIND:
import { put } from '@vercel/blob'

REPLACE WITH:
import { put } from '@/lib/storage'

No other changes needed — the put() function signature is identical.
```

---

## PROMPT R.4 — Create Railway Scheduler (replaces vercel.json crons)

```
DELETE vercel.json from the project root if it exists.

CREATE src/lib/scheduler.ts — node-cron scheduler that runs inside the app.

import cron from 'node-cron'

let schedulerStarted = false

export function startScheduler() {
  -- Guard against double-start in development hot reload
  if (schedulerStarted) return
  schedulerStarted = true

  console.log('[SCHEDULER] CaterOS cron scheduler starting...')

  -- CRON GUARD: all jobs verify CRON_SECRET from env
  -- In Railway the scheduler runs IN the same process so no HTTP auth needed
  -- We use a simple boolean flag instead

  -- 7:00am weekdays — Morning Scout
  cron.schedule('0 7 * * 1-5', async () => {
    console.log('[CRON] morning-scout starting')
    try {
      const { runMorningScoutCycle } = await import('@/agents/scout')
      await runMorningScoutCycle()
      console.log('[CRON] morning-scout complete')
    } catch (e) { console.error('[CRON] morning-scout failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- 7:30am weekdays — Morning Briefing
  cron.schedule('30 7 * * 1-5', async () => {
    console.log('[CRON] morning-briefing starting')
    try {
      const { generateMorningBriefing } = await import('@/agents/orchestrator')
      await generateMorningBriefing()
      console.log('[CRON] morning-briefing complete')
    } catch (e) { console.error('[CRON] morning-briefing failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- 9:00am weekdays — Morning Pipeline
  cron.schedule('0 9 * * 1-5', async () => {
    console.log('[CRON] morning-pipeline starting')
    try {
      const { runMorningPipelineCycle } = await import('@/agents/pipeline')
      await runMorningPipelineCycle()
      console.log('[CRON] morning-pipeline complete')
    } catch (e) { console.error('[CRON] morning-pipeline failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- Every 30 minutes — Social Publish Queue
  cron.schedule('*/30 * * * *', async () => {
    try {
      const { runPublishQueue } = await import('@/agents/broadcast')
      await runPublishQueue()
    } catch (e) { console.error('[CRON] social-publish failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- Every 30 minutes — Feedback Processor
  cron.schedule('*/30 * * * *', async () => {
    try {
      const { processFeedbackBatch } = await import('@/agents/customer-care')
      await processFeedbackBatch()
    } catch (e) { console.error('[CRON] feedback-processor failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- Every 2 hours — Engagement Sync
  cron.schedule('0 */2 * * *', async () => {
    try {
      const { runEngagementSync } = await import('@/agents/broadcast')
      await runEngagementSync()
    } catch (e) { console.error('[CRON] engagement-sync failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- Every 4 hours — Escalation Check
  cron.schedule('0 */4 * * *', async () => {
    try {
      const { runEscalationCheck } = await import('@/agents/orchestrator')
      await runEscalationCheck()
    } catch (e) { console.error('[CRON] escalation-check failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- Monday 6:00am — Weekly Batch
  cron.schedule('0 6 * * 1', async () => {
    console.log('[CRON] weekly-batch starting')
    try {
      const { runWeeklyContentBatch } = await import('@/agents/broadcast')
      const { runWeeklySEOBatch } = await import('@/agents/seo-engine')
      const { runWeeklyFinancialReview } = await import('@/agents/orchestrator')
      await Promise.allSettled([
        runWeeklyContentBatch(),
        runWeeklySEOBatch(),
        runWeeklyFinancialReview()
      ])
      console.log('[CRON] weekly-batch complete')
    } catch (e) { console.error('[CRON] weekly-batch failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  -- 1st of month 6:00am — Monthly Competitive Intelligence
  cron.schedule('0 6 1 * *', async () => {
    console.log('[CRON] monthly-intel starting')
    try {
      const { runCompetitiveIntelligence } = await import('@/agents/customer-care')
      const industries = ['school_food_uae', 'corporate_catering_uae', 'meal_subscription_uae']
      for (const industry of industries) {
        await runCompetitiveIntelligence(industry)
      }
      console.log('[CRON] monthly-intel complete')
    } catch (e) { console.error('[CRON] monthly-intel failed:', e) }
  }, { timezone: 'Asia/Dubai' })

  console.log('[SCHEDULER] All 9 cron jobs registered (timezone: Asia/Dubai)')
}
```

---

## PROMPT R.5 — Start Scheduler in App Entry Point

```
Update src/app/layout.tsx to start the scheduler when the app boots.
The scheduler must only start on the server side, never in the browser.

In src/app/layout.tsx, add this block BEFORE the export default function:

-- Start the cron scheduler on server boot (Railway persistent process)
-- This runs once when the Next.js server starts
if (typeof window === 'undefined' && process.env.NODE_ENV === 'production') {
  import('@/lib/scheduler').then(({ startScheduler }) => {
    startScheduler()
  })
}

IMPORTANT: This works because Railway runs Next.js as a persistent Node.js process,
not as ephemeral serverless functions. The scheduler stays alive indefinitely.
In development, use the manual trigger routes instead of waiting for cron times.
```

---

## PROMPT R.6 — Update next.config.js for Railway

```
Replace the contents of next.config.js with:

/** @type {import('next').NextConfig} */
const nextConfig = {
  -- Railway requires standalone output for containerised deployment
  output: 'standalone',

  experimental: {
    serverComponentsExternalPackages: [
      '@neondatabase/serverless',
      'sharp',
      'node-cron'
    ]
  },

  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' }
        ]
      },
      {
        source: '/feedback',
        headers: [{ key: 'Cache-Control', value: 'no-store' }]
      }
    ]
  }
}

module.exports = nextConfig

NOTE: output: 'standalone' is critical for Railway.
It bundles all dependencies into a self-contained .next/standalone folder
that Railway's Docker container can run directly.
```

---

## PROMPT R.7 — Remove export const dynamic From All Routes

```
In Vercel serverless, export const dynamic = 'force-dynamic' prevents
static caching of API responses. In Railway (persistent Node process),
this is unnecessary and adds noise.

In Cursor, run this find-and-replace across the entire project:

Find:    export const dynamic = 'force-dynamic'\n
Replace: (empty — delete the line)

Do this across ALL files in src/app/api/

Alternatively run in terminal from project root:
find src/app/api -name "*.ts" -exec sed -i "/export const dynamic = 'force-dynamic'/d" {} \;

Verify with:
grep -r "export const dynamic" src/app/api/
-- Should return nothing
```

---

## PROMPT R.8 — Create railway.toml

```
CREATE railway.toml in the project root (same level as package.json):

[build]
builder = "NIXPACKS"
buildCommand = "npm run build"

[deploy]
startCommand = "node .next/standalone/server.js"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[environments.production.variables]
NODE_ENV = "production"
PORT = "3000"

This tells Railway:
- Build using Nixpacks (auto-detects Node.js)
- Run the standalone Next.js server
- Health check via /api/health every 30s
- Restart automatically on failure (keeps agents running)
```

---

## PROMPT R.9 — Update .env.local for Railway

```
Update .env.local — replace Vercel-specific variables with Railway equivalents.

REMOVE these variables:
VERCEL_BLOB_READ_WRITE_TOKEN

ADD these variables:
# Cloudflare R2 (image storage for Creative Agent)
R2_ACCOUNT_ID=                     ← Cloudflare dashboard → R2 → Account ID
R2_ACCESS_KEY_ID=                   ← R2 → Manage R2 API tokens → Create token
R2_SECRET_ACCESS_KEY=               ← Same token creation flow
R2_BUCKET_NAME=cateros
R2_PUBLIC_URL=                      ← Your R2 bucket public URL (enable public access in R2 settings)

# Railway (set automatically by Railway, but useful for local testing)
RAILWAY_ENVIRONMENT=development
PORT=3000

The full .env.local for Railway deployment:

# Core
DATABASE_URL=
ANTHROPIC_API_KEY=
RESEND_API_KEY=
CRON_SECRET=
NEXT_PUBLIC_APP_URL=https://your-app.up.railway.app

# Owner
OWNER_WHATSAPP=+971XXXXXXXXX
OWNER_EMAIL=
OWNER_APPROVAL_TOKEN=

# WhatsApp Business
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=

# Meta / Instagram
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_WEBHOOK_VERIFY_TOKEN=

# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORGANIZATION_ID=

# Scraping
SERPAPI_KEY=
APIFY_API_TOKEN=

# Creative Agent
OPENAI_API_KEY=
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=cateros
R2_PUBLIC_URL=

# Image generation model
IMAGE_GENERATION_MODEL=dall-e-3

# Financial
USD_TO_AED_RATE=3.67
ROI_TARGET_MULTIPLIER=20
PLATFORM_STARTING_TIER=standard
```

---

## PROMPT R.10 — Update Cost Tier Seed Data for Railway

```
In src/lib/seed.ts, update the cost_breakdown in all four platform tiers.
Replace vercel_usd: 20 with railway_usd: 5 in all four tiers.
Railway Hobby plan costs $5/month vs Vercel Pro at $20/month.

Also update r2_usd: 0 (free tier covers CaterOS usage comfortably):
- Free: 10GB storage, 1M Class A operations, 10M Class B operations per month
- CaterOS generates ~500 images/month at ~500KB each = ~250MB storage
- Well within the free tier permanently at normal operation

FLOOR tier cost_breakdown:
{ claude_api_usd: 50, railway_usd: 5, resend_usd: 0, whatsapp_api_usd: 8,
  serpapi_usd: 0, apify_usd: 5, neon_usd: 0, r2_usd: 0 }
Monthly total: ~$68 (was ~$83 on Vercel)

STANDARD tier cost_breakdown:
{ claude_api_usd: 100, railway_usd: 5, resend_usd: 20, whatsapp_api_usd: 12,
  serpapi_usd: 30, apify_usd: 15, neon_usd: 0, r2_usd: 0 }
Monthly total: ~$182 (was ~$197 on Vercel)

EXPANDED tier cost_breakdown:
{ claude_api_usd: 180, railway_usd: 10, resend_usd: 20, whatsapp_api_usd: 20,
  serpapi_usd: 50, apify_usd: 30, neon_usd: 19, r2_usd: 0 }
Monthly total: ~$329 (was ~$339 on Vercel)

SCALE tier cost_breakdown:
{ claude_api_usd: 300, railway_usd: 20, resend_usd: 40, whatsapp_api_usd: 35,
  serpapi_usd: 75, apify_usd: 50, neon_usd: 19, r2_usd: 0 }
Monthly total: ~$539 (was ~$559 on Vercel)

Also update monthly_ceiling_aed and monthly_ceiling_usd on all tiers
to reflect the lower Railway costs (reduce each by AED 55 / $15 respectively).
```

---

## PROMPT R.11 — Railway Production Deployment Guide (replaces PROMPT 10.1)

```
Deploy CaterOS to Railway. Follow every step in order.

━━━ PREREQUISITES ━━━
- Railway account at railway.app (Hobby plan $5/month minimum)
- GitHub repository with CaterOS code pushed
- Neon Postgres database created
- Cloudflare account with R2 bucket created (free)
- All API credentials from .env.local ready

━━━ STEP 1: Set Up Cloudflare R2 ━━━
1. Go to dash.cloudflare.com → R2
2. Create bucket named 'cateros'
3. Settings → Public Access → Enable (required for image URLs to work)
4. Manage R2 API Tokens → Create Token:
   - Permissions: Object Read & Write
   - Bucket: cateros
5. Copy: Account ID, Access Key ID, Secret Access Key
6. Your public URL will be: https://pub-[hash].r2.dev
   (shown in R2 bucket settings after enabling public access)

━━━ STEP 2: Push Schema to Neon ━━━
In your local project with DATABASE_URL set:
npx drizzle-kit push:pg

Verify tables exist in Neon console — you should see all cateros_ tables.

━━━ STEP 3: Deploy to Railway ━━━
1. Go to railway.app → New Project → Deploy from GitHub repo
2. Select your CaterOS repository
3. Railway detects Next.js automatically via Nixpacks
4. DO NOT deploy yet — add environment variables first

━━━ STEP 4: Add Environment Variables ━━━
In Railway project → Variables tab, add ALL variables from .env.local.
Railway injects these at build time and runtime.

Critical variables to double-check:
NEXT_PUBLIC_APP_URL = https://[your-project].up.railway.app
  (Railway shows this URL in the project settings — set it BEFORE deploying)
NODE_ENV = production
PORT = 3000

━━━ STEP 5: Deploy ━━━
Click Deploy in Railway dashboard.
Railway builds using Nixpacks, runs npm run build, starts the server.
Build takes 3-5 minutes first time.
Watch the build logs — should end with:
  ✓ Ready in [X]ms
  [SCHEDULER] CaterOS cron scheduler starting...
  [SCHEDULER] All 9 cron jobs registered (timezone: Asia/Dubai)

If you see the scheduler log lines, crons are running. ✅

━━━ STEP 6: Seed Database ━━━
After first deployment, seed the database once:
In Railway → your service → Shell tab (or use Railway CLI):
  curl -X POST https://[your-app].up.railway.app/api/dev/seed \
    -H "Content-Type: application/json"

Or temporarily set NODE_ENV=development, hit the endpoint, then set back to production.

━━━ STEP 7: Register Webhooks ━━━
Your Railway URL is: https://[your-app].up.railway.app

WhatsApp webhook:
  URL: https://[your-app].up.railway.app/api/approvals/whatsapp
  Token: value of WHATSAPP_WEBHOOK_VERIFY_TOKEN
  Events: messages

Instagram webhook:
  URL: https://[your-app].up.railway.app/api/broadcast/webhooks/instagram
  Token: value of META_WEBHOOK_VERIFY_TOKEN
  Events: comments, mentions

━━━ STEP 8: Verify Everything Is Working ━━━

TEST 1 — Health check:
GET https://[your-app].up.railway.app/api/health
Expected: { status: 'ok', pendingApprovals: 11, roiTarget: '20x' }

TEST 2 — Trigger morning briefing manually:
GET https://[your-app].up.railway.app/api/cron/morning-briefing
Header: Authorization: Bearer {CRON_SECRET}
Expected: WhatsApp message arrives on your phone within 60 seconds
NOTE: On Railway the crons run automatically — this manual trigger is just for testing.

TEST 3 — Check scheduler is running:
Railway → your service → Logs
You should see [SCHEDULER] lines at the top and [CRON] lines at 7:00am, 7:30am, 9:00am UAE time.

TEST 4 — Feedback form:
Open https://[your-app].up.railway.app/feedback?brand=boxedgo
Submit test feedback.
Check Railway logs for [CARE] classification log.

TEST 5 — Creative Agent:
POST https://[your-app].up.railway.app/api/creative/generate
Body: { "postId": "[any seed post id]", "brand": "boxedgo" }
Expected: Image generated and stored in R2, URL returned.
Check R2 bucket in Cloudflare dashboard — should see the image file.

━━━ STEP 9: Go Live ━━━
1. Set NEXT_PUBLIC_APP_URL to your final Railway domain (or custom domain)
2. Open CaterOS in browser — https://[your-app].up.railway.app
3. Check the briefing page — 11 pending approvals from seed data should appear
4. Reply APPROVE via WhatsApp to each approval
5. Monitor Railway logs for agent activity

━━━ CUSTOM DOMAIN (optional) ━━━
Railway → your service → Settings → Domains → Add Custom Domain
Point your DNS CNAME to: [your-app].up.railway.app
SSL is automatic.

━━━ MONITORING ━━━
Railway provides built-in metrics: CPU, memory, request volume.
Your CaterOS app should idle at ~50-100MB RAM between cron runs.
Agent runs (Scout, Broadcast batch, Competitive Intel) spike to ~200-300MB briefly.
Railway Hobby plan allows up to 512MB RAM — well within limits for normal operation.
Upgrade to Pro ($20/month) if you exceed 512MB consistently at scale.

━━━ MAINTENANCE ━━━
Railway auto-deploys when you push to your connected GitHub branch.
No manual redeploy needed for code updates.
Environment variable changes require a manual redeploy (Railway → Deploy).
LinkedIn + Instagram tokens expire every 60 days — update in Railway Variables.
```

---

## RAILWAY VS VERCEL — SUMMARY OF ALL CHANGES

```
WHAT CHANGES:

FILE DELETED:
  vercel.json                          → deleted entirely

FILES ADDED:
  railway.toml                         → build + deploy config
  src/lib/scheduler.ts                 → node-cron replaces Vercel cron jobs
  src/lib/storage.ts                   → R2 replaces @vercel/blob

FILES MODIFIED:
  next.config.js                       → add output: 'standalone'
  src/app/layout.tsx                   → start scheduler on boot
  src/agents/creative.ts               → import from @/lib/storage not @vercel/blob
  src/lib/seed.ts                      → update cost tier breakdowns
  every src/app/api/**/*.ts            → remove export const dynamic = 'force-dynamic'

PACKAGES:
  REMOVED: @vercel/blob
  ADDED:   node-cron @aws-sdk/client-s3 @aws-sdk/lib-storage

ENV VARIABLES:
  REMOVED: VERCEL_BLOB_READ_WRITE_TOKEN
  ADDED:   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
           R2_BUCKET_NAME, R2_PUBLIC_URL

COST IMPACT:
  Railway Hobby: $5/month (vs Vercel Pro $20/month)
  Cloudflare R2: $0/month (free tier)
  Net saving per CaterOS instance: ~$15/month
  At 20 agency clients each on Railway: saves $300/month vs Vercel

KEY BENEFIT:
  No serverless timeout. Agents run to completion.
  Competitive intel, Blue Ocean synthesis, weekly content batch
  all run without risk of mid-execution timeout.

BUILD ORDER FOR RAILWAY:
  Run prompts 0–C and F as normal.
  Then run R.1 → R.11 in order.
  R.11 (deployment guide) replaces PROMPT 10.1 entirely.
```
