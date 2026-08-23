"""Deterministic lead decision engine – PRD section 9.

Two layers, deliberately kept separate:

1. extract_lead_state(): turns raw speech into a structured LeadState.
   Phase 1 uses keyword patterns; this gets swapped for a Claude call on
   Day 4 without touching the layer below.

2. classify_lead(): pure business rules over the structured state plus
   detected conversational signals. It picks HOT/WARM/COLD, a confidence
   score and the permitted next action. The LLM never chooses side
   effects directly.
"""
import re
from typing import List, Optional

from ..schemas import Decision, LeadState

# ---------------------------------------------------------------------------
# Layer 1: signal extraction (Phase-1 keyword stand-in for the LLM)
# ---------------------------------------------------------------------------

_BUDGET_AMOUNT = re.compile(
    r"(?:(?:rs\.?|inr|₹|\$)\s*(\d[\d,.]*)|(\d[\d,.]*)\s*(?:k|thousand|lakh|lac|crore)\b)",
    re.IGNORECASE,
)

_URGENCY = [
    r"\basap\b", r"\burgent(?:ly)?\b", r"\bimmediately\b", r"\bthis week\b",
    r"\bwithin\s+\w+\s+weeks?\b", r"\btomorrow\b", r"\bjaldi\b",
]

_TIMELINE = [
    r"\b\d+\s*(?:day|week|month)s?\b",
    r"\bwithin\s+(?:a|an|one|two|\d+)\s*(?:day|week|month)s?\b",
    r"\bnext month\b", r"\bthis month\b", r"\bby next week\b", r"\bsoon\b",
]

_PROCEED = [
    r"\blet'?s (?:do it|proceed|start|go ahead)\b",
    r"\bgo ahead\b",
    r"\bi(?:'m| am) ready to (?:proceed|start|buy)\b",
    r"\bi want to (?:proceed|buy|order)\b",
]

_NEXT_STEP = [
    r"send me (?:the )?(?:details|proposal|quote|pricing)",
    r"share (?:the )?(?:details|proposal|quote)",
    r"whatsapp me (?:the )?(?:details|proposal|quote)",
    r"how soon can you (?:start|deliver)",
    r"when can you start",
]

_NEEDS_APPROVAL = [
    r"my (?:brother|sister|husband|wife|father|mother|son|daughter|partner|boss|manager|team)\b[^.?!]*\b(?:handles?|decides?|looks? after|manages?)\b",
    r"(?:check|talk|discuss|speak) with my ",
    r"\bi will (?:check|confirm|let you know)\b",
    r"(?:decision maker|decision taker) is my (?:brother|husband|wife|father|partner|boss)",
    r"\bmy brother handles\b",
]

_BUDGET_NOT_FINALIZED = [
    r"budget is not (?:much|finalized|fixed|decided|ready)",
    r"(?:no|not much of a) budget right now",
    r"tight budget", r"can'?t afford right now",
    r"thoda tight", r"budget nahi hai abhi",
]

_TIMING_UNCERTAIN = [
    r"maybe (?:later|next)", r"not right now", r"next year",
    r"after some time", r"baad mein",
]

_NEEDS_MORE_INFO = [
    r"need more (?:information|details) first",
    r"tell me more about",
    r"first (?:let me know|give me) (?:the )?(?:price|cost|details)",
]

_CALLBACK_REQUEST = [
    r"\bcall me back\b", r"\bcallback\b", r"\bcall back\b",
    r"call kar (?:lijiye|dena|do|dijiye)", r"\bcall karna\b",
]

_NO_NEED = [
    r"just (?:looking|curious|browsing|exploring|asking)",
    r"\bno need\b",
    r"not (?:interested|planning) right now",
    r"no plans? (?:for|of) a website",
    r"we don'?t need",
]

_FEATURES = {
    "payment_gateway": r"payment (?:gateway|integration)|online payment|\bupi\b",
    "inventory": r"\binventory\b|stock management",
    "shipping": r"\bshipping\b|delivery integration|courier",
    "admin_panel": r"admin (?:panel|dashboard)",
    "mobile_app": r"mobile app",
}

_PRODUCT_COUNT = re.compile(r"\b(\d{1,4})\s*\+?\s*(?:products?|items?|skus?)\b", re.IGNORECASE)


def _match_any(text: str, patterns: List[str]) -> Optional[str]:
    """Return the first matching pattern string, else None."""
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return pattern
    return None


def _extract_budget(text: str) -> Optional[str]:
    match = _BUDGET_AMOUNT.search(text)
    if not match:
        return None
    amount = match.group(1) or match.group(2)
    unit = "USD" if text.lstrip().startswith("$") else "INR"
    return f"{amount} {unit}"


def _extract_timeline(text: str) -> Optional[str]:
    pattern = _match_any(text, _URGENCY + _TIMELINE)
    if not pattern:
        return None
    found = re.search(pattern, text, flags=re.IGNORECASE)
    return found.group(0).lower() if found else None


