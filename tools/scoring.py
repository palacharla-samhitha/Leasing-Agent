# ============================================================================
# tools/scoring.py — Lead, vacancy demand, and match scoring
# Writes results to lead_scores table.
# Function signatures match what nodes.py expects.
# ============================================================================

from datetime import datetime, timezone
from db import get_conn, dict_cursor


# ── Lead Score ────────────────────────────────────────────────────────────────

def calculate_lead_score(inquiry: dict) -> dict:
    """
    Score a tenant inquiry 0.0–1.0. Grade A / B / C.
    Matches original scoring logic from dev1.
    Also upserts result to lead_scores table.
    """
    score = 0.0
    pos, neg = [], []

    # Established brand vs new entrant
    if not inquiry.get("first_uae_store", True):
        score += 0.20
        pos.append("Established brand with existing UAE presence")
    elif inquiry.get("first_uae_store"):
        score += 0.10
        pos.append("New market entrant — parent guarantee expected")

    # Risk flags
    risk = inquiry.get("risk_flag")
    if risk in (None, ""):
        score += 0.20
        pos.append("No risk flags — financial profile assumed strong")
    elif risk == "new_market_entrant":
        score += 0.10
        pos.append("New market entrant — moderate financial confidence")
        neg.append("New market entrant risk — no local trading history")
    elif risk == "documents_expired":
        score += 0.05
        neg.append("Expired documents — compliance risk until renewed")

    # Clear size requirement
    if inquiry.get("size_min_sqm") and inquiry.get("size_max_sqm"):
        score += 0.10
        pos.append(f"Clear size requirement: {inquiry['size_min_sqm']}–{inquiry['size_max_sqm']} sqm")

    # Channel quality
    ch = inquiry.get("channel", "")
    if ch in ("partner_connect", "broker_portal"):
        score += 0.10
        pos.append(f"Inquiry via {ch.replace('_', ' ').title()} — qualified channel")
    else:
        neg.append(f"Inquiry via {ch} — unqualified channel, may need vetting")

    # Risk flag penalty
    if risk and risk not in (None, "", "new_market_entrant"):
        score -= 0.10

    # Target opening timeline
    target = inquiry.get("target_opening", "")
    months_out = _estimate_months_to_opening(target)
    if months_out is not None and months_out >= 6:
        score += 0.15
        pos.append(f"Target opening {target} — {months_out} months out, healthy timeline")
    elif months_out is not None:
        neg.append(f"Target opening {target} — only {months_out} months out, tight timeline")

    score = round(max(0.0, min(1.0, score)), 2)
    grade = "A" if score >= 0.75 else ("B" if score >= 0.55 else "C")

    result = {
        "inquiry_id": inquiry.get("inquiry_id"),
        "lead_score": score,
        "lead_grade": grade,
        "signals_positive": pos,
        "signals_negative": neg,
        "reasoning": _build_lead_reasoning(inquiry, score, grade, pos, neg),
    }

    # Write to DB if inquiry_id present
    if result["inquiry_id"]:
        _upsert_lead_score(result)

    return result


def _upsert_lead_score(result: dict) -> None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            """
            INSERT INTO lead_scores
              (inquiry_id, lead_score, lead_grade,
               signals_positive, signals_negative, reasoning, scored_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (inquiry_id) DO UPDATE SET
              lead_score       = EXCLUDED.lead_score,
              lead_grade       = EXCLUDED.lead_grade,
              signals_positive = EXCLUDED.signals_positive,
              signals_negative = EXCLUDED.signals_negative,
              reasoning        = EXCLUDED.reasoning,
              scored_at        = NOW()
            """,
            (
                result["inquiry_id"],
                result["lead_score"],
                result["lead_grade"],
                result["signals_positive"],
                result["signals_negative"],
                result["reasoning"],
            ),
        )


def get_lead_score(inquiry_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM lead_scores WHERE inquiry_id = %s", (inquiry_id,)
        )
        return cur.fetchone()


# ── Vacancy Demand Score ──────────────────────────────────────────────────────

