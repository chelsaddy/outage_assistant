-- Telecom Outage Assistant: database schema
-- Loaded automatically by the Postgres container on first start.

CREATE TABLE service_areas (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    region      TEXT NOT NULL                     -- e.g. 'North', 'South', 'Tobago'
);

CREATE TABLE customers (
    id            SERIAL PRIMARY KEY,
    account_no    TEXT NOT NULL UNIQUE,           -- e.g. 'ACC-100001'
    full_name     TEXT NOT NULL,
    phone         TEXT NOT NULL UNIQUE,           -- E.164, e.g. '+18685550101'
    email         TEXT,
    service_type  TEXT NOT NULL CHECK (service_type IN ('fibre', 'dsl', 'mobile', 'fixed_wireless')),
    area_id       INT  NOT NULL REFERENCES service_areas(id),
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE outages (
    id            SERIAL PRIMARY KEY,
    area_id       INT  NOT NULL REFERENCES service_areas(id),
    service_type  TEXT NOT NULL,                  -- which service is affected
    cause         TEXT NOT NULL,                  -- e.g. 'Fibre cut', 'Power failure at node'
    status        TEXT NOT NULL CHECK (status IN ('active', 'resolved')),
    started_at    TIMESTAMPTZ NOT NULL,
    eta           TIMESTAMPTZ,                    -- estimated restore time
    resolved_at   TIMESTAMPTZ
);
CREATE INDEX outages_active_area_idx ON outages (area_id) WHERE status = 'active';

CREATE TABLE conversations (
    id            SERIAL PRIMARY KEY,
    customer_id   INT REFERENCES customers(id),   -- null until the agent identifies the customer
    channel       TEXT NOT NULL DEFAULT 'chat',
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'escalated', 'closed')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tickets (
    id               SERIAL PRIMARY KEY,
    customer_id      INT  NOT NULL REFERENCES customers(id),
    conversation_id  INT  REFERENCES conversations(id),
    category         TEXT NOT NULL,               -- e.g. 'no_service', 'slow_speed', 'escalation'
    priority         TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    summary          TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'closed')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sms_messages (
    id            SERIAL PRIMARY KEY,
    customer_id   INT  REFERENCES customers(id),
    to_phone      TEXT NOT NULL,
    body          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'queued', -- queued | sent | failed | simulated
    provider_sid  TEXT,                           -- Twilio message SID when sent for real
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every step the agent takes, so the dashboard can show the full trace.
CREATE TABLE agent_steps (
    id               SERIAL PRIMARY KEY,
    conversation_id  INT  NOT NULL REFERENCES conversations(id),
    step_no          INT  NOT NULL,
    kind             TEXT NOT NULL CHECK (kind IN ('user_message', 'assistant_message', 'tool_call', 'tool_result', 'escalation')),
    tool_name        TEXT,
    payload          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, step_no)
);
