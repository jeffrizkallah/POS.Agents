"""
agents/seo_engine.py

Phase 13: SEO Engine Agent

run_seo_engine(pool, client, brand)  — runs Monday 06:00 (alongside broadcast batch)
  1. Fetch brand config (industry, target_audience, location).
  2. Call Claude (seo_keywords.txt) to generate new keyword clusters — save any new
     keywords not already in DB.
  3. Fetch up to 4 priority keywords (status='identified') per brand per run.
  4. Fetch published slugs to pass as context (avoid duplicate articles).
  5. For each keyword: call Claude (seo_article.txt) — returns full article with
     schema_markup, meta fields, and FAQ.
  6. Save article as pending_approval; mark keyword status=in_progress;
     create approval request via Orchestrator.

Called via _async_client_agent_job() in main.py.
Schedule: CronTrigger(day_of_week='mon', hour=6, minute=0)
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import anthropic

from tools.database import (
    get_brand_config,
    get_priority_keywords,
    get_published_slugs,
    save_seo_article,
    update_keyword_status,
    save_keyword_cluster,
    save_approval_request,
    log_client_agent_action,
)

# How many priority keywords to process per brand per weekly run
MAX_KEYWORDS_PER_RUN = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(
    system_prompt: str, user_content: str, max_tokens: int = 4000
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
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:100]


# ---------------------------------------------------------------------------
# 13C-1: Keyword cluster generation
# ---------------------------------------------------------------------------

async def _generate_keyword_clusters(
    brand_config: dict, system_prompt: str
) -> list[dict]:
    """Ask Claude to generate new keyword clusters for this brand's industry + audience.

    Returns a flat list of keyword dicts ready for save_keyword_cluster().
    """
    user_content = json.dumps({
        "industry": brand_config.get("industry"),
        "target_audience": brand_config.get("target_audience"),
        "language": brand_config.get("language_primary", "English"),
        "business_model": brand_config.get("business_model"),
    })
    try:
        result = await asyncio.to_thread(_call_claude, system_prompt, user_content, 2000)
    except Exception as e:
        print(f"[SEO] Keyword generation Claude error: {e}")
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
# 13C-2: Article generation
# ---------------------------------------------------------------------------

async def _generate_article(
    brand_config: dict,
    keyword: dict,
    published_slugs: list[str],
    system_prompt: str,
) -> dict | None:
    """Ask Claude to write a full SEO article for a single keyword.

    Returns the article dict or None on failure.
    """
    user_content = json.dumps({
        "brand": {
            "name": brand_config.get("name"),
            "industry": brand_config.get("industry"),
            "target_audience": brand_config.get("target_audience"),
            "tone": brand_config.get("tone", "professional"),
            "language_primary": brand_config.get("language_primary", "English"),
        },
        "primary_keyword": keyword.get("keyword"),
        "intent": keyword.get("intent"),
        "cluster_topic": keyword.get("cluster_topic"),
        "word_count_target": 1200,
        "existing_slugs": published_slugs,
    })
    try:
        result = await asyncio.to_thread(_call_claude, system_prompt, user_content, 4000)
        return result
    except Exception as e:
        print(f"[SEO] Article generation Claude error for keyword '{keyword.get('keyword')}': {e}")
        return None


# ---------------------------------------------------------------------------
# 13C-3: Main agent entry point
# ---------------------------------------------------------------------------

async def run_seo_engine(pool, client: dict, brand: dict) -> None:
    """Generate SEO keyword clusters and long-form articles for a brand.

    Steps:
      1. Fetch brand config.
      2. Generate new keyword clusters + save to DB.
      3. Fetch up to MAX_KEYWORDS_PER_RUN priority keywords.
      4. For each keyword: generate article → save as pending_approval → mark in_progress.
      5. Create Orchestrator approval request for each article.
    """
    t_start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    brand_name = brand.get("name", "unknown")

    # 1. Brand config
    brand_config = await get_brand_config(pool, brand_id)
    if not brand_config:
        print(f"[SEO] {brand_name}: no brand config — skipping")
        return

    keyword_prompt = _load_prompt("seo_keywords.txt")
    article_prompt = _load_prompt("seo_article.txt")

    # 2. Generate + save new keyword clusters
    new_keywords = await _generate_keyword_clusters(brand_config, keyword_prompt)
    if new_keywords:
        inserted = await save_keyword_cluster(pool, brand_id, new_keywords)
        print(f"[SEO] {brand_name}: {inserted} new keyword(s) saved from cluster generation")

    # 3. Fetch priority keywords
    keywords = await get_priority_keywords(pool, brand_id, MAX_KEYWORDS_PER_RUN)
    if not keywords:
        print(f"[SEO] {brand_name}: no identified keywords — nothing to write")
        await log_client_agent_action(
            pool, client_id, brand_id, "seo_engine", "no_keywords",
            "No identified keywords available this week", {}, "completed",
        )
        return

    # 4. Fetch existing slugs to prevent duplicates
    published_slugs = await get_published_slugs(pool, client_id, brand_id)

    articles_created = 0

    for kw in keywords:
        keyword_id = str(kw["id"])
        keyword_text = kw.get("keyword", "")

        # Generate article
        article = await _generate_article(brand_config, kw, published_slugs, article_prompt)
        if not article:
            continue

        # Ensure slug is unique; fall back to slugifying the title
        slug = article.get("slug") or _slugify(article.get("title", keyword_text))
        if slug in published_slugs:
            slug = f"{slug}-{int(time.time())}"
        article["slug"] = slug

        # Save article
        article_id = await save_seo_article(pool, client_id, brand_id, keyword_id, article)
        if not article_id:
            print(f"[SEO] {brand_name}: duplicate slug '{slug}' — skipped")
            continue

        # Track slug to prevent duplicates within same run
        published_slugs.append(slug)

        # Mark keyword in_progress
        await update_keyword_status(pool, keyword_id, "in_progress")

        # Create approval request (72h expiry — articles take more review time)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
        await save_approval_request(
            pool,
            client_id,
            brand_id,
            "seo_engine",
            "article_approval",
            {
                "article_id": article_id,
                "title": article.get("title"),
                "slug": slug,
                "keyword": keyword_text,
                "word_count": article.get("word_count"),
                "seo_score": article.get("seo_score"),
            },
            expires_at,
        )
        articles_created += 1
        print(f"[SEO] {brand_name}: article queued — '{article.get('title')}' ({article.get('word_count', 0)} words)")

    duration_ms = int((time.time() - t_start) * 1000)
    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "seo_engine",
            "articles_generated",
            f"Generated {articles_created} SEO article(s) from {len(keywords)} keyword(s)",
            {"articles_created": articles_created, "keywords_processed": len(keywords)},
            "completed",
            duration_ms,
        )
    except Exception as e:
        print(f"[SEO] {brand_name}: log_client_agent_action failed — {e}")
    print(f"[SEO] {brand_name}: {articles_created}/{len(keywords)} article(s) queued for approval ({duration_ms}ms)")
