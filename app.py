# app.py
# Streamlit UI for the AI Leasing Agent
# Three panel layout: left progress | main output | right state viewer

import json
import streamlit as st
from agent.graph import leasing_graph
from agent.state import get_initial_state
from utils.pdf_generator import generate_ejari_pdf

st.set_page_config(page_title="AI Leasing Agent — MAF Properties",
                   page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { background: linear-gradient(90deg, #0a2342, #1a3a5c);
        padding: 1rem 2rem; border-radius: 8px; margin-bottom: 1.5rem; }
    .main-header h1 { color: #00c4b4; margin: 0; font-size: 1.4rem; }
    .main-header p  { color: #a0b4c8; margin: 0; font-size: 0.85rem; }
    .step-item { padding: 0.5rem 0.75rem; border-radius: 6px;
        margin-bottom: 0.4rem; font-size: 0.82rem; font-weight: 500; }
    .step-complete  { background: #0d3d2e; color: #00c4b4; border-left: 3px solid #00c4b4; }
    .step-active    { background: #1a3a5c; color: #ffffff; border-left: 3px solid #4a9eff; }
    .step-gate      { background: #2d1f00; color: #ffaa00; border-left: 3px solid #ffaa00; }
    .step-pending   { background: #1a1a2e; color: #555577; border-left: 3px solid #333355; }
    .reasoning-box  { background: #f8f9fa; border-left: 3px solid #6c757d;
        padding: 1rem; border-radius: 4px; font-style: italic; font-size: 0.88rem;
        color: #444; margin-bottom: 1rem; }
    .gate-box { background: #fff8e1; border: 2px solid #ffaa00;
        padding: 1.2rem; border-radius: 8px; margin-bottom: 1rem; }
    .deal-closed { background: #0d3d2e; color: #00c4b4; padding: 1.5rem;
        border-radius: 8px; text-align: center; }
    .grade-badge { display: inline-block; padding: 0.15rem 0.6rem;
        border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    .grade-a { background: #0d3d2e; color: #00c4b4; }
    .grade-b { background: #2d1f00; color: #ffaa00; }
    .grade-c { background: #3d0d0d; color: #ff4444; }
    .score-card { background: #f0f4f8; border: 1px solid #d0d8e0;
        border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem; }
    .score-label { font-size: 0.75rem; color: #666; margin-bottom: 0.2rem; }
    .score-value { font-size: 1.1rem; font-weight: 600; }
    .demand-signal { background: #e8f4fd; border-left: 3px solid #4a9eff;
        padding: 0.6rem 0.8rem; border-radius: 4px; font-size: 0.82rem;
        color: #1a3a5c; margin-top: 0.4rem; }
    .weak-warning { background: #fff3cd; border: 1px solid #ffaa00;
        padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.85rem;
        color: #856404; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
for k, v in {"graph_state": None, "thread_id": "leasing-demo-001", "running": False,
             "waiting_at_gate": None, "selected_inquiry": None,
             "config": {"configurable": {"thread_id": "leasing-demo-001"}}}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Load inquiries ────────────────────────────────────────────────────────────
@st.cache_data
def load_inquiries():
    with open("data/inquiries.json", "r") as f:
        return json.load(f)

inquiries = load_inquiries()
inquiry_options = {i["brand_name"]: i for i in inquiries}

# ── Steps ─────────────────────────────────────────────────────────────────────
STEPS = [
    ("node_intake",     "1. Intake & Lead Scoring"),
    ("node_unit_match", "2. Unit Match & Scoring"),
    ("node_hot_draft",  "3. Heads of Terms Draft"),
    ("gate_1",          "⚑ Gate 1 — Exec Review"),
    ("node_doc_request","4. Document Request"),
    ("node_doc_verify", "4b. Document Verification"),
    ("gate_2",          "⚑ Gate 2 — LCM Review"),
    ("node_lease_gen",  "5. Lease Generation"),
    ("gate_3",          "⚑ Gate 3 — Final Approval"),
    ("node_ejari",      "6. EJARI Filing"),
    ("complete",        "✓ Deal Closed"),
]
STEP_ORDER = [s[0] for s in STEPS]
GRADE_CSS = {"A": "grade-a", "B": "grade-b", "C": "grade-c"}


def get_step_class(step_key, current):
    if current == "complete":
        return "step-complete"
    if step_key == current:
        return "step-gate" if "gate" in step_key else "step-active"
    try:
        if STEP_ORDER.index(step_key) < STEP_ORDER.index(current):
            return "step-complete"
    except ValueError:
        pass
    return "step-gate" if "gate" in step_key else "step-pending"


# ── Graph runner ──────────────────────────────────────────────────────────────
def run_graph_until_gate(initial_state=None):
    cfg = st.session_state["config"]
    for _ in leasing_graph.stream(initial_state if initial_state else None, cfg):
        pass
    snap = leasing_graph.get_state(cfg)
    st.session_state["graph_state"] = snap.values
    nxt = snap.next
    st.session_state["waiting_at_gate"] = nxt[0] if nxt and any("gate" in n for n in nxt) else None


def resume_after_gate(decision, edits=None, rejection_reason=None):
    cfg = st.session_state["config"]
    updates = {"gate_decision": decision, "gate_edits": edits or {},
               "rejection_reason": rejection_reason or ""}
    gs = st.session_state["graph_state"]
    gate = st.session_state["waiting_at_gate"]

    if decision in ("approve", "edit") and edits:
        if gate == "gate_1":
            updates["hot_approved"] = edits.get("hot_approved", gs.get("hot_draft"))
            updates["selected_unit"] = edits.get("selected_unit",
                gs["matched_units"][0] if gs.get("matched_units") else None)
        elif gate == "gate_2":
            updates["documents_approved"] = True
        elif gate == "gate_3":
            updates["lease_approved"] = True

    leasing_graph.update_state(cfg, updates)
    run_graph_until_gate()


# ── Shared UI helpers ─────────────────────────────────────────────────────────
def _score_card(label, value, extra_style=""):
    st.markdown(f'<div class="score-card"><div class="score-label">{label}</div>'
                f'<div class="score-value" {extra_style}>{value}</div></div>',
                unsafe_allow_html=True)


def _gate_buttons(approve_label, reject_label, notes_key, on_approve, on_reject):
    """Shared approve/reject buttons for all gates."""
    st.markdown("---")
    ca, cr = st.columns([1, 1])
    with ca:
        if st.button(f"✅ {approve_label}", type="primary", use_container_width=True):
            on_approve()
            st.rerun()
    with cr:
        reason = st.text_input("Rejection reason", placeholder="Required if rejecting...",
                               key=f"reject_{notes_key}")
        if st.button(f"❌ {reject_label}", use_container_width=True):
            if reason:
                on_reject(reason)
                st.rerun()
            else:
                st.error("Please provide a rejection reason.")


# ── Gate 1 ────────────────────────────────────────────────────────────────────
def render_gate_1(state):
    st.markdown('<div class="gate-box">', unsafe_allow_html=True)
    st.markdown("### ⚑ Gate 1 — Leasing Executive Review")
    st.markdown("Review lead qualification, matched units, and Heads of Terms.")

    # Lead score
    lead = state.get("lead_score_result") or {}
    if lead:
        grade = lead.get("lead_grade", "?")
        st.markdown("#### Tenant Lead Score")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            _score_card("Lead Score", f"{lead.get('lead_score', 0):.2f}")
        with c2:
            css = GRADE_CSS.get(grade, "grade-b")
            _score_card("Grade", f'<span class="grade-badge {css}">{grade}</span>')
        with c3:
            _score_card("Assessment", f'<span style="font-size:0.82rem">{lead.get("reasoning", "")}</span>')

        pos, neg = lead.get("signals_positive", []), lead.get("signals_negative", [])
        if pos or neg:
            with st.expander("Lead Score Signals", expanded=False):
                for s in pos: st.markdown(f"✅ {s}")
                for s in neg: st.markdown(f"⚠️ {s}")

    # Weak match warning
    warn = state.get("weak_match_warning")
    if warn:
        st.markdown(f'<div class="weak-warning">⚠️ {warn}</div>', unsafe_allow_html=True)

    # Matched units
    matched = state.get("matched_units", [])
    hot = state.get("hot_draft") or {}

    st.markdown("#### Matched Units")
    unit_ids = [u.get("unit_id", "") for u in matched]
    if not unit_ids:
        st.warning("No units matched. Reject to loop back.")
        selected_uid = None
    else:
        for unit in matched:
            sc = unit.get("_scoring", {})
            m_score = sc.get("match_score", unit.get("match_score", 0))
            m_status = sc.get("match_status", "unknown")
            color = {"strong": "#00c4b4", "moderate": "#ffaa00"}.get(m_status, "#ff4444")

            uc1, uc2, uc3, uc4 = st.columns([1.5, 1, 1, 1])
            with uc1:
                st.markdown(f"**{unit.get('unit_id', '')}**")
                st.caption(f"{unit.get('mall', '')} · {unit.get('zone', '')}")
                st.caption(f"{unit.get('size_sqm', 0)} sqm · AED {unit.get('base_rent_aed_sqm', 0):,}/sqm")
            with uc2:
                _score_card("Match", f'{m_score:.2f}', f'style="color:{color}"')
            with uc3:
                _score_card("Demand", f"{sc.get('vacancy_demand_score', 0):.2f}")
            with uc4:
                cat_icon = "✅" if sc.get("category_match") else "❌"
                _score_card("Category", f"{cat_icon} {sc.get('footfall_tier', 'standard').title()}")

            sig = sc.get("demand_signal", "")
            if sig:
                st.markdown(f'<div class="demand-signal">📊 {sig}</div>', unsafe_allow_html=True)
            if unit.get("rationale"):
                st.caption(unit["rationale"])
            st.markdown("---")

        selected_uid = st.selectbox("Select unit to proceed with", unit_ids)

    # HoT form
    st.markdown("#### Heads of Terms")
    if hot:
        c1, c2, c3 = st.columns(3)
        with c1:
            rent = st.number_input("Base Rent (AED/sqm)", value=int(hot.get("base_rent_aed_sqm", 0)), step=50)
            fit_out = st.number_input("Fit-out Months", value=int(hot.get("fit_out_months", 3)), min_value=1, max_value=6)
        with c2:
            duration = st.number_input("Lease Duration (years)", value=int(hot.get("lease_duration_years", 3)), min_value=1, max_value=10)
            escalation = st.number_input("Annual Escalation (%)", value=float(hot.get("annual_escalation_pct", 6.0)), step=0.5)
        with c3:
            dep_months = st.number_input("Security Deposit (months)", value=int(hot.get("security_deposit_months", 3)), min_value=1, max_value=6)
            rent_free = st.number_input("Rent Free Months", value=int(hot.get("rent_free_months", 0)), min_value=0, max_value=3)
        notes = st.text_area("Executive Notes (optional)", placeholder="Add any notes on changes made...")
    else:
        st.warning("No HoT draft available.")
        rent = fit_out = duration = escalation = dep_months = rent_free = 0
        notes = ""

    def on_approve():
        sel = next((u for u in matched if u.get("unit_id") == selected_uid), None)
        edited = {**(hot or {}), "base_rent_aed_sqm": rent, "fit_out_months": fit_out,
                  "lease_duration_years": duration, "annual_escalation_pct": escalation,
                  "security_deposit_months": dep_months, "rent_free_months": rent_free,
                  "executive_notes": notes}
        resume_after_gate("approve", edits={"hot_approved": edited, "selected_unit": sel})

    _gate_buttons("Approve & Proceed", "Reject — Re-run Unit Match", "g1",
                  on_approve, lambda r: resume_after_gate("reject", rejection_reason=r))
    st.markdown('</div>', unsafe_allow_html=True)


# ── Gate 2 ────────────────────────────────────────────────────────────────────
def render_gate_2(state):
    st.markdown('<div class="gate-box">', unsafe_allow_html=True)
    st.markdown("### ⚑ Gate 2 — LCM Document Review")

    docs = state.get("documents_received", {})
    for doc in docs.get("documents_submitted", []):
        status = doc.get("status", "unknown")
        icon = {"valid": "✅", "warning": "⚠️"}.get(status, "❌")
        st.markdown(f"{icon} **{doc.get('doc_type', '').replace('_', ' ').title()}** "
                    f"— {status.upper()} · Expiry: {doc.get('expiry_date', 'N/A') or 'N/A'}")
        if "flag" in doc:
            st.caption(f"🚩 {doc['flag']}")

    for m in docs.get("missing_documents", []):
        st.markdown(f"❌ {m.replace('_', ' ').title()}")

    for issue in state.get("document_issues", []):
        st.warning(issue)

    lcm_notes = st.text_area("LCM Notes", placeholder="Add notes on document review decision...")

    _gate_buttons("Approve Document Package", "Request Resubmission", "g2",
                  lambda: resume_after_gate("approve", edits={"lcm_notes": lcm_notes}),
                  lambda r: resume_after_gate("reject", rejection_reason=r))
    st.markdown('</div>', unsafe_allow_html=True)


# ── Gate 3 ────────────────────────────────────────────────────────────────────
def render_gate_3(state):
    st.markdown('<div class="gate-box">', unsafe_allow_html=True)
    st.markdown("### ⚑ Gate 3 — Senior Manager Final Approval")

    lease = state.get("lease_draft", {})
    check = state.get("consistency_check", {})

    if lease:
        st.markdown("#### Deal Summary")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Tenant", lease.get("tenant_brand_name", "—"))
            st.metric("Unit", lease.get("unit_id", "—"))
            st.metric("Annual Rent", f"AED {lease.get('annual_base_rent_aed', 0):,}")
        with c2:
            st.metric("Lease Start", lease.get("lease_start_date", "—"))
            st.metric("Lease End", lease.get("lease_end_date", "—"))
            st.metric("Security Deposit", f"AED {lease.get('security_deposit_aed', 0):,}")

        if check:
            icon = "✅" if check.get("status") == "pass" else "❌"
            st.markdown(f"#### Consistency Check {icon}")
            st.markdown(f"**{check.get('checks_run', 0)} checks · {check.get('issues_found', 0)} issues**")
            for c in check.get("checks_detail", []):
                if c.get("result") == "fail":
                    st.error(f"{c.get('check_id')} — {c.get('description')}: {c.get('detail')}")

        with st.expander("View Full Lease JSON"):
            st.json(lease)

    mgr_notes = st.text_area("Manager Notes", placeholder="Optional notes on approval...")

    _gate_buttons("Approve & Send to Tenant", "Send Back for Revision", "g3",
                  lambda: resume_after_gate("approve", edits={"manager_notes": mgr_notes}),
                  lambda r: resume_after_gate("reject", rejection_reason=r))
    st.markdown('</div>', unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────
def render_main_output(state, waiting):
    for entry in state.get("reasoning_log", []):
        label = next((s[1] for s in STEPS if s[0] == entry["step"]), entry["step"])
        with st.expander(f"✅ {label}", expanded=False):
            if entry.get("reasoning"):
                st.markdown(f'<div class="reasoning-box">💭 {entry["reasoning"]}</div>',
                            unsafe_allow_html=True)
            st.json(entry["output"])

    {"gate_1": render_gate_1, "gate_2": render_gate_2, "gate_3": render_gate_3
     }.get(waiting, lambda s: None)(state)

    if state.get("current_step") == "complete" or state.get("deal_closed"):
        cert = state.get("ejari_certificate", {})
        st.markdown(f"""
        <div class="deal-closed">
            <h2>🎉 Deal Closed</h2>
            <p>EJARI Registration: <strong>{cert.get('registration_number', '—')}</strong></p>
            <p>Status: <strong>{cert.get('status', '—')}</strong></p>
            <p>Handoff to Agent 02 — Tenant Onboarding initiated</p>
        </div>
        """, unsafe_allow_html=True)
        try:
            pdf = generate_ejari_pdf(state)
            brand = state.get("inquiry", {}).get("brand_name", "Tenant")
            st.download_button("📄 Download EJARI Certificate (PDF)", pdf,
                file_name=f"EJARI_Certificate_{brand.replace(' ', '_')}.pdf",
                mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

    if state.get("errors"):
        with st.expander("⚠️ Errors"):
            for e in state["errors"]:
                st.error(e)


# ── Layout ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏢 AI Leasing Agent — MAF Properties</h1>
    <p>Intake & Lead Scoring → Unit Match & Demand Scoring → HoT → Documents → Lease → EJARI</p>
</div>
""", unsafe_allow_html=True)

left, main, right = st.columns([1.2, 3, 1.2])

with left:
    st.markdown("#### Workflow Progress")
    gs = st.session_state.get("graph_state") or {}
    cur = gs.get("current_step", "node_intake") if gs else "node_intake"
    waiting = st.session_state.get("waiting_at_gate")
    display = waiting or cur
    for key, label in STEPS:
        st.markdown(f'<div class="step-item {get_step_class(key, display)}">{label}</div>',
                    unsafe_allow_html=True)
    if gs.get("errors"):
        st.error(f"⚠️ {len(gs['errors'])} error(s)")

with main:
    if not st.session_state["graph_state"]:
        st.markdown("### Select an inquiry to begin")
        name = st.selectbox("Choose tenant inquiry", list(inquiry_options.keys()))
        inq = inquiry_options[name]
        st.markdown(f"""
        | Field | Value |
        |---|---|
        | **Brand** | {inq['brand_name']} |
        | **Legal Entity** | {inq['legal_entity_name']} |
        | **Category** | {inq['category']} |
        | **Preferred Mall** | {inq['preferred_mall']} |
        | **Size** | {inq['size_min_sqm']}–{inq['size_max_sqm']} sqm |
        | **Priority** | {inq['priority'].title()} |
        | **Target Opening** | {inq['target_opening']} |
        | **First UAE Store** | {'Yes' if inq.get('first_uae_store') else 'No'} |
        | **Risk Flag** | {inq.get('risk_flag') or 'None'} |
        """)
        if st.button("🚀 Start Leasing Workflow", type="primary", use_container_width=True):
            st.session_state["config"] = {"configurable": {"thread_id": f"leasing-{inq['inquiry_id']}"}}
            with st.spinner("Agent running — intake, scoring, unit matching, HoT drafting..."):
                run_graph_until_gate(initial_state=get_initial_state(inq))
            st.rerun()
    else:
        render_main_output(st.session_state["graph_state"], st.session_state["waiting_at_gate"])

    if st.session_state["graph_state"]:
        st.markdown("---")
        if st.button("🔄 Start New Deal", use_container_width=True):
            st.session_state["graph_state"] = None
            st.session_state["waiting_at_gate"] = None
            st.rerun()

with right:
    st.markdown("#### State Viewer")
    gs = st.session_state.get("graph_state")
    if gs:
        lead = gs.get("lead_score_result")
        if lead:
            g = lead.get("lead_grade", "?")
            st.markdown(f'Lead: <span class="grade-badge {GRADE_CSS.get(g, "grade-b")}">{g}</span> '
                        f'({lead.get("lead_score", 0):.2f})', unsafe_allow_html=True)
        if gs.get("weak_match_warning"):
            st.warning(gs["weak_match_warning"])
        with st.expander("Full State JSON", expanded=False):
            st.json(gs)
        st.code(gs.get("current_step", "—"))
        if gs.get("matched_units"):
            st.markdown(f"**Units matched:** {len(gs['matched_units'])}")
        if gs.get("document_issues"):
            st.markdown(f"**Doc issues:** {len(gs['document_issues'])}")
        if gs.get("ejari_certificate"):
            st.markdown("**EJARI:** ✅ Filed")
    else:
        st.caption("State will appear here once the workflow starts.")