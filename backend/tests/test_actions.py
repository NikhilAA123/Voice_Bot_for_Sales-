"""Idempotency tests – duplicate webhooks must never double-fire actions.

Runs against an isolated SQLite file per test; no server, no network.
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
import app.models  # noqa: F401
from app.models import Action, Call
from app.services.actions import build_idem_key, get_or_create_action, mark_status


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _session_factory(engine):
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return factory


def test_duplicate_key_returns_same_row(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'a.db'}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = _session_factory(engine)

        async with Session() as db:
            call = Call(call_sid="CA-IDEM-1")
            db.add(call)
            await db.commit()
            await db.refresh(call)

            key = build_idem_key("CA-IDEM-1", "send_whatsapp_mid_call")
            action1, created1 = await get_or_create_action(
                db, call_id=call.id, action_type="send_whatsapp_mid_call", idem_key=key
            )
            action2, created2 = await get_or_create_action(
                db, call_id=call.id, action_type="send_whatsapp_mid_call", idem_key=key
            )

            assert created1 is True
            assert created2 is False
            assert action1.id == action2.id
        await engine.dispose()

    run(scenario())


def test_mark_status_tracks_attempts_and_provider(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'b.db'}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = _session_factory(engine)

        async with Session() as db:
            call = Call(call_sid="CA-IDEM-2")
            db.add(call)
            await db.commit()
            await db.refresh(call)

            action, _ = await get_or_create_action(
                db,
                call_id=call.id,
                action_type="send_whatsapp_mid_call",
                idem_key=build_idem_key("CA-IDEM-2", "send_whatsapp_mid_call"),
            )

            # First attempt fails (WhatsApp down), second succeeds.
            await mark_status(db, action, "failed", error="provider timeout")
            await mark_status(db, action, "sent", provider_id="SM999")

            result = await db.execute(select(Action).where(Action.id == action.id))
            final = result.scalar_one()
            assert final.status == "sent"
            assert final.provider_id == "SM999"
            assert final.attempts == 2
            assert "timeout" in final.last_error
        await engine.dispose()

    run(scenario())


def test_different_action_types_get_distinct_keys():
    assert build_idem_key("C1", "send_whatsapp_mid_call") != build_idem_key("C1", "schedule_callback")
    assert build_idem_key("C1", "x") != build_idem_key("C2", "x")
