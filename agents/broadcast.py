"""
agents/broadcast.py

Phase 12: Broadcast Agent

run_content_batch(pool, client, brand)   — runs Monday 06:00
  1. Fetches brand content config (platforms, posts_per_week, pillars, word limits).
  2. For each active platform: calls Claude (broadcast_post.txt) to generate
     the week's posts.
  3. Saves each post as pending_approval; creates Orchestrator approval request.

run_publish_queue(pool, client, brand)   — runs every 30 min
  1. Fetches approved posts with scheduled_for <= now.
  2. Calls platform API (stubbed; real Instagram/LinkedIn wired in production).
  3. Updates status to published or failed; logs to client_agent_activity.

run_engagement_sync(pool, client, brand) — runs every 2 hours
  1. Fetches published posts from last 30 days.
  2. Pulls metrics from platform API (stubbed).
  3. Upserts engagement counters.
  4. Fetches new comments; calls Claude (broadcast_comment.txt) to classify +
     draft reply.
  5. Escalates to client_intelligence if required; otherwise saves as
     pending_approval.

Called via _async_client_agent_job() in main.py.
Schedules:
  broadcast_batch_job()      — CronTrigger(day_of_week='mon', hour=6, minute=0)
  broadcast_publish_job()    — CronTrigger(minute='*/30')
  broadcast_engagement_job() — CronTrigger(hour='*/2')
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone

import anthropic

from tools.database import (
    get_brand_config,
    get_brand_content_config,
    get_brand_channels,
    save_social_post,
    get_approved_posts,
    update_post_status,
    update_post_engagement,
    get_recent_comments,
    save_comment_classification,
    save_approval_request,
    save_intelligence,
    log_client_agent_action,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(
    system_prompt: str, user_content: str, max_tokens: int = 2000
) -> dict:
    """Synchronous Claude Haiku call. Wrapped with asyncio.to_thread by callers."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _scheduled_for(days_from_now: int) -> datetime:
    """Return a UTC datetime N days from now at 10:00 AM (good posting time)."""
    base = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    return base + timedelta(days=days_from_now)


# ---------------------------------------------------------------------------
# Stub: platform publishing (replace with real SDK calls in production)
# ---------------------------------------------------------------------------

def _publish_to_platform(platform: str, caption: str, hashtags: list[str]) -> dict:
    """Stub publisher. Returns a simulated success result.

    In production: replace with Instagram Graph API / LinkedIn API calls
    using credentials from brand_channels.
    """
    return {
        "success": True,
        "platform_post_id": f"stub_{platform}_{int(time.time())}",
        "note": "Stubbed — wire real API in production",
    }


def _fetch_platform_engagement(platform: str, platform_post_id: str) -> dict:
    """Stub engagement fetcher. Returns zero metrics until real API is wired."""
    return {
        "likes_count": 0,
        "comments_count": 0,
        "reach": 0,
        "impressions": 0,
        "engagement_rate": 0.0,
    }


def _fetch_new_comments(platform: str, platform_post_id: str) -> list[dict]:
    """Stub comment fetcher. Returns empty list until real API is wired."""
    return []


# ---------------------------------------------------------------------------
# 12C-1: Content batch generation (Monday 06:00)
# ---------------------------------------------------------------------------

async def run_content_batch(pool, client: dict, brand: dict) -> None:
    """Generate this week's social posts for all active platforms of a brand."""
    t_start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    brand_name = brand.get("name", "unknown")

    brand_config = await get_brand_config(pool, brand_id)
    if not brand_config:
        print(f"[Broadcast] {brand_name}: no brand config — skipping")
        return

    content_configs = await get_brand_content_config(pool, brand_id)
    if not content_configs:
        print(f"[Broadcast] {brand_name}: no content config — skipping")
        return

    # content_config may be a single dict or a list; normalise to list
    if isinstance(content_configs, dict):
        content_configs = [content_configs]

    system_prompt = _load_prompt("broadcast_post.txt")
    posts_created = 0

    for cfg in content_configs:
        platform = cfg.get("platform", "instagram")
        posts_per_week = int(cfg.get("posts_per_week") or 3)
        pillars = cfg.get("content_pillars") or []
        word_limit = int(cfg.get("word_limit_step1") or 150)

        user_content = json.dumps({
            "brand": {
                "name": brand_name,
                "tone": brand_config.get("tone"),
                "language_primary": brand_config.get("language_primary", "English"),
                "language_secondary": brand_config.get("language_secondary"),
                "target_audience": brand_config.get("target_audience"),
                "industry": brand_config.get("industry"),
            },
            "platform": platform,
            "posts_per_week": posts_per_week,
            "content_pillars": pillars,
            "word_limit": word_limit,
        })

        try:
            result = await asyncio.to_thread(_call_claude, system_prompt, user_content)
        except Exception as e:
            print(f"[Broadcast] {brand_name}/{platform}: Claude error — {e}")
            continue

        posts = result.get("posts") or []
        for i, post in enumerate(posts[:posts_per_week]):
            post_data = {
                "platform": platform,
                "post_type": post.get("post_type", "feed"),
                "content_pillar": post.get("content_pillar"),
                "caption": post.get("caption"),
                "caption_secondary_language": post.get("caption_secondary_language"),
                "visual_brief": post.get("visual_brief"),
                "hashtags": post.get("hashtags") or [],
                "scheduled_for": _scheduled_for(i + 1),  # spread Mon–Sat
            }
            post_id = await save_social_post(pool, client_id, brand_id, post_data)
            if post_id:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
                await save_approval_request(
                    pool,
                    client_id,
                    brand_id,
                    "broadcast",
                    "post_approval",
                    {"post_id": post_id, "platform": platform, "caption": post_data["caption"]},
                    expires_at,
                )
                posts_created += 1

    duration_ms = int((time.time() - t_start) * 1000)
    await log_client_agent_action(
        pool,
        client_id,
        brand_id,
        "broadcast",
        "content_batch_generated",
        f"Generated {posts_created} posts across {len(content_configs)} platform(s)",
        {"posts_created": posts_created},
        "completed",
    )
    print(f"[Broadcast] {brand_name}: {posts_created} post(s) queued for approval ({duration_ms}ms)")


