# ============================================================================
# api/routers/properties.py — Properties router
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Endpoints:
#   GET  /properties                    — list all properties with optional filters
#   GET  /properties/{property_id}      — get property detail with full unit rows
#
# All DB access via get_conn() + dict_cursor() from db.py
# ============================================================================

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import get_conn, dict_cursor

router = APIRouter()


# ── GET /properties ───────────────────────────────────────────────────────────

@router.get("/")
def list_properties(
    status:  Optional[str] = Query(None, description="Filter by status: active | inactive"),
    country: Optional[str] = Query(None, description="Filter by country e.g. UAE, Oman, Bahrain"),
    city:    Optional[str] = Query(None, description="Filter by city e.g. Dubai, Sharjah"),
):
    """
    List all properties with optional filters.
    No filter → returns all properties (active + inactive).
    Pass status=active to get only active malls.

    Also returns unit counts per property (total, vacant, expiring_soon)
    so the frontend can show occupancy at a glance without a second request.
    """
    filters = []
    params  = []

    if status:
        filters.append("p.status = %s")
        params.append(status)
    if country:
        filters.append("p.address_country = %s")
        params.append(country)
    if city:
        filters.append("p.address_city = %s")
        params.append(city)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        SELECT
            p.property_id,
            p.code,
            p.name,
            p.address_city,
            p.address_region,
            p.address_country,
            p.status,
            p.ejari_applicable,
            p.rera_applicable,
            p.portfolio,
            p.management_company,
            p.created_at,
            -- unit counts
            COUNT(u.unit_id)                                            AS total_units,
            COUNT(u.unit_id) FILTER (WHERE u.status = 'vacant')        AS vacant_units,
            COUNT(u.unit_id) FILTER (WHERE u.status = 'expiring_soon') AS expiring_units,
            COUNT(u.unit_id) FILTER (WHERE u.status = 'signed_unoccupied') AS signed_units
        FROM properties p
        LEFT JOIN units u ON u.property_id = p.property_id
        {where}
        GROUP BY
            p.property_id, p.code, p.name,
            p.address_city, p.address_region, p.address_country,
            p.status, p.ejari_applicable, p.rera_applicable,
            p.portfolio, p.management_company, p.created_at
        ORDER BY
            p.address_country ASC,
            p.address_city ASC,
            p.name ASC
    """

    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(query, params)
        rows = cur.fetchall()

    return {"count": len(rows), "properties": rows}


# ── GET /properties/{property_id} ─────────────────────────────────────────────

@router.get("/{property_id}")
def get_property(property_id: str):
    """
    Get full property detail including:
    - All property fields
    - Full unit rows with vacancy plan data
    - Pricing rules configured for this property
    - Summary counts (total, vacant, expiring, occupancy rate)
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Main property row
        cur.execute("""
            SELECT *
            FROM properties
            WHERE property_id = %s
        """, (property_id,))
        prop = cur.fetchone()

        if not prop:
            raise HTTPException(
                status_code=404,
                detail=f"Property {property_id} not found"
            )

        # Full unit rows + vacancy plan data
        cur.execute("""
            SELECT
                u.unit_id,
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
                u.turnover_rent_pct,
                u.fit_out_allowance,
                u.typical_fit_out_months,
                u.last_tenant,
                u.availability_date,
                u.lease_expiry,
                u.category_fit,
                u.notes,
                u.created_at,
                -- vacancy plan fields
                vp.priority             AS vp_priority,
                vp.demand_category      AS vp_demand_category,
                vp.demand_score         AS vp_demand_score,
                vp.demand_signal        AS vp_demand_signal,
                vp.vacancy_days         AS vp_vacancy_days,
                vp.footfall_tier        AS vp_footfall_tier,
                vp.target_tenant_profile AS vp_target_tenant_profile,
                vp.scored_at            AS vp_scored_at
            FROM units u
            LEFT JOIN vacancy_plan vp ON u.unit_id = vp.unit_id
            WHERE u.property_id = %s
            ORDER BY
                u.floor ASC,
                u.unit_number ASC
        """, (property_id,))
        units = cur.fetchall()

        # Pricing rules for this property
        cur.execute("""
            SELECT
                rule_id,
                category,
                base_rent_sqm_min,
                base_rent_sqm_max,
                max_fit_out_months,
                rent_free_months_allowed,
                annual_escalation_pct,
                security_deposit_months
            FROM pricing_rules
            WHERE property_id = %s
            ORDER BY category ASC
        """, (property_id,))
        pricing_rules = cur.fetchall()

    # Build summary counts from unit rows
    total      = len(units)
    vacant     = sum(1 for u in units if u["status"] == "vacant")
    expiring   = sum(1 for u in units if u["status"] == "expiring_soon")
    occupied   = sum(1 for u in units if u["status"] in ("signed_unoccupied", "reserved_informally"))
    held       = sum(1 for u in units if u["status"] == "held_strategically")
    occupancy_rate = round((occupied / total * 100), 1) if total > 0 else 0.0

    summary = {
        "total_units":     total,
        "vacant":          vacant,
        "expiring_soon":   expiring,
        "occupied":        occupied,
        "held_strategic":  held,
        "occupancy_rate":  occupancy_rate,
        "pricing_rules_count": len(pricing_rules),
    }

    return {
        "property":      prop,
        "summary":       summary,
        "units":         units,
        "pricing_rules": pricing_rules,
    }