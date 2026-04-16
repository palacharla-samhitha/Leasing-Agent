# agent/fallbacks.py
# ============================================================================
# Per-node rule-based fallback functions
# MAF Properties · ReKnew · Phase 2 · April 2026
#
# Each function activates when the LLM fails 3 consecutive times on that node.
# Fallbacks produce a valid output in the EXACT same JSON shape the LLM would
# return — so the rest of the workflow continues without modification.
#
# Fallback philosophy:
#   - Never crash the workflow
#   - Always return the correct output shape
#   - Use Python-calculated values and DB data directly
#   - Skip narrative/reasoning fields — leave as empty strings
#   - Log every activation to audit_events as fallback_triggered
#
# Fallback outputs are less rich than LLM outputs but always mathematically
# correct. The leasing exec reviews everything at Gates 1/2/3 anyway.
# ============================================================================

from datetime import datetime
from dateutil.relativedelta import relativedelta


# ── Generic template strings ──────────────────────────────────────────────────

_FALLBACK_NOTE = "[FALLBACK] LLM unavailable — generated from rules and database values."

_GENERIC_TENANT_MESSAGE = (
    "Dear {brand_name},\n\n"
    "Thank you for your inquiry. To proceed with your leasing application, "
    "please submit the required documents listed below at your earliest convenience. "
    "Our leasing team will review your submission and be in touch shortly.\n\n"
    "Kind regards,\n"
    "MAF Properties Leasing Team"
)


# ── Node 1 — Intake & Lead Scoring ───────────────────────────────────────────

def fallback_node_intake(state: dict, lead: dict, inquiry: dict) -> dict:
    """
    Fallback for node_intake.
    Derives tenant_type and classification directly from inquiry fields.
    Uses lead score result without LLM interpretation.
    """
    category = inquiry.get("category", "").lower()
    is_new   = inquiry.get("first_uae_store", False)
    risk     = inquiry.get("risk_flag")

    # Derive tenant type from category keywords
    if any(k in category for k in ("f&b", "cafe", "restaurant", "dining", "food")):
        tenant_type = "f&b"
    elif any(k in category for k in ("sport", "outdoor", "fitness", "adventure")):
        tenant_type = "sports & outdoor"
    elif any(k in category for k in ("beauty", "skincare", "wellness", "cosmetic")):
        tenant_type = "lifestyle"
    elif any(k in category for k in ("fashion", "premium", "luxury", "accessories")):
        tenant_type = "premium retail"
    else:
        tenant_type = "general retail"

    # Derive financial profile from risk flag
    if risk in (None, ""):
        financial_profile = "strong"
    elif risk == "new_market_entrant":
        financial_profile = "moderate"
    else:
        financial_profile = "unknown"

    # Risk flags
    risk_flags = []
    if is_new:
        risk_flags.append("first_uae_store — parent guarantee required")
    if risk and risk not in (None, ""):
        risk_flags.append(risk)

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "tenant_type":           tenant_type,
            "category":              inquiry.get("category", ""),
            "size_min_sqm":          inquiry.get("size_min_sqm", 0),
            "size_max_sqm":          inquiry.get("size_max_sqm", 0),
            "preferred_mall":        inquiry.get("preferred_mall", ""),
            "preferred_zone":        inquiry.get("preferred_zone"),
            "priority":              inquiry.get("priority", "medium"),
            "financial_profile":     financial_profile,
            "first_uae_store":       is_new,
            "risk_flags":            risk_flags,
            "special_requirements":  [],
            "missing_information":   [],
            "lead_assessment":       (
                f"Grade {lead.get('lead_grade', '?')} tenant "
                f"(score: {lead.get('lead_score', 0):.2f}). "
                f"{' '.join(lead.get('signals_positive', [])[:2])}. "
                f"[Fallback — LLM interpretation unavailable]"
            ),
            "agent_assessment":      (
                f"{inquiry.get('brand_name', 'Tenant')} — {tenant_type}. "
                f"Priority: {inquiry.get('priority', 'medium')}. "
                f"[Fallback — LLM assessment unavailable]"
            ),
        }
    }


# ── Node 2 — Unit Match ───────────────────────────────────────────────────────

