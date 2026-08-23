from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Call, ConversationMessage

# Simple placeholder LLM extraction – in a real system you would call Claude/GPT here.
async def dummy_extract_requirements(transcript: str) -> Dict:
    # Very naive keyword detection – just for the scaffold.
    lower = transcript.lower()
    budget = None
    timeline = None
    if "lakh" in lower or "$" in lower:
        # Extract a number before the word "lakh" or after $ – crude demo
        import re
        m = re.search(r"(\d+[\d,.]*)\s*lakh", lower)
        if m:
            budget = f"{m.group(1)} lakh"
        else:
            m = re.search(r"\$(\d+[\d,.]*)", transcript)
            if m:
                budget = f"${m.group(1)}"
    if "week" in lower or "month" in lower:
        timeline = "short"
    # Determine intent via simple heuristics
    intent = "COLD"
    if budget and timeline:
        intent = "HOT"
    elif budget:
        intent = "WARM"
    return {
        "budget": budget,
        "timeline": timeline,
        "intent": intent,
        "evidence": [],
    }

async def store_message(db: AsyncSession, call_sid: str, speaker: str, content: str):
    # Find or create the call record
    result = await db.execute(select(Call).where(Call.call_sid == call_sid))
    call = result.scalar_one_or_none()
    if not call:
        call = Call(call_sid=call_sid, status="in_progress")
        db.add(call)
        await db.commit()
        await db.refresh(call)
    # Insert the message
    msg = ConversationMessage(
        call_id=call.id,
        speaker=speaker,
        content=content,
        seq_number=0,  # simple placeholder – real implementation would increment
    )
    db.add(msg)
    await db.commit()
    return call.id
