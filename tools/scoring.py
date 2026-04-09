# ============================================================================
# tools/scoring.py — Lead, vacancy demand, and match scoring
# Writes results to lead_scores using Postgres ON CONFLICT upsert.
# TEXT[] columns (signals_positive, signals_negative) are native Postgres arrays.
# ============================================================================

from db import get_conn, dict_cursor


# ── Lead Score ────────────────────────────────────────────────────────────────

def calculate_lead_score(inquiry: dict) -> dict:
    """
    Score a tenant inquiry 0.0–1.0. Grade A / B / C.
    Weights: channel quality 20, UAE presence 20, risk flag 30, priority 10,
             size clarity 10, category defined 10.
    """
    score = 0.0
    pos, neg = [], []

    # Channel quality (20 pts)
    channel_scores = {
        "broker_portal": 20, "referral": 20,
        "partner_connect": 18, "direct_email": 15, "walk_in": 10,
    }
    score += channel_scores.get(inquiry.get("channel", ""), 10)
    if inquiry.get("channel") in ("broker_portal", "referral"):
        pos.append("High-quality acquisition channel")

    # First UAE store (−10 risk)
    if inquiry.get("first_uae_store"):
        score -= 10
        neg.append("First UAE store — higher onboarding risk")
    else:
        score += 10
        pos.append("Established UAE presence")

    # Risk flag (−20)
    if inquiry.get("risk_flag"):
        score -= 20
        neg.append(f"Risk flag: {inquiry['risk_flag']}")
    else:
        score += 10
        pos.append("No risk flags")

    # Priority signal
    score += {"high": 10, "medium": 5, "low": 0}.get(inquiry.get("priority", "medium"), 5)
    if inquiry.get("priority") == "high":
        pos.append("High-priority inquiry")

    # Size clarity
    size_min = inquiry.get("size_min_sqm", 0) or 0
    size_max = inquiry.get("size_max_sqm", 0) or 0
    if 0 < size_min < size_max and (size_max - size_min) <= 300:
        score += 10
        pos.append("Clear, specific size requirement")
    else:
        neg.append("Vague or very wide size range")

    # Category defined
    if inquiry.get("category"):
        score += 10
        pos.append("Category clearly defined")

    # Target opening noted
    if inquiry.get("target_opening"):
        pos.append(f"Target opening: {inquiry['target_opening']}")

    normalised = round(max(0.0, min(100.0, score)) / 100, 2)
    grade = "A" if normalised >= 0.75 else ("B" if normalised >= 0.50 else "C")

    result = {
        "inquiry_id": inquiry["inquiry_id"],
        "lead_score": normalised,
        "lead_grade": grade,
        "signals_positive": pos,
        "signals_negative": neg,
        "reasoning": (
            f"Score {normalised} ({grade}): "
            f"{len(pos)} positive signals, {len(neg)} negative signals."
        ),
    }
    _upsert_lead_score(result)
    return result


def _upsert_lead_score(result: dict) -> None:
    """
    Insert or update lead score.
    signals_positive / signals_negative are passed as Python lists —
    psycopg2 maps them natively to Postgres TEXT[].
    """
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
                result["signals_positive"],   # list → TEXT[] natively
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

def calculate_vacancy_demand_score(vacancy_plan: dict) -> dict:
    """
    Score a unit's demand urgency 0.0–1.0 based on vacancy_plan data.
    """
    score = 0.0
    signals = []

    days = vacancy_plan.get("vacancy_days") or 0
    if days > 180:
        score += 40; signals.append(f"Vacant {days} days — high urgency")
    elif days > 90:
        score += 25; signals.append(f"Vacant {days} days — moderate urgency")
    elif days > 30:
        score += 10; signals.append(f"Vacant {days} days — low urgency")

    # demand_score from Databricks ML model (0.0–1.0), weighted 40 pts
    demand_score = float(vacancy_plan.get("demand_score") or 0)
    score += demand_score * 40
    signals.append(f"Databricks demand score: {demand_score}")

    # footfall tier
    footfall_pts = {"premium": 20, "high": 12, "standard": 5}
    tier = vacancy_plan.get("footfall_tier", "standard")
    score += footfall_pts.get(tier, 5)
    signals.append(f"Footfall tier: {tier}")

    # strategic hold flag
    if vacancy_plan.get("priority") is False:
        score -= 20
        signals.append("Not a priority unit — demand score adjusted down")

    normalised = round(max(0.0, min(100.0, score)) / 100, 2)
    return {
        "unit_id": vacancy_plan.get("unit_id"),
        "vacancy_demand_score": normalised,
        "demand_grade": (
            "High" if normalised >= 0.7 else
            ("Medium" if normalised >= 0.4 else "Low")
        ),
        "signals": signals,
    }


# ── Match Score ───────────────────────────────────────────────────────────────

def calculate_match_score(lead_score: float, vacancy_demand_score: float) -> float:
    """
    Combined score = 40% lead quality + 60% vacancy demand urgency.
    MAF's priority is filling the right units, so demand is weighted higher.
    """
    return round((lead_score * 0.4) + (vacancy_demand_score * 0.6), 2)