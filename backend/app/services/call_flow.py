"""Call-flow orchestration – one place that wires every turn:

store the utterance -> decide intent -> persist the decision ->
fire the permitted side effect (idempotently) -> craft the bot reply.

Mid-call WhatsApp and callback booking never block the conversation:
providers are awaited but failures only mark the action FAILED, they do
not raise (PRD section 14: WhatsApp failure must not break the call).
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from ..logger import logger
from ..models import Call, Callback, ConversationMessage, Lead, LeadDecision
from ..schemas import VoiceWebhookPayload
from ..settings import settings
from .actions import build_idem_key, get_or_create_action, mark_status
from .decision import decide_from_transcript
from .followup import build_midcall_whatsapp
from .providers import get_whatsapp_sender
from .timeparse import IST, parse_callback_time
from .voice import store_message

_IST = ZoneInfo("Asia/Kolkata")


async def _get_call(db: AsyncSession, call_sid: str) -> Call | None:
    result = await db.execute(select(Call).where(Call.call_sid == call_sid))
    return result.scalar_one_or_none()


async def _ensure_lead(db: AsyncSession, call: Call, fallback_number: str | None) -> Lead | None:
    if call.lead_id is not None:
        result = await db.execute(select(Lead).where(Lead.id == call.lead_id))
        return result.scalar_one_or_none()

    phone = fallback_number or "unknown"
    lead = Lead(phone_number=phone)
    db.add(lead)
    await db.flush()
    call.lead_id = lead.id
    await db.commit()
    await db.refresh(call)
    return lead


async def _persist_decision(db: AsyncSession, call: Call, decision, transcript: str) -> None:
    row = LeadDecision(
        call_id=call.id,
        intent=decision.intent,
        confidence=decision.confidence,
        signals=decision.signals,
        barrier=decision.barrier,
        next_action=decision.next_action,
        raw_json={"transcript": transcript, **decision.model_dump(mode="json")},
    )
    db.add(row)
    await db.commit()


async def _fire_midcall_whatsapp(
    db: AsyncSession, call: Call, lead: Lead | None, decision, my_mobile: str
) -> dict:
    """HOT path: WhatsApp during the live call. Idempotent per call."""
    action, created = await get_or_create_action(
        db,
        call_id=call.id,
        action_type="send_whatsapp_mid_call",
        idem_key=build_idem_key(call.call_sid, "send_whatsapp_mid_call"),
    )
    if not created and action.status in ("sent", "pending"):
        logger.info("whatsapp already {} for call {}, skipping duplicate", action.status, call.call_sid)
        return {"fired": False, "reason": "duplicate"}

    to_number = lead.phone_number if lead and lead.phone_number != "unknown" else my_mobile
    body = build_midcall_whatsapp(decision.state, my_mobile)

    sender = get_whatsapp_sender()
    try:
        result = await sender.send(to_number, body)
    except Exception as exc:                       # noqa: BLE001 – never break the call
        logger.error("mid-call whatsapp crashed for {}: {}", call.call_sid, exc)
        await mark_status(db, action, "failed", error=str(exc))
        return {"fired": False, "reason": "error"}

    status = "sent" if result.status == "sent" else "failed"
    await mark_status(db, action, status, provider_id=result.provider_call_id or None,
                      error=None if status == "sent" else str(result.raw))
    logger.info("mid-call whatsapp {} -> {} ({})", call.call_sid, status, to_number)
    return {"fired": status == "sent", "to": to_number}


async def _book_callback(db: AsyncSession, call: Call, lead: Lead | None, transcript: str) -> tuple[Callback | None, bool]:
    """WARM path: parse spoken time; book once per call."""
    when = parse_callback_time(transcript)
    if when is None:
        return None, False

    action, created = await get_or_create_action(
        db,
        call_id=call.id,
        action_type="schedule_callback",
        idem_key=build_idem_key(call.call_sid, "schedule_callback"),
    )
    if not created:
        return None, False                          # callback already booked this call

    if lead is None:
        await mark_status(db, action, "failed", error="no lead attached to call")
        return None, False

    callback = Callback(
        lead_id=lead.id,
        scheduled_at=datetime.fromtimestamp(when.timestamp(), tz=_IST),
        timezone="Asia/Kolkata",
        status="pending",
    )
    db.add(callback)
    await mark_status(db, action, "sent", provider_id=str(callback.scheduled_at))
    logger.info("callback booked call={} at {}", call.call_sid, when.isoformat())
    return callback, True


def _reply_for(intent: str, booked: bool, when: datetime | None) -> str:
    if intent == "HOT":
        return "Great! I’ll send you a WhatsApp with the proposal right now."
    if intent == "WARM":
        if booked and when:
            friendly = when.strftime("%A at %I:%M %p")
            return f"No problem – I’ll call you back {friendly}. Talk to you then!"
        return "I understand. Let me know a good time and I’ll book a callback for you."
    return "Thanks for the info. I’ll follow up via email later."


async def _customer_transcript(db: AsyncSession, call: Call) -> str:
    """All customer utterances so far – intent is judged on cumulative
    evidence (PRD: requirements are extracted continuously), not per turn."""
    result = await db.execute(
        select(ConversationMessage.content)
        .where(ConversationMessage.call_id == call.id, ConversationMessage.speaker == "customer")
        .order_by(ConversationMessage.id)
    )
    return " ".join(row[0] for row in result.all())


async def handle_call_turn(db: AsyncSession, payload: VoiceWebhookPayload) -> dict:
    """Process one webhook turn end-to-end. Never raises on provider errors."""
    # 1️⃣ Store the customer's utterance
    call_id = await store_message(db, payload.call_sid, "customer", payload.transcript)

    # Not final yet: acknowledge, no decisions on partial speech.
    if not payload.is_final:
        return {"reply": "", "intent": None}

    call = await _get_call(db, payload.call_sid)
    if call is None:                                # defensive: should not happen
        return {"reply": "", "intent": None, "error": "call not found"}

    lead = await _ensure_lead(db, call, payload.from_number)

    # 2️⃣ Decide on the FULL conversation so far (deterministic engine until Claude lands)
    full_transcript = await _customer_transcript(db, call)
    decision = decide_from_transcript(full_transcript)
    logger.info(
        "decision call={} intent={} confidence={} signals={} barrier={}",
        payload.call_sid, decision.intent, decision.confidence,
        decision.signals, decision.barrier,
    )
    await _persist_decision(db, call, decision, full_transcript)

    # 3️⃣ Act while still on the call
    whatsapp_result = None
    callback_booked, when = False, None
    if decision.intent == "HOT":
        whatsapp_result = await _fire_midcall_whatsapp(db, call, lead, decision, settings.MY_MOBILE)
    elif decision.intent == "WARM":
        callback, booked = await _book_callback(db, call, lead, payload.transcript)
        callback_booked, when = booked, callback.scheduled_at if callback else None

    # 4️⃣ Craft the spoken reply
    reply = _reply_for(decision.intent, callback_booked, when)

    # 5️⃣ Mirror the bot turn into the transcript
    await store_message(db, payload.call_sid, "bot", reply)

    return {
        "reply": reply,
        "intent": decision.intent,
        "confidence": decision.confidence,
        "signals": decision.signals,
        "barrier": decision.barrier,
        "next_action": decision.next_action,
        "whatsapp": whatsapp_result,
        "callback_scheduled_at": when.isoformat() if when else None,
    }
