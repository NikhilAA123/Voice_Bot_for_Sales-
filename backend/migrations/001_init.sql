-- 001_init.sql – run only once; later migrations can be added similarly.
CREATE TABLE IF NOT EXISTS leads (
    id            SERIAL PRIMARY KEY,
    phone_number  TEXT NOT NULL,
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
    speaker       TEXT NOT NULL,
    content       TEXT NOT NULL,
    seq_number    INTEGER NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lead_decisions (
    id            SERIAL PRIMARY KEY,
    call_id       INTEGER REFERENCES calls(id) ON DELETE CASCADE,
    intent        TEXT NOT NULL,
    confidence    NUMERIC(5,2),
    raw_json      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS actions (
    id            SERIAL PRIMARY KEY,
    call_id       INTEGER REFERENCES calls(id) ON DELETE CASCADE,
    type          TEXT NOT NULL,
    idem_key      TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'pending',
    attempts      INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS callbacks (
    id            SERIAL PRIMARY KEY,
    lead_id       INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    scheduled_for TIMESTAMPTZ NOT NULL,
    timezone      TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    status        TEXT NOT NULL DEFAULT 'pending',
    attempts      INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
