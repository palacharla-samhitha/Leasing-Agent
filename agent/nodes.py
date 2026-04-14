# agent/nodes.py
# All agent nodes for the leasing workflow

import json
import os
import time
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from groq import Groq

from agent.prompts import PROMPTS
from agent.state import LeasingAgentState
from tools.yardi import (
    get_available_units, get_all_units, get_pricing_rule,
    get_unit_by_id, is_ejari_required,
)
from tools.documents import (
    get_verification_scenario, get_required_documents,
    determine_tenant_type, verify_documents,
)
from tools.verification import run_all_checks
from tools.ejari import file_ejari, generate_ejari_reference
from tools.scoring import calculate_lead_score, calculate_match_score

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"


# ── JSON serializer — handles Postgres Decimal and date types ─────────────────

def _decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ── LLM caller ────────────────────────────────────────────────────────────────

def _call_llm(node_name: str, context: dict) -> dict:
    """Calls Groq with node prompt and context. Retries on rate limit or bad JSON."""
    prompt = PROMPTS[node_name]
    msg = f"Here is the data for this step:\n\n{json.dumps(context, indent=2, default=_decimal_default)}"

    for attempt in range(3):
        if attempt == 2:
            msg += "\nIMPORTANT: Respond with valid JSON only. No markdown."
        try:
            raw = client.chat.completions.create(
                model=MODEL, temperature=0.3, max_tokens=2000,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": msg},
                ]
            ).choices[0].message.content.strip()
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "rate_limit" in str(e).lower()):
                time.sleep(15)
                continue
            return {"reasoning": f"LLM error: {e}", "output": {}, "error": str(e)}

        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt == 2:
                return {"reasoning": "JSON parse failed", "output": {}, "error": raw}
            time.sleep(2)

    return {"reasoning": "", "output": {}}


# ── Node runner wrapper ───────────────────────────────────────────────────────

def _run_node(state, step_name, next_step, context, post_fn=None):
    state["current_step"] = step_name
    result   = _call_llm(step_name, context)
    reasoning = result.get("reasoning", "")
    output    = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"{step_name}: {result['error']}")

    if post_fn:
        post_fn(state, output, result)

    state["reasoning_log"].append({
        "step": step_name, "reasoning": reasoning,
        "output": output, "timestamp": datetime.now().isoformat()
    })
    state["current_step"] = next_step
    return state


# ── Slim helpers — reduce token usage ────────────────────────────────────────

def _slim_inquiry(inquiry: dict, fields=None) -> dict:
    default = ["brand_name", "legal_entity_name", "category", "preferred_mall",
               "preferred_zone", "size_min_sqm", "size_max_sqm", "target_opening",
               "first_uae_store", "priority", "risk_flag", "channel"]
    return {k: inquiry.get(k) for k in (fields or default)}


def _slim_unit(unit: dict) -> dict:
    """Extract only the fields the LLM needs — uses schema field names."""
    return {k: unit.get(k) for k in [
        "unit_id", "mall_name", "floor", "zone", "sqm", "status",
        "base_rent_sqm", "service_charge_sqm", "marketing_levy_sqm",
        "turnover_rent_pct", "typical_fit_out_months", "category_fit", "_scoring",
    ] if unit.get(k) is not None}


# ── Node 1 — Intake & Lead Scoring ───────────────────────────────────────────

def node_intake(state: LeasingAgentState) -> LeasingAgentState:
    inquiry = state["inquiry"]
    lead    = calculate_lead_score(inquiry)
    state["lead_score_result"] = lead

    context = {
        "inquiry":    _slim_inquiry(inquiry),
        "lead_score": {"lead_score": lead["lead_score"], "lead_grade": lead["lead_grade"]},
    }

    def post(s, output, _result):
        s["classification"] = output

    return _run_node(state, "node_intake", "node_unit_match", context, post)


# ── Node 2 — Unit Match & Scoring ────────────────────────────────────────────

