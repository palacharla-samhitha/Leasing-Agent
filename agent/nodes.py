# agent/nodes.py
# All agent nodes for the leasing workflow
# Integrated with real tool functions from tools/

import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from groq import Groq

from agent.prompts import PROMPTS
from agent.state import LeasingAgentState

# ── Real tool imports ─────────────────────────────────────────────────────────
from tools.yardi import (
    get_available_units,
    get_all_units,
    get_pricing_rule,
    get_unit_by_id,
    is_ejari_required,
)
from tools.documents import (
    get_verification_scenario,
    get_required_documents,
    determine_tenant_type,
    verify_documents,
)
from tools.verification import run_all_checks
from tools.ejari import file_ejari, generate_ejari_reference
from tools.scoring import calculate_lead_score, calculate_match_score

load_dotenv()

# ── Groq client ───────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.1-8b-instant"


# ── Helpers ───────────────────────────────────────────────────────────────────

def call_gemini(node_name: str, context: dict) -> dict:
    """
    Calls Groq/Llama with the node's system prompt and context.
    Named call_gemini to avoid renaming every call site.
    Returns parsed JSON with 'reasoning' and 'output' keys.
    Retries once with stricter instruction if JSON parsing fails.
    """
    user_message = f"Here is the data for this step:\n\n{json.dumps(context, indent=2)}"

    for attempt in range(2):
        msg = user_message
        if attempt == 1:
            msg += "\n\nIMPORTANT: Your response must be valid JSON only. No markdown, no backticks, no preamble."

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROMPTS[node_name]},
                {"role": "user",   "content": msg}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt == 1:
                return {
                    "reasoning": "Failed to parse Groq response after retry.",
                    "output": {},
                    "error": raw
                }

    return {"reasoning": "", "output": {}}


def log_step(state: LeasingAgentState, step: str, reasoning: str, output: dict) -> None:
    """Appends a reasoning log entry for this step."""
    state["reasoning_log"].append({
        "step": step,
        "reasoning": reasoning,
        "output": output,
        "timestamp": datetime.now().isoformat()
    })


# ── Node 1 — Intake ───────────────────────────────────────────────────────────

def node_intake(state: LeasingAgentState) -> LeasingAgentState:
    """
    Classifies the inquiry, extracts key requirements, and runs lead scoring.
    Stage 1 (Vacancy ID) + Stage 2 (Tenant Qualification) combined.
    Reads: inquiry
    Writes: classification, lead_score_result, current_step, reasoning_log
    """
    state["current_step"] = "node_intake"

    inquiry = state["inquiry"]

    # ── Run lead scoring (Stage 2 — Tenant Qualification) ─────────────────
    lead_result = calculate_lead_score(inquiry)
    state["lead_score_result"] = lead_result

    # ── Pass lead score to LLM for classification context ─────────────────
    context = {
        "inquiry": inquiry,
        "lead_score": lead_result
    }

    result = call_gemini("node_intake", context)

    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_intake: {result['error']}")

    state["classification"] = output
    log_step(state, "node_intake", reasoning, {
        **output,
        "lead_score_result": lead_result
    })
    state["current_step"] = "node_unit_match"

    return state


# ── Node 2 — Unit Match ───────────────────────────────────────────────────────

