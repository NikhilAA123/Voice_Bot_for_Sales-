from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Call, ConversationMessage

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
