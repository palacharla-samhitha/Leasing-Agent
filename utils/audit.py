# utils/audit.py
# ============================================================================
# Audit Trail — single write point for the entire leasing agent codebase
# MAF Properties · ReKnew · Phase 2 · April 2026
#
# ONE function: write_audit_event()
# Called from three places:
#   1. agent/nodes.py  — after every node, LLM call, fallback, and error
#   2. api/routers/workflows.py — after every gate decision
#   3. tools/ejari.py  — after every EJARI filing attempt
#
# Design principles:
#   - Fire-and-forget safe: all DB errors are caught and logged to stderr
#     so a failed audit write NEVER crashes the agent workflow
#   - Actor defaults: agent actions use node_name, human actions use
#     actor_id passed in, system events use "system"
#   - append-only — never UPDATE or DELETE from audit_events
# ============================================================================

import json
import traceback
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from db import get_conn, dict_cursor


# ── JSON serializer ───────────────────────────────────────────────────────────

def _safe_json(obj: Any) -> Any:
    """Recursively make an object JSON-safe for the payload JSONB column."""
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json(i) for i in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


# ── Core audit writer ─────────────────────────────────────────────────────────

def write_audit_event(
    event_type: str,
    *,
    thread_id:  Optional[str]  = None,
    inquiry_id: Optional[str]  = None,
    actor_type: str            = "agent",
    actor_id:   Optional[str]  = None,
    node_name:  Optional[str]  = None,
    gate_name:  Optional[str]  = None,
    payload:    Optional[dict] = None,
) -> Optional[str]:
    """
    Write one immutable row to audit_events.
    Returns the new event_id (UUID string) on success, None on failure.
    Never raises — a failed audit write must not crash the workflow.

    actor_id defaults:
      - agent actions  → node_name
      - human actions  → caller passes the user identifier
      - system events  → "system"
    """
    resolved_actor_id = actor_id or node_name or "system"
    safe_payload      = _safe_json(payload) if payload else None

    sql = """
        INSERT INTO audit_events
            (event_type, thread_id, inquiry_id,
             actor_type, actor_id, node_name, gate_name, payload)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING event_id::text
    """

    try:
        with get_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute(sql, (
                event_type,
                thread_id,
                inquiry_id,
                actor_type,
                resolved_actor_id,
                node_name,
                gate_name,
                json.dumps(safe_payload) if safe_payload is not None else None,
            ))
            row = cur.fetchone()
            return row["event_id"] if row else None

    except Exception:
        # Never crash the workflow — print to stderr and move on
        print(
            f"[AUDIT ERROR] Failed to write '{event_type}' "
            f"inquiry={inquiry_id} thread={thread_id}\n"
            f"{traceback.format_exc()}",
            flush=True,
        )
        return None


# ── Convenience wrappers ──────────────────────────────────────────────────────
# These reduce boilerplate in nodes.py — call these instead of write_audit_event
# directly wherever possible.

def audit_node_completed(
    node_name:  str,
    state:      dict,
    output:     dict,
    latency_ms: Optional[int] = None,
) -> None:
    """Call after every node completes successfully."""
    write_audit_event(
        "node_completed",
        thread_id=state.get("thread_id"),
        inquiry_id=state.get("inquiry_id"),
        node_name=node_name,
        payload={
            "output":     _safe_json(output),
            "latency_ms": latency_ms,
        },
    )


def audit_llm_call(
    node_name:         str,
    state:             dict,
    model:             str,
    success:           bool,
    latency_ms:        Optional[int] = None,
    prompt_tokens:     Optional[int] = None,
    completion_tokens: Optional[int] = None,
    error:             Optional[str] = None,
) -> None:
    """Call after every LLM call — success or failure."""
    write_audit_event(
        "llm_called" if success else "llm_failed",
        thread_id=state.get("thread_id"),
        inquiry_id=state.get("inquiry_id"),
        node_name=node_name,
        payload={
            "model":             model,
            "success":           success,
            "latency_ms":        latency_ms,
            "prompt_tokens":     prompt_tokens,
            "completion_tokens": completion_tokens,
            "error":             error,
        },
    )


def audit_gate_event(
    event_type: str,
    gate_name:  str,
    state:      dict,
    actor_id:   str  = "system",
    payload:    dict = None,
) -> None:
    """Call when a gate decision is made by a human."""
    write_audit_event(
        event_type,
        thread_id=state.get("thread_id"),
        inquiry_id=state.get("inquiry_id"),
        actor_type="human",
        actor_id=actor_id,
        gate_name=gate_name,
        payload=payload,
    )


def audit_ejari_filed(
    state:   dict,
    success: bool,
    payload: dict,
) -> None:
    """Call after every EJARI filing attempt."""
    write_audit_event(
        "ejari_filed",
        thread_id=state.get("thread_id"),
        inquiry_id=state.get("inquiry_id"),
        node_name="node_ejari",
        actor_type="agent",
        payload={**_safe_json(payload), "success": success},
    )


def audit_error(
    node_name: str,
    state:     dict,
    error:     Exception,
    context:   Optional[dict] = None,
) -> None:
    """Call whenever an error occurs inside a node."""
    write_audit_event(
        "error_occurred",
        thread_id=state.get("thread_id"),
        inquiry_id=state.get("inquiry_id"),
        node_name=node_name,
        payload={
            "error":     str(error),
            "traceback": traceback.format_exc(),
            "context":   _safe_json(context) if context else None,
        },
    )