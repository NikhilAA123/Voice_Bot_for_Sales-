"""Personalized WhatsApp message builders – assignment section 06.

The follow-up must reference what the caller ACTUALLY said, read like a
person wrote it, and carry the sender's mobile number. Attachments
(resume, architecture image) are sent as media URLs when provided.
"""
from typing import Optional

from ..schemas import LeadState

MY_NUMBER_LINE = "You can reach me directly at {mobile}."


def _budget_line(state: LeadState) -> str:
    if state.budget:
        return f"you mentioned a budget of around {state.budget}"
    return None


def _timeline_line(state: LeadState) -> str:
    if state.timeline:
        return f"timeline around {state.timeline}"
    return None


def build_midcall_whatsapp(state: LeadState, my_mobile: str) -> str:
    """Short message fired DURING the call for HOT leads (assignment #07)."""
    parts = ["Hi! This is Nikhil's AI assistant – glad you're interested in the e-commerce website."]

    details = [p for p in (_budget_line(state), _timeline_line(state)) if p]
    if state.features:
        details.append("features: " + ", ".join(state.features))
    if details:
        parts.append("Noted down " + "; ".join(details) + ".")

    parts.append("Sending over our proposal right away, like promised!")
    parts.append(MY_NUMBER_LINE.format(mobile=my_mobile))
    return "\n".join(parts)


def build_postcall_followup(
    state: LeadState,
    customer_turns: list[str],
    my_mobile: str,
    *,
    resume_url: Optional[str] = None,
    architecture_url: Optional[str] = None,
) -> str:
    """Post-call follow-up that quotes the caller's own words (assignment #09)."""
    parts = ["Hi! Nikhil here – following up on our call about your e-commerce website."]

    specifics = []
    if state.budget:
        specifics.append(f"budget around {state.budget}")
    if state.timeline:
        specifics.append(f"delivery in {state.timeline}")
    if state.product_count:
        specifics.append(f"{state.product_count} products")
    if state.features:
        specifics.append(", ".join(state.features))

    if specifics:
        parts.append(
            "Quick recap so nothing gets lost: " + ", ".join(specifics) + "."
        )

    # Quote their longest actual sentence back at them (their own words).
    if customer_turns:
        quoted = max(customer_turns, key=len).strip()
        if len(quoted) > 10:
            parts.append(f'You said "{quoted}" – that\'s exactly what we\'ll build first.')

    if resume_url:
        parts.append("Attaching my resume so you know who you talked to.")
    if architecture_url:
        parts.append("Also attaching a sketch of exactly how this system works.")

    parts.append(MY_NUMBER_LINE.format(mobile=my_mobile))
    parts.append("Ping me anytime – happy to adjust the plan.")
    return "\n".join(parts)
