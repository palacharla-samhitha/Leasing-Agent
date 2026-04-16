# ============================================================================
# api/routers/audit.py — Audit router
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Endpoints:
#   GET  /audit/events                      — paginated event log with filters (summary)
#   GET  /audit/events/{event_id}           — single event with full payload
#   GET  /audit/inquiry/{inquiry_id}        — all events for an inquiry (summary)
#   GET  /audit/thread/{thread_id}          — all events for a workflow thread (summary)
#
# All DB access via get_conn() + dict_cursor() from db.py
# audit_events is append-only — no POST, PATCH, or DELETE endpoints here
# ============================================================================

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import get_conn, dict_cursor

router = APIRouter()


# ── Shared column list ────────────────────────────────────────────────────────
# Used by all summary queries — excludes the payload JSONB column
# payload is only returned by GET /audit/events/{event_id}

SUMMARY_COLS = """
    event_id::text,
    event_type,
    thread_id,
    inquiry_id,
    actor_type,
    actor_id,
    node_name,
    gate_name,
    created_at
"""


# ── GET /audit/events ─────────────────────────────────────────────────────────

@router.get("/events")
def list_audit_events(
    event_type: Optional[str] = Query(None, description="Filter by event type e.g. node_completed, gate_approved, llm_called"),
    inquiry_id: Optional[str] = Query(None, description="Filter by inquiry_id e.g. INQ-2026-0041"),
    date_from:  Optional[str] = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    date_to:    Optional[str] = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    limit:      int           = Query(50,   description="Number of events to return (default 50)", ge=1, le=500),
    offset:     int           = Query(0,    description="Number of events to skip (default 0)",    ge=0),
):
    """
    Paginated audit event log with optional filters.
    Returns summary rows only — no payload field.
    Use GET /audit/events/{event_id} to retrieve the full payload for a single event.

    Results are ordered newest first so the most recent activity appears at the top.

    Pagination example:
        GET /audit/events?limit=50&offset=0    → first page
        GET /audit/events?limit=50&offset=50   → second page
    """
    filters = []
    params  = []

    if event_type:
        filters.append("event_type = %s")
        params.append(event_type)
    if inquiry_id:
        filters.append("inquiry_id = %s")
        params.append(inquiry_id)
    if date_from:
        filters.append("created_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("created_at <= %s")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    # Total count query — same filters, no limit/offset
    count_query = f"SELECT COUNT(*) AS total FROM audit_events {where}"

    # Data query — summary cols only, paginated
    data_query = f"""
        SELECT {SUMMARY_COLS}
        FROM audit_events
        {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """

    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Get total count for pagination metadata
        cur.execute(count_query, params)
        total = cur.fetchone()["total"]

        # Get page of results
        cur.execute(data_query, params + [limit, offset])
        rows = cur.fetchall()

    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "count":  len(rows),
        "events": rows,
    }


# ── GET /audit/events/{event_id} ──────────────────────────────────────────────

@router.get("/events/{event_id}")
def get_audit_event(event_id: str):
    """
    Get a single audit event including the full payload JSONB.
    Use this to inspect the full node output, gate edits, LLM call details,
    or error traceback for any specific event.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT
                event_id::text,
                event_type,
                thread_id,
                inquiry_id,
                actor_type,
                actor_id,
                node_name,
                gate_name,
                payload,
                created_at
            FROM audit_events
            WHERE event_id = %s::uuid
        """, (event_id,))
        event = cur.fetchone()

    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Audit event {event_id} not found"
        )

    return {"event": event}


# ── GET /audit/inquiry/{inquiry_id} ───────────────────────────────────────────

@router.get("/inquiry/{inquiry_id}")
def get_inquiry_audit_trail(inquiry_id: str):
    """
    Full audit trail for a specific inquiry.
    Returns all events from first intake to deal close, ordered oldest first
    so the timeline reads chronologically top to bottom.

    This is what MAF's compliance and leasing operations teams use to
    review any deal — every agent action, gate decision, LLM call,
    and error in sequence.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Check inquiry exists
        cur.execute(
            "SELECT inquiry_id FROM inquiries WHERE inquiry_id = %s",
            (inquiry_id,)
        )
        if not cur.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Inquiry {inquiry_id} not found"
            )

        # All events for this inquiry — oldest first for timeline view
        cur.execute(f"""
            SELECT {SUMMARY_COLS}
            FROM audit_events
            WHERE inquiry_id = %s
            ORDER BY created_at ASC
        """, (inquiry_id,))
        events = cur.fetchall()

    # Group events by type for quick summary
    type_counts = {}
    for e in events:
        t = e["event_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "inquiry_id":   inquiry_id,
        "total_events": len(events),
        "event_types":  type_counts,
        "events":       events,
    }


# ── GET /audit/thread/{thread_id} ─────────────────────────────────────────────

@router.get("/thread/{thread_id}")
def get_thread_audit_trail(thread_id: str):
    """
    Full audit trail for a specific workflow thread.
    Returns all events tied to this LangGraph thread_id, ordered oldest first.

    Useful for debugging a specific workflow run — see exactly which nodes
    ran, how long each LLM call took, which gate decisions were made,
    and any errors that occurred.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Check thread exists in audit_events
        cur.execute(
            "SELECT COUNT(*) AS total FROM audit_events WHERE thread_id = %s",
            (thread_id,)
        )
        result = cur.fetchone()
        if result["total"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No audit events found for thread {thread_id}"
            )

        # All events for this thread — oldest first
        cur.execute(f"""
            SELECT {SUMMARY_COLS}
            FROM audit_events
            WHERE thread_id = %s
            ORDER BY created_at ASC
        """, (thread_id,))
        events = cur.fetchall()

    # Pull inquiry_id from first event that has one
    inquiry_id = next(
        (e["inquiry_id"] for e in events if e["inquiry_id"]),
        None
    )

    # Group events by node for quick debugging summary
    node_counts = {}
    for e in events:
        node = e["node_name"] or "system"
        node_counts[node] = node_counts.get(node, 0) + 1

    return {
        "thread_id":    thread_id,
        "inquiry_id":   inquiry_id,
        "total_events": len(events),
        "nodes_hit":    node_counts,
        "events":       events,
    }