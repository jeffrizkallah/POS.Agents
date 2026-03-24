"""
tests/test_scout.py

Tests for Phase 9: Scout Agent.

Run with: pytest tests/test_scout.py -v
These tests use the real Neon DB (test client/brand + seeded prospects from Phase 9A SQL).
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, date, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from tools.database import (
    create_pool,
    get_all_clients,
    get_brands_for_client,
    get_unqualified_prospects,
    save_prospect,
    update_prospect_score,
    save_lead,
    get_contracts_nearing_renewal,
    save_approval_request,
    get_pending_approvals,
    update_approval_status,
)
from agents.scout import QUALIFICATION_THRESHOLD


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


# ---------------------------------------------------------------------------
# Unit tests — no DB required
# ---------------------------------------------------------------------------

class TestQualificationThreshold:
    def test_threshold_is_six(self):
        assert QUALIFICATION_THRESHOLD == 6.0

    def test_score_above_threshold_qualifies(self):
        assert 7.5 >= QUALIFICATION_THRESHOLD

    def test_score_below_threshold_disqualifies(self):
        assert 5.9 < QUALIFICATION_THRESHOLD

    def test_score_at_threshold_qualifies(self):
        assert 6.0 >= QUALIFICATION_THRESHOLD

    def test_score_zero_disqualifies(self):
        assert 0.0 < QUALIFICATION_THRESHOLD


# ---------------------------------------------------------------------------
# DB integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_unqualified_prospects(pool, test_client_and_brand):
    """get_unqualified_prospects should return a list (seeded prospects from Phase 9A)."""
    client, brand = test_client_and_brand
    prospects = await get_unqualified_prospects(pool, str(client["id"]), str(brand["id"]), limit=3)
    assert isinstance(prospects, list)
    # Each prospect row should have expected keys
    if prospects:
        p = prospects[0]
        assert "id" in p
        assert "name" in p
        assert "status" in p
        assert p["status"] == "researched"


@pytest.mark.asyncio
async def test_save_prospect(pool, test_client_and_brand):
    """save_prospect should insert and return a UUID."""
    client, brand = test_client_and_brand
    prospect_id = await save_prospect(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "name": "Test Prospect Co",
            "website": "https://test-prospect.com",
            "industry": "Technology",
            "size_signal": "10-50 employees",
            "location": "London, UK",
            "source": "manual",
        },
    )
    assert prospect_id, "save_prospect returned empty string"
    assert len(prospect_id) == 36, "Expected a UUID string"


@pytest.mark.asyncio
async def test_update_prospect_score_qualified(pool, test_client_and_brand):
    """update_prospect_score should update status to 'qualified' when score >= threshold."""
    client, brand = test_client_and_brand

    # Create a fresh prospect to update
    prospect_id = await save_prospect(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "name": "Score Test Prospect",
            "website": "https://scoretest.com",
            "industry": "Hospitality",
            "size_signal": "50-200 employees",
            "location": "Manchester, UK",
            "source": "manual",
        },
    )
    assert prospect_id

    fit_signals = [
        {"signal": "Industry match", "weight": "high", "evidence": "Hospitality = target sector"},
        {"signal": "Size match", "weight": "medium", "evidence": "50-200 employees = ICP"},
    ]
    await update_prospect_score(pool, prospect_id, 7.5, fit_signals, roi_estimate=8000.0, status="qualified")

    # Verify by re-fetching unqualified — should not appear (status changed)
    prospects = await get_unqualified_prospects(pool, str(client["id"]), str(brand["id"]), limit=20)
    ids = [str(p["id"]) for p in prospects]
    assert prospect_id not in ids, "Qualified prospect still appears as unqualified"


@pytest.mark.asyncio
async def test_update_prospect_score_disqualified(pool, test_client_and_brand):
    """update_prospect_score with status='disqualified' should remove from unqualified queue."""
    client, brand = test_client_and_brand

    prospect_id = await save_prospect(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "name": "Disqualify Test Prospect",
            "website": "https://disqualify.com",
            "industry": "Unknown",
            "size_signal": None,
            "location": None,
            "source": "manual",
        },
    )
    assert prospect_id

    await update_prospect_score(pool, prospect_id, 2.0, [], status="disqualified")

    prospects = await get_unqualified_prospects(pool, str(client["id"]), str(brand["id"]), limit=20)
    ids = [str(p["id"]) for p in prospects]
    assert prospect_id not in ids


@pytest.mark.asyncio
async def test_save_lead_creates_row(pool, test_client_and_brand):
    """save_lead should create a lead in pending_approval stage."""
    client, brand = test_client_and_brand

    # Create a prospect to turn into a lead
    prospect_id = await save_prospect(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "name": "Lead Creation Test",
            "website": "https://leadcreation.com",
            "industry": "Food & Beverage",
            "size_signal": "10-50 employees",
            "location": "Bristol, UK",
            "source": "manual",
        },
    )
    assert prospect_id

    await update_prospect_score(pool, prospect_id, 8.0, [], status="qualified")

    lead_id = await save_lead(
        pool,
        str(client["id"]),
        str(brand["id"]),
        prospect_id,
        stage="pending_approval",
        contract_value_estimate=10000.0,
    )
    assert lead_id, "save_lead returned empty string"
    assert len(lead_id) == 36


@pytest.mark.asyncio
async def test_get_contracts_nearing_renewal_empty(pool, test_client_and_brand):
    """get_contracts_nearing_renewal should return a list (may be empty for a fresh test client)."""
    client, _ = test_client_and_brand
    result = await get_contracts_nearing_renewal(pool, str(client["id"]), days=90)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_approval_request_created_for_qualified_lead(pool, test_client_and_brand):
    """Qualified leads should trigger an approval request via save_approval_request."""
    client, brand = test_client_and_brand
    client_id = str(client["id"])
    brand_id = str(brand["id"])

    prospect_id = await save_prospect(
        pool,
        client_id,
        brand_id,
        {
            "name": "Approval Flow Test Prospect",
            "website": "https://approvaltest.com",
            "industry": "Food & Beverage",
            "size_signal": "50-200 employees",
            "location": "London, UK",
            "source": "manual",
        },
    )
    await update_prospect_score(pool, prospect_id, 8.5, [], status="qualified")

    lead_id = await save_lead(pool, client_id, brand_id, prospect_id, stage="pending_approval", contract_value_estimate=15000.0)

    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    approval_id = await save_approval_request(
        pool,
        client_id,
        brand_id,
        agent_name="scout",
        approval_type="new_lead",
        payload={
            "lead_id": lead_id,
            "prospect_name": "Approval Flow Test Prospect",
            "score": 8.5,
            "fit_signals": [],
            "roi_estimate": 15000.0,
        },
        expires_at=expires_at,
    )
    assert approval_id, "save_approval_request returned empty string"

    pending = await get_pending_approvals(pool, client_id)
    ids = [str(r["id"]) for r in pending]
    assert approval_id in ids, "Approval request not found in pending list"

    # Clean up
    await update_approval_status(pool, approval_id, "approved")


@pytest.mark.asyncio
async def test_run_scout_no_crash(pool, test_client_and_brand):
    """run_scout must complete without raising for the test client/brand."""
    from agents.scout import run_scout
    client, brand = test_client_and_brand
    # Should not raise even if no Claude API key is set in test env
    try:
        await run_scout(pool, client, brand)
    except Exception as e:
        # Only tolerate Claude API failures (no key in test env); DB errors must not happen
        assert "api_key" in str(e).lower() or "authentication" in str(e).lower() or "anthropic" in str(e).lower(), (
            f"run_scout raised an unexpected error: {e}"
        )
