# ============================================================================
# api/routers/workflows.py — Workflows router
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Endpoints:
#   POST /workflows/start                    — start leasing workflow for an inquiry
#   GET  /workflows/{thread_id}/state        — get current agent state (polled by frontend)
#   POST /workflows/{thread_id}/resume       — submit gate decision (approve/reject)
#   GET  /workflows/{thread_id}/history      — full audit trail for this workflow
#   GET  /workflows/active                   — list all running or paused workflows
#
# Wired directly to agent/graph.py → leasing_graph (MemorySaver checkpointer)
# Gates are interrupt_before: gate_1, gate_2, gate_3
# ============================================================================

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.graph import leasing_graph
from agent.state import get_initial_state
from db import get_conn, dict_cursor

router = APIRouter()


# ── In-memory workflow registry ───────────────────────────────────────────────
# Maps thread_id → inquiry_id so we can look up workflows by inquiry
# In production this would be persisted to DB
_workflow_registry: dict[str, str] = {}


# ── Pydantic models ───────────────────────────────────────────────────────────

class WorkflowStartRequest(BaseModel):
    inquiry_id: str


class GateResumeRequest(BaseModel):
    decision:str # "approve" | "reject"
    gate:str   # "gate_1" | "gate_2" | "gate_3"
    agent_note: Optional[str] = None  # optional note from leasing exec
    hot_edits: Optional[dict] = None # Gate 1 — human-edited HoT fields
                                            # e.g. rent, fit_out_months, duration
    selected_unit_id: Optional[str] = None  # Gate 1 — unit selected by leasing exec


# ── Helper — get inquiry from DB ──────────────────────────────────────────────

def _get_inquiry(inquiry_id: str) -> dict:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM inquiries WHERE inquiry_id = %s", (inquiry_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")
    return row


def _update_inquiry_status(inquiry_id: str, status: str):
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "UPDATE inquiries SET status = %s WHERE inquiry_id = %s",
            (status, inquiry_id)
        )


# ── Helper — format state for frontend ───────────────────────────────────────

