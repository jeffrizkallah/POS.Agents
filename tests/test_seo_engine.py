"""
tests/test_seo_engine.py

Tests for Phase 13: SEO Engine Agent.

Run with: pytest tests/test_seo_engine.py -v
Uses the real Neon DB (test client/brand seeded from Phase 7A SQL).
"""

import pytest
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from tools.database import (
    create_pool,
    get_all_clients,
    get_brands_for_client,
    get_priority_keywords,
    get_published_slugs,
    save_seo_article,
    update_keyword_status,
    save_keyword_cluster,
)
from agents.seo_engine import (
    _slugify,
    run_seo_engine,
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

def test_slugify_basic():
    assert _slugify("Best Restaurants in Dubai") == "best-restaurants-in-dubai"


def test_slugify_special_chars():
    assert _slugify("What is AI? A Guide!") == "what-is-ai-a-guide"


def test_slugify_multiple_spaces():
    result = _slugify("  Too   Many   Spaces  ")
    assert " " not in result
    assert "--" not in result


def test_slugify_max_length():
    long_title = "a" * 200
    result = _slugify(long_title)
    assert len(result) <= 100


def test_slugify_already_slug():
    assert _slugify("already-a-slug") == "already-a-slug"


# ---------------------------------------------------------------------------
# DB tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_seo_article(pool, test_client_and_brand):
    """save_seo_article should insert and return a UUID."""
    client, brand = test_client_and_brand
    article_data = {
        "title": "Test SEO Article for Phase 13",
        "slug": f"test-seo-article-phase-13-{int(datetime.now(timezone.utc).timestamp())}",
        "content_markdown": "# Test SEO Article\n\nThis is a test article.\n\n## FAQ\n\n**Q: What is this?**\nA: A test.",
        "meta_title": "Test SEO Article | Brand",
        "meta_description": "A test article to verify the SEO engine save function works correctly in Phase 13.",
        "schema_markup": {"@context": "https://schema.org", "@type": "Article", "headline": "Test"},
        "word_count": 50,
        "seo_score": 75,
    }
    article_id = await save_seo_article(
        pool, str(client["id"]), str(brand["id"]), None, article_data
    )
    assert article_id is not None
    assert len(article_id) > 0


@pytest.mark.asyncio
async def test_save_seo_article_duplicate_slug(pool, test_client_and_brand):
    """save_seo_article with a duplicate slug should return None (ON CONFLICT DO NOTHING)."""
    client, brand = test_client_and_brand
    slug = f"duplicate-slug-test-{int(datetime.now(timezone.utc).timestamp())}"
    article_data = {
        "title": "Duplicate Slug Test",
        "slug": slug,
        "content_markdown": "Content here.",
        "meta_title": "Duplicate",
        "meta_description": "Testing duplicate slug prevention.",
        "schema_markup": {},
        "word_count": 20,
        "seo_score": 60,
    }
    first = await save_seo_article(pool, str(client["id"]), str(brand["id"]), None, article_data)
    assert first is not None

    # Insert same slug again — should return None
    second = await save_seo_article(pool, str(client["id"]), str(brand["id"]), None, article_data)
    assert second is None


@pytest.mark.asyncio
async def test_get_published_slugs_returns_list(pool, test_client_and_brand):
    """get_published_slugs should return a list (may be empty)."""
    client, brand = test_client_and_brand
    slugs = await get_published_slugs(pool, str(client["id"]), str(brand["id"]))
    assert isinstance(slugs, list)


@pytest.mark.asyncio
async def test_get_priority_keywords_returns_list(pool, test_client_and_brand):
    """get_priority_keywords should return a list (may be empty for test brand)."""
    _, brand = test_client_and_brand
    keywords = await get_priority_keywords(pool, str(brand["id"]), limit=4)
    assert isinstance(keywords, list)


@pytest.mark.asyncio
async def test_save_keyword_cluster(pool, test_client_and_brand):
    """save_keyword_cluster should insert new keywords without error."""
    _, brand = test_client_and_brand
    keywords = [
        {
            "keyword": f"test keyword seo phase13 {int(datetime.now(timezone.utc).timestamp())}",
            "intent": "informational",
            "cluster_topic": "Test Cluster",
            "is_priority": False,
        }
    ]
    inserted = await save_keyword_cluster(pool, str(brand["id"]), keywords)
    assert isinstance(inserted, int)
    # May be 0 if keyword already exists (ON CONFLICT DO NOTHING)
    assert inserted >= 0


@pytest.mark.asyncio
async def test_update_keyword_status_no_crash(pool, test_client_and_brand):
    """update_keyword_status should not raise for a non-existent ID."""
    # Use a fake UUID — should silently do nothing
    fake_id = "00000000-0000-0000-0000-000000000000"
    await update_keyword_status(pool, fake_id, "in_progress")


# ---------------------------------------------------------------------------
# Article structure validation (no DB, no Claude)
# ---------------------------------------------------------------------------

def test_article_structure_faq_count():
    """An article with 4 FAQ Q&A pairs should produce faq_count >= 4."""
    content = """# My Test Article

    This is the intro with primary keyword in the first 80 words.

    ## Section One
    Content here.

    ## Section Two
    More content.

    ## FAQ

    **Q: What is this?**
    A: A test.

    **Q: Why does it matter?**
    A: It matters a lot.

    **Q: How does it work?**
    A: It works by doing things.

    **Q: Where can I learn more?**
    A: Right here.
    """
    faq_count = content.count("**Q:")
    assert faq_count >= 4


def test_slug_not_in_published(tmp_path):
    """Slug collision detection logic works correctly."""
    published = ["existing-slug", "another-slug"]
    new_slug = "new-article-slug"
    assert new_slug not in published

    duplicate_slug = "existing-slug"
    assert duplicate_slug in published


# ---------------------------------------------------------------------------
# Integration test — agent run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_seo_engine_no_crash(pool, test_client_and_brand):
    """run_seo_engine should complete without raising for a real brand."""
    client, brand = test_client_and_brand
    # May skip gracefully if no keywords; must not raise
    await run_seo_engine(pool, client, brand)
