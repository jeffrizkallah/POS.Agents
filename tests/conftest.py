"""
tests/conftest.py — Shared pytest fixtures

Function-scoped pool is required because asyncpg pools are bound to the event
loop they were created in. pytest-asyncio 0.23.0 creates a new event loop per
test function, so each test must create its own pool.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest_asyncio
from dotenv import load_dotenv

load_dotenv()

from tools.database import create_pool, get_all_restaurants


@pytest_asyncio.fixture
async def pool():
    """Fresh asyncpg pool for each test. Closed after the test completes."""
    p = await create_pool()
    yield p
    await p.close()


@pytest_asyncio.fixture
async def demo_restaurant(pool):
    """First restaurant row from the DB (Demo Bistro in dev)."""
    restaurants = await get_all_restaurants(pool)
    assert restaurants, "No restaurants found in DB — seed data missing."
    return restaurants[0]