def fallback_node_unit_match(state: dict, scored_units: list, inquiry: dict) -> dict:
    """
    Fallback for node_unit_match.
    Returns top-scored units directly from calculate_match_score() results.
    Uses demand_signal from vacancy_plan as rationale text.
    No LLM re-ranking or narrative.
    """
    recommended = []
    for unit in scored_units[:3]:
        sc = unit.get("_scoring", {})
        recommended.append({
            "unit_id":              unit.get("unit_id", ""),
            "mall":                 unit.get("mall_name", ""),
            "floor":                unit.get("floor", ""),
            "zone":                 unit.get("zone", ""),
            "size_sqm":             unit.get("sqm", 0),
            "status":               unit.get("status", ""),
            "base_rent_aed_sqm":    unit.get("base_rent_sqm", 0),
            "match_score":          sc.get("match_score", 0),
            "lead_score":           sc.get("lead_score", 0),
            "vacancy_demand_score": sc.get("vacancy_demand_score", 0),
            "category_match":       sc.get("category_match", False),
            "demand_signal":        sc.get("demand_signal", "No demand data available"),
            "rationale":            (
                sc.get("demand_signal", "") or
                f"Match score: {sc.get('match_score', 0):.2f}. "
                f"[Fallback — LLM rationale unavailable]"
            ),
        })

    top_score = scored_units[0]["_scoring"]["match_score"] if scored_units else 0
    warning   = f"Best match scores {top_score:.2f}." if top_score < 0.50 else ""

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "recommended_units":      recommended,
            "units_excluded":         [],
            "recommendation_summary": (
                f"Top match: {recommended[0]['unit_id']} "
                f"(score {top_score:.2f}). "
                f"{warning} [Fallback — LLM ranking unavailable]"
                if recommended else
                "No units available. [Fallback]"
            ),
        }
    }


# ── Node 3 — HoT Draft ───────────────────────────────────────────────────────

def fallback_node_hot_draft(
    state:       dict,
    unit:        dict,
    pricing:     dict,
    lease_start: str,
    inquiry:     dict,
) -> dict:
    """
    Fallback for node_hot_draft.
    Generates HoT using pricing rule minimum rent values directly.
    Fit-out set to pricing rule maximum.
    Security deposit set to 3 months.
    Escalation set to pricing rule default.
    No LLM narrative — special_conditions and terms_requiring_judgment left empty.
    """
    # Use pricing rule minimums — conservative safe values
    base_rent_sqm  = float(pricing.get("base_rent_sqm_min", unit.get("base_rent_sqm", 0)))
    sqm            = float(unit.get("sqm", 0))
    fit_out_months = int(pricing.get("max_fit_out_months", 3))
    rent_free      = int(pricing.get("rent_free_months_allowed", 0))
    escalation_pct = float(pricing.get("annual_escalation_pct", 5.0))
    deposit_months = int(pricing.get("security_deposit_months", 3))
    duration_years = 3   # standard lease duration

    # Date calculations
    lease_start_dt  = datetime.strptime(lease_start[:10], "%Y-%m-%d")
    fit_out_end_dt  = lease_start_dt + relativedelta(months=fit_out_months) - relativedelta(days=1)
    rent_commence_dt = fit_out_end_dt + relativedelta(days=1) + relativedelta(months=rent_free)
    lease_end_dt    = lease_start_dt + relativedelta(years=duration_years) - relativedelta(days=1)

    # Financial calculations
    annual_rent      = round(base_rent_sqm * sqm, 2)
    monthly_rent     = round(annual_rent / 12, 2)
    security_deposit = round(monthly_rent * deposit_months, 2)
    fit_out_deposit  = round(monthly_rent * 2, 2)
    year2_rent       = round(annual_rent * (1 + escalation_pct / 100), 2)
    year3_rent       = round(year2_rent  * (1 + escalation_pct / 100), 2)

    service_charge   = float(unit.get("service_charge_sqm", 0))
    marketing_levy   = float(unit.get("marketing_levy_sqm", 0))
    total_occ_cost   = round(base_rent_sqm + service_charge + marketing_levy, 2)
    turnover_pct     = float(unit.get("turnover_rent_pct", 8))

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "tenant":                       inquiry.get("legal_entity_name", ""),
            "unit_id":                      unit.get("unit_id", ""),
            "mall":                         unit.get("mall_name", ""),
            "lease_start_date":             lease_start_dt.strftime("%Y-%m-%d"),
            "fit_out_months":               fit_out_months,
            "rent_commencement_date":       rent_commence_dt.strftime("%Y-%m-%d"),
            "lease_end_date":               lease_end_dt.strftime("%Y-%m-%d"),
            "lease_duration_years":         duration_years,
            "base_rent_aed_sqm":            base_rent_sqm,
            "annual_base_rent_aed":         annual_rent,
            "monthly_base_rent_aed":        monthly_rent,
            "service_charge_aed_sqm":       service_charge,
            "marketing_levy_aed_sqm":       marketing_levy,
            "total_occupancy_cost_aed_sqm": total_occ_cost,
            "security_deposit_aed":         security_deposit,
            "fit_out_deposit_aed":          fit_out_deposit,
            "rent_free_months":             rent_free,
            "annual_escalation_pct":        escalation_pct,
            "year_2_rent_aed":              year2_rent,
            "year_3_rent_aed":              year3_rent,
            "turnover_rent_pct":            turnover_pct,
            "turnover_rent_threshold_aed":  round(annual_rent * 2.5, 2),
            "special_conditions":           [],
            "terms_requiring_judgment":     ["[Fallback] LLM unavailable — all terms set to pricing rule minimums. Executive review required at Gate 1."],
        }
    }


