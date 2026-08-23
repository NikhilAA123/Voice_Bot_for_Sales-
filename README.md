# AI Voice Sales Agent

A backend for an outbound AI sales system. It calls prospects, holds a natural discovery conversation, works out how serious the buyer is, and triggers follow-up actions such as WhatsApp messages and callbacks while the call is still live.

Built around the ElevateBox SDE intern assignment. The PRD in this repository describes the full 14-day implementation plan this project follows.

## Stack

| Component | Technology | Why |
|-----------|------------|-----|
| API | FastAPI (Python 3.12) | Async-first, lightweight, easy to test |
| Database | PostgreSQL 15 (Docker), SQLite for quick local runs | Durable storage for calls, leads, callbacks |
| Voice layer | Retell | Managed real-time voice: STT, TTS, streaming, turn detection |
| LLM | Claude | Structured requirement extraction and lead classification |
| Telephony and WhatsApp | Twilio | Outbound calling plus WhatsApp follow-ups |
| Logging | Loguru, JSON output | Structured logs that are easy to filter |

## Getting started locally

Prerequisites: [uv](https://docs.astral.sh/uv/) installed, Docker only if you want PostgreSQL instead of SQLite.

```bash
# 1. Create the virtual environment and install dependencies
uv venv --python 3.12
uv pip install -r backend/requirements.txt

# 2. Create a real .env from the example and fill in your values
cp .env.example .env

# 3. Start the API (defaults to SQLite, no database server needed)
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload   # Windows
```

Verify the service is healthy:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"voice_sales_agent"}
```

### Running with Docker (PostgreSQL)

```bash
docker compose up --build -d
docker compose down   # when done
```

Compose injects its own `DATABASE_URL` pointing at the Postgres container and loads the remaining variables from `.env`, so the same `.env` file serves both modes.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe, checks DB connectivity |
| POST | `/webhooks/voice` | Receives transcripts from the voice provider, stores both sides of the conversation, returns the next bot reply |

Request latency is measured by middleware on every call and returned in the `X-Process-Time-Ms` header. Anything over 150 ms is logged as `SLOW`, matching the internal overhead targets in the PRD.

## Project structure

```
voice-sales-agent/
│
├─ .env.example                 # copy to .env with real secrets
├─ docker-compose.yml           # Postgres + API
├─ README.md
│
├─ backend/
│   ├─ app/
│   │   ├─ main.py             # FastAPI entry point, health, webhook, latency metrics
│   │   ├─ settings.py         # pydantic-settings configuration
│   │   ├─ logger.py           # JSON logger
│   │   ├─ db.py               # async SQLAlchemy engine and session factory
│   │   ├─ models.py           # ORM schema: leads, calls, requirements, decisions, actions, callbacks
│   │   ├─ schemas.py          # webhook payloads
│   │   └─ services/
│   │       └─ voice.py        # transcript storage and intent extraction placeholder
│   │
│   ├─ migrations/
│   │   └─ 001_init.sql        # Postgres schema, mirrors models.py
│   │
│   ├─ requirements.txt
│   └─ Dockerfile
```

Tables are created automatically at startup from `models.py`. The SQL migration is kept in sync for anyone who prefers applying it manually to Postgres.

## Roadmap

Work follows the PRD's day-by-day plan. Done so far: project foundation, database schema, health check, webhook scaffold with latency measurement. Next: wire the Retell agent, place real outbound calls, replace the placeholder extractor with Claude, add the Hot/Warm/Cold decision engine, mid-call WhatsApp, callback scheduling and the personalized post-call follow-up.
