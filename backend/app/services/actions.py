"""Idempotent action engine – PRD section 10 / 14.

Every external side effect (WhatsApp, callback booking, follow-up) is
recorded in the actions table BEFORE it fires, keyed by a deterministic
idempotency key. Duplicate webhooks or retries can never double-send.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Action


def build_idem_key(call_sid: str, action_type: str, turn: int = 0) -> str:
    """Deterministic key: same call + same action type never repeats.

    `turn` lets the same call legitimately send different action types
    multiple times when the conversation genuinely re-triggers them
    (e.g. caller upgrades from WARM to HOT mid-call uses a distinct type).
    """
    return f"{call_sid}:{action_type}:{turn}"


async def get_or_create_action(
    db: AsyncSession,
    *,
    call_id: int,
    action_type: str,
    idem_key: str,
) -> tuple[Action, bool]:
    """Return (action, created). Reuses an existing row on duplicate key."""
    result = await db.execute(select(Action).where(Action.idem_key == idem_key))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing, False

    action = Action(call_id=call_id, type=action_type, idem_key=idem_key)
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action, True


async def mark_status(
    db: AsyncSession,
    action: Action,
    status: str,
    *,
    provider_id: str | None = None,
    error: str | None = None,
    bump_attempts: bool = True,
) -> Action:
    """Persist SENT/FAILED/... after the provider call resolves."""
    action.status = status
    if provider_id is not None:
        action.provider_id = provider_id
    if error is not None:
        action.last_error = error[:500]
    if bump_attempts:
        action.attempts += 1
    await db.commit()
    await db.refresh(action)
    return action