def node_unit_match(state: LeasingAgentState) -> LeasingAgentState:
    state["current_step"] = "node_unit_match"
    inquiry = state["inquiry"]

    # Fetch available units
    available = get_available_units(
        size_min=inquiry.get("size_min_sqm", 0),
        size_max=inquiry.get("size_max_sqm", 9999),
        category=inquiry.get("category", ""),
        preferred_mall=inquiry.get("preferred_mall"),
    )
    if not available:
        available = [u.copy() for u in get_all_units()
                     if u["status"] in ("vacant", "expiring_soon")]

    # Score and rank — top 3 only to stay within token limits
    for unit in available:
        unit["_scoring"] = calculate_match_score(inquiry, unit)
    available.sort(key=lambda u: u["_scoring"]["match_score"], reverse=True)
    scored = available[:3]

    # Weak match warning
    if scored:
        top = scored[0]["_scoring"]["match_score"]
        state["weak_match_warning"] = (
            f"Best match scores only {top} — no strong fit. Executive judgment required."
            if top < 0.50 else None
        )
    else:
        state["weak_match_warning"] = "No available units found matching criteria."

    context = {
        "inquiry": _slim_inquiry(inquiry, ["brand_name", "category", "preferred_mall",
                                            "size_min_sqm", "size_max_sqm"]),
        "lead_score":      state.get("lead_score_result", {}),
        "available_units": [_slim_unit(u) for u in scored],
    }
    result    = _call_llm("node_unit_match", context)
    reasoning = result.get("reasoning", "")
    output    = result.get("output", {})

    if "error" in result:
        state["errors"].append(f"node_unit_match: {result['error']}")

    # Merge LLM ranking with full DB data from scored list
    llm_units = output.get("recommended_units", [])
    final = []
    for lu in llm_units:
        src = next((u for u in scored if u.get("unit_id") == lu.get("unit_id")), None)
        if src:
            # Overwrite LLM values with authoritative DB values
            lu.update({k: src[k] for k in [
                "sqm", "base_rent_sqm", "mall_name", "zone",
                "floor", "status", "category_fit", "_scoring"
            ] if k in src})
        final.append(lu)

    # Fallback if LLM returned nothing or wrong unit IDs
    if not final:
        final = [{
            "unit_id":       u["unit_id"],
            "mall_name":     u.get("mall_name"),
            "zone":          u.get("zone"),
            "sqm":           u.get("sqm"),
            "base_rent_sqm": u.get("base_rent_sqm"),
            "_scoring":      u["_scoring"],
        } for u in scored]

    # Single assignment — no duplicate
    state["matched_units"] = final

    state["reasoning_log"].append({
        "step": "node_unit_match", "reasoning": reasoning,
        "output": {**output, "units_scored": len(scored),
                   "weak_match_warning": state.get("weak_match_warning")},
        "timestamp": datetime.now().isoformat()
    })
    state["current_step"] = "node_hot_draft"
    return state


# ── Node 3 — HoT Draft ───────────────────────────────────────────────────────

def node_hot_draft(state: LeasingAgentState) -> LeasingAgentState:
    inquiry = state["inquiry"]

    # Resolve unit — use assigned_unit from inquiry first, then top match
    uid      = inquiry.get("assigned_unit")
    top_unit = get_unit_by_id(uid) if uid else None
    if not top_unit and state["matched_units"]:
        uid      = state["matched_units"][0].get("unit_id")
        top_unit = get_unit_by_id(uid) if uid else None
    if not top_unit:
        state["errors"].append("node_hot_draft: No matched unit available for HoT drafting")
        return state

    pricing     = get_pricing_rule(top_unit.get("mall_code", ""), inquiry.get("category", "")) or {}
    lease_start = (datetime.now() + relativedelta(months=1)).strftime("%Y-%m-%d")

    context = {
        "inquiry": _slim_inquiry(inquiry, ["brand_name", "legal_entity_name",
                                            "category", "first_uae_store", "target_opening"]),
        "selected_unit":     _slim_unit(top_unit),
        "pricing_parameters": pricing,
        "lease_start_date":  lease_start,
    }

    def post(s, output, _result):
        # Always ensure lease_start_date is in the HoT draft
        if "lease_start_date" not in output:
            output["lease_start_date"] = lease_start
        s["hot_draft"] = output

    return _run_node(state, "node_hot_draft", "gate_1", context, post)


# ── Node 4 — Document Request ─────────────────────────────────────────────────

def node_doc_request(state: LeasingAgentState) -> LeasingAgentState:
    inquiry       = state["inquiry"]
    tenant_type   = determine_tenant_type(inquiry)
    required_docs = get_required_documents(tenant_type)

    context = {
        "inquiry": _slim_inquiry(inquiry, ["brand_name", "legal_entity_name",
                                            "contact_name", "first_uae_store", "category"]),
        "tenant_type":       tenant_type,
        "required_documents": required_docs,
    }

    def post(s, output, _result):
        s["document_checklist"] = required_docs
        s["tenant_message"]     = output.get("tenant_message", "")

    return _run_node(state, "node_doc_request", "node_doc_verify", context, post)


