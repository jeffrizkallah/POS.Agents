"""
agents/marketing.py

Phase 14B: Marketing Content Agent

Generates SEO blog posts for RestaurantOS's own marketing website, targeting
"AI restaurant management" and related keywords. This is company-level content,
NOT content generated for clients.

Workflow:
  Weekly (Monday 07:00) — run_marketing_content(pool):
    1. Call Claude (marketing_keywords.txt) to generate new keyword clusters.
    2. Save new keywords to company_marketing_keywords (deduplicated).
    3. Fetch up to POSTS_PER_WEEK priority keywords with status='identified'.
    4. For each: call Claude (marketing_article.txt) to write a 1,500-word post.
    5. Save post as pending_approval; mark keyword in_progress.

  Daily weekdays (10:30) — run_marketing_publish(pool):
    1. Fetch approved blog posts not yet published.
    2. Post to Buffer API (stub — wire real Buffer API in production).
    3. Mark post as published.

Environment variables required:
  ANTHROPIC_API_KEY    — Claude API key (shared with other agents)
  BUFFER_ACCESS_TOKEN  — Buffer API token (optional; stubbed if missing)
  MARKETING_SITE_URL   — Base URL of the marketing blog (e.g. https://restaurantos.ai/blog)
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone

import anthropic

from tools.database import (
    get_pending_marketing_keywords,
    get_published_blog_slugs,
    save_blog_post,
    update_marketing_keyword_status,
    save_marketing_keyword_cluster,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSTS_PER_WEEK = 3            # Blog posts to generate per weekly run
TARGET_WORD_COUNT = 1500      # Target post length
MAX_KEYWORDS_PER_RUN = POSTS_PER_WEEK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 4000) -> dict:
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
    return json.loads(raw.strip())


def _slugify(text: str) -> str:
    """Convert title text to a URL-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:100]


# ---------------------------------------------------------------------------
# 14B-1: Keyword cluster generation
# ---------------------------------------------------------------------------

async def _generate_marketing_keywords(system_prompt: str) -> list[dict]:
    """Ask Claude to generate keyword clusters for the RestaurantOS blog.

    Returns a flat list of keyword dicts ready for save_marketing_keyword_cluster().
    """
    user_content = json.dumps({
        "company": "RestaurantOS",
        "product_category": "AI restaurant management software",
        "target_audience": "independent restaurant owners and multi-location operators",
        "primary_topics": [
            "AI in restaurant management",
            "inventory management automation",
            "food cost control",
            "restaurant profitability",
            "restaurant technology",
        ],
    })

    try:
        result = await asyncio.to_thread(_call_claude, system_prompt, user_content, 2000)
    except Exception as e:
        print(f"[Marketing] Keyword generation Claude error: {e}")
        return []

    clusters = result.get("clusters") or []
    keywords: list[dict] = []
    for cluster in clusters:
        cluster_topic = cluster.get("cluster_topic", "")
        for kw in cluster.get("keywords") or []:
            keywords.append({
                "keyword": kw.get("keyword"),
                "intent": kw.get("intent"),
                "cluster_topic": cluster_topic,
                "is_priority": False,
            })
    return keywords


# ---------------------------------------------------------------------------
# 14B-2: Blog post generation
# ---------------------------------------------------------------------------

async def _generate_blog_post(
    keyword: dict, existing_slugs: list[str], system_prompt: str
) -> dict | None:
    """Ask Claude to write a full SEO blog post for a single keyword.

    Returns the post dict or None on failure.
    """
    user_content = json.dumps({
        "company": "RestaurantOS",
        "website_url": os.environ.get("MARKETING_SITE_URL", "https://restaurantos.ai/blog"),
        "primary_keyword": keyword.get("keyword"),
        "intent": keyword.get("intent"),
        "cluster_topic": keyword.get("cluster_topic"),
        "word_count_target": TARGET_WORD_COUNT,
        "existing_slugs": existing_slugs,
        "tone": "authoritative yet approachable — written for busy restaurant owners, not tech people",
        "cta": "Start your free trial at restaurantos.ai",
    })

    try:
        result = await asyncio.to_thread(_call_claude, system_prompt, user_content, 4000)
        return result
    except Exception as e:
        print(f"[Marketing] Article Claude error for keyword '{keyword.get('keyword')}': {e}")
        return None


# ---------------------------------------------------------------------------
# 14B-3: Buffer publish (stub — wire real API in production)
# ---------------------------------------------------------------------------