def extract_lead_state(transcript: str) -> LeadState:
    """Keyword layer: transcript -> structured state. Replaced by Claude on Day 4."""
    text = transcript.lower()

    features = [name for name, pattern in _FEATURES.items() if re.search(pattern, text)]
    count_match = _PRODUCT_COUNT.search(text)

    decision_maker = "other" if _match_any(text, _NEEDS_APPROVAL) else None

    barrier = None
    if _match_any(text, _BUDGET_NOT_FINALIZED):
        barrier = "budget_not_finalized"
    elif _match_any(text, _TIMING_UNCERTAIN):
        barrier = "timing_uncertain"
    elif _match_any(text, _NEEDS_APPROVAL):
        barrier = "needs_approval"
    elif _match_any(text, _NEEDS_MORE_INFO):
        barrier = "needs_more_info"

    return LeadState(
        product_or_service="ecommerce_website" if re.search(r"website|online store|e-?commerce", text) else None,
        product_count=int(count_match.group(1)) if count_match else None,
        features=features,
        budget=_extract_budget(transcript),
        timeline=_extract_timeline(text),
        decision_maker=decision_maker,
        barrier=barrier,
    )


# ---------------------------------------------------------------------------
# Layer 2: deterministic classification – PRD sections 9.1 / 9.2 / 9.3
# ---------------------------------------------------------------------------

def detect_conversation_signals(transcript: str) -> dict:
    """Detect conversational signals the keyword layer can spot in raw speech.

    The conversation layer may override any of these with richer LLM output.
    """
    text = transcript.lower()
    return {
        "proceed_request": _match_any(text, _PROCEED) is not None,
        "next_step_request": _match_any(text, _NEXT_STEP) is not None,
        "no_need": _match_any(text, _NO_NEED) is not None,
        "callback_request": _match_any(text, _CALLBACK_REQUEST) is not None,
    }


def classify_lead(
    state: LeadState,
    *,
    proceed_request: bool = False,
    next_step_request: bool = False,
    no_need_signal: bool = False,
    callback_request: bool = False,
) -> Decision:
    """Pure business rules – PRD sections 9.1/9.2/9.3.

    HOT needs real evidence: budget + timeline, willingness to proceed, or a
    concrete next step backed by budget/timeline. A single weak positive is
    WARM. Barriers always hold a lead at WARM so they get captured.
    """
    has_budget = state.budget is not None
    has_timeline = state.timeline is not None
    has_specs = bool(state.features or state.product_count)

    hot_signals: List[str] = []
    warm_signals: List[str] = []
    cold_signals: List[str] = []

    # Section 9.1
    if has_budget and has_timeline:
        hot_signals.append("budget_and_timeline")
    if proceed_request:
        # Record the evidence even when a barrier blocks it – kept for audit.
        hot_signals.append("willing_to_proceed")
    if next_step_request and (has_budget or has_timeline or has_specs):
        hot_signals.append("requested_next_step_with_context")
    elif next_step_request:
        warm_signals.append("requested_next_step")
    if callback_request:
        # Asking for a callback is engagement, even when nothing else was said.
        warm_signals.append("requested_callback")

    # Section 9.2 supporting signals
    if has_budget:
        warm_signals.append("budget_mentioned")
    if has_timeline:
        warm_signals.append("timeline_mentioned")
    if has_specs:
        warm_signals.append("specific_requirements")

    # Section 9.3
    if no_need_signal and not hot_signals and not warm_signals:
        cold_signals.append("exploring_no_need")

    barrier = state.barrier

    # --- decision rules ----------------------------------------------------
    if cold_signals:
        intent, confidence, signals = "COLD", 0.6, cold_signals
        next_action = "persist_lead"

    elif hot_signals and not barrier:
        confidence = min(0.95, 0.7 + 0.12 * len(hot_signals))
        intent, signals = "HOT", hot_signals
        next_action = "send_whatsapp_mid_call"

    else:
        # Everything else stays WARM: single weak positives and all barriers.
        if barrier and hot_signals:
            # Strong buying evidence blocked by a real-world barrier.
            warm_signals.extend(hot_signals)
        if barrier:
            warm_signals.append("barrier:" + barrier)
        if warm_signals:
            confidence = min(0.9, 0.55 + 0.1 * len(warm_signals))
            intent, signals = "WARM", warm_signals
            next_action = "schedule_callback"
        else:
            intent, confidence, signals = "COLD", 0.55, ["insufficient_evidence"]
            next_action = "persist_lead"

    return Decision(
        intent=intent,
        confidence=round(confidence, 2),
        signals=signals,
        barrier=barrier,
        next_action=next_action,
        state=state,
    )


def decide_from_transcript(transcript: str) -> Decision:
    """Convenience path used by the webhook: extract, detect, classify."""
    state = extract_lead_state(transcript)
    signals = detect_conversation_signals(transcript)
    return classify_lead(
        state,
        proceed_request=signals["proceed_request"],
        next_step_request=signals["next_step_request"],
        no_need_signal=signals["no_need"],
        callback_request=signals["callback_request"],
    )