# ── Node 4b — Document Verification ──────────────────────────────────────────

def node_doc_verify(state: LeasingAgentState) -> LeasingAgentState:
    verification = verify_documents(state["inquiry_id"])
    state["documents_received"] = get_verification_scenario(state["inquiry_id"]) or {}

    context = {
        "document_checklist":  state["document_checklist"],
        "verification_result": verification,
        "brand_name":          state["inquiry"].get("brand_name"),
    }

    def post(s, output, _result):
        issues = []
        for doc in verification.get("expired", []):
            issues.append(f"{doc['doc_type']}: EXPIRED — {doc.get('expiry_date', '')}")
        for name in verification.get("missing", []):
            issues.append(f"{name}: MISSING")
        s["document_issues"] = issues

    return _run_node(state, "node_doc_verify", "gate_2", context, post)


# ── Node 5 — Lease Generation ─────────────────────────────────────────────────

def node_lease_gen(state: LeasingAgentState) -> LeasingAgentState:
    hot      = state["hot_approved"] or {}
    unit     = state["selected_unit"] or {}
    inquiry  = state["inquiry"]
    mall_code = unit.get("mall_code", "")

    pricing_rule = get_pricing_rule(
        mall_code,
        (state["classification"] or {}).get("category", ""),
    ) or {}

    # ── Pre-calculate all dates and financials in Python ──────────────────
    # Never let the LLM calculate these — it gets them wrong.
    fit_out_months   = int(hot.get("fit_out_months", 3))
    rent_free_months = int(hot.get("rent_free_months", 0))
    duration_years   = int(hot.get("lease_duration_years", 3))
    base_rent_sqm    = float(hot.get("base_rent_aed_sqm", 0))
    sqm              = float(unit.get("sqm") or 0)
    deposit_months   = int(hot.get("security_deposit_months",
                          int(pricing_rule.get("security_deposit_months", 3))))
    escalation_pct   = float(hot.get("annual_escalation_pct",
                          float(pricing_rule.get("annual_escalation_pct", 5.0))))

    # Parse lease start from hot_approved — fall back to next month
    raw_start = hot.get("lease_start_date") or \
                (datetime.now() + relativedelta(months=1)).strftime("%Y-%m-%d")
    lease_start   = datetime.strptime(str(raw_start)[:10], "%Y-%m-%d")
    fit_out_end   = lease_start + relativedelta(months=fit_out_months) - relativedelta(days=1)
    rent_commence = fit_out_end + relativedelta(days=1) + relativedelta(months=rent_free_months)
    lease_end     = lease_start + relativedelta(years=duration_years) - relativedelta(days=1)

    annual_rent      = round(base_rent_sqm * sqm, 2)
    monthly_rent     = round(annual_rent / 12, 2)
    security_deposit = round(monthly_rent * deposit_months, 2)
    year2_rent       = round(annual_rent * (1 + escalation_pct / 100), 2)
    year3_rent       = round(year2_rent  * (1 + escalation_pct / 100), 2)

    calculated = {
        "lease_start_date":       lease_start.strftime("%Y-%m-%d"),
        "fit_out_end_date":       fit_out_end.strftime("%Y-%m-%d"),
        "rent_commencement_date": rent_commence.strftime("%Y-%m-%d"),
        "lease_end_date":         lease_end.strftime("%Y-%m-%d"),
        "annual_base_rent_aed":   annual_rent,
        "monthly_base_rent_aed":  monthly_rent,
        "security_deposit_aed":   security_deposit,
        "year_2_rent_aed":        year2_rent,
        "year_3_rent_aed":        year3_rent,
        "fit_out_months":         fit_out_months,
        "rent_free_months":       rent_free_months,
        "lease_duration_years":   duration_years,
        "base_rent_aed_sqm":      base_rent_sqm,
        "security_deposit_months": deposit_months,
        "annual_escalation_pct":  escalation_pct,
    }

    context = {
        "hot_approved":       hot,
        "calculated_figures": calculated,  # LLM must copy these exactly
        "unit_id":            unit.get("unit_id"),
        "mall":               unit.get("mall_name"),
        "size_sqm":           unit.get("sqm"),
        "tenant_legal_name":  inquiry.get("legal_entity_name"),
        "tenant_brand_name":  inquiry.get("brand_name"),
    }

    def post(s, output, _result):
        lease = output.get("lease_document", {})

        # Override critical financial fields with our Python-calculated values
        # regardless of what the LLM produced
        lease.update({
            "lease_start_date":       calculated["lease_start_date"],
            "fit_out_end_date":       calculated["fit_out_end_date"],
            "rent_commencement_date": calculated["rent_commencement_date"],
            "lease_end_date":         calculated["lease_end_date"],
            "annual_base_rent_aed":   calculated["annual_base_rent_aed"],
            "monthly_base_rent_aed":  calculated["monthly_base_rent_aed"],
            "security_deposit_aed":   calculated["security_deposit_aed"],
            "year_2_rent_aed":        calculated["year_2_rent_aed"],
            "year_3_rent_aed":        calculated["year_3_rent_aed"],
            "base_rent_aed_sqm":      calculated["base_rent_aed_sqm"],
        })
        s["lease_draft"] = lease

        # Run consistency checks against our calculated values — not LLM values
        cs = {
            "fit_out_end_date":       calculated["fit_out_end_date"],
            "lease_start_date":       calculated["lease_start_date"],
            "rent_commencement_date": calculated["rent_commencement_date"],
            "rent_free_months":       rent_free_months,
            "annual_base_rent_aed":   calculated["annual_base_rent_aed"],
            "base_rent_aed_sqm":      calculated["base_rent_aed_sqm"],
            "security_deposit_aed":   calculated["security_deposit_aed"],
            "legal_entity_name":      inquiry.get("legal_entity_name", ""),
            "selected_unit_id":       unit.get("unit_id", ""),
            "mall_code":              mall_code,
            "ejari_required":         is_ejari_required(mall_code),
            "selected_unit":          unit,
            "pricing_rule":           pricing_rule,
        }
        passed, checks = run_all_checks(cs)
        s["consistency_check"] = {
            "status":       "pass" if passed else "fail",
            "checks_run":   len(checks),
            "issues_found": sum(1 for c in checks if not c.passed),
            "checks_detail": [{
                "check_id":    c.check_id,
                "description": c.description,
                "result":      "pass" if c.passed else "fail",
                "detail":      c.detail,
            } for c in checks],
        }

    return _run_node(state, "node_lease_gen", "gate_3", context, post)


