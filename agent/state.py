# agent/state.py
# LeasingAgentState — single source of truth for the entire workflow
# Every node reads from this and writes back to it
# Phase 2: thread_id added for audit trail linkage

from typing import TypedDict, Optional, List, Literal


class LeasingAgentState(TypedDict):

    # ── Workflow Identity ─────────────────────────────────────────────────────
    thread_id: Optional[str]            # LangGraph thread identifier
                                        # Set by the workflow router on POST /workflows/start
                                        # Used by audit_events to link all events for a workflow

    # ── Inquiry ───────────────────────────────────────────────────────────────
    inquiry_id: str
    inquiry: dict                       # Full inquiry object from inquiries table

    # ── Intake & Classification ───────────────────────────────────────────────
    classification: Optional[dict]      # Agent output from node_intake
                                        # keys: tenant_type, category, size_min,
                                        # size_max, preferred_mall, priority,
                                        # financial_profile, special_requirements

    # ── Lead Scoring (Stage 2 — Tenant Qualification) ─────────────────────────
    lead_score_result: Optional[dict]   # Output from calculate_lead_score()
                                        # keys: lead_score, lead_grade,
                                        # signals_positive, signals_negative, reasoning

    # ── Unit Matching ─────────────────────────────────────────────────────────
    matched_units: List[dict]           # Units returned and ranked by node_unit_match
    selected_unit: Optional[dict]       # Unit confirmed by human at Gate 1
    weak_match_warning: Optional[str]   # Populated if top unit match_score < 0.50

    # ── Heads of Terms ────────────────────────────────────────────────────────
    hot_draft: Optional[dict]           # Agent-generated HoT from node_hot_draft
    hot_approved: Optional[dict]        # Human-edited and approved HoT at Gate 1

    # ── Documents ─────────────────────────────────────────────────────────────
    document_checklist: List[str]       # List of required documents for this tenant
    tenant_message: Optional[str]       # Covering message sent to tenant
    documents_received: Optional[dict]  # Verification scenario from documents table
    document_issues: List[str]          # Flags raised by node_doc_verify
    documents_approved: bool            # LCM approval decision at Gate 2

    # ── Lease ─────────────────────────────────────────────────────────────────
    lease_draft: Optional[dict]         # Generated lease JSON from node_lease_gen
    consistency_check: Optional[dict]   # Result of consistency check
    lease_approved: bool                # Senior manager approval at Gate 3

    # ── EJARI ─────────────────────────────────────────────────────────────────
    ejari_filed: bool
    ejari_certificate: Optional[dict]
    deal_closed: bool

    # ── Agent Reasoning Log ───────────────────────────────────────────────────
    reasoning_log: List[dict]           # Each step appends:
                                        # { step, reasoning, output, timestamp, fallback_used }

    # ── Flow Control ──────────────────────────────────────────────────────────
    current_step: str
    gate_decision: Optional[Literal["approve", "edit", "reject"]]
    gate_edits: Optional[dict]
    rejection_reason: Optional[str]
    errors: List[str]


def get_initial_state(inquiry: dict, thread_id: str = None) -> LeasingAgentState:
    """
    Returns a clean initial state for a given inquiry.
    Call this when starting a new leasing workflow.

    thread_id is passed in from the workflow router (POST /workflows/start)
    so audit events can be linked to the correct LangGraph thread.
    """
    return LeasingAgentState(
        # Workflow identity
        thread_id=thread_id,

        # Inquiry
        inquiry_id=inquiry["inquiry_id"],
        inquiry=inquiry,

        # Intake
        classification=None,

        # Lead scoring
        lead_score_result=None,

        # Unit matching
        matched_units=[],
        selected_unit=None,
        weak_match_warning=None,

        # HoT
        hot_draft=None,
        hot_approved=None,

        # Documents
        document_checklist=[],
        tenant_message=None,
        documents_received=None,
        document_issues=[],
        documents_approved=False,

        # Lease
        lease_draft=None,
        consistency_check=None,
        lease_approved=False,

        # EJARI
        ejari_filed=False,
        ejari_certificate=None,
        deal_closed=False,

        # Reasoning
        reasoning_log=[],

        # Flow control
        current_step="node_intake",
        gate_decision=None,
        gate_edits=None,
        rejection_reason=None,
        errors=[],
    )