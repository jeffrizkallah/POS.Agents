"""
tests/test_pipeline.py

Tests for Phase 10: Pipeline Agent.

Run with: pytest tests/test_pipeline.py -v
These tests use the real Neon DB (test client/brand seeded from Phase 7A + 9A SQL).
"""

import pytest
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from tools.database import (
    create_pool,
    get_all_clients,
    get_brands_for_client,
    save_prospect,
    update_prospect_score,
    save_lead,
    get_approved_leads,
    get_outreach_sequence,
    save_outreach_step,
    get_due_outreach_steps,
    mark_outreach_sent,
    get_draft_steps_due_for_promotion,
    update_outreach_status,
    save_approval_request,
    get_pending_approvals,
    update_approval_status,
)
from agents.pipeline import STEP_DAYS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def pool():
    p = await create_pool()
    yield p
    await p.close()


@pytest.fixture
async def test_client_and_brand(pool):
    clients = await get_all_clients(pool)
    assert clients, "No active clients found — seed at least one test client (Phase 7A SQL)"
    client = clients[0]
    brands = await get_brands_for_client(pool, str(client["id"]))
    assert brands, f"No brands found for client {client['name']}"
    return client, brands[0]


@pytest.fixture
async def approved_lead(pool, test_client_and_brand):
    """Create a qualified prospect → identified lead for pipeline tests."""
    client, brand = test_client_and_brand
    client_id = str(client["id"])
    brand_id = str(brand["id"])

    prospect_id = await save_prospect(
        pool,
        client_id,
        brand_id,
        {
            "name": "Pipeline Test Prospect",
            "website": "https://pipeline-test.com",
            "industry": "Technology",
            "size_signal": "50-200 employees",
            "location": "London, UK",
            "source": "manual",
        },
    )
    await update_prospect_score(pool, prospect_id, 7.5, [], status="qualified")

    lead_id = await save_lead(
        pool,
        client_id,
        brand_id,
        prospect_id,
        stage="identified",  # Orchestrator approved it
        contract_value_estimate=8000.0,
    )
    assert lead_id, "Failed to create test lead"
    yield {"id": lead_id, "prospect_id": prospect_id, "client_id": client_id, "brand_id": brand_id}


# ---------------------------------------------------------------------------
# Unit tests — no DB required
# ---------------------------------------------------------------------------

class TestStepDays:
    def test_step_1_is_day_0(self):
        assert STEP_DAYS[1] == 0

    def test_step_2_is_day_3(self):
        assert STEP_DAYS[2] == 3

    def test_step_3_is_day_7(self):
        assert STEP_DAYS[3] == 7

    def test_step_4_is_day_14(self):
        assert STEP_DAYS[4] == 14

    def test_step_5_is_day_21(self):
        assert STEP_DAYS[5] == 21

    def test_five_steps_defined(self):
        assert len(STEP_DAYS) == 5