# ── Node 4 — Document Request ─────────────────────────────────────────────────

def fallback_node_doc_request(
    state:        dict,
    tenant_type:  str,
    required_docs: list,
    inquiry:      dict,
) -> dict:
    """
    Fallback for node_doc_request.
    Returns the standard required document list for the tenant type.
    Tenant message populated with a generic template.
    No LLM covering message or specific flags.
    """
    brand = inquiry.get("brand_name", "Valued Tenant")
    message = _GENERIC_TENANT_MESSAGE.format(brand_name=brand)

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "document_checklist": required_docs,
            "flags":              [],
            "tenant_message":     message,
        }
    }


# ── Node 4b — Document Verification ──────────────────────────────────────────

def fallback_node_doc_verify(
    state:        dict,
    verification: dict,
    checklist:    list,
) -> dict:
    """
    Fallback for node_doc_verify.
    Returns raw database verification result without LLM summary.
    Overall outcome set directly from expired/missing document counts.
    """
    expired = verification.get("expired", [])
    missing = verification.get("missing", [])
    valid   = verification.get("valid", [])

    # Determine outcome from counts
    if expired and missing:
        outcome = "blocked"
        summary = f"{len(expired)} document(s) expired, {len(missing)} missing. Deal blocked pending resubmission."
        action  = "Request tenant to resubmit expired documents and provide missing items before proceeding."
    elif expired:
        outcome = "conditional_approval"
        summary = f"{len(expired)} document(s) expired. Conditional approval — renewal required."
        action  = "Request renewal of expired documents. LCM may approve conditionally at Gate 2."
    elif missing:
        outcome = "blocked"
        summary = f"{len(missing)} document(s) missing from required checklist."
        action  = "Request tenant to submit missing documents before Gate 2 review."
    else:
        outcome = "approved"
        summary = "All submitted documents appear valid. No issues detected."
        action  = "LCM may approve document package at Gate 2."

    # Build verification results list
    verification_results = []
    for doc in valid:
        verification_results.append({
            "doc_type": doc.get("doc_type", ""),
            "status":   "valid",
            "note":     f"Valid until {doc.get('expiry_date', 'N/A')}",
        })
    for doc in expired:
        verification_results.append({
            "doc_type": doc.get("doc_type", ""),
            "status":   "expired",
            "note":     f"Expired {doc.get('expiry_date', '')} — {doc.get('flag', 'renewal required')}",
        })
    for doc_type in missing:
        verification_results.append({
            "doc_type": doc_type,
            "status":   "missing",
            "note":     "Not submitted — required for this tenant type",
        })

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "verification_results": verification_results,
            "missing_documents":    missing,
            "overall_outcome":      outcome,
            "summary":              summary,
            "recommended_action":   action,
        }
    }


# ── Node 5 — Lease Generation ─────────────────────────────────────────────────