def node_unit_match(state: LeasingAgentState) -> LeasingAgentState:
    """
    Searches available units, scores each with calculate_match_score(),
    then passes pre-scored units to LLM for ranking and explanation.
    Reads: inquiry, classification, lead_score_result
    Writes: matched_units, weak_match_warning, current_step, reasoning_log
    """
    state["current_step"] = "node_unit_match"

    inquiry = state["inquiry"]
    classification = state["classification"] or {}

    # ── Get available units from Yardi ────────────────────────────────────
    # Always use inquiry's original category — LLM reclassification may not
    # match category_fit strings in units.json
    available = get_available_units(
        size_min=inquiry.get("size_min_sqm", 0),
        size_max=inquiry.get("size_max_sqm", 9999),
        category=inquiry.get("category", ""),
        preferred_mall=inquiry.get("preferred_mall")
    )

    # If strict filters return nothing, get ALL leasable units so the exec
    # can see what's available and make a judgment call at Gate 1
    if not available:
        all_units = get_all_units()
        available = [u.copy() for u in all_units if u["status"] in ("vacant", "expiring_soon")]
        for u in available:
            u["_preferred"] = False

    # Fallback: if strict match returns nothing, relax filters progressively
    if not available:
        # Try without category filter
        available = get_available_units(
            size_min=inquiry.get("size_min_sqm", 0),
            size_max=inquiry.get("size_max_sqm", 9999),
            category="",
            preferred_mall=inquiry.get("preferred_mall")
        )
    if not available:
        # Try without mall preference and category
        available = get_available_units(
            size_min=inquiry.get("size_min_sqm", 0),
            size_max=inquiry.get("size_max_sqm", 9999),
            category="",
            preferred_mall=None
        )

    # ── Score every unit before passing to LLM ────────────────────────────
    scored_units = []
    for unit in available:
        score_result = calculate_match_score(inquiry, unit)
        unit["_scoring"] = score_result
        scored_units.append(unit)

    # Sort by match_score descending
    scored_units.sort(key=lambda u: u["_scoring"]["match_score"], reverse=True)

    # ── Check for weak match warning ──────────────────────────────────────
    if scored_units:
        top_score = scored_units[0]["_scoring"]["match_score"]
        if top_score < 0.50:
            state["weak_match_warning"] = (
                f"Best available match scores only {top_score} — "
                f"no strong fit found for this inquiry. "
                f"Executive judgment required at Gate 1."
            )
        else:
            state["weak_match_warning"] = None
    else:
        state["weak_match_warning"] = "No available units found matching criteria."

    # ── Pass scored units to LLM for ranking explanation ──────────────────
    # Send slim unit data to stay within token limits
    slim_units = []
    for u in scored_units:
        slim_units.append({
            "unit_id": u.get("unit_id"),
            "mall": u.get("mall"),
            "floor": u.get("floor"),
            "zone": u.get("zone"),
            "size_sqm": u.get("size_sqm"),
            "status": u.get("status"),
            "base_rent_aed_sqm": u.get("base_rent_aed_sqm"),
            "category_fit": u.get("category_fit"),
            "_scoring": u.get("_scoring"),
        })

    context = {
        "inquiry": {
            "brand_name": inquiry.get("brand_name"),
            "category": inquiry.get("category"),
            "preferred_mall": inquiry.get("preferred_mall"),
            "size_min_sqm": inquiry.get("size_min_sqm"),
            "size_max_sqm": inquiry.get("size_max_sqm"),
        },
        "classification": classification,
        "lead_score": state.get("lead_score_result", {}),
        "available_units": slim_units
    }

    result = call_gemini("node_unit_match", context)

    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_unit_match: {result['error']}")

    # ── Build matched_units with scoring data preserved ───────────────────
    llm_ranked = output.get("recommended_units", [])

    # Merge LLM output with our pre-calculated scores
    final_units = []
    for llm_unit in llm_ranked:
        uid = llm_unit.get("unit_id", "")
        # Find the scored unit to attach _scoring
        scored = next((u for u in scored_units if u.get("unit_id") == uid), None)
        if scored:
            llm_unit["_scoring"] = scored["_scoring"]
        final_units.append(llm_unit)

    # If LLM didn't return units, fall back to tool-scored list
    if not final_units and scored_units:
        for u in scored_units[:3]:
            final_units.append({
                "unit_id": u["unit_id"],
                "mall": u.get("mall", ""),
                "zone": u.get("zone", ""),
                "size_sqm": u.get("size_sqm", 0),
                "base_rent_aed_sqm": u.get("base_rent_aed_sqm", 0),
                "match_rationale": u["_scoring"].get("demand_signal", ""),
                "_scoring": u["_scoring"]
            })

    state["matched_units"] = final_units
    log_step(state, "node_unit_match", reasoning, {
        **output,
        "units_scored": len(scored_units),
        "weak_match_warning": state.get("weak_match_warning")
    })
    state["current_step"] = "node_hot_draft"

    return state


# ── Node 3 — HoT Draft ────────────────────────────────────────────────────────