def calculate_vacancy_demand_score(unit: dict, inquiry: dict) -> dict:
    """
    Score a unit's demand urgency 0.0–1.0.
    Reads vacancy_plan from DB using unit_id.
    Falls back gracefully if no vacancy_plan exists.
    """
    from tools.yardi import get_vacancy_plan
    vp = get_vacancy_plan(unit.get("unit_id", "")) or {}

    score = 0.0

    # Footfall tier
    tier = vp.get("footfall_tier", "standard")
    if tier == "premium":
        score += 0.25
    elif tier == "high":
        score += 0.15

    # Category match
    demand_cat = vp.get("demand_category", "").lower()
    inq_cat = inquiry.get("category", "").lower()
    cat_match = _check_category_match(inq_cat, demand_cat)
    if cat_match:
        score += 0.30
    else:
        score -= 0.20

    # Priority unit
    priority = vp.get("priority", False)
    if priority:
        score += 0.25

    # Vacancy duration
    vac_days = vp.get("vacancy_days", 0) or 0
    if vac_days > 60:
        score += 0.20
    elif vac_days > 30:
        score += 0.10

    score = round(max(0.0, min(1.0, score)), 2)

    return {
        "vacancy_demand_score": score,
        "demand_signal": vp.get("demand_signal", "No demand data available"),
        "category_match": cat_match,
        "vacancy_days": vac_days,
        "priority_unit": priority,
        "footfall_tier": tier,
    }


# ── Match Score ───────────────────────────────────────────────────────────────

def calculate_match_score(inquiry: dict, unit: dict) -> dict:
    """
    Combined score = 40% lead quality + 60% vacancy demand.
    Returns full scoring dict that nodes.py reads for _scoring key.
    """
    lead = calculate_lead_score(inquiry)
    demand = calculate_vacancy_demand_score(unit, inquiry)

    match = round((lead["lead_score"] * 0.4) + (demand["vacancy_demand_score"] * 0.6), 2)

    if match >= 0.70:
        status = "strong"
        warning = None
    elif match >= 0.50:
        status = "moderate"
        warning = f"Moderate match ({match}) — executive judgment recommended at Gate 1"
    else:
        status = "weak"
        warning = (
            f"Weak match ({match}) — exec must justify proceeding. "
            f"Lead grade: {lead['lead_grade']}, demand score: {demand['vacancy_demand_score']}"
        )

    return {
        "match_score": match,
        "match_status": status,
        "lead_score": lead["lead_score"],
        "lead_grade": lead["lead_grade"],
        "vacancy_demand_score": demand["vacancy_demand_score"],
        "demand_signal": demand["demand_signal"],
        "category_match": demand["category_match"],
        "priority_unit": demand["priority_unit"],
        "footfall_tier": demand["footfall_tier"],
        "match_warning": warning,
        "lead_signals_positive": lead["signals_positive"],
        "lead_signals_negative": lead["signals_negative"],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _estimate_months_to_opening(target: str) -> int | None:
    now = datetime.now(timezone.utc)
    q_map = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}
    try:
        parts = target.strip().split()
        q = q_map.get(parts[0])
        yr = int(parts[1])
        if q is None:
            return None
        target_dt = datetime(yr, q, 1, tzinfo=timezone.utc)
        diff = (target_dt.year - now.year) * 12 + (target_dt.month - now.month)
        return max(0, diff)
    except (IndexError, ValueError):
        return None


def _check_category_match(inquiry_cat: str, demand_cat: str) -> bool:
    if not demand_cat or not inquiry_cat:
        return False
    inq_words = set(inquiry_cat.replace("&", " ").replace(",", " ").lower().split())
    dem_words = set(demand_cat.replace("&", " ").replace(",", " ").lower().split())
    stop = {"and", "the", "a", "of", "for", "in", "to", "or"}
    inq_words -= stop
    dem_words -= stop
    return len(inq_words & dem_words) >= 1


def _build_lead_reasoning(inq: dict, score: float, grade: str, pos: list, neg: list) -> str:
    brand = inq.get("brand_name", "Unknown")
    lines = [f"{brand} scores {score} (Grade {grade})."]
    if pos:
        lines.append("Strengths: " + "; ".join(pos) + ".")
    if neg:
        lines.append("Concerns: " + "; ".join(neg) + ".")
    return " ".join(lines)