def fallback_node_lease_gen(
    state:      dict,
    calculated: dict,
    unit:       dict,
    inquiry:    dict,
    hot:        dict,
    checks:     list,
    passed:     bool,
) -> dict:
    """
    Fallback for node_lease_gen.
    Uses Python-calculated figures exclusively — these are already computed
    before the LLM call in node_lease_gen, so this fallback is mathematically
    identical to the LLM output for all critical fields.
    Non-calculated fields (permitted_use, signatory) use safe defaults.
    """
    year = datetime.now().year
    lease_number = f"MAF-LEASE-{year}-FALLBACK"

    lease_document = {
        "document_reference":          lease_number,
        "landlord":                    "Majid Al Futtaim Properties LLC",
        "tenant_legal_name":           inquiry.get("legal_entity_name", ""),
        "tenant_brand_name":           inquiry.get("brand_name", ""),
        "unit_id":                     unit.get("unit_id", ""),
        "mall":                        unit.get("mall_name", ""),
        "permitted_use":               (
            f"Retail use for {inquiry.get('category', 'general retail')} "
            f"under the brand name {inquiry.get('brand_name', '')}. "
            f"[Fallback — detailed permitted use clause requires LCM input]"
        ),
        # All critical fields from Python calculations — authoritative values
        "lease_start_date":            calculated["lease_start_date"],
        "fit_out_end_date":            calculated["fit_out_end_date"],
        "rent_commencement_date":      calculated["rent_commencement_date"],
        "lease_end_date":              calculated["lease_end_date"],
        "base_rent_aed_sqm":           calculated["base_rent_aed_sqm"],
        "annual_base_rent_aed":        calculated["annual_base_rent_aed"],
        "monthly_base_rent_aed":       calculated["monthly_base_rent_aed"],
        "security_deposit_aed":        calculated["security_deposit_aed"],
        "year_2_rent_aed":             calculated["year_2_rent_aed"],
        "year_3_rent_aed":             calculated["year_3_rent_aed"],
        # Derived fields
        "service_charge_annual_aed":   round(
            float(unit.get("service_charge_sqm", 0)) * float(unit.get("sqm", 0)), 2
        ),
        "marketing_levy_annual_aed":   round(
            float(unit.get("marketing_levy_sqm", 0)) * float(unit.get("sqm", 0)), 2
        ),
        "fit_out_deposit_aed":         round(calculated["monthly_base_rent_aed"] * 2, 2),
        "turnover_rent_pct":           float(unit.get("turnover_rent_pct", 8)),
        "turnover_rent_threshold_aed": round(calculated["annual_base_rent_aed"] * 2.5, 2),
        "signatory_tenant":            inquiry.get("contact_name", "Authorised Signatory"),
        "signatory_landlord":          "Leasing Director, MAF Properties",
    }

    # Build consistency check result from Python checks
    consistency_check = {
        "status":        "pass" if passed else "fail",
        "checks_run":    len(checks),
        "issues_found":  sum(1 for c in checks if not c.passed),
        "checks_detail": [{
            "field":       c.check_id,
            "hot_value":   "",
            "lease_value": c.detail,
            "result":      "pass" if c.passed else "fail",
            "note":        c.detail if not c.passed else "",
        } for c in checks],
    }

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "lease_document":   lease_document,
            "consistency_check": consistency_check,
        }
    }


# ── Node 6 — EJARI ───────────────────────────────────────────────────────────

def fallback_node_ejari(
    state:  dict,
    cert:   dict,
    filing: dict,
    unit:   dict,
    inquiry: dict,
    lease:  dict,
) -> dict:
    """
    Fallback for node_ejari.
    Uses the filing result from file_ejari() directly.
    Generates handoff note from template — no LLM narrative.
    """
    handoff = (
        f"Deal closed for {inquiry.get('brand_name', 'Tenant')} "
        f"at {unit.get('mall_name', 'MAF Mall')}, Unit {unit.get('unit_id', '')}. "
        f"EJARI registration: {cert.get('registration_number', 'N/A')}. "
        f"Lease commences {lease.get('rent_commencement_date', 'TBC')}. "
        f"Annual rent: AED {lease.get('annual_base_rent_aed', 0):,.0f}. "
        f"Please initiate tenant onboarding — fit-out period begins immediately. "
        f"[Fallback — LLM handoff narrative unavailable]"
    )

    return {
        "reasoning": _FALLBACK_NOTE,
        "output": {
            "ejari_certificate": cert,
            "deal_status":       "closed" if filing.get("success") else "failed",
            "handoff_note":      handoff,
        }
    }