-- Cache table for storing API responses with TTL
CREATE TABLE IF NOT EXISTS cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,          -- Format: "source:entity_type:entity_id"
    source TEXT NOT NULL,                     -- "brevo_crm", "brevo_notes", "brevo_tasks", "linkedin", "web"
    entity_type TEXT NOT NULL,                -- "contact", "deal", "company"
    entity_id TEXT NOT NULL,
    data_json TEXT NOT NULL,                  -- Serialized JSON data
    data_hash TEXT NOT NULL,                  -- SHA256 hash for change detection
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_minutes INTEGER NOT NULL,             -- Time-to-live in minutes
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(cache_key)
);

CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_entity ON cache(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_expiry ON cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_source ON cache(source);

-- Metadata table for tracking enrichment runs
CREATE TABLE IF NOT EXISTS enrichment_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sources_used TEXT NOT NULL,               -- JSON array of sources used
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    api_calls_made INTEGER DEFAULT 0,
    total_duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_enrichment_entity ON enrichment_runs(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_enrichment_timestamp ON enrichment_runs(run_timestamp);
