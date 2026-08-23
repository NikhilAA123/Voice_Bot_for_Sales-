from fastapi import FastAPI, Depends, HTTPException, Request
from starlette.responses import JSONResponse
from sqlalchemy import text
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

from .schemas import VoiceWebhookPayload
from .services.voice import store_message
from .services.decision import decide_from_transcript
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
    """Endpoint that receives a transcript from the managed voice provider.
    It stores the message, runs a tiny placeholder extraction, and returns the next bot reply.
    """
    # 1️⃣ Store the customer's utterance
    call_id = await store_message(db, payload.call_sid, "customer", payload.transcript)

    # 2️⃣ If the turn is not final yet, we just acknowledge (no bot reply)
    if not payload.is_final:
        return {"reply": ""}

    # 3️⃣ Deterministic decision engine (PRD §9) – keyword layer until Claude lands on Day 4
    decision = decide_from_transcript(payload.transcript)
    logger.info(
        "decision call={} intent={} confidence={} signals={} barrier={}",
        payload.call_sid, decision.intent, decision.confidence,
        decision.signals, decision.barrier,
    )

    # 4️⃣ Response generation based on the decided next action
    if decision.intent == "HOT":
        reply = "Great! I’ll send you a WhatsApp with the proposal right now."
    elif decision.intent == "WARM":
        reply = "I understand. Let me book a callback at a time that works for you."
    else:
        reply = "Thanks for the info. I’ll follow up via email later."

    # 5️⃣ Store the bot reply as well (so the conversation is complete)
    await store_message(db, payload.call_sid, "bot", reply)

    return {"reply": reply}
