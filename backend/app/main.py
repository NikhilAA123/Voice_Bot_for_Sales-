from fastapi import FastAPI, Depends, HTTPException
from starlette.responses import JSONResponse
from .logger import logger
from .settings import settings
from .db import engine, Base, get_db
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI(title="Voice Sales Agent", version="0.1.0")

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
            await conn.execute("SELECT 1")
    except Exception as exc:
        logger.error("Health check failed: {}", exc)
        raise HTTPException(status_code=503, detail="DB unavailable")
    return {"status": "ok", "service": "voice_sales_agent"}
