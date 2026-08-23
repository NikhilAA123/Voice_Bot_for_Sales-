"""WhatsApp message builder tests – the assignment's section 06 rules:
context must be specific, human-sounding, and carry the mobile number.
"""
from app.schemas import LeadState
from app.services.followup import build_midcall_whatsapp, build_postcall_followup

MY_MOBILE = "+919999999999"


def test_midcall_mentions_budget_and_number():
    state = LeadState(budget="3 lakh INR", timeline="one month", features=["payment_gateway"])
    msg = build_midcall_whatsapp(state, MY_MOBILE)

    assert "3 lakh INR" in msg
    assert "payment_gateway" in msg
    assert MY_MOBILE in msg


def test_postcall_quotes_the_callers_own_words():
    state = LeadState(budget="5 INR", timeline="tomorrow")
    turns = [
        "hello",
        "I sell handmade jewellery online and I need it before Diwali season",
        "ok",
    ]
    msg = build_postcall_followup(state, turns, MY_MOBILE)

    # The longest customer sentence is quoted verbatim – assignment #09.
    assert "handmade jewellery" in msg
    assert MY_MOBILE in msg
    assert "budget around 5 INR" in msg


def test_messages_stay_human_when_state_is_empty():
    msg = build_postcall_followup(LeadState(), ["hi"], MY_MOBILE)
    assert MY_MOBILE in msg
    assert "None" not in msg          # unknown fields must never leak as 'None'