def node_hot_draft(state: LeasingAgentState) -> LeasingAgentState:
    """
    Drafts the Heads of Terms for the top matched unit.
    Uses get_pricing_rule() from tools/yardi.py for pricing parameters.
    Reads: inquiry, matched_units, classification
    Writes: hot_draft, current_step, reasoning_log
    """
    state["current_step"] = "node_hot_draft"

    inquiry = state["inquiry"]
    classification = state["classification"] or {}

    # Use pre-assigned unit if available, otherwise top match
    assigned_unit_id = inquiry.get("assigned_unit")
    top_unit = None

    if assigned_unit_id:
        top_unit = get_unit_by_id(assigned_unit_id)

    if not top_unit and state["matched_units"]:
        top_uid = state["matched_units"][0].get("unit_id")
        top_unit = get_unit_by_id(top_uid) if top_uid else None

    if not top_unit:
        state["errors"].append("node_hot_draft: No matched unit available for HoT drafting")
        return state

    # Get real pricing rule
    mall_code = top_unit.get("mall_code", "")
    category = classification.get("category", inquiry.get("category", ""))
    pricing = get_pricing_rule(mall_code, category) or {}

    lease_start = datetime.now() + relativedelta(months=1)
    lease_start_str = lease_start.strftime("%Y-%m-%d")

    context = {
        "inquiry": inquiry,
        "selected_unit": top_unit,
        "pricing_parameters": pricing,
        "lease_start_date": lease_start_str,
        "classification": classification
    }

    result = call_gemini("node_hot_draft", context)

    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_hot_draft: {result['error']}")

    state["hot_draft"] = output
    log_step(state, "node_hot_draft", reasoning, output)
    state["current_step"] = "gate_1"

    return state


# ── Node 4 — Document Request ─────────────────────────────────────────────────

def node_doc_request(state: LeasingAgentState) -> LeasingAgentState:
    """
    Generates document checklist and tenant message.
    Uses determine_tenant_type() and get_required_documents() from tools/documents.py
    Reads: inquiry, selected_unit, hot_approved, classification
    Writes: document_checklist, tenant_message, current_step, reasoning_log
    """
    state["current_step"] = "node_doc_request"

    inquiry = state["inquiry"]

    # Use real tool to determine tenant type and required docs
    tenant_type = determine_tenant_type(inquiry)
    required_docs = get_required_documents(tenant_type)

    context = {
        "inquiry": inquiry,
        "selected_unit": state["selected_unit"],
        "hot_approved": state["hot_approved"],
        "classification": state["classification"],
        "tenant_type": tenant_type,
        "required_documents": required_docs
    }

    result = call_gemini("node_doc_request", context)

    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_doc_request: {result['error']}")

    state["document_checklist"] = required_docs
    state["tenant_message"] = output.get("tenant_message", "")
    log_step(state, "node_doc_request", reasoning, {
        **output,
        "document_checklist": required_docs,
        "tenant_type": tenant_type
    })
    state["current_step"] = "node_doc_verify"

    return state


# ── Node 4b — Document Verification ──────────────────────────────────────────

def node_doc_verify(state: LeasingAgentState) -> LeasingAgentState:
    """
    Verifies submitted documents using verify_documents() from tools/documents.py.
    Reads: document_checklist, inquiry_id
    Writes: documents_received, document_issues, current_step, reasoning_log
    """
    state["current_step"] = "node_doc_verify"

    inquiry_id = state["inquiry_id"]

    verification_result = verify_documents(inquiry_id)
    scenario = get_verification_scenario(inquiry_id) or {}
    state["documents_received"] = scenario

    context = {
        "document_checklist": state["document_checklist"],
        "verification_result": verification_result,
        "inquiry": state["inquiry"]
    }

    result = call_gemini("node_doc_verify", context)

    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_doc_verify: {result['error']}")

    issues = []
    for doc in verification_result.get("expired", []):
        issues.append(f"{doc['doc_type']}: EXPIRED — {doc.get('expiry_date', '')}")
    for doc_name in verification_result.get("missing", []):
        issues.append(f"{doc_name}: MISSING")

    state["document_issues"] = issues
    log_step(state, "node_doc_verify", reasoning, {
        **output,
        "verification_result": verification_result
    })
    state["current_step"] = "gate_2"

    return state


# ── Node 5 — Lease Generation ─────────────────────────────────────────────────