def _publish_to_buffer(post: dict) -> str | None:
    """Publish a blog post link to Buffer for LinkedIn/Instagram scheduling.

    Returns Buffer post ID or None if Buffer token is not set (stub mode).

    Production: POST https://api.bufferapp.com/1/updates/create.json
    """
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        print("[Marketing] BUFFER_ACCESS_TOKEN not set — skipping Buffer publish (stub mode)")
        return None

    site_url = os.environ.get("MARKETING_SITE_URL", "https://restaurantos.ai/blog")
    post_url = f"{site_url}/{post.get('slug', '')}"

    import requests  # local import to keep top-level imports minimal
    payload = {
        "access_token": token,
        "text": f"New post: {post.get('meta_title') or post.get('title')} — {post_url}",
        "media[link]": post_url,
        "media[title]": post.get("meta_title") or post.get("title"),
        "media[description]": post.get("meta_description", ""),
        "now": False,
    }
    try:
        resp = requests.post(
            "https://api.bufferapp.com/1/updates/create.json",
            data=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("id") or data.get("updates", [{}])[0].get("id")
    except Exception as e:
        print(f"[Marketing] Buffer API error for post '{post.get('slug')}': {e}")
        return None


# ---------------------------------------------------------------------------
# 14B-4: Main entry points
# ---------------------------------------------------------------------------

async def run_marketing_content(pool) -> None:
    """Weekly job: generate keyword clusters and write blog posts.

    Called by marketing_content_job() in main.py.
    Schedule: CronTrigger(day_of_week='mon', hour=7, minute=0)
    """
    t_start = time.time()

    keyword_prompt = _load_prompt("marketing_keywords.txt")
    article_prompt = _load_prompt("marketing_article.txt")

    # 1. Generate + save new keyword clusters
    new_keywords = await _generate_marketing_keywords(keyword_prompt)
    if new_keywords:
        inserted = await save_marketing_keyword_cluster(pool, new_keywords)
        print(f"[Marketing] {inserted} new keyword(s) saved from cluster generation")

    # 2. Fetch priority keywords
    keywords = await get_pending_marketing_keywords(pool, limit=MAX_KEYWORDS_PER_RUN)
    if not keywords:
        print("[Marketing] No identified marketing keywords — nothing to write this week")
        return

    # 3. Fetch existing slugs to prevent duplicates
    existing_slugs = await get_published_blog_slugs(pool)

    posts_created = 0

    for kw in keywords:
        keyword_id = str(kw["id"])
        keyword_text = kw.get("keyword", "")

        # 4. Generate blog post
        post = await _generate_blog_post(kw, existing_slugs, article_prompt)
        if not post:
            continue

        # Ensure slug is unique
        slug = post.get("slug") or _slugify(post.get("title", keyword_text))
        if slug in existing_slugs:
            slug = f"{slug}-{int(time.time())}"
        post["slug"] = slug

        # 5. Save as pending_approval
        post_id = await save_blog_post(pool, keyword_id, post)
        if not post_id:
            print(f"[Marketing] Duplicate slug '{slug}' — skipped")
            continue

        # Track slug within same run
        existing_slugs.append(slug)

        # Mark keyword in_progress
        await update_marketing_keyword_status(pool, keyword_id, "in_progress")

        posts_created += 1
        print(
            f"[Marketing] Post queued — '{post.get('title')}' "
            f"({post.get('word_count', 0)} words, SEO score={post.get('seo_score')})"
        )

    duration_ms = int((time.time() - t_start) * 1000)
    print(
        f"[Marketing] run_marketing_content complete — "
        f"{posts_created}/{len(keywords)} post(s) queued for approval ({duration_ms}ms)"
    )


async def run_marketing_publish(pool) -> None:
    """Daily job: publish approved blog posts via Buffer.

    Called by marketing_publish_job() in main.py.
    Schedule: CronTrigger(day_of_week='mon-fri', hour=10, minute=30)
    """
    t_start = time.time()

    try:
        rows = await pool.fetch(
            """
            SELECT id, keyword_id, title, slug, meta_title, meta_description,
                   word_count, seo_score
            FROM company_blog_posts
            WHERE status = 'approved'
            ORDER BY created_at ASC
            LIMIT 5
            """
        )
        approved_posts = [dict(r) for r in rows]
    except Exception as e:
        print(f"[Marketing] Failed to fetch approved posts: {e}")
        return

    if not approved_posts:
        print("[Marketing] No approved posts to publish")
        return

    print(f"[Marketing] {len(approved_posts)} approved post(s) to publish")
    published = 0

    for post in approved_posts:
        post_id = str(post["id"])
        title = post.get("title", "")

        # Publish via Buffer (stub if token not set)
        buffer_id = await asyncio.to_thread(_publish_to_buffer, post)

        try:
            await pool.execute(
                """
                UPDATE company_blog_posts
                SET status         = 'published',
                    published_at   = NOW(),
                    buffer_post_id = $2
                WHERE id = $1
                """,
                post_id,
                buffer_id,
            )
            # Mark keyword as published
            if post.get("keyword_id"):
                await update_marketing_keyword_status(
                    pool, str(post["keyword_id"]), "published"
                )
        except Exception as e:
            print(f"[Marketing] DB update failed for post '{title}': {e}")
            continue

        published += 1
        status_note = f"buffer_id={buffer_id}" if buffer_id else "Buffer stub (no token)"
        print(f"[Marketing] Published '{title}' — {status_note}")

    duration_ms = int((time.time() - t_start) * 1000)
    print(f"[Marketing] run_marketing_publish complete — {published} published ({duration_ms}ms)")
