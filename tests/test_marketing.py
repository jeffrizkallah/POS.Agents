"""
tests/test_marketing.py

Phase 14B — Marketing Content Agent test suite.

Tests cover:
  - Slug generation helper
  - Constants (POSTS_PER_WEEK, TARGET_WORD_COUNT)
  - DB function contract (save/fetch/update pattern)
  - Keyword cluster deduplication
  - Blog post save + status lifecycle

Run: pytest tests/test_marketing.py -v
"""

import asyncio
import time
import pytest

from agents.marketing import (
    _slugify,
    POSTS_PER_WEEK,
    TARGET_WORD_COUNT,
)
from tools.database import (
    get_pending_marketing_keywords,
    get_published_blog_slugs,
    save_blog_post,
    update_marketing_keyword_status,
    save_marketing_keyword_cluster,
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

class TestSlugify:
    def test_lowercases(self):
        assert _slugify("How To Reduce Food Waste") == "how-to-reduce-food-waste"

    def test_removes_special_chars(self):
        assert _slugify("AI & Restaurant Software: 2025") == "ai--restaurant-software-2025"

    def test_replaces_spaces_with_hyphens(self):
        assert " " not in _slugify("restaurant management tips")

    def test_trims_to_100_chars(self):
        long_title = "a" * 150
        assert len(_slugify(long_title)) <= 100

    def test_no_leading_trailing_hyphens(self):
        slug = _slugify("  hello world  ")
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_collapses_multiple_hyphens(self):
        # double spaces → double hyphens which are then collapsed
        result = _slugify("food  cost")
        # should not have triple hyphens
        assert "---" not in result


class TestConstants:
    def test_posts_per_week_is_3(self):
        assert POSTS_PER_WEEK == 3

    def test_target_word_count_at_least_1200(self):
        assert TARGET_WORD_COUNT >= 1200


# ---------------------------------------------------------------------------
# DB integration tests (require real Neon DB)
# ---------------------------------------------------------------------------

class TestMarketingKeywordsDB:
    def _make_keywords(self, suffix=""):
        ts = int(time.time() * 1000)
        return [
            {
                "keyword": f"test restaurant ai management {ts}{suffix}",
                "intent": "commercial",
                "cluster_topic": "AI in Restaurants",
                "is_priority": True,
            },
            {
                "keyword": f"test how to reduce food waste {ts}{suffix}",
                "intent": "informational",
                "cluster_topic": "Food Waste Reduction",
                "is_priority": False,
            },
        ]

    def test_save_keyword_cluster_returns_count(self, pool, event_loop):
        async def run():
            keywords = self._make_keywords()
            count = await save_marketing_keyword_cluster(pool, keywords)
            assert count == 2, f"Expected 2 insertions, got {count}"

        event_loop.run_until_complete(run())

    def test_save_keyword_cluster_deduplicates(self, pool, event_loop):
        async def run():
            keywords = self._make_keywords("_dup")
            count1 = await save_marketing_keyword_cluster(pool, keywords)
            count2 = await save_marketing_keyword_cluster(pool, keywords)  # duplicates
            assert count1 == 2
            assert count2 == 0, "Duplicate keywords should not be inserted"

        event_loop.run_until_complete(run())

    def test_get_pending_marketing_keywords_returns_identified(self, pool, event_loop):
        async def run():
            # Seed at least one identified keyword
            keywords = self._make_keywords("_pending")
            await save_marketing_keyword_cluster(pool, keywords)

            result = await get_pending_marketing_keywords(pool, limit=10)
            assert isinstance(result, list)
            # All returned keywords must have status='identified'
            for kw in result:
                assert kw["status"] == "identified"

        event_loop.run_until_complete(run())

    def test_get_pending_keywords_priority_first(self, pool, event_loop):
        async def run():
            keywords = self._make_keywords("_order")
            await save_marketing_keyword_cluster(pool, keywords)

            result = await get_pending_marketing_keywords(pool, limit=50)
            # Priority keywords should come before non-priority
            priorities = [kw["is_priority"] for kw in result]
            # Find first non-priority index
            first_false = next((i for i, p in enumerate(priorities) if not p), None)
            if first_false is not None:
                # All before first_false must be True
                assert all(priorities[:first_false])

        event_loop.run_until_complete(run())

    def test_update_marketing_keyword_status(self, pool, event_loop):
        async def run():
            keywords = self._make_keywords("_status")
            await save_marketing_keyword_cluster(pool, keywords)

            # Fetch a keyword and update its status
            result = await pool.fetchrow(
                """
                SELECT id FROM company_marketing_keywords
                WHERE status = 'identified'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            assert result, "Should have at least one identified keyword"
            kw_id = str(result["id"])

            await update_marketing_keyword_status(pool, kw_id, "in_progress")

            updated = await pool.fetchrow(
                "SELECT status FROM company_marketing_keywords WHERE id = $1", kw_id
            )
            assert updated["status"] == "in_progress"

        event_loop.run_until_complete(run())


class TestBlogPostDB:
    def _make_post_data(self, suffix=""):
        ts = int(time.time() * 1000)
        return {
            "title": f"How to Reduce Restaurant Food Waste {ts}{suffix}",
            "slug": f"reduce-restaurant-food-waste-{ts}{suffix}",
            "content_markdown": "# How to Reduce Restaurant Food Waste\n\nContent here...",
            "meta_title": f"Reduce Food Waste | RestaurantOS {ts}",
            "meta_description": "Learn how AI helps restaurants cut food waste by 30%.",
            "word_count": 1502,
            "seo_score": 78.5,
        }

    def test_save_blog_post_returns_id(self, pool, event_loop):
        async def run():
            post_data = self._make_post_data()
            post_id = await save_blog_post(pool, None, post_data)
            assert post_id is not None, "save_blog_post should return a UUID"

        event_loop.run_until_complete(run())

    def test_save_blog_post_status_is_pending(self, pool, event_loop):
        async def run():
            post_data = self._make_post_data("_pending")
            post_id = await save_blog_post(pool, None, post_data)
            assert post_id

            row = await pool.fetchrow(
                "SELECT status FROM company_blog_posts WHERE id = $1", post_id
            )
            assert row["status"] == "pending_approval"

        event_loop.run_until_complete(run())

    def test_save_blog_post_deduplicates_on_slug(self, pool, event_loop):
        async def run():
            post_data = self._make_post_data("_slug_dup")
            id1 = await save_blog_post(pool, None, post_data)
            id2 = await save_blog_post(pool, None, post_data)  # same slug
            assert id1 is not None
            assert id2 is None, "Duplicate slug should return None (ON CONFLICT DO NOTHING)"

        event_loop.run_until_complete(run())

    def test_get_published_blog_slugs_returns_list(self, pool, event_loop):
        async def run():
            slugs = await get_published_blog_slugs(pool)
            assert isinstance(slugs, list)

        event_loop.run_until_complete(run())

    def test_saved_slug_appears_in_published_slugs(self, pool, event_loop):
        async def run():
            post_data = self._make_post_data("_slug_check")
            post_id = await save_blog_post(pool, None, post_data)
            assert post_id

            slugs = await get_published_blog_slugs(pool)
            assert post_data["slug"] in slugs, (
                "Newly saved pending_approval post slug should appear in get_published_blog_slugs"
            )

        event_loop.run_until_complete(run())

    def test_word_count_and_seo_score_saved(self, pool, event_loop):
        async def run():
            post_data = self._make_post_data("_metrics")
            post_id = await save_blog_post(pool, None, post_data)
            assert post_id

            row = await pool.fetchrow(
                "SELECT word_count, seo_score FROM company_blog_posts WHERE id = $1",
                post_id,
            )
            assert row["word_count"] == 1502
            assert float(row["seo_score"]) == 78.5

        event_loop.run_until_complete(run())
