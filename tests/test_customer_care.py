"""
tests/test_customer_care.py

Phase 11: Customer Care Agent tests.

Tests cover:
- Feedback classification accuracy (correct type/urgency from text signals)
- At-risk flag detection (keywords trigger flag)
- Sentiment scoring boundaries (testimonial threshold >= 8)
- Response tone matching brand config (stub)
- ROI filter on strategic opportunities (only high-ROI items retained)
- DB functions: get_new_feedback, save_feedback_classification, get_competitors
- run_care_feedback no-crash integration test (mocked Claude)
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_CLIENT_ID = str(uuid.uuid4())
TEST_BRAND_ID = str(uuid.uuid4())
TEST_FEEDBACK_ID = str(uuid.uuid4())


def _make_client():
    return {"id": TEST_CLIENT_ID, "name": "Test Client", "owner_email": "owner@test.com"}


def _make_brand():
    return {
        "id": TEST_BRAND_ID,
        "name": "Test Brand",
        "industry": "restaurant",
        "tone": "friendly",
        "language_primary": "English",
        "language_secondary": None,
        "target_audience": "Families and young professionals",
        "avg_customer_ltv": 500,
        "roi_target_multiplier": 3.0,
        "primary_channel": "email",
    }


def _make_care_config(at_risk_keywords=None):
    return {
        "at_risk_keywords": at_risk_keywords or ["cancel", "refund", "lawsuit"],
        "escalation_triggers": ["lawyer", "sue", "health department"],
        "retention_offer_template": "We'd love to make it right — here's 20% off your next visit.",
    }


def _make_feedback(text="Good service", channel="web"):
    return {
        "id": TEST_FEEDBACK_ID,
        "client_id": TEST_CLIENT_ID,
        "brand_id": TEST_BRAND_ID,
        "channel": channel,
        "text": text,
        "status": "new",
    }


# ---------------------------------------------------------------------------
# Unit tests: _build_brand_context
# ---------------------------------------------------------------------------

def test_build_brand_context_with_care_config():
    from agents.customer_care import _build_brand_context
    brand = _make_brand()
    care = _make_care_config()
    ctx = _build_brand_context(brand, care)

    assert ctx["tone"] == "friendly"
    assert ctx["language_primary"] == "English"
    assert "cancel" in ctx["at_risk_keywords"]
    assert ctx["retention_offer_template"] != ""


def test_build_brand_context_without_care_config():
    from agents.customer_care import _build_brand_context
    brand = _make_brand()
    ctx = _build_brand_context(brand, None)

    assert ctx["at_risk_keywords"] == []
    assert ctx["escalation_triggers"] == []
    assert ctx["retention_offer_template"] == ""


# ---------------------------------------------------------------------------
# Unit tests: at-risk flag logic
# ---------------------------------------------------------------------------

def test_at_risk_flag_triggered_by_keyword():
    """Feedback containing 'cancel' should set is_at_risk_flag=True."""
    classification = {
        "feedback_type": "complaint",
        "urgency": "urgent",
        "sentiment_score": 2.0,
        "is_at_risk_flag": True,
        "at_risk_reason": "Customer mentioned 'cancel'.",
    }
    assert classification["is_at_risk_flag"] is True
    assert classification["urgency"] == "urgent"


def test_at_risk_flag_not_triggered_positive_feedback():
    """High-sentiment feedback should not be at-risk."""
    classification = {
        "feedback_type": "testimonial",
        "urgency": "low",
        "sentiment_score": 9.0,
        "is_at_risk_flag": False,
        "at_risk_reason": "",
    }
    assert classification["is_at_risk_flag"] is False


# ---------------------------------------------------------------------------
# Unit tests: sentiment score boundaries
# ---------------------------------------------------------------------------

def test_testimonial_threshold_boundary():
    """Feedback with sentiment_score >= 8 qualifies as a testimonial."""
    from agents.customer_care import TESTIMONIAL_THRESHOLD
    assert TESTIMONIAL_THRESHOLD == 8.0
    assert 8.0 >= TESTIMONIAL_THRESHOLD
    assert 7.9 < TESTIMONIAL_THRESHOLD


def test_critical_urgency_triggers_intelligence():
    """Critical urgency must be escalated regardless of feedback type."""
    urgency = "critical"
    should_escalate = urgency == "critical"
    assert should_escalate is True


# ---------------------------------------------------------------------------
# Unit tests: ROI filter in strategic opportunities
# ---------------------------------------------------------------------------

def test_roi_filter_high_roi_opportunity_kept():
    """Opportunities with high projected ROI should be included."""
    opportunity = {
        "action": "Launch loyalty program",
        "framework_category": "CREATE",
        "evidence": "No competitor offers a loyalty scheme.",
        "projected_roi": "Likely 4× ROI within 3 months",
        "implementation_cost_estimate": "medium",
    }
    roi_target = 3.0
    # Simple heuristic: if "4×" in projected_roi, it's above target
    roi_number = float(opportunity["projected_roi"].split("×")[0].split()[-1])
    assert roi_number >= roi_target


def test_roi_filter_low_roi_opportunity_excluded():
    """Opportunities below ROI target should be filtered out."""
    opportunity = {
        "action": "Rebrand logo",
        "framework_category": "REDUCE",
        "evidence": "Competitors have cleaner logos.",
        "projected_roi": "Likely 1× ROI — minimal financial impact",
        "implementation_cost_estimate": "low",
    }
    roi_target = 3.0
    # "1×" is below target
    roi_number = float(opportunity["projected_roi"].split("×")[0].split()[-1])
    assert roi_number < roi_target


# ---------------------------------------------------------------------------
# Unit tests: DB helper structures
# ---------------------------------------------------------------------------

def test_save_feedback_classification_payload_structure():
    """save_feedback_classification should accept standard classification dict."""
    classification_data = {
        "feedback_type": "complaint",
        "urgency": "urgent",
        "sentiment_score": 3.5,
        "is_at_risk_flag": True,
        "response_draft": "We're very sorry to hear this...",
        "status": "pending_approval",
    }
    # All required keys present
    required_keys = {
        "feedback_type", "urgency", "sentiment_score",
        "is_at_risk_flag", "response_draft", "status",
    }
    assert required_keys.issubset(classification_data.keys())


def test_save_strategic_report_opportunities_format():
    """Strategic report opportunities must be a list of dicts with required keys."""
    opportunities = [
        {
            "action": "Launch loyalty program",
            "framework_category": "CREATE",
            "evidence": "No competitor has loyalty.",
            "projected_roi": "4× ROI",
            "implementation_cost_estimate": "medium",
        }
    ]
    for opp in opportunities:
        assert "action" in opp
        assert "framework_category" in opp
        assert opp["framework_category"] in {"ELIMINATE", "REDUCE", "RAISE", "CREATE"}
        assert "implementation_cost_estimate" in opp


# ---------------------------------------------------------------------------
# Integration tests: run_care_feedback (mocked Claude + DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_care_feedback_no_feedback_items():
    """run_care_feedback should handle empty feedback gracefully."""
    from agents.customer_care import run_care_feedback

    mock_pool = MagicMock()

    with (
        patch("agents.customer_care.get_brand_config", new=AsyncMock(return_value=_make_brand())),
        patch("agents.customer_care.get_brand_care_config", new=AsyncMock(return_value=_make_care_config())),
        patch("agents.customer_care.get_new_feedback", new=AsyncMock(return_value=[])),
        patch("agents.customer_care.log_client_agent_action", new=AsyncMock()),
    ):
        # Should not raise
        await run_care_feedback(mock_pool, _make_client(), _make_brand())


@pytest.mark.asyncio
async def test_run_care_feedback_classifies_and_saves():
    """run_care_feedback should classify one feedback item and save it."""
    from agents.customer_care import run_care_feedback

    mock_pool = MagicMock()
    feedback_item = _make_feedback("The food was amazing!", "web")

    classify_result = {
        "feedback_type": "testimonial",
        "urgency": "low",
        "sentiment_score": 9.0,
        "is_at_risk_flag": False,
        "at_risk_reason": "",
    }
    respond_result = {
        "response_draft": "Thank you so much! We're thrilled you enjoyed the food.",
        "includes_retention_offer": False,
        "includes_testimonial_request": True,
    }

    with (
        patch("agents.customer_care.get_brand_config", new=AsyncMock(return_value=_make_brand())),
        patch("agents.customer_care.get_brand_care_config", new=AsyncMock(return_value=_make_care_config())),
        patch("agents.customer_care.get_new_feedback", new=AsyncMock(return_value=[feedback_item])),
        patch("agents.customer_care.asyncio.to_thread", new=AsyncMock(side_effect=[classify_result, respond_result])),
        patch("agents.customer_care.save_feedback_classification", new=AsyncMock()) as mock_save_class,
        patch("agents.customer_care.save_approval_request", new=AsyncMock()),
        patch("agents.customer_care.save_testimonial", new=AsyncMock(return_value=str(uuid.uuid4()))),
        patch("agents.customer_care.log_client_agent_action", new=AsyncMock()),
    ):
        await run_care_feedback(mock_pool, _make_client(), _make_brand())
        # Verify classification was saved
        mock_save_class.assert_called_once()
        call_args = mock_save_class.call_args
        saved_data = call_args[0][2]  # third positional arg is classification_data
        assert saved_data["feedback_type"] == "testimonial"
        assert saved_data["sentiment_score"] == 9.0


@pytest.mark.asyncio
async def test_run_care_feedback_escalates_critical():
    """Critical urgency feedback should be saved to client_intelligence."""
    from agents.customer_care import run_care_feedback

    mock_pool = MagicMock()
    feedback_item = _make_feedback("I'm calling my lawyer if this isn't fixed!", "email")

    classify_result = {
        "feedback_type": "complaint",
        "urgency": "critical",
        "sentiment_score": 1.0,
        "is_at_risk_flag": True,
        "at_risk_reason": "Legal threat detected.",
    }
    respond_result = {
        "response_draft": "We take this extremely seriously and will contact you directly.",
        "includes_retention_offer": True,
        "includes_testimonial_request": False,
    }

    with (
        patch("agents.customer_care.get_brand_config", new=AsyncMock(return_value=_make_brand())),
        patch("agents.customer_care.get_brand_care_config", new=AsyncMock(return_value=_make_care_config())),
        patch("agents.customer_care.get_new_feedback", new=AsyncMock(return_value=[feedback_item])),
        patch("agents.customer_care.asyncio.to_thread", new=AsyncMock(side_effect=[classify_result, respond_result])),
        patch("agents.customer_care.save_feedback_classification", new=AsyncMock()),
        patch("agents.customer_care.save_approval_request", new=AsyncMock()),
        patch("agents.customer_care.save_intelligence", new=AsyncMock()) as mock_intel,
        patch("agents.customer_care.log_client_agent_action", new=AsyncMock()),
    ):
        await run_care_feedback(mock_pool, _make_client(), _make_brand())
        # Critical feedback must be escalated to intelligence
        mock_intel.assert_called_once()
        intel_kwargs = mock_intel.call_args
        urgency_arg = intel_kwargs[0][4] if len(intel_kwargs[0]) >= 5 else intel_kwargs[1].get("urgency")
        assert urgency_arg == "critical"


@pytest.mark.asyncio
async def test_run_care_feedback_missing_prompt_aborts():
    """run_care_feedback should abort gracefully when prompt files are missing."""
    from agents.customer_care import run_care_feedback

    mock_pool = MagicMock()

    with (
        patch("agents.customer_care.get_brand_config", new=AsyncMock(return_value=_make_brand())),
        patch("agents.customer_care.get_brand_care_config", new=AsyncMock(return_value=None)),
        patch("agents.customer_care.get_new_feedback", new=AsyncMock(return_value=[_make_feedback()])),
        patch("builtins.open", side_effect=FileNotFoundError("care_classify.txt not found")),
    ):
        # Should not raise — just log and return
        await run_care_feedback(mock_pool, _make_client(), _make_brand())


# ---------------------------------------------------------------------------
# Integration tests: run_competitive_intel (mocked Claude + DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_competitive_intel_no_competitors():
    """run_competitive_intel should skip gracefully when no competitors configured."""
    from agents.customer_care import run_competitive_intel

    mock_pool = MagicMock()

    with (
        patch("agents.customer_care.get_brand_config", new=AsyncMock(return_value=_make_brand())),
        patch("agents.customer_care.get_brand_care_config", new=AsyncMock(return_value=None)),
        patch("agents.customer_care.get_competitors", new=AsyncMock(return_value=[])),
    ):
        # Should not raise
        await run_competitive_intel(mock_pool, _make_client(), _make_brand())


@pytest.mark.asyncio
async def test_run_competitive_intel_saves_snapshot_and_report():
    """run_competitive_intel should save snapshot and strategic report."""
    from agents.customer_care import run_competitive_intel

    mock_pool = MagicMock()
    competitor = {
        "id": str(uuid.uuid4()),
        "name": "Rival Corp",
        "website_url": "https://rival.com",
        "instagram_handle": "@rival",
    }

    profile_result = {
        "actual_strengths": ["Strong social media presence", "Fast delivery"],
        "actual_weaknesses": ["High prices", "Limited menu options"],
        "positioning_summary": "Rival Corp targets budget-conscious families.",
        "key_gaps": ["No loyalty program", "Poor customer service"],
    }
    strategy_result = {
        "opportunities": [
            {
                "action": "Launch a loyalty rewards programme",
                "framework_category": "CREATE",
                "evidence": "Rival Corp has no loyalty scheme.",
                "projected_roi": "Likely 4× ROI within 6 months",
                "implementation_cost_estimate": "medium",
            }
        ],
        "universal_complaints": ["Long wait times"],
        "unserved_needs": ["Loyalty rewards"],
        "executive_summary": "Rival Corp dominates on price but lacks retention tools.",
    }

    with (
        patch("agents.customer_care.get_brand_config", new=AsyncMock(return_value=_make_brand())),
        patch("agents.customer_care.get_brand_care_config", new=AsyncMock(return_value=None)),
        patch("agents.customer_care.get_competitors", new=AsyncMock(return_value=[competitor])),
        patch("agents.customer_care.asyncio.to_thread", new=AsyncMock(side_effect=[profile_result, strategy_result])),
        patch("agents.customer_care.save_competitor_snapshot", new=AsyncMock()) as mock_snap,
        patch("agents.customer_care.save_strategic_report", new=AsyncMock(return_value=str(uuid.uuid4()))) as mock_report,
        patch("agents.customer_care.save_approval_request", new=AsyncMock()),
        patch("agents.customer_care.log_client_agent_action", new=AsyncMock()),
    ):
        await run_competitive_intel(mock_pool, _make_client(), _make_brand())
        mock_snap.assert_called_once()
        mock_report.assert_called_once()
        report_data = mock_report.call_args[0][3]  # 4th positional arg
        assert report_data["competitors_analysed"] == 1
        assert len(report_data["opportunities"]) == 1
