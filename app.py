# app.py
# Streamlit UI for the AI Leasing Agent
# Three panel layout: left progress | main output | right state viewer

import json
import streamlit as st
from agent.graph import leasing_graph
from agent.state import get_initial_state

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Leasing Agent — MAF Properties",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0a2342 0%, #1a3a5c 100%);
        padding: 1rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: #00c4b4; margin: 0; font-size: 1.4rem; }
    .main-header p  { color: #a0b4c8; margin: 0; font-size: 0.85rem; }

    .step-item {
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.4rem;
        font-size: 0.82rem;
        font-weight: 500;
    }
    .step-complete  { background: #0d3d2e; color: #00c4b4; border-left: 3px solid #00c4b4; }
    .step-active    { background: #1a3a5c; color: #ffffff; border-left: 3px solid #4a9eff; }
    .step-gate      { background: #2d1f00; color: #ffaa00; border-left: 3px solid #ffaa00; }
    .step-pending   { background: #1a1a2e; color: #555577; border-left: 3px solid #333355; }

    .reasoning-box {
        background: #f8f9fa;
        border-left: 3px solid #6c757d;
        padding: 1rem;
        border-radius: 4px;
        font-style: italic;
        font-size: 0.88rem;
        color: #444;
        margin-bottom: 1rem;
    }
    .output-box {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .gate-box {
        background: #fff8e1;
        border: 2px solid #ffaa00;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .status-pass    { color: #00c4b4; font-weight: bold; }
    .status-warning { color: #ffaa00; font-weight: bold; }
    .status-fail    { color: #ff4444; font-weight: bold; }
    .deal-closed    { background: #0d3d2e; color: #00c4b4; padding: 1.5rem;
                      border-radius: 8px; text-align: center; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "graph_state": None,
        "thread_id": "leasing-demo-001",
        "running": False,
        "waiting_at_gate": None,   # "gate_1" | "gate_2" | "gate_3" | None
        "selected_inquiry": None,
        "config": {"configurable": {"thread_id": "leasing-demo-001"}},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── Load inquiries ────────────────────────────────────────────────────────────
@st.cache_data
def load_inquiries():
    with open("data/inquiries.json", "r") as f:
        return json.load(f)

inquiries = load_inquiries()
inquiry_options = {i["brand_name"]: i for i in inquiries}


# ── Step definitions ──────────────────────────────────────────────────────────
STEPS = [
    ("node_intake",     "1. Inquiry Intake",         "agent"),
    ("node_unit_match", "2. Unit Matching",           "agent"),
    ("node_hot_draft",  "3. Heads of Terms Draft",   "agent"),
    ("gate_1",          "⚑ Gate 1 — Exec Review",    "gate"),
    ("node_doc_request","4. Document Request",        "agent"),
    ("node_doc_verify", "4b. Document Verification", "agent"),
    ("gate_2",          "⚑ Gate 2 — LCM Review",     "gate"),
    ("node_lease_gen",  "5. Lease Generation",        "agent"),
    ("gate_3",          "⚑ Gate 3 — Final Approval", "gate"),
    ("node_ejari",      "6. EJARI Filing",            "agent"),
    ("complete",        "✓ Deal Closed",              "complete"),
]

STEP_ORDER = [s[0] for s in STEPS]


def get_step_class(step_key: str, current_step: str) -> str:
    if current_step == "complete":
        return "step-complete"
    if step_key == current_step:
        return "step-gate" if "gate" in step_key else "step-active"
    try:
        current_idx = STEP_ORDER.index(current_step)
        step_idx    = STEP_ORDER.index(step_key)
        if step_idx < current_idx:
            return "step-complete"
    except ValueError:
        pass
    return "step-gate" if "gate" in step_key else "step-pending"


# ── Graph runner ──────────────────────────────────────────────────────────────
def run_graph_until_gate(initial_state=None):
    """
    Runs the graph from start or resumes from last interrupt.
    Stops at next gate or END.
    """
    cfg = st.session_state["config"]

    if initial_state:
        # Fresh start
        for _ in leasing_graph.stream(initial_state, cfg):
            pass
    else:
        # Resume after human gate input
        for _ in leasing_graph.stream(None, cfg):
            pass

    # Get latest state
    snapshot = leasing_graph.get_state(cfg)
    st.session_state["graph_state"] = snapshot.values

    # Check if paused at a gate
    next_nodes = snapshot.next
    if next_nodes and any("gate" in n for n in next_nodes):
        st.session_state["waiting_at_gate"] = next_nodes[0]
    else:
        st.session_state["waiting_at_gate"] = None


def resume_after_gate(gate_decision: str, gate_edits: dict = None, rejection_reason: str = None):
    """Updates state with human decision then resumes the graph."""
    cfg = st.session_state["config"]
    updates = {
        "gate_decision": gate_decision,
        "gate_edits": gate_edits or {},
        "rejection_reason": rejection_reason or "",
    }
    # Apply human edits to approved fields
    if gate_decision in ("approve", "edit") and gate_edits:
        if st.session_state["waiting_at_gate"] == "gate_1":
            updates["hot_approved"] = gate_edits.get("hot_approved",
                                      st.session_state["graph_state"].get("hot_draft"))
            updates["selected_unit"] = gate_edits.get("selected_unit",
                                       st.session_state["graph_state"]["matched_units"][0]
                                       if st.session_state["graph_state"]["matched_units"] else None)
        elif st.session_state["waiting_at_gate"] == "gate_2":
            updates["documents_approved"] = True
        elif st.session_state["waiting_at_gate"] == "gate_3":
            updates["lease_approved"] = True

    leasing_graph.update_state(cfg, updates)
    run_graph_until_gate()


# ── UI helpers ────────────────────────────────────────────────────────────────
def render_reasoning(reasoning: str):
    if reasoning:
        st.markdown(f'<div class="reasoning-box">💭 {reasoning}</div>', unsafe_allow_html=True)


def render_json_output(data: dict, title: str = ""):
    if title:
        st.markdown(f"**{title}**")
    st.json(data)


def render_step_log(state: dict, step_key: str):
    """Find and render the reasoning log entry for a given step."""
    for entry in state.get("reasoning_log", []):
        if entry["step"] == step_key:
            render_reasoning(entry["reasoning"])
            render_json_output(entry["output"])
            return


# ── Gate 1 UI ─────────────────────────────────────────────────────────────────
def render_gate_1(state: dict):
    st.markdown('<div class="gate-box">', unsafe_allow_html=True)
    st.markdown("### ⚑ Gate 1 — Leasing Executive Review")
    st.markdown("Review the matched units and Heads of Terms. Edit any fields before approving.")

    matched = state.get("matched_units", [])
    hot = state.get("hot_draft", {})

    # Unit selection
    st.markdown("#### Matched Units")
    unit_ids = [u.get("unit_id", "") for u in matched]
    if not unit_ids:
        st.warning("No units matched. Reject to loop back.")
        selected_uid = None
    else:
        cols = st.columns(len(unit_ids))
        for i, (col, unit) in enumerate(zip(cols, matched)):
            with col:
                st.markdown(f"**{unit.get('unit_id')}**")
                st.caption(f"{unit.get('mall')} · {unit.get('floor')}")
                st.caption(f"{unit.get('size_sqm')} sqm · AED {unit.get('base_rent_aed_sqm'):,}/sqm")
                score = unit.get('match_score', 0)
                st.progress(score, text=f"Match: {score:.0%}")
                st.caption(unit.get("rationale", ""))

        selected_uid = st.selectbox("Select unit to proceed with", unit_ids)

    # HoT editable form
    st.markdown("#### Heads of Terms")
    if hot:
        col1, col2, col3 = st.columns(3)
        with col1:
            rent = st.number_input("Base Rent (AED/sqm)",
                value=int(hot.get("base_rent_aed_sqm", 0)), step=50)
            fit_out = st.number_input("Fit-out Months",
                value=int(hot.get("fit_out_months", 3)), min_value=1, max_value=6)
        with col2:
            duration = st.number_input("Lease Duration (years)",
                value=int(hot.get("lease_duration_years", 3)), min_value=1, max_value=10)
            escalation = st.number_input("Annual Escalation (%)",
                value=float(hot.get("annual_escalation_pct", 6.0)), step=0.5)
        with col3:
            deposit_months = st.number_input("Security Deposit (months)",
                value=int(hot.get("security_deposit_months", 3)), min_value=1, max_value=6)
            rent_free = st.number_input("Rent Free Months",
                value=int(hot.get("rent_free_months", 0)), min_value=0, max_value=3)

        notes = st.text_area("Executive Notes (optional)", placeholder="Add any notes on changes made...")
    else:
        st.warning("No HoT draft available.")
        rent = fit_out = duration = escalation = deposit_months = rent_free = 0
        notes = ""

    # Approve / Reject
    st.markdown("---")
    col_a, col_r = st.columns([1, 1])
    with col_a:
        if st.button("✅ Approve & Proceed", type="primary", use_container_width=True):
            selected_unit = next((u for u in matched if u.get("unit_id") == selected_uid), None)
            edited_hot = {**hot,
                "base_rent_aed_sqm": rent,
                "fit_out_months": fit_out,
                "lease_duration_years": duration,
                "annual_escalation_pct": escalation,
                "security_deposit_months": deposit_months,
                "rent_free_months": rent_free,
                "executive_notes": notes
            }
            resume_after_gate("approve",
                gate_edits={"hot_approved": edited_hot, "selected_unit": selected_unit})
            st.rerun()
    with col_r:
        reject_reason = st.text_input("Rejection reason", placeholder="Required if rejecting...")
        if st.button("❌ Reject — Re-run Unit Match", use_container_width=True):
            if reject_reason:
                resume_after_gate("reject", rejection_reason=reject_reason)
                st.rerun()
            else:
                st.error("Please provide a rejection reason.")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Gate 2 UI ─────────────────────────────────────────────────────────────────
def render_gate_2(state: dict):
    st.markdown('<div class="gate-box">', unsafe_allow_html=True)
    st.markdown("### ⚑ Gate 2 — LCM Document Review")

    docs_received = state.get("documents_received", {})
    issues = state.get("document_issues", [])

    # Document table
    submitted = docs_received.get("documents_submitted", [])
    missing = docs_received.get("missing_documents", [])

    if submitted:
        st.markdown("#### Submitted Documents")
        for doc in submitted:
            status = doc.get("status", "unknown")
            icon = "✅" if status == "valid" else "⚠️" if status == "warning" else "❌"
            expiry = doc.get("expiry_date", "N/A") or "N/A"
            st.markdown(f"{icon} **{doc.get('doc_type', '').replace('_', ' ').title()}** "
                        f"— {status.upper()} · Expiry: {expiry}")
            if "flag" in doc:
                st.caption(f"🚩 {doc['flag']}")

    if missing:
        st.markdown("#### Missing Documents")
        for m in missing:
            st.markdown(f"❌ {m.replace('_', ' ').title()}")

    if issues:
        st.markdown("#### Agent Flags")
        for issue in issues:
            st.warning(issue)

    lcm_notes = st.text_area("LCM Notes", placeholder="Add notes on document review decision...")

    st.markdown("---")
    col_a, col_r = st.columns([1, 1])
    with col_a:
        if st.button("✅ Approve Document Package", type="primary", use_container_width=True):
            resume_after_gate("approve", gate_edits={"lcm_notes": lcm_notes})
            st.rerun()
    with col_r:
        reject_reason = st.text_input("Rejection reason", placeholder="Required if rejecting...")
        if st.button("❌ Request Resubmission", use_container_width=True):
            if reject_reason:
                resume_after_gate("reject", rejection_reason=reject_reason)
                st.rerun()
            else:
                st.error("Please provide a rejection reason.")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Gate 3 UI ─────────────────────────────────────────────────────────────────
def render_gate_3(state: dict):
    st.markdown('<div class="gate-box">', unsafe_allow_html=True)
    st.markdown("### ⚑ Gate 3 — Senior Manager Final Approval")

    lease = state.get("lease_draft", {})
    check = state.get("consistency_check", {})

    if lease:
        st.markdown("#### Deal Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tenant", lease.get("tenant_brand_name", "—"))
            st.metric("Unit", lease.get("unit_id", "—"))
            st.metric("Annual Rent", f"AED {lease.get('annual_base_rent_aed', 0):,}")
        with col2:
            st.metric("Lease Start", lease.get("lease_start_date", "—"))
            st.metric("Lease End", lease.get("lease_end_date", "—"))
            st.metric("Security Deposit", f"AED {lease.get('security_deposit_aed', 0):,}")

        # Consistency check result
        if check:
            status = check.get("status", "unknown")
            issues = check.get("issues_found", 0)
            icon = "✅" if status == "pass" else "❌"
            st.markdown(f"#### Consistency Check {icon}")
            st.markdown(f"**{check.get('checks_run', 0)} checks run · "
                        f"{issues} issues found**")
            if issues > 0:
                for c in check.get("checks_detail", []):
                    if c.get("result") == "fail":
                        st.error(f"{c.get('check_id')} — {c.get('description')}: {c.get('detail')}")

        with st.expander("View Full Lease JSON"):
            st.json(lease)

    manager_notes = st.text_area("Manager Notes", placeholder="Optional notes on approval...")

    st.markdown("---")
    col_a, col_r = st.columns([1, 1])
    with col_a:
        if st.button("✅ Approve & Send to Tenant", type="primary", use_container_width=True):
            resume_after_gate("approve", gate_edits={"manager_notes": manager_notes})
            st.rerun()
    with col_r:
        reject_reason = st.text_input("Rejection reason", placeholder="Required if rejecting...")
        if st.button("❌ Send Back for Revision", use_container_width=True):
            if reject_reason:
                resume_after_gate("reject", rejection_reason=reject_reason)
                st.rerun()
            else:
                st.error("Please provide a rejection reason.")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────
def render_main_output(state: dict, waiting_at_gate: str):
    current = state.get("current_step", "node_intake")

    # Show completed steps
    for entry in state.get("reasoning_log", []):
        step = entry["step"]
        label = next((s[1] for s in STEPS if s[0] == step), step)
        with st.expander(f"✅ {label}", expanded=False):
            render_reasoning(entry["reasoning"])
            st.json(entry["output"])

    # Show active gate
    if waiting_at_gate == "gate_1":
        render_gate_1(state)
    elif waiting_at_gate == "gate_2":
        render_gate_2(state)
    elif waiting_at_gate == "gate_3":
        render_gate_3(state)

    # Deal closed
    if current == "complete" or state.get("deal_closed"):
        cert = state.get("ejari_certificate", {})
        st.markdown(f"""
        <div class="deal-closed">
            <h2>🎉 Deal Closed</h2>
            <p>EJARI Registration: <strong>{cert.get('registration_number', '—')}</strong></p>
            <p>Status: <strong>{cert.get('status', '—')}</strong></p>
            <p>Handoff to Agent 02 — Tenant Onboarding initiated</p>
        </div>
        """, unsafe_allow_html=True)

    # Errors
    if state.get("errors"):
        with st.expander("⚠️ Errors"):
            for e in state["errors"]:
                st.error(e)


# ── Layout ────────────────────────────────────────────────────────────────────

# Header
st.markdown("""
<div class="main-header">
    <h1>🏢 AI Leasing Agent — MAF Properties</h1>
    <p>Agentic leasing workflow · Inquiry → Unit Match → HoT → Documents → Lease → EJARI</p>
</div>
""", unsafe_allow_html=True)

# Three columns
left, main, right = st.columns([1.2, 3, 1.2])

# ── LEFT — Step progress ──────────────────────────────────────────────────────
with left:
    st.markdown("#### Workflow Progress")
    state = st.session_state.get("graph_state") or {}
    current_step = state.get("current_step", "node_intake") if state else "node_intake"
    waiting = st.session_state.get("waiting_at_gate")

    # If waiting at gate, highlight the gate
    display_step = waiting if waiting else current_step

    for step_key, label, kind in STEPS:
        css = get_step_class(step_key, display_step)
        st.markdown(f'<div class="step-item {css}">{label}</div>',
                    unsafe_allow_html=True)

    if state.get("errors"):
        st.markdown("---")
        st.error(f"⚠️ {len(state['errors'])} error(s)")


# ── MAIN — Agent output + gates ───────────────────────────────────────────────
with main:
    if not st.session_state["graph_state"]:
        # Start screen
        st.markdown("### Select an inquiry to begin")
        selected_name = st.selectbox("Choose tenant inquiry",
                                     list(inquiry_options.keys()))
        inquiry = inquiry_options[selected_name]

        st.markdown("**Inquiry summary:**")
        st.markdown(f"""
        | Field | Value |
        |---|---|
        | **Brand** | {inquiry['brand_name']} |
        | **Legal Entity** | {inquiry['legal_entity_name']} |
        | **Category** | {inquiry['category']} |
        | **Preferred Mall** | {inquiry['preferred_mall']} |
        | **Size Requirement** | {inquiry['size_min_sqm']}–{inquiry['size_max_sqm']} sqm |
        | **Priority** | {inquiry['priority'].title()} |
        | **Target Opening** | {inquiry['target_opening']} |
        | **First UAE Store** | {'Yes' if inquiry.get('first_uae_store') else 'No'} |
        | **Risk Flag** | {inquiry.get('risk_flag') or 'None'} |
        """)

        if st.button("🚀 Start Leasing Workflow", type="primary", use_container_width=True):
            # Reset thread for fresh run
            st.session_state["config"] = {
                "configurable": {"thread_id": f"leasing-{inquiry['inquiry_id']}"}
            }
            initial_state = get_initial_state(inquiry)
            with st.spinner("Agent running..."):
                run_graph_until_gate(initial_state=initial_state)
            st.rerun()
    else:
        state = st.session_state["graph_state"]
        waiting = st.session_state["waiting_at_gate"]
        render_main_output(state, waiting)

    # Reset button
    if st.session_state["graph_state"]:
        st.markdown("---")
        if st.button("🔄 Start New Deal", use_container_width=True):
            st.session_state["graph_state"] = None
            st.session_state["waiting_at_gate"] = None
            st.rerun()


# ── RIGHT — State viewer ──────────────────────────────────────────────────────
with right:
    st.markdown("#### State Viewer")
    state = st.session_state.get("graph_state")
    if state:
        with st.expander("Full State JSON", expanded=False):
            st.json(state)

        # Quick stats
        st.markdown("**Current step:**")
        st.code(state.get("current_step", "—"))

        if state.get("matched_units"):
            st.markdown(f"**Units matched:** {len(state['matched_units'])}")

        if state.get("document_issues"):
            st.markdown(f"**Doc issues:** {len(state['document_issues'])}")

        if state.get("ejari_certificate"):
            st.markdown("**EJARI:** ✅ Filed")
    else:
        st.caption("State will appear here once the workflow starts.")