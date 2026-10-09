-- IndexPulse database schema
-- Safe to run repeatedly: the backend runs this on startup to create any missing tables.

CREATE TABLE IF NOT EXISTS users (
    email           VARCHAR(255) PRIMARY KEY,
    hashed_password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
    id           SERIAL PRIMARY KEY,
    label        VARCHAR(255),
    category     VARCHAR(100) DEFAULT 'Uncategorized',
    query_params JSONB,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS results (
    id           SERIAL PRIMARY KEY,
    watchlist_id INTEGER REFERENCES watchlists(id),
    title        TEXT,
    link         TEXT UNIQUE,
    snippet      TEXT,
    source       VARCHAR(255),
    date_found   VARCHAR(100),
    is_new       BOOLEAN DEFAULT TRUE,
    is_read      BOOLEAN NOT NULL DEFAULT FALSE,
    fetched_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS digests (
    id           SERIAL PRIMARY KEY,
    watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    headline     TEXT NOT NULL,
    narrative    TEXT NOT NULL,
    severity     TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    alert_ids    JSONB,
    generated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dossiers (
    watchlist_id INTEGER PRIMARY KEY REFERENCES watchlists(id) ON DELETE CASCADE,
    summary      TEXT NOT NULL,
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);