# ── Node 6 — EJARI ───────────────────────────────────────────────────────────

def _build_certificate(cert_data: dict, inquiry: dict, unit: dict, lease: dict) -> dict:
    return {
        "registration_number": cert_data.get("ejari_ref", ""),
        "property":            f"{unit.get('mall_name', '')} — Unit {unit.get('unit_id', '')}",
        "landlord":            "Majid Al Futtaim Properties LLC",
        "tenant_legal_name":   inquiry.get("legal_entity_name", ""),
        "tenant_brand_name":   inquiry.get("brand_name", ""),
        "lease_start_date":    lease.get("lease_start_date", ""),
        "lease_end_date":      lease.get("lease_end_date", ""),
        "annual_rent_aed":     lease.get("annual_base_rent_aed", 0),
        "registration_date":   datetime.now().strftime("%Y-%m-%d"),
        "filed_at":            cert_data.get("filed_at", ""),
        "status":              "Registered" if cert_data.get("success") else "Failed",
        "message":             cert_data.get("message", ""),
    }


def node_ejari(state: LeasingAgentState) -> LeasingAgentState:
    lease   = state["lease_draft"] or {}
    inquiry = state["inquiry"]
    unit    = state["selected_unit"] or {}

    filing = file_ejari(
        mall_code=         unit.get("mall_code", ""),
        inquiry_id=        inquiry.get("inquiry_id", ""),
        legal_entity_name= inquiry.get("legal_entity_name", ""),
        unit_id=           unit.get("unit_id", ""),
        lease_start_date=  lease.get("lease_start_date", ""),
        lease_expiry_date= lease.get("lease_end_date", ""),
        annual_rent_aed=   lease.get("annual_base_rent_aed", 0),
        kofax_doc_ref=     lease.get("document_reference", "MAF-LEASE-POC"),
    )

    cert = _build_certificate(filing, inquiry, unit, lease)

    context = {
        "ejari_certificate": cert,
        "brand_name":        inquiry.get("brand_name"),
        "unit_id":           unit.get("unit_id"),
        "mall":              unit.get("mall_name"),
        "filing_success":    filing.get("success"),
    }

    def post(s, output, _result):
        s["ejari_certificate"] = cert
        s["ejari_filed"]       = filing.get("success", False)
        s["deal_closed"]       = filing.get("success", False)

    return _run_node(state, "node_ejari", "complete", context, post)