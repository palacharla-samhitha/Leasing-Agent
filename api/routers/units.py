# ============================================================================
# api/routers/units.py — Units router
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Endpoints:
#   GET   /units                        — list units with filters
#   GET   /units/{unit_id}              — get unit detail including vacancy plan
#   PATCH /units/{unit_id}/status       — update unit status
#
# All DB access via get_conn() + dict_cursor() from db.py
# ============================================================================

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import get_conn, dict_cursor

router = APIRouter()


# ── Pydantic models ───────────────────────────────────────────────────────────

class UnitStatusUpdate(BaseModel):
    """Only status is updatable via this endpoint."""
    status: str  # vacant | expiring_soon | reserved_informally | signed_unoccupied | held_strategically


# ── Valid status values ───────────────────────────────────────────────────────
VALID_STATUSES = {
    "vacant",
    "expiring_soon",
    "reserved_informally",
    "signed_unoccupied",
    "held_strategically",
}


# ── GET /units ────────────────────────────────────────────────────────────────

@router.get("/")
def list_units(
    property_id: Optional[str] = Query(None, description="Filter by property e.g. prop_MOE"),
    status:      Optional[str] = Query(None, description="Filter by status: vacant | expiring_soon | ..."),
    category:    Optional[str] = Query(None, description="Filter by category fit e.g. sports"),
    size_min:    Optional[int] = Query(None, description="Minimum size in sqm"),
    size_max:    Optional[int] = Query(None, description="Maximum size in sqm"),
):
    """
    List units with optional filters.
    Always joins vacancy_plan so demand score and footfall tier are included.
    """
    filters = []
    params  = []

    if property_id:
        filters.append("u.property_id = %s")
        params.append(property_id)

    if status:
        filters.append("u.status = %s")
        params.append(status)

    if category:
        # category_fit is a TEXT[] array — use ANY to search inside it
        filters.append("%s = ANY(u.category_fit)")
        params.append(category)

    if size_min:
        filters.append("u.sqm >= %s")
        params.append(size_min)

    if size_max:
        filters.append("u.sqm <= %s")
        params.append(size_max)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        SELECT
            u.unit_id,
            u.property_id,
            p.name          AS property_name,
            u.unit_number,
            u.floor,
            u.zone,
            u.unit_type,
            u.sqm,
            u.frontage_m,
            u.status,
            u.market_rent_monthly,
            u.base_rent_sqm,
            u.service_charge_sqm,
            u.marketing_levy_sqm,
            u.fit_out_allowance,
            u.typical_fit_out_months,
            u.availability_date,
            u.lease_expiry,
            u.category_fit,
            -- vacancy plan fields
            vp.priority         AS vp_priority,
            vp.demand_category  AS vp_demand_category,
            vp.demand_score     AS vp_demand_score,
            vp.demand_signal    AS vp_demand_signal,
            vp.vacancy_days     AS vp_vacancy_days,
            vp.footfall_tier    AS vp_footfall_tier,
            vp.target_tenant_profile AS vp_target_tenant_profile
        FROM units u
        JOIN properties p       ON u.property_id = p.property_id
        LEFT JOIN vacancy_plan vp ON u.unit_id   = vp.unit_id
        {where}
        ORDER BY
            COALESCE(vp.demand_score, 0) DESC,
            u.sqm ASC
    """

    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(query, params)
        rows = cur.fetchall()

    return {"count": len(rows), "units": rows}


# ── GET /units/{unit_id} ──────────────────────────────────────────────────────

@router.get("/{unit_id}")
def get_unit(unit_id: str):
    """
    Get full unit detail including:
    - All unit fields
    - Vacancy plan (demand score, footfall tier, target profile)
    - Current active lease on this unit (if any)
    - Pricing rules for this unit's property + category
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Main unit row + vacancy plan
        cur.execute("""
            SELECT
                u.*,
                p.name          AS property_name,
                p.code          AS property_code,
                p.ejari_applicable,
                vp.priority         AS vp_priority,
                vp.demand_category  AS vp_demand_category,
                vp.demand_score     AS vp_demand_score,
                vp.demand_signal    AS vp_demand_signal,
                vp.vacancy_days     AS vp_vacancy_days,
                vp.footfall_tier    AS vp_footfall_tier,
                vp.target_tenant_profile AS vp_target_tenant_profile,
                vp.scored_at        AS vp_scored_at
            FROM units u
            JOIN properties p         ON u.property_id = p.property_id
            LEFT JOIN vacancy_plan vp ON u.unit_id      = vp.unit_id
            WHERE u.unit_id = %s
        """, (unit_id,))
        unit = cur.fetchone()

        if not unit:
            raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found")

        # Current active lease on this unit (if any)
        cur.execute("""
            SELECT
                l.lease_id,
                l.lease_number,
                l.tenant_brand_name,
                l.tenant_legal_name,
                l.start_date,
                l.end_date,
                l.rent_commencement,
                l.status
            FROM leases l
            WHERE l.unit_id = %s
              AND l.status IN ('active', 'pending_signature')
            ORDER BY l.created_at DESC
            LIMIT 1
        """, (unit_id,))
        current_lease = cur.fetchone()

        # Pricing rules for this property + category
        cur.execute("""
            SELECT *
            FROM pricing_rules
            WHERE property_id = %s
        """, (unit["property_id"],))
        pricing_rules = cur.fetchall()

    return {
        "unit":          unit,
        "current_lease": current_lease,
        "pricing_rules": pricing_rules,
    }


# ── PATCH /units/{unit_id}/status ─────────────────────────────────────────────

@router.patch("/{unit_id}/status")
def update_unit_status(unit_id: str, body: UnitStatusUpdate):
    """
    Update the status of a unit.
    Valid values: vacant | expiring_soon | reserved_informally |
                  signed_unoccupied | held_strategically
    """
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of: {sorted(VALID_STATUSES)}"
        )

    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Check unit exists
        cur.execute(
            "SELECT unit_id, status FROM units WHERE unit_id = %s",
            (unit_id,)
        )
        unit = cur.fetchone()

        if not unit:
            raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found")

        if unit["status"] == body.status:
            raise HTTPException(
                status_code=400,
                detail=f"Unit is already '{body.status}'"
            )

        cur.execute("""
            UPDATE units
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE unit_id = %s
        """, (body.status, unit_id))

    return {
        "unit_id":    unit_id,
        "old_status": unit["status"],
        "new_status": body.status,
    }