def node_lease_gen(state: LeasingAgentState) -> LeasingAgentState:
    """
    Generates the lease document then runs real consistency checks.
    Reads: hot_approved, selected_unit, inquiry
    Writes: lease_draft, consistency_check, current_step, reasoning_log
    """
    state["current_step"] = "node_lease_gen"

    hot = state["hot_approved"] or {}
    unit = state["selected_unit"] or {}
    inquiry = state["inquiry"]

    mall_code = unit.get("mall_code", "")
    category = (state["classification"] or {}).get("category", "")
    pricing_rule = get_pricing_rule(mall_code, category) or {}

    context = {
        "hot_approved": hot,
        "selected_unit": unit,
        "inquiry": inquiry,
        "documents_approved": state["documents_approved"]
    }

    result = call_gemini("node_lease_gen", context)

    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_lease_gen: {result['error']}")

    lease_doc = output.get("lease_document", {})
    state["lease_draft"] = lease_doc

    check_state = {
        "fit_out_end_date":        hot.get("fit_out_end_date", hot.get("rent_commencement_date", "")),
        "lease_start_date":        lease_doc.get("lease_start_date", ""),
        "rent_commencement_date":  lease_doc.get("rent_commencement_date", ""),
        "rent_free_months":        hot.get("rent_free_months", 0),
        "annual_base_rent_aed":    lease_doc.get("annual_base_rent_aed", 0),
        "base_rent_aed_sqm":       hot.get("base_rent_aed_sqm", 0),
        "security_deposit_aed":    lease_doc.get("security_deposit_aed", 0),
        "legal_entity_name":       inquiry.get("legal_entity_name", ""),
        "selected_unit_id":        unit.get("unit_id", ""),
        "mall_code":               mall_code,
        "ejari_required":          is_ejari_required(mall_code),
        "selected_unit":           unit,
        "pricing_rule":            pricing_rule,
    }

    all_passed, check_results = run_all_checks(check_state)

    state["consistency_check"] = {
        "status": "pass" if all_passed else "fail",
        "checks_run": len(check_results),
        "issues_found": sum(1 for r in check_results if not r.passed),
        "checks_detail": [
            {
                "check_id": r.check_id,
                "description": r.description,
                "result": "pass" if r.passed else "fail",
                "detail": r.detail
            }
            for r in check_results
        ]
    }

    log_step(state, "node_lease_gen", reasoning, {
        **output,
        "consistency_check": state["consistency_check"]
    })
    state["current_step"] = "gate_3"

    return state


# ── Node 6 — EJARI ────────────────────────────────────────────────────────────

def node_ejari(state: LeasingAgentState) -> LeasingAgentState:
    """
    Files EJARI using file_ejari() from tools/ejari.py.
    Reads: lease_draft, inquiry, selected_unit
    Writes: ejari_filed, ejari_certificate, deal_closed, reasoning_log
    """
    state["current_step"] = "node_ejari"

    lease = state["lease_draft"] or {}
    inquiry = state["inquiry"]
    unit = state["selected_unit"] or {}
    mall_code = unit.get("mall_code", "")

    filing_result = file_ejari(
        mall_code=mall_code,
        inquiry_id=inquiry.get("inquiry_id", ""),
        legal_entity_name=inquiry.get("legal_entity_name", ""),
        unit_id=unit.get("unit_id", ""),
        lease_start_date=lease.get("lease_start_date", ""),
        lease_expiry_date=lease.get("lease_end_date", ""),
        annual_rent_aed=lease.get("annual_base_rent_aed", 0),
        kofax_doc_ref=lease.get("document_reference", "MAF-LEASE-POC")
    )

    ejari_ref = filing_result.get("ejari_ref", "")

    ejari_certificate = {
        "registration_number": ejari_ref,
        "property": f"{unit.get('mall', '')} — Unit {unit.get('unit_id', '')}",
        "landlord": "Majid Al Futtaim Properties LLC",
        "tenant_legal_name": inquiry.get("legal_entity_name", ""),
        "tenant_brand_name": inquiry.get("brand_name", ""),
        "lease_start_date": lease.get("lease_start_date", ""),
        "lease_end_date": lease.get("lease_end_date", ""),
        "annual_rent_aed": lease.get("annual_base_rent_aed", 0),
        "registration_date": datetime.now().strftime("%Y-%m-%d"),
        "filed_at": filing_result.get("filed_at", ""),
        "status": "Registered" if filing_result.get("success") else "Failed",
        "message": filing_result.get("message", "")
    }

    context = {
        "lease_draft": lease,
        "ejari_certificate": ejari_certificate,
        "inquiry": inquiry,
        "selected_unit": unit,
        "filing_result": filing_result
    }

    result = call_gemini("node_ejari", context)
    reasoning = result.get("reasoning", "")
    output = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_ejari: {result['error']}")

    state["ejari_certificate"] = ejari_certificate
    state["ejari_filed"] = filing_result.get("success", False)
    state["deal_closed"] = filing_result.get("success", False)

    log_step(state, "node_ejari", reasoning, {
        "ejari_certificate": ejari_certificate,
        "filing_result": filing_result,
        "handoff_note": output.get("handoff_note", "")
    })
    state["current_step"] = "complete"

    return state