def _format_state(thread_id: str) -> dict:
    """
    Pulls current graph state from MemorySaver checkpointer.
    Returns a clean dict the frontend can render.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = leasing_graph.get_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Workflow {thread_id} not found")

    state_values = snapshot.values if snapshot.values else {}

    # next is a tuple of node names the graph will run next
    # empty tuple means graph has finished
    next_nodes = list(snapshot.next) if snapshot.next else []

    # Determine if paused at a gate
    paused_at = None
    for node in next_nodes:
        if node in ("gate_1", "gate_2", "gate_3"):
            paused_at = node
            break

    # Map gate name to human-readable label
    gate_labels = {
        "gate_1": "Gate 1 — Leasing Executive Approval",
        "gate_2": "Gate 2 — LCM Document Review",
        "gate_3": "Gate 3 — Senior Manager Final Approval",
    }

    return {
        "thread_id":  thread_id,
        "inquiry_id": _workflow_registry.get(thread_id),
        "status":     "paused" if paused_at else ("completed" if not next_nodes else "running"),
        "paused_at":  paused_at,
        "gate_label": gate_labels.get(paused_at) if paused_at else None,
        "next_nodes": next_nodes,
        "state":      state_values,
    }


# ── POST /workflows/start ─────────────────────────────────────────────────────

@router.post("/start", status_code=201)
def start_workflow(body: WorkflowStartRequest):
    """
    Start a leasing workflow for an inquiry.
    - Fetches inquiry from DB
    - Generates a unique thread_id
    - Invokes leasing_graph — runs until it hits gate_1 and pauses
    - Returns thread_id for frontend to poll
    """
    inquiry = _get_inquiry(body.inquiry_id)

    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    # Register thread → inquiry mapping
    _workflow_registry[thread_id] = body.inquiry_id

    # Update inquiry status to in_progress
    _update_inquiry_status(body.inquiry_id, "in_progress")

    # Convert DB row (RealDictRow) → plain dict, then build full state via state.py
    inquiry_dict  = dict(inquiry)
    initial_state = get_initial_state(inquiry_dict)

    # Invoke graph — runs node_intake → node_unit_match → node_hot_draft → pauses at gate_1
    try:
        leasing_graph.invoke(initial_state, config)
    except Exception as e:
        _workflow_registry.pop(thread_id, None)
        raise HTTPException(status_code=500, detail=f"Graph failed to start: {str(e)}")

    # Update inquiry status to pending_gate_1
    _update_inquiry_status(body.inquiry_id, "pending_gate_1")

    return {
        "thread_id":  thread_id,
        "inquiry_id": body.inquiry_id,
        "status":     "paused",
        "paused_at":  "gate_1",
        "message":    "Workflow started. Paused at Gate 1 — awaiting Leasing Executive approval.",
    }


# ── GET /workflows/active ─────────────────────────────────────────────────────
# IMPORTANT: This route MUST be defined before /{thread_id} routes.
# FastAPI matches routes top-down — if /{thread_id}/state comes first,
# "active" gets treated as a thread_id and this endpoint never runs.

@router.get("/active")
def get_active_workflows():
    """
    List all currently running or paused workflows.
    Reads from in-memory registry + queries each thread's state.
    """
    active = []

    for thread_id, inquiry_id in _workflow_registry.items():
        try:
            config   = {"configurable": {"thread_id": thread_id}}
            snapshot = leasing_graph.get_state(config)
            next_nodes = list(snapshot.next) if snapshot.next else []

            # Skip completed workflows
            if not next_nodes:
                continue

            paused_at = next(
                (n for n in next_nodes if n in ("gate_1", "gate_2", "gate_3")),
                None
            )

            active.append({
                "thread_id":  thread_id,
                "inquiry_id": inquiry_id,
                "status":     "paused" if paused_at else "running",
                "paused_at":  paused_at,
                "next_nodes": next_nodes,
            })
        except Exception:
            continue

    return {"count": len(active), "workflows": active}


# ── GET /workflows/{thread_id}/state ─────────────────────────────────────────

@router.get("/{thread_id}/state")
def get_workflow_state(thread_id: str):
    """
    Get current agent state for a workflow.
    Frontend polls this endpoint to know:
    - Is it still running?
    - Is it paused at a gate? Which one?
    - What did the agent produce? (matched units, HoT draft, doc status, etc.)
    - Is it completed?
    """
    return _format_state(thread_id)


# ── POST /workflows/{thread_id}/resume ───────────────────────────────────────

@router.post("/{thread_id}/resume")
def resume_workflow(thread_id: str, body: GateResumeRequest):
    """
    Submit a gate decision and resume the workflow.
    - decision: "approve" → graph moves forward to next step
    - decision: "reject"  → graph loops back to previous step
    - agent_note: optional note saved to inquiry
    """
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")

    if body.gate not in ("gate_1", "gate_2", "gate_3"):
        raise HTTPException(status_code=400, detail="gate must be gate_1, gate_2, or gate_3")

    config = {"configurable": {"thread_id": thread_id}}

    # Verify workflow exists and is paused at the correct gate
    try:
        snapshot = leasing_graph.get_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Workflow {thread_id} not found")

    next_nodes = list(snapshot.next) if snapshot.next else []
    if body.gate not in next_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow is not paused at {body.gate}. Currently at: {next_nodes}"
        )

    # Map decision to gate_decision value the routing functions expect
    gate_decision = "reject" if body.decision == "reject" else "approve"

    # Update state with gate decision + optional note
    update = {"gate_decision": gate_decision}
    if body.agent_note:
        update["agent_note"] = body.agent_note

    # Gate 1 — pass back HoT edits and selected unit if provided
    if body.gate == "gate_1":
        if body.hot_edits:
            update["hot_approved"] = body.hot_edits
        if body.selected_unit_id:
            # Fetch full unit from DB and pass into state
            from tools.yardi import get_unit_by_id
            unit = get_unit_by_id(body.selected_unit_id)
            if unit:
                update["selected_unit"] = unit
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unit {body.selected_unit_id} not found"
                )

    leasing_graph.update_state(config, update)

    # Save note to DB if provided
    if body.agent_note:
        inquiry_id = _workflow_registry.get(thread_id)
        if inquiry_id:
            with get_conn() as conn:
                cur = dict_cursor(conn)
                cur.execute(
                    "UPDATE inquiries SET agent_note = %s WHERE inquiry_id = %s",
                    (body.agent_note, inquiry_id)
                )

    # Resume graph — runs until next gate or END
    try:
        leasing_graph.invoke(None, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph failed to resume: {str(e)}")

    # Get updated state and return
    updated = _format_state(thread_id)

    # Update inquiry status based on where the graph is now
    inquiry_id = _workflow_registry.get(thread_id)
    if inquiry_id:
        status_map = {
            "gate_1":  "pending_gate_1",
            "gate_2":  "blocked_documents",
            "gate_3":  "unit_matched",
            None:      "completed",
        }
        new_status = status_map.get(updated["paused_at"], "in_progress")
        _update_inquiry_status(inquiry_id, new_status)

    return {
        "thread_id": thread_id,
        "decision":  body.decision,
        "gate":      body.gate,
        "workflow":  updated,
    }


# ── GET /workflows/{thread_id}/history ───────────────────────────────────────

@router.get("/{thread_id}/history")
def get_workflow_history(thread_id: str):
    """
    Full audit trail for a workflow.
    Returns every checkpoint saved by MemorySaver —
    each node execution, gate decision, and state change.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        history = list(leasing_graph.get_state_history(config))
    except Exception:
        raise HTTPException(status_code=404, detail=f"Workflow {thread_id} not found")

    audit_trail = []
    for checkpoint in reversed(history):   # oldest first
        audit_trail.append({
            "step":       checkpoint.metadata.get("step"),
            "node":       checkpoint.metadata.get("source"),
            "next_nodes": list(checkpoint.next) if checkpoint.next else [],
            "state":      checkpoint.values,
            "timestamp":  str(checkpoint.metadata.get("created_at", "")),
        })

    return {
        "thread_id":   thread_id,
        "inquiry_id":  _workflow_registry.get(thread_id),
        "total_steps": len(audit_trail),
        "history":     audit_trail,
    }