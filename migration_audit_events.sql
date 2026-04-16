-- ============================================================================
-- migration_audit_events.sql
-- AI Leasing Agent · MAF Properties · ReKnew · April 2026
--
-- Minimal migration — creates only the audit_events table and its indexes.
-- Run this against your existing database after db_schema_sql.sql.
--
-- Safe to re-run: uses IF NOT EXISTS throughout.
-- ============================================================================


-- Enable UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ── audit_events ─────────────────────────────────────────────────────────────
-- Immutable append-only event log.
-- Every agent action, gate decision, LLM call, fallback trigger,
-- EJARI filing, and error is written here permanently.
-- Never UPDATE or DELETE rows in this table.

CREATE TABLE IF NOT EXISTS audit_events (
    event_id    UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  VARCHAR(50)     NOT NULL,
        -- node_completed | gate_reached | gate_approved | gate_rejected
        -- gate_edited | llm_called | llm_failed | fallback_triggered
        -- ejari_filed | error_occurred
    thread_id   VARCHAR(100),               -- LangGraph thread identifier
    inquiry_id  VARCHAR(30)
                    REFERENCES inquiries(inquiry_id),
    actor_type  VARCHAR(20)     NOT NULL    -- "agent" | "human" | "system"
                    DEFAULT 'agent',
    actor_id    VARCHAR(50),                -- node name, user id, or "system"
    node_name   VARCHAR(50),                -- which agent node triggered this
    gate_name   VARCHAR(20),                -- gate_1 | gate_2 | gate_3 | null
    payload     JSONB,                      -- full event context
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ── Indexes ───────────────────────────────────────────────────────────────────

-- Primary query pattern — all events for a specific inquiry (timeline view)
CREATE INDEX IF NOT EXISTS idx_audit_inquiry_time
    ON audit_events(inquiry_id, created_at);

-- All events for a specific LangGraph thread (debugging)
CREATE INDEX IF NOT EXISTS idx_audit_thread_time
    ON audit_events(thread_id, created_at);

-- Filter by event type (e.g. all fallback_triggered events across all deals)
CREATE INDEX IF NOT EXISTS idx_audit_event_type
    ON audit_events(event_type, created_at);


-- ============================================================================
-- DONE
-- Verify with:
--   SELECT table_name FROM information_schema.tables
--   WHERE table_name = 'audit_events';
-- ============================================================================
