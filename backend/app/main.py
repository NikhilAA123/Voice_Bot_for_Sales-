from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from sqlalchemy import select, text
from .logger import logger
from .settings import settings
from .db import engine, Base, get_db
from . import models  # noqa: F401 – registers tables on Base.metadata
from sqlalchemy.ext.asyncio import AsyncSession
import time

app = FastAPI(title="Voice Sales Agent", version="0.1.0")


@app.middleware("http")
async def latency_metrics(request: Request, call_next):
    """PRD §11: measure first – log every request's duration against targets."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    path = request.url.path
    # §11 targets: webhook/action overhead < 100–150 ms; warn when exceeded
    if elapsed_ms > 150:
        logger.warning("SLOW request {} {} -> {:.1f} ms", request.method, path, elapsed_ms)
    else:
        logger.info("request {} {} -> {:.1f} ms", request.method, path, elapsed_ms)
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response

from .models import Call, Callback, Lead
from .schemas import VoiceWebhookPayload
from .services.call_flow import handle_call_turn
from .services.providers import get_voice_provider
from fastapi import Body


@app.on_event("startup")
async def on_startup():
    # Ensure tables exist – safe for dev, ignored in prod migrations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables ensured")

@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Simple liveness probe – returns 200 if DB connection works."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Health check failed: {}", exc)
        raise HTTPException(status_code=503, detail="DB unavailable")
    return {"status": "ok", "service": "voice_sales_agent"}


@app.post("/webhooks/voice", response_class=JSONResponse)
async def voice_webhook(payload: VoiceWebhookPayload = Body(...), db: AsyncSession = Depends(get_db)):
    """Receives one transcript turn from the managed voice provider and runs
    the full pipeline: store -> decide -> act (idempotent) -> reply.
    """
    return await handle_call_turn(db, payload)


# ---------------------------------------------------------------------------
# Outbound calling – PRD section 13 / assignment requirement #01
# ---------------------------------------------------------------------------

class OutboundCallRequest(BaseModel):
    to_number: str = Field(..., description="E.164 number to dial, e.g. +918688664337")
    from_number: str | None = Field(None, description="Optional caller ID override")


@app.post("/calls/outbound", response_class=JSONResponse)
async def place_outbound_call(req: OutboundCallRequest, db: AsyncSession = Depends(get_db)):
    """Trigger the system to dial a prospect on its own. In mock mode (no
    RETELL_API_KEY) the call is only simulated so the flow stays testable."""
    provider = get_voice_provider()
    result = await provider.place_call(req.to_number, req.from_number)

    if result.status == "failed":
        raise HTTPException(status_code=502, detail=result.raw)

    lead = Lead(phone_number=req.to_number)
    db.add(lead)
    await db.flush()
    call = Call(call_sid=result.provider_call_id, lead_id=lead.id, status="in_progress")
    db.add(call)
    await db.commit()
    await db.refresh(call)

    logger.info("outbound call placed to {} -> sid={} ({})",
                req.to_number, result.provider_call_id, type(provider).__name__)
    return {
        "call_sid": result.provider_call_id,
        "lead_id": lead.id,
        "call_id": call.id,
        "status": result.status,
        "provider": type(provider).__name__,
    }


@app.get("/calls/{call_sid}", response_class=JSONResponse)
async def get_call(call_sid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Call).where(Call.call_sid == call_sid))
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="call not found")
    return {
        "call_sid": call.call_sid,
        "lead_id": call.lead_id,
        "status": call.status,
        "started_at": call.started_at.isoformat(),
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "language": call.language,
    }


@app.get("/leads/{lead_id}", response_class=JSONResponse)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    calls_result = await db.execute(select(Call).where(Call.lead_id == lead.id))
    callbacks_result = await db.execute(select(Callback).where(Callback.lead_id == lead.id))
    return {
        "lead_id": lead.id,
        "phone_number": lead.phone_number,
        "status": lead.status,
        "summary": lead.summary,
        "calls": [{"call_sid": c.call_sid, "status": c.status} for c in calls_result.scalars()],
        "callbacks": [
            {"scheduled_at": cb.scheduled_at.isoformat(), "timezone": cb.timezone, "status": cb.status}
            for cb in callbacks_result.scalars()
        ],
    }
