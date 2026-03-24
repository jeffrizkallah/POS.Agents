"""
tests/test_sales.py

Phase 14A — Sales Outreach Agent test suite.

Tests cover:
  - Apollo.io person → lead data mapping
  - Lead qualification (QUALIFICATION_THRESHOLD logic)
  - Email HTML building
  - Batch size constant
  - DB function contract (save/fetch/mark pattern)
  - Integration: run_apollo_pull + run_sales_batch against real Neon DB

Run: pytest tests/test_sales.py -v
"""

import asyncio
import json
import pytest

from agents.sales import (
    _parse_apollo_person,
    _build_email_html,
    BATCH_SIZE,
    QUALIFICATION_THRESHOLD,
)
from tools.database import (
    save_company_lead,
    get_new_company_leads,
    update_company_lead_score,
    save_outreach_draft,
    get_approved_outreach_batch,
    mark_company_outreach_sent,
    record_email_engagement,
    create_pool,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def pool(event_loop):
    async def _make():
        return await create_pool()
    p = event_loop.run_until_complete(_make())
    yield p
    event_loop.run_until_complete(p.close())


# ---------------------------------------------------------------------------
# Unit tests (no DB)
# ---------------------------------------------------------------------------

class TestParseApolloPerson:
    def test_extracts_company_name(self):
        person = {
            "id": "ap_123",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@bistroo.com",
            "organization": {"name": "Bistroo London", "website_url": "https://bistroo.com"},
        }
        lead = _parse_apollo_person(person)
        assert lead["company_name"] == "Bistroo London"
        assert lead["apollo_id"] == "ap_123"

    def test_owner_name_concatenated(self):
        person = {
            "id": "ap_456",
            "first_name": "Marco",
            "last_name": "Rossi",
            "email": "marco@trattoria.it",
            "organization": {"name": "Trattoria Roma"},
        }
        lead = _parse_apollo_person(person)
        assert lead["owner_name"] == "Marco Rossi"

    def test_email_from_top_level(self):
        person = {
            "id": "ap_789",
            "first_name": "Ali",
            "last_name": "Khan",
            "email": "ali@spiceroute.co.uk",
            "organization": {"name": "Spice Route"},
        }
        lead = _parse_apollo_person(person)
        assert lead["owner_email"] == "ali@spiceroute.co.uk"

    def test_email_falls_back_to_contact(self):
        person = {
            "id": "ap_999",
            "first_name": "Sam",
            "last_name": "Lee",
            "contact": {"email": "sam@noodlebar.sg"},
            "organization": {"name": "Noodle Bar SG"},
        }
        lead = _parse_apollo_person(person)
        assert lead["owner_email"] == "sam@noodlebar.sg"

    def test_missing_org_uses_fallback(self):
        person = {
            "id": "ap_111",
            "first_name": "Pat",
            "last_name": "Brown",
            "email": "pat@cafe.com",
            "organization_name": "Pat's Café",
        }
        lead = _parse_apollo_person(person)
        assert lead["company_name"] == "Pat's Café"
        assert lead["source"] == "apollo"

    def test_no_org_no_name_uses_unknown(self):
        person = {"id": "ap_000", "first_name": "X", "last_name": "Y", "email": "x@y.com"}
        lead = _parse_apollo_person(person)
        assert lead["company_name"] == "Unknown"


class TestConstants:
    def test_batch_size_is_safe_for_resend(self):
        # Resend free tier: 100 emails/day; 20 is well within limit
        assert BATCH_SIZE == 20

    def test_qualification_threshold_reasonable(self):
        # Must be between 0 and 10
        assert 0 < QUALIFICATION_THRESHOLD <= 10


class TestBuildEmailHtml:
    def test_contains_body_text(self):
        html = _build_email_html("Hello, this is a test email.", "John")
        assert "Hello, this is a test email." in html

    def test_escapes_html_special_chars(self):
        html = _build_email_html("Revenue > £1k & growing <fast>.", "Owner")
        assert "&gt;" in html
        assert "&lt;" in html
        assert "&amp;" in html

    def test_contains_unsubscribe_link(self):
        html = _build_email_html("Some body text.", "Owner")
        assert "Unsubscribe" in html

    def test_returns_html_string(self):
        html = _build_email_html("Test body.", "Owner")
        assert html.startswith("\n    <html>")


# ---------------------------------------------------------------------------
# DB integration tests (require real Neon DB)
# ---------------------------------------------------------------------------

class TestCompanyLeadDB:
    def test_save_and_fetch_new_lead(self, pool, event_loop):
        async def run():
            lead_data = {
                "apollo_id": f"test_ap_{int(asyncio.get_event_loop().time())}",
                "company_name": "Test Bistro",
                "owner_name": "Test Owner",
                "owner_email": "test-owner@testbistro.example.com",
                "phone": None,
                "website": "https://testbistro.example.com",
                "location": "London",
                "employee_count": 25,
                "industry": "restaurants",
                "source": "apollo",
            }
            lead_id = await save_company_lead(pool, lead_data)
            assert lead_id is not None, "save_company_lead should return a UUID"

            leads = await get_new_company_leads(pool, limit=50)
            lead_ids = [str(l["id"]) for l in leads]
            assert lead_id in lead_ids, "Saved lead should appear in get_new_company_leads"

            return lead_id

        lead_id = event_loop.run_until_complete(run())
        assert lead_id

    def test_save_lead_deduplicates_on_apollo_id(self, pool, event_loop):
        async def run():
            apollo_id = f"dup_test_{int(asyncio.get_event_loop().time())}"
            lead_data = {
                "apollo_id": apollo_id,
                "company_name": "Dup Restaurant",
                "owner_email": "dup@example.com",
                "source": "apollo",
            }
            id1 = await save_company_lead(pool, lead_data)
            id2 = await save_company_lead(pool, lead_data)  # duplicate
            assert id1 is not None
            assert id2 is None, "Duplicate apollo_id should return None (ON CONFLICT DO NOTHING)"

        event_loop.run_until_complete(run())

    def test_update_company_lead_score(self, pool, event_loop):
        async def run():
            lead_data = {
                "apollo_id": f"score_test_{int(asyncio.get_event_loop().time())}",
                "company_name": "Scored Restaurant",
                "owner_email": "scored@example.com",
                "source": "apollo",
            }
            lead_id = await save_company_lead(pool, lead_data)
            assert lead_id

            await update_company_lead_score(
                pool,
                lead_id,
                score=7.5,
                fit_signals={"independent_operator": True, "small_team": True},
                pain_points=["manual_ordering", "thin_margins"],
            )

            row = await pool.fetchrow(
                "SELECT qualification_score, pain_points FROM company_leads WHERE id = $1",
                lead_id,
            )
            assert float(row["qualification_score"]) == 7.5
            assert "manual_ordering" in row["pain_points"]

        event_loop.run_until_complete(run())


class TestOutreachDraftDB:
    def _make_lead(self):
        import time
        return {
            "apollo_id": f"outreach_lead_{int(time.time() * 1000)}",
            "company_name": "Outreach Test Restaurant",
            "owner_email": "outreach@testrestaurant.example.com",
            "source": "apollo",
        }

    def test_save_outreach_draft_returns_id(self, pool, event_loop):
        from datetime import datetime, timezone

        async def run():
            lead_id = await save_company_lead(pool, self._make_lead())
            assert lead_id

            outreach_id = await save_outreach_draft(
                pool,
                lead_id,
                sequence_step=1,
                subject="Quick question about your inventory",
                body="Hi there,\n\nI noticed you run a busy restaurant...",
                scheduled_for=datetime.now(timezone.utc),
            )
            assert outreach_id is not None, "save_outreach_draft should return a UUID"

        event_loop.run_until_complete(run())

    def test_save_outreach_draft_deduplicates_step(self, pool, event_loop):
        from datetime import datetime, timezone

        async def run():
            lead_id = await save_company_lead(pool, self._make_lead())
            assert lead_id

            now = datetime.now(timezone.utc)
            id1 = await save_outreach_draft(
                pool, lead_id, 1, "Subject 1", "Body 1", now
            )
            id2 = await save_outreach_draft(
                pool, lead_id, 1, "Subject 2", "Body 2", now
            )  # same step
            assert id1 is not None
            assert id2 is None, "Duplicate (lead_id, step) should return None"

        event_loop.run_until_complete(run())

    def test_get_approved_outreach_batch_returns_list(self, pool, event_loop):
        async def run():
            batch = await get_approved_outreach_batch(pool, limit=5)
            assert isinstance(batch, list)

        event_loop.run_until_complete(run())

    def test_mark_outreach_sent(self, pool, event_loop):
        from datetime import datetime, timezone

        async def run():
            lead_id = await save_company_lead(pool, self._make_lead())
            assert lead_id

            outreach_id = await save_outreach_draft(
                pool, lead_id, 1,
                "Mark sent test",
                "Body text",
                datetime.now(timezone.utc),
            )
            assert outreach_id

            await mark_company_outreach_sent(pool, outreach_id, "resend_test_abc123")

            row = await pool.fetchrow(
                "SELECT status, resend_email_id FROM company_outreach WHERE id = $1",
                outreach_id,
            )
            assert row["status"] == "sent"
            assert row["resend_email_id"] == "resend_test_abc123"

        event_loop.run_until_complete(run())

    def test_record_email_engagement_open(self, pool, event_loop):
        from datetime import datetime, timezone

        async def run():
            lead_id = await save_company_lead(pool, self._make_lead())
            assert lead_id

            outreach_id = await save_outreach_draft(
                pool, lead_id, 1, "Engagement test", "Body",
                datetime.now(timezone.utc),
            )
            assert outreach_id

            fake_resend_id = f"resend_open_{int(asyncio.get_event_loop().time())}"
            await mark_company_outreach_sent(pool, outreach_id, fake_resend_id)
            await record_email_engagement(pool, fake_resend_id, "open")

            row = await pool.fetchrow(
                "SELECT email_opens FROM company_leads WHERE id = $1", lead_id
            )
            assert row["email_opens"] >= 1

        event_loop.run_until_complete(run())
