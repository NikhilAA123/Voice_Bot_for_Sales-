# AI Voice Sales Agent – Day 1 Foundation

A **reliable, low‑latency, production‑ready** backend for an outbound AI sales system. This repository contains the foundation you need to build a voice‑first sales agent that can call prospects, conduct a natural discovery conversation, classify leads, and trigger follow‑up actions.

## 📦 What you get
| Component | Technology | Why we chose it |
|-----------|------------|-----------------|
| API | FastAPI (Python 3.12) | Async‑first, lightweight, easy to test |
| DB | PostgreSQL 15 (Docker) | Durable storage for calls, leads, callbacks |
| Containerisation | Docker + Docker‑Compose | Reproducible dev environment |
| Logging | Loguru (JSON) | Structured logs – simple to filter |
| Health‑check | `/health` endpoint | Liveness probe for CI/evaluation |

## 🛠️ Prerequisites
- Docker + Docker‑Compose (≥ 2.20)
- Git (optional, for version control)

## 🚀 Getting started locally
```bash
# 1️⃣ Clone (or copy) the repo
# git clone <repo‑url> ai-voice-sales-agent
# or work directly in the folder you just created.

cd voice-sales-agent

# 2️⃣ Create a real .env from the example and fill in your secrets
cp .env.example .env
# edit .env → replace the placeholder values with your actual credentials

# 3️⃣ Build and start the stack
docker compose up --build -d

# 4️⃣ Verify the service is healthy
curl http://localhost:8000/health
# Expected output: {"status":"ok","service":"voice_sales_agent"}

# 5️⃣ When you’re finished, stop everything
docker compose down
```

## 📂 Directory layout
```
voice-sales-agent/
│
├─ .env.example                 # copy → .env with real secrets
├─ .gitignore
├─ docker-compose.yml
├─ README.md
│
├─ backend/
│   ├─ app/
│   │   ├─ __init__.py
│   │   ├─ main.py            # FastAPI entry point, health endpoint
│   │   ├─ settings.py        # pydantic‑based config
│   │   ├─ logger.py          # JSON logger
│   │   └─ db.py              # async SQLAlchemy engine / session factory
│   │
│   ├─ migrations/
│   │   └─ 001_init.sql       # initial schema (tables you’ll extend later)
│   │
│   ├─ requirements.txt
│   └─ Dockerfile
│
└─ README.md
```

## 🎯 Next steps (Day 2)
- Choose a managed real‑time voice platform (e.g., Retell or Vapi) and obtain an API key.
- Wire the platform’s outbound‑call webhook to a new endpoint (e.g., `POST /voice/webhook`).
- Verify a real phone call can connect and that the API receives a JSON payload containing the transcript and language information.

All subsequent days will extend this solid foundation with discovery flow, LLM extraction, lead classification, WhatsApp integration, scheduling, and latency measurement.
