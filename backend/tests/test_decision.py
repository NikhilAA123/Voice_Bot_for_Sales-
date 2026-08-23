"""Scorecard scenario tests for the decision engine.

Each case mirrors the indirect phrasings the assignment warns about:
"send me the details", "my budget is not much right now",
"my brother handles this", "how soon can you start".
"""
import pytest

from app.schemas import LeadState
from app.services.decision import classify_lead, decide_from_transcript


# ---------------------------------------------------------------------------
# HOT – high buying intent, WhatsApp fires mid call
# ---------------------------------------------------------------------------

def test_hot_budget_timeline_and_next_step():
    d = decide_from_transcript(
        "My budget is around 5 lakh and I need it within one month. "
        "How soon can you start?"
    )
    assert d.intent == "HOT"
    assert d.next_action == "send_whatsapp_mid_call"
    assert "budget_and_timeline" in d.signals
    assert "requested_next_step_with_context" in d.signals
    assert d.state.budget == "5 INR"
    assert d.confidence > 0.85


def test_hot_willing_to_proceed_alone_is_enough():
    d = decide_from_transcript("Sounds good, let's do it, go ahead.")
    assert d.intent == "HOT"
    assert "willing_to_proceed" in d.signals
    assert d.next_action == "send_whatsapp_mid_call"


def test_hot_next_step_backed_by_budget():
    d = decide_from_transcript("Budget is 2 lakh. Please send me the details.")
    assert d.intent == "HOT"
    assert d.next_action == "send_whatsapp_mid_call"
    assert "requested_next_step_with_context" in d.signals


# ---------------------------------------------------------------------------
# WARM – interested but a barrier holds it back
# ---------------------------------------------------------------------------

def test_warm_budget_not_finalized():
    d = decide_from_transcript("My budget is not much right now, maybe after some time.")
    assert d.intent == "WARM"
    assert d.state.barrier == "budget_not_finalized"
    assert "barrier:budget_not_finalized" in d.signals
    assert d.next_action == "schedule_callback"


def test_warm_decision_maker_is_someone_else():
    d = decide_from_transcript("My brother handles this, I will discuss with him and tell you.")
    assert d.intent == "WARM"
    assert d.state.decision_maker == "other"
    assert d.state.barrier in ("needs_approval", None) or d.barrier in ("needs_approval",)
    assert d.next_action == "schedule_callback"


def test_warm_hinglish_tight_budget():
    d = decide_from_transcript("Budget thoda tight hai abhi, baad mein dekhte hain.")
    assert d.intent == "WARM"
    assert d.state.barrier == "budget_not_finalized"


def test_warm_bare_next_step_request_without_context():
    """'Send me the details' with nothing else: interest, not readiness."""
    d = decide_from_transcript("Okay, send me the details on WhatsApp.")
    assert d.intent == "WARM"
    assert "requested_next_step" in d.signals
    assert d.next_action == "schedule_callback"


def test_barrier_blocks_even_strong_intent():
    """Proceed request + approval barrier: WARM wins so the barrier is captured."""
    d = decide_from_transcript(
        "I want to proceed right away, but my brother handles these decisions."
    )
    assert d.intent == "WARM"
    assert d.state.barrier == "needs_approval"
    assert "willing_to_proceed" in d.signals  # evidence kept for the LLM/audit
    assert d.next_action == "schedule_callback"


# ---------------------------------------------------------------------------
# COLD – exploring, no need
# ---------------------------------------------------------------------------

def test_cold_just_looking():
    d = decide_from_transcript("No no, I am just looking around for now.")
    assert d.intent == "COLD"
    assert "exploring_no_need" in d.signals
    assert d.next_action == "persist_lead"


def test_cold_nothing_detectable_defaults_safe():
    """Neutral chatter must not trigger any side effect."""
    d = decide_from_transcript("hello hello, can you hear me")
    assert d.intent == "COLD"
    assert d.signals == ["insufficient_evidence"]
    assert d.next_action == "persist_lead"


# ---------------------------------------------------------------------------
# Extraction details + confidence behaviour
# ---------------------------------------------------------------------------

def test_extraction_fills_features_and_product_count():
    d = decide_from_transcript(
        "I have around 500 products, need payment gateway and inventory management."
    )
    assert d.state.product_count == 500
    assert set(d.state.features) >= {"payment_gateway", "inventory"}
    # Specific requirements alone: WARM until budget/timeline arrive.
    assert d.intent == "WARM"


def test_more_evidence_means_higher_confidence():
    strong = decide_from_transcript(
        "Budget 10 lakh, needed within two weeks, send me the proposal."
    )
    weak = decide_from_transcript("Send me the proposal.")
    assert strong.confidence > weak.confidence
    assert 0 < weak.confidence <= 0.95


def test_classify_works_on_pure_state_without_transcript():
    state = LeadState(budget="3 INR", timeline="next month")
    d = classify_lead(state)
    assert d.intent == "HOT"
    assert d.next_action == "send_whatsapp_mid_call"
