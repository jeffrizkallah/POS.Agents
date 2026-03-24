"""
tests/test_broadcast.py

Tests for Phase 12: Broadcast Agent.

Run with: pytest tests/test_broadcast.py -v
Uses the real Neon DB (test client/brand seeded from Phase 7A SQL).
"""

import pytest
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from tools.database import (
    create_pool,
    get_all_clients,
    get_brands_for_client,
    save_social_post,
    get_approved_posts,
    update_post_status,
    update_post_engagement,
    get_recent_comments,
    save_comment_classification,
)
from agents.broadcast import (
    _scheduled_for,
    _publish_to_platform,
    _fetch_platform_engagement,
    _fetch_new_comments,
    run_content_batch,
    run_publish_queue,
    run_engagement_sync,
)


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
    assert clients, "No active clients — seed Phase 7A SQL first"
    client = clients[0]
    brands = await get_brands_for_client(pool, str(client["id"]))
    assert brands, f"No brands for client {client['name']}"
    return client, brands[0]


# ---------------------------------------------------------------------------
# Unit tests — no DB
# ---------------------------------------------------------------------------

def test_scheduled_for_is_future():
    """_scheduled_for(1) should return a datetime > now."""
    result = _scheduled_for(1)
    assert result > datetime.now(timezone.utc)


def test_scheduled_for_offset():
    """_scheduled_for(3) should be ~3 days ahead of _scheduled_for(0)."""
    d0 = _scheduled_for(0)
    d3 = _scheduled_for(3)
    diff_days = (d3 - d0).days
    assert diff_days == 3


def test_publish_stub_returns_success():
    result = _publish_to_platform("instagram", "Test caption", ["#test"])
    assert result["success"] is True
    assert "platform_post_id" in result


def test_engagement_stub_returns_zeros():
    metrics = _fetch_platform_engagement("instagram", "stub_123")
    assert metrics["likes_count"] == 0
    assert metrics["engagement_rate"] == 0.0


def test_comments_stub_returns_empty():
    comments = _fetch_new_comments("instagram", "stub_123")
    assert comments == []


# ---------------------------------------------------------------------------
# DB tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_social_post(pool, test_client_and_brand):
    client, brand = test_client_and_brand
    post_data = {
        "platform": "instagram",
        "post_type": "feed",
        "content_pillar": "educational",
        "caption": "Test post caption for broadcast tests.",
        "caption_secondary_language": None,
        "visual_brief": "Bright flat-lay of product on white surface.",
        "hashtags": ["#test", "#broadcast"],
        "scheduled_for": _scheduled_for(1),
    }
    post_id = await save_social_post(pool, str(client["id"]), str(brand["id"]), post_data)
    assert post_id is not None
    assert len(post_id) > 0


@pytest.mark.asyncio
async def test_get_approved_posts_empty(pool, test_client_and_brand):
    """Approved posts list should be a list (may be empty for test brand)."""
    client, _ = test_client_and_brand
    posts = await get_approved_posts(pool, str(client["id"]))
    assert isinstance(posts, list)


@pytest.mark.asyncio
async def test_update_post_status(pool, test_client_and_brand):
    """Save a post then update its status — should not raise."""
    client, brand = test_client_and_brand
    post_id = await save_social_post(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "platform": "linkedin",
            "caption": "Status update test",
            "hashtags": [],
            "scheduled_for": _scheduled_for(2),
        },
    )
    assert post_id
    await update_post_status(pool, post_id, "failed")  # should not raise


@pytest.mark.asyncio
async def test_update_post_engagement(pool, test_client_and_brand):
    """Save a post then update engagement metrics — should not raise."""
    client, brand = test_client_and_brand
    post_id = await save_social_post(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "platform": "instagram",
            "caption": "Engagement test post",
            "hashtags": [],
            "scheduled_for": _scheduled_for(3),
        },
    )
    assert post_id
    await update_post_engagement(
        pool,
        post_id,
        {"likes_count": 42, "comments_count": 5, "reach": 800, "impressions": 1200, "engagement_rate": 3.9},
    )


@pytest.mark.asyncio
async def test_get_recent_comments_returns_list(pool, test_client_and_brand):
    """get_recent_comments should return a list (empty for test brand)."""
    client, brand = test_client_and_brand
    since = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    comments = await get_recent_comments(pool, str(client["id"]), str(brand["id"]), since)
    assert isinstance(comments, list)


# ---------------------------------------------------------------------------
# Integration tests — agent functions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_content_batch_no_crash(pool, test_client_and_brand):
    """run_content_batch should complete without raising for a real brand."""
    client, brand = test_client_and_brand
    # May skip gracefully if no content config; must not raise
    await run_content_batch(pool, client, brand)


@pytest.mark.asyncio
async def test_run_publish_queue_no_crash(pool, test_client_and_brand):
    """run_publish_queue should complete without raising."""
    client, brand = test_client_and_brand
    await run_publish_queue(pool, client, brand)


@pytest.mark.asyncio
async def test_run_engagement_sync_no_crash(pool, test_client_and_brand):
    """run_engagement_sync should complete without raising."""
    client, brand = test_client_and_brand
    await run_engagement_sync(pool, client, brand)


@pytest.mark.asyncio
async def test_post_status_lifecycle(pool, test_client_and_brand):
    """A post saved as pending_approval should reflect approved then published status updates."""
    client, brand = test_client_and_brand
    post_id = await save_social_post(
        pool,
        str(client["id"]),
        str(brand["id"]),
        {
            "platform": "instagram",
            "caption": "Lifecycle test post",
            "hashtags": ["#lifecycle"],
            "scheduled_for": _scheduled_for(0),
        },
    )
    assert post_id
    await update_post_status(pool, post_id, "approved")
    await update_post_status(pool, post_id, "published")
    # Verify published_at is set by fetching the row
    row = await pool.fetchrow("SELECT status, published_at FROM client_social_posts WHERE id = $1", post_id)
    assert row["status"] == "published"
    assert row["published_at"] is not None
