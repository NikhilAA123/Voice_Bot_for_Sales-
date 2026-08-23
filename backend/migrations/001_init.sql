-- 001_init.sql – mirrors backend/app/models.py (PRD §12). Applied manually to Postgres
-- if you don't rely on Base.metadata.create_all at startup.
CREATE TABLE IF NOT EXISTS leads (
    id            SERIAL PRIMARY KEY,
    phone_number  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new',
    summary       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calls (
    id            SERIAL PRIMARY KEY,
    call_sid      TEXT UNIQUE NOT NULL,
    lead_id       INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at      TIMESTAMPTZ,
    language      TEXT,
    status        TEXT NOT NULL DEFAULT 'in_progress',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id            SERIAL PRIMARY KEY,
    call_id       INTEGER REFERENCES calls(id) ON DELETE CASCADE,
    speaker       TEXT NOT NULL,           -- PRD §12 "role": customer | bot
    content       TEXT NOT NULL,
    seq_number    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS requirements (
    id                 SERIAL PRIMARY KEY,
    call_id            INTEGER REFERENCES calls(id) ON DELETE CASCADE,
    business_type      TEXT,
    product_or_service TEXT,
    product_count      INTEGER,
    features           JSONB DEFAULT '[]'::jsonb,   -- unknown fields stay null/empty
    budget             TEXT,
    timeline           TEXT,
    decision_maker     TEXT,
    pain_points        JSONB DEFAULT '[]'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lead_decisions (
    id            SERIAL PRIMARY KEY,
    call_id       INTEGER REFERENCES calls(id) ON DELETE CASCADE,
    intent        TEXT NOT NULL,           -- HOT | WARM | COLD
    confidence    NUMERIC(5,2),
    signals       JSONB DEFAULT '[]'::jsonb,
    barrier       TEXT,
    next_action   TEXT,
    raw_json      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS actions (
    id            SERIAL PRIMARY KEY,
    call_id       INTEGER REFERENCES calls(id) ON DELETE CASCADE,
    type          TEXT NOT NULL,
    idem_key      TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'pending',
    provider_id   TEXT,
    attempts      INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS callbacks (
    id            SERIAL PRIMARY KEY,
    lead_id       INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    scheduled_at  TIMESTAMPTZ NOT NULL,
    timezone      TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    status        TEXT NOT NULL DEFAULT 'pending',
    attempts      INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