# ---------------------------------------------------------------------------
# DB integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_approved_leads_returns_list(pool, test_client_and_brand):
    """get_approved_leads should return a list (may be empty before any leads approved)."""
    client, brand = test_client_and_brand
    result = await get_approved_leads(pool, str(client["id"]), str(brand["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_save_outreach_step_creates_row(pool, approved_lead):
    """save_outreach_step should insert a row and return a UUID."""
    scheduled = datetime.now(timezone.utc) + timedelta(days=0)
    step_id = await save_outreach_step(
        pool,
        approved_lead["client_id"],
        approved_lead["brand_id"],
        approved_lead["id"],
        {
            "step_number": 1,
            "sequence_type": "new_acquisition",
            "channel": "email",
            "subject": "Quick question about your ops",
            "body": "Hi there, I noticed your company ...",
            "word_count": 50,
            "status": "pending_approval",
            "scheduled_for": scheduled,
        },
    )
    assert step_id, "save_outreach_step returned empty string"
    assert len(step_id) == 36, "Expected a UUID string"


@pytest.mark.asyncio
async def test_step_1_pending_approval_steps_2_to_5_draft(pool, approved_lead):
    """Step 1 should be pending_approval; Steps 2-5 should be saved as draft."""
    client_id = approved_lead["client_id"]
    brand_id = approved_lead["brand_id"]
    lead_id = approved_lead["id"]
    now = datetime.now(timezone.utc)

    # Save 5 steps with correct statuses
    for step_num, day_offset in STEP_DAYS.items():
        status = "pending_approval" if step_num == 1 else "draft"
        await save_outreach_step(
            pool,
            client_id,
            brand_id,
            lead_id,
            {
                "step_number": step_num,
                "sequence_type": "new_acquisition",
                "channel": "email",
                "subject": f"Step {step_num} subject",
                "body": f"Body of step {step_num}.",
                "word_count": 10,
                "status": status,
                "scheduled_for": now + timedelta(days=day_offset),
            },
        )

    steps = await get_outreach_sequence(pool, lead_id)
    assert len(steps) == 5

    statuses = {s["step_number"]: s["status"] for s in steps}
    assert statuses[1] == "pending_approval"
    assert statuses[2] == "draft"
    assert statuses[3] == "draft"
    assert statuses[4] == "draft"
    assert statuses[5] == "draft"


@pytest.mark.asyncio
async def test_get_outreach_sequence_ordered(pool, approved_lead):
    """get_outreach_sequence should return steps ordered by step_number."""
    lead_id = approved_lead["id"]
    steps = await get_outreach_sequence(pool, lead_id)
    if len(steps) > 1:
        for i in range(len(steps) - 1):
            assert steps[i]["step_number"] < steps[i + 1]["step_number"]


@pytest.mark.asyncio
async def test_duplicate_step_ignored(pool, approved_lead):
    """Saving a step with an existing step_number for the same lead should be ignored (ON CONFLICT DO NOTHING)."""
    client_id = approved_lead["client_id"]
    brand_id = approved_lead["brand_id"]
    lead_id = approved_lead["id"]

    step_data = {
        "step_number": 99,
        "sequence_type": "new_acquisition",
        "channel": "email",
        "subject": "Duplicate test",
        "body": "First insert",
        "word_count": 3,
        "status": "draft",
    }
    id1 = await save_outreach_step(pool, client_id, brand_id, lead_id, step_data)
    step_data["body"] = "Second insert"
    id2 = await save_outreach_step(pool, client_id, brand_id, lead_id, step_data)

    # Second insert returns empty (ON CONFLICT DO NOTHING)
    assert id2 == "" or id2 is None or id2 == id1


@pytest.mark.asyncio
async def test_mark_outreach_sent_updates_status(pool, approved_lead):
    """mark_outreach_sent should set status=sent and sent_at timestamp."""
    client_id = approved_lead["client_id"]
    brand_id = approved_lead["brand_id"]
    lead_id = approved_lead["id"]

    step_id = await save_outreach_step(
        pool,
        client_id,
        brand_id,
        lead_id,
        {
            "step_number": 88,
            "sequence_type": "new_acquisition",
            "channel": "email",
            "subject": "Sending test",
            "body": "This step will be marked sent.",
            "word_count": 7,
            "status": "approved",
            "scheduled_for": datetime.now(timezone.utc) - timedelta(hours=1),
        },
    )
    assert step_id

    await mark_outreach_sent(pool, step_id)

    sequence = await get_outreach_sequence(pool, lead_id)
    step = next((s for s in sequence if str(s["id"]) == step_id), None)
    assert step is not None
    assert step["status"] == "sent"
    assert step["sent_at"] is not None


@pytest.mark.asyncio
async def test_get_due_outreach_steps_returns_approved_past_due(pool, approved_lead):
    """get_due_outreach_steps should return approved steps with scheduled_for in the past."""
    client_id = approved_lead["client_id"]
    brand_id = approved_lead["brand_id"]
    lead_id = approved_lead["id"]

    step_id = await save_outreach_step(
        pool,
        client_id,
        brand_id,
        lead_id,
        {
            "step_number": 77,
            "sequence_type": "new_acquisition",
            "channel": "email",
            "subject": "Due step",
            "body": "This step is past due.",
            "word_count": 5,
            "status": "approved",
            "scheduled_for": datetime.now(timezone.utc) - timedelta(hours=2),
        },
    )
    assert step_id

    due = await get_due_outreach_steps(pool, client_id)
    ids = [str(s["id"]) for s in due]
    assert step_id in ids, "Approved past-due step not returned by get_due_outreach_steps"

    # Clean up
    await mark_outreach_sent(pool, step_id)


@pytest.mark.asyncio
async def test_draft_step_not_in_due_steps(pool, approved_lead):
    """Draft steps should NOT appear in get_due_outreach_steps even if past scheduled_for."""
    client_id = approved_lead["client_id"]
    brand_id = approved_lead["brand_id"]
    lead_id = approved_lead["id"]

    step_id = await save_outreach_step(
        pool,
        client_id,
        brand_id,
        lead_id,
        {
            "step_number": 66,
            "sequence_type": "new_acquisition",
            "channel": "email",
            "subject": "Draft only",
            "body": "Should not appear in due steps.",
            "word_count": 6,
            "status": "draft",
            "scheduled_for": datetime.now(timezone.utc) - timedelta(hours=3),
        },
    )
    assert step_id

    due = await get_due_outreach_steps(pool, client_id)
    ids = [str(s["id"]) for s in due]
    assert step_id not in ids


@pytest.mark.asyncio
async def test_approval_request_created_for_step_1(pool, test_client_and_brand, approved_lead):
    """Pipeline step 1 should trigger an approval request via save_approval_request."""
    client, brand = test_client_and_brand
    client_id = str(client["id"])
    brand_id = str(brand["id"])

    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    approval_id = await save_approval_request(
        pool,
        client_id,
        brand_id,
        agent_name="pipeline",
        approval_type="outreach_step_1",
        payload={
            "lead_id": approved_lead["id"],
            "prospect_name": "Pipeline Test Prospect",
            "sequence_type": "new_acquisition",
            "channel": "email",
            "subject": "Quick question",
            "body_preview": "Hi there...",
            "total_steps": 5,
        },
        expires_at=expires_at,
    )
    assert approval_id, "save_approval_request returned empty"

    pending = await get_pending_approvals(pool, client_id)
    ids = [str(r["id"]) for r in pending]
    assert approval_id in ids

    # Clean up
    await update_approval_status(pool, approval_id, "approved")


@pytest.mark.asyncio
async def test_run_pipeline_no_crash(pool, test_client_and_brand):
    """run_pipeline must complete without raising for the test client/brand."""
    from agents.pipeline import run_pipeline
    client, brand = test_client_and_brand
    try:
        await run_pipeline(pool, client, brand)
    except Exception as e:
        # Only tolerate Claude API failures in test env
        assert (
            "api_key" in str(e).lower()
            or "authentication" in str(e).lower()
            or "anthropic" in str(e).lower()
        ), f"run_pipeline raised an unexpected error: {e}"
