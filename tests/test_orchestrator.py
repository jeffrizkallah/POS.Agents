"""
tests/test_orchestrator.py

Tests for the Phase 8 Orchestrator Agent.

Run with: pytest tests/test_orchestrator.py -v
These tests use the real Neon DB (test client/brand seeded in Phase 7A).
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from tools.database import (
    create_pool,
    get_all_clients,
    get_brands_for_client,
    get_pending_approvals,
    save_approval_request,
    update_approval_status,
    get_roi_by_channel,
    get_budget_envelopes,
    save_roi_snapshot,
    save_intelligence,
    get_recent_intelligence,
)
from agents.orchestrator import classify_roi


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
    """Return the first active client and its first brand for testing."""
    clients = await get_all_clients(pool)
    assert clients, "No active clients found — seed at least one test client (Phase 7A SQL)"
    client = clients[0]
    brands = await get_brands_for_client(pool, str(client["id"]))
    assert brands, f"No brands found for client {client['name']} — seed at least one test brand"
    brand = brands[0]
    return client, brand


# ---------------------------------------------------------------------------
# Unit tests — no DB required
# ---------------------------------------------------------------------------

class TestClassifyRoi:
    def test_green_at_target(self):
        assert classify_roi(3.0, 3.0) == "green"

    def test_green_above_target(self):
        assert classify_roi(5.0, 3.0) == "green"

    def test_yellow_just_below_target(self):
        # 70% of 3.0 = 2.1
        assert classify_roi(2.1, 3.0) == "yellow"

    def test_yellow_boundary(self):
        # Exactly 70% of target
        assert classify_roi(2.1, 3.0) == "yellow"

    def test_red_below_yellow(self):
        # 30–70% of 3.0 = 0.9–2.1
        assert classify_roi(1.2, 3.0) == "red"

    def test_black_critically_low(self):
        # < 30% of 3.0 = < 0.9
        assert classify_roi(0.5, 3.0) == "black"

    def test_black_zero_roi(self):
        assert classify_roi(0.0, 3.0) == "black"

    def test_different_target(self):
        # target=5.0: green ≥ 5, yellow ≥ 3.5, red ≥ 1.5, black < 1.5
        assert classify_roi(5.0, 5.0) == "green"
        assert classify_roi(4.0, 5.0) == "yellow"
        assert classify_roi(2.0, 5.0) == "red"
        assert classify_roi(1.0, 5.0) == "black"


# ---------------------------------------------------------------------------
# Integration tests — require real DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_get_approval_request(pool, test_client_and_brand):
    client, brand = test_client_and_brand
    client_id = str(client["id"])
    brand_id = str(brand["id"])

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    approval_id = await save_approval_request(
        pool,
        client_id,
        brand_id,
        agent_name="test_agent",
        approval_type="test_approval",
        payload={"test": True, "item": "pytest fixture"},
        expires_at=expires_at,
    )
    assert approval_id, "save_approval_request returned empty id"

    pending = await get_pending_approvals(pool, client_id)
    ids = [str(r["id"]) for r in pending]
    assert approval_id in ids, "Saved approval not found in pending list"

    # Clean up — approve it so it doesn't litter future test runs
    await update_approval_status(pool, approval_id, "approved")

    # Verify it is no longer pending
    pending_after = await get_pending_approvals(pool, client_id)
    ids_after = [str(r["id"]) for r in pending_after]
    assert approval_id not in ids_after, "Approval still pending after status update"


@pytest.mark.asyncio
async def test_update_approval_expired(pool, test_client_and_brand):
    client, brand = test_client_and_brand
    client_id = str(client["id"])
    brand_id = str(brand["id"])

    approval_id = await save_approval_request(
        pool,
        client_id,
        brand_id,
        agent_name="test_agent",
        approval_type="expiry_test",
        payload={},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await update_approval_status(pool, approval_id, "expired")

    # Should not appear in pending list
    pending = await get_pending_approvals(pool, client_id)
    assert approval_id not in [str(r["id"]) for r in pending]


@pytest.mark.asyncio
async def test_get_roi_by_channel_empty(pool, test_client_and_brand):
    """With no spend entries, get_roi_by_channel should return an empty list (not crash)."""
    client, _ = test_client_and_brand
    result = await get_roi_by_channel(pool, str(client["id"]), 30)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_budget_envelopes(pool, test_client_and_brand):
    """get_budget_envelopes should return a list (may be empty for a new test client)."""
    client, _ = test_client_and_brand
    result = await get_budget_envelopes(pool, str(client["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_save_roi_snapshot(pool, test_client_and_brand):
    client, _ = test_client_and_brand
    client_id = str(client["id"])

    snapshot_id = await save_roi_snapshot(
        pool,
        client_id,
        {
            "total_spend": 1000.0,
            "total_revenue": 4500.0,
            "platform_cost": 50.0,
            "spend_by_channel": {"email": 500.0, "social": 500.0},
            "revenue_by_channel": {"email": 3000.0, "social": 1500.0},
            "channels_below_target": {},
            "compounding_channels": {"email": 6.0, "social": 3.0},
        },
    )
    assert snapshot_id, "save_roi_snapshot returned empty id"


@pytest.mark.asyncio
async def test_save_and_get_intelligence(pool, test_client_and_brand):
    client, _ = test_client_and_brand
    client_id = str(client["id"])

    intel_id = await save_intelligence(
        pool,
        client_id,
        "roi_alert",
        {"below_target_channels": [{"channel": "social", "roi": 0.8, "color": "red"}]},
        urgency="normal",
    )
    assert intel_id, "save_intelligence returned empty id"

    recent = await get_recent_intelligence(pool, client_id, 5)
    assert isinstance(recent, list)
    ids = [str(r["id"]) for r in recent]
    assert intel_id in ids, "Saved intelligence not found in recent list"


@pytest.mark.asyncio
async def test_run_orchestrator_no_crash(pool, test_client_and_brand):
    """run_orchestrator must complete without raising for the test client/brand."""
    from agents.orchestrator import run_orchestrator
    client, brand = test_client_and_brand
    # Should not raise even with no spend data / no pending approvals
    await run_orchestrator(pool, client, brand)


@pytest.mark.asyncio
async def test_run_daily_briefing_no_owner_email(pool, test_client_and_brand):
    """run_daily_briefing must skip gracefully when owner_email is absent."""
    from agents.orchestrator import run_daily_briefing
    client, brand = test_client_and_brand
    # Pass a fake client dict with no owner_email
    fake_client = {**client, "owner_email": None}
    # Should not raise
    await run_daily_briefing(pool, fake_client, brand)