# ---------------------------------------------------------------------------
# 12C-2: Publish queue (every 30 min)
# ---------------------------------------------------------------------------

async def run_publish_queue(pool, client: dict, brand: dict) -> None:
    """Publish all approved posts whose scheduled_for time has passed."""
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    brand_name = brand.get("name", "unknown")

    approved_posts = await get_approved_posts(pool, client_id)
    # filter to this brand
    brand_posts = [p for p in approved_posts if str(p["brand_id"]) == brand_id]

    if not brand_posts:
        return

    published = 0
    failed = 0

    for post in brand_posts:
        post_id = str(post["id"])
        platform = post.get("platform", "instagram")
        caption = post.get("caption") or ""
        hashtags = post.get("hashtags") or []

        try:
            result = await asyncio.to_thread(
                _publish_to_platform, platform, caption, hashtags
            )
            if result.get("success"):
                await update_post_status(pool, post_id, "published")
                published += 1
            else:
                await update_post_status(pool, post_id, "failed")
                failed += 1
        except Exception as e:
            print(f"[Broadcast] {brand_name}: publish failed for post {post_id} — {e}")
            await update_post_status(pool, post_id, "failed")
            failed += 1

    if published or failed:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "broadcast",
            "posts_published",
            f"Published {published}, failed {failed}",
            {"published": published, "failed": failed},
            "completed" if not failed else "partial",
        )
        print(f"[Broadcast] {brand_name}: published={published} failed={failed}")


# ---------------------------------------------------------------------------
# 12C-3: Engagement sync + comment classification (every 2 hours)
# ---------------------------------------------------------------------------

async def run_engagement_sync(pool, client: dict, brand: dict) -> None:
    """Sync engagement metrics and classify new comments for a brand."""
    t_start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    brand_name = brand.get("name", "unknown")

    brand_config = await get_brand_config(pool, brand_id)
    tone = brand_config.get("tone", "professional") if brand_config else "professional"

    # Stub: in production fetch published posts from last 30 days and call platform APIs
    # For now we just look for unprocessed comments already seeded in the DB
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    comments = await get_recent_comments(pool, client_id, brand_id, since_iso)

    if not comments:
        return

    system_prompt = _load_prompt("broadcast_comment.txt")
    classified = 0
    escalated = 0

    for comment in comments:
        comment_id = str(comment["id"])
        text = comment.get("text") or ""

        user_content = json.dumps({
            "brand": {"tone": tone, "word_limit": 80},
            "comment": text,
        })

        try:
            result = await asyncio.to_thread(_call_claude, system_prompt, user_content, 500)
        except Exception as e:
            print(f"[Broadcast] {brand_name}: comment classify error — {e}")
            continue

        await save_comment_classification(pool, comment_id, result)
        classified += 1

        if result.get("escalate_to_human"):
            await save_intelligence(
                pool,
                client_id,
                "comment_escalation",
                {
                    "comment_id": comment_id,
                    "comment_text": text,
                    "escalation_reason": result.get("escalation_reason"),
                    "brand_id": brand_id,
                },
                "critical",
            )
            escalated += 1

    duration_ms = int((time.time() - t_start) * 1000)
    if classified:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "broadcast",
            "engagement_sync",
            f"Classified {classified} comment(s), escalated {escalated}",
            {"classified": classified, "escalated": escalated},
            "completed",
        )
        print(f"[Broadcast] {brand_name}: {classified} comment(s) classified, {escalated} escalated ({duration_ms}ms)")
