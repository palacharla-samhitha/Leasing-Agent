# agent/state.py
# LeasingAgentState — single source of truth for the entire workflow
# Every node reads from this and writes back to it

from typing import TypedDict, Optional, List, Literal


class LeasingAgentState(TypedDict):

    # ── Inquiry ───────────────────────────────────────────────────────────────
    inquiry_id: str
    inquiry: dict                       # Full inquiry object from inquiries.json

    # ── Intake & Classification ───────────────────────────────────────────────
    classification: Optional[dict]      # Agent output from node_intake
                                        # keys: tenant_type, category, size_min,
                                        # size_max, preferred_mall, priority,
                                        # financial_profile, special_requirements

    # ── Unit Matching ─────────────────────────────────────────────────────────
    matched_units: List[dict]           # Units returned and ranked by node_unit_match
    selected_unit: Optional[dict]       # Unit confirmed by human at Gate 1

    # ── Heads of Terms ────────────────────────────────────────────────────────
    hot_draft: Optional[dict]           # Agent-generated HoT from node_hot_draft
    hot_approved: Optional[dict]        # Human-edited and approved HoT at Gate 1

    # ── Documents ─────────────────────────────────────────────────────────────
    document_checklist: List[str]       # List of required documents for this tenant
    tenant_message: Optional[str]       # Covering message sent to tenant
    documents_received: Optional[dict]  # Verification scenario loaded from documents.json
    document_issues: List[str]          # Flags raised by node_doc_verify
    documents_approved: bool            # LCM approval decision at Gate 2

    # ── Lease ─────────────────────────────────────────────────────────────────
    lease_draft: Optional[dict]         # Generated lease JSON from node_lease_gen
    consistency_check: Optional[dict]   # Result of consistency check
                                        # keys: status, checks_run, issues_found, detail
    lease_approved: bool                # Senior manager approval at Gate 3

    # ── EJARI ─────────────────────────────────────────────────────────────────
    ejari_filed: bool
    ejari_certificate: Optional[dict]   # Simulated EJARI registration certificate
    deal_closed: bool

    # ── Agent Reasoning Log ───────────────────────────────────────────────────
    reasoning_log: List[dict]           # Each step appends:
                                        # { step, reasoning, output, timestamp }

    # ── Flow Control ──────────────────────────────────────────────────────────
    current_step: str                   # Current node name
    gate_decision: Optional[Literal["approve", "edit", "reject"]]
    gate_edits: Optional[dict]          # Human edits made at any gate
    rejection_reason: Optional[str]     # Populated when gate_decision == "reject"
    errors: List[str]                   # Any errors encountered during execution


def get_initial_state(inquiry: dict) -> LeasingAgentState:
    """
    Returns a clean initial state for a given inquiry.
    Call this when starting a new leasing workflow.
    """
    return LeasingAgentState(
        # Inquiry
        inquiry_id=inquiry["inquiry_id"],
        inquiry=inquiry,

        # Intake
        classification=None,

        # Unit matching
        matched_units=[],
        selected_unit=None,

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