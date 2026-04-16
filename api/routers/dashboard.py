# ============================================================================
# api/routers/dashboard.py — Dashboard router
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Endpoints:
#   GET  /dashboard/summary     — active deals, pipeline value, occupancy rate
#   GET  /dashboard/pipeline    — inquiry counts per status stage
#   GET  /dashboard/units       — vacancy summary per property
#
# All DB access via get_conn() + dict_cursor() from db.py
# All endpoints are read-only — no writes happen here
# ============================================================================

from fastapi import APIRouter

from db import get_conn, dict_cursor

router = APIRouter()


# ── GET /dashboard/summary ────────────────────────────────────────────────────

@router.get("/summary")
def get_dashboard_summary():
    """
    Top-level dashboard numbers.

    Returns:
    - active_leases          — count of leases with status = active
    - active_lease_value_aed — total annual rent across all active leases
    - pipeline_inquiries     — count of inquiries currently in progress (not completed/cancelled)
    - pipeline_value_aed     — estimated annual rent value of in-progress inquiries
                               calculated as: avg base_rent_sqm × avg size_sqm per inquiry
    - total_units            — total units across all active properties
    - vacant_units           — units currently available to lease
    - expiring_units         — units expiring soon (available shortly)
    - occupancy_rate         — percentage of units that are occupied
    - properties_count       — total active properties
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Active leases + their total annual rent value
        # annual rent = sum of all RENT charge rows × 12 months
        cur.execute("""
            SELECT
                COUNT(DISTINCT l.lease_id)              AS active_leases,
                COALESCE(SUM(rc.amount * 12), 0)        AS active_lease_value_aed
            FROM leases l
            LEFT JOIN rent_charges rc
                ON  rc.lease_id = l.lease_id
                AND rc.code     = 'RENT'
            WHERE l.status = 'active'
        """)
        lease_stats = cur.fetchone()

        # In-progress inquiries pipeline
        # Pipeline value estimated from pricing rules:
        # mid-point of base_rent range × mid-point of size range per inquiry
        cur.execute("""
            SELECT
                COUNT(i.inquiry_id)     AS pipeline_inquiries,
                COALESCE(SUM(
                    -- mid-point rent × mid-point size × 12 months
                    ((pr.base_rent_sqm_min + pr.base_rent_sqm_max) / 2.0)
                    * ((i.size_min_sqm + i.size_max_sqm) / 2.0)
                ), 0)                   AS pipeline_value_aed
            FROM inquiries i
            LEFT JOIN pricing_rules pr
                ON  pr.property_id = i.preferred_mall
                AND pr.category    ILIKE '%' || split_part(i.category, ' ', 1) || '%'
            WHERE i.status NOT IN ('completed', 'cancelled')
        """)
        pipeline_stats = cur.fetchone()

        # Unit vacancy counts across all active properties
        cur.execute("""
            SELECT
                COUNT(u.unit_id)                                                AS total_units,
                COUNT(u.unit_id) FILTER (WHERE u.status = 'vacant')            AS vacant_units,
                COUNT(u.unit_id) FILTER (WHERE u.status = 'expiring_soon')     AS expiring_units,
                COUNT(u.unit_id) FILTER (WHERE u.status IN (
                    'signed_unoccupied', 'reserved_informally'
                ))                                                              AS occupied_units,
                COUNT(u.unit_id) FILTER (WHERE u.status = 'held_strategically') AS held_units
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE p.status = 'active'
        """)
        unit_stats = cur.fetchone()

        # Active properties count
        cur.execute("""
            SELECT COUNT(*) AS properties_count
            FROM properties
            WHERE status = 'active'
        """)
        prop_stats = cur.fetchone()

    # Compute occupancy rate from unit counts
    total_units   = unit_stats["total_units"] or 0
    occupied      = unit_stats["occupied_units"] or 0
    occupancy_rate = round((occupied / total_units * 100), 1) if total_units > 0 else 0.0

    return {
        # Leases
        "active_leases":           lease_stats["active_leases"],
        "active_lease_value_aed":  float(lease_stats["active_lease_value_aed"]),

        # Pipeline
        "pipeline_inquiries":      pipeline_stats["pipeline_inquiries"],
        "pipeline_value_aed":      float(pipeline_stats["pipeline_value_aed"]),

        # Units
        "total_units":             total_units,
        "vacant_units":            unit_stats["vacant_units"],
        "expiring_units":          unit_stats["expiring_units"],
        "occupied_units":          occupied,
        "held_units":              unit_stats["held_units"],
        "occupancy_rate":          occupancy_rate,

        # Properties
        "properties_count":        prop_stats["properties_count"],
    }


# ── GET /dashboard/pipeline ───────────────────────────────────────────────────

@router.get("/pipeline")
def get_pipeline():
    """
    Inquiry counts broken down by status.
    Shows exactly where every deal sits in the leasing lifecycle.

    Statuses:
        in_progress       — workflow started, running through agent nodes
        pending_gate_1    — paused at Gate 1, awaiting leasing exec approval
        blocked_documents — paused at Gate 2, documents incomplete or expired
        unit_matched      — paused at Gate 3, awaiting senior manager approval
        completed         — deal closed, EJARI filed
        cancelled         — inquiry soft-deleted or rejected

    Also returns total_active — all inquiries excluding completed and cancelled.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT
                status,
                COUNT(*) AS count
            FROM inquiries
            GROUP BY status
            ORDER BY
                CASE status
                    WHEN 'in_progress'       THEN 1
                    WHEN 'pending_gate_1'    THEN 2
                    WHEN 'blocked_documents' THEN 3
                    WHEN 'unit_matched'      THEN 4
                    WHEN 'completed'         THEN 5
                    WHEN 'cancelled'         THEN 6
                    ELSE 7
                END
        """)
        rows = cur.fetchall()

    # Build status map with zero-defaults for statuses that have no inquiries yet
    all_statuses = [
        "in_progress",
        "pending_gate_1",
        "blocked_documents",
        "unit_matched",
        "completed",
        "cancelled",
    ]
    counts = {s: 0 for s in all_statuses}
    for row in rows:
        counts[row["status"]] = row["count"]

    # Total active = everything except completed and cancelled
    total_active = sum(
        v for k, v in counts.items()
        if k not in ("completed", "cancelled")
    )

    return {
        "total_active": total_active,
        "pipeline":     counts,
    }


# ── GET /dashboard/units ──────────────────────────────────────────────────────

@router.get("/units")
def get_units_vacancy_summary():
    """
    Vacancy summary — one row per active property.

    Each row contains:
        property_id, property_name, city, country
        total_units, vacant, expiring_soon, occupied, held_strategically
        occupancy_rate  — percentage of units that are occupied
        avg_demand_score — average vacancy plan demand score across all units
                           (indicates how urgently units need to be filled)

    Ordered by vacant_units descending so properties with the most
    available space appear at the top.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT
                p.property_id,
                p.name                  AS property_name,
                p.code                  AS property_code,
                p.address_city          AS city,
                p.address_country       AS country,
                p.ejari_applicable,

                -- unit counts
                COUNT(u.unit_id)        AS total_units,

                COUNT(u.unit_id) FILTER (WHERE u.status = 'vacant')
                                        AS vacant_units,

                COUNT(u.unit_id) FILTER (WHERE u.status = 'expiring_soon')
                                        AS expiring_units,

                COUNT(u.unit_id) FILTER (WHERE u.status IN (
                    'signed_unoccupied', 'reserved_informally'
                ))                      AS occupied_units,

                COUNT(u.unit_id) FILTER (WHERE u.status = 'held_strategically')
                                        AS held_units,

                -- occupancy rate
                ROUND(
                    COUNT(u.unit_id) FILTER (WHERE u.status IN (
                        'signed_unoccupied', 'reserved_informally'
                    ))::numeric
                    / NULLIF(COUNT(u.unit_id), 0) * 100
                , 1)                    AS occupancy_rate,

                -- average demand score across all units in this property
                ROUND(
                    AVG(vp.demand_score)::numeric
                , 2)                    AS avg_demand_score

            FROM properties p
            LEFT JOIN units u
                ON  u.property_id = p.property_id
            LEFT JOIN vacancy_plan vp
                ON  vp.unit_id = u.unit_id
            WHERE p.status = 'active'
            GROUP BY
                p.property_id, p.name, p.code,
                p.address_city, p.address_country,
                p.ejari_applicable
            ORDER BY
                vacant_units DESC,
                p.address_country ASC,
                p.name ASC
        """)
        rows = cur.fetchall()

    # Portfolio-level totals across all properties
    total_vacant   = sum(r["vacant_units"]   or 0 for r in rows)
    total_expiring = sum(r["expiring_units"] or 0 for r in rows)
    total_occupied = sum(r["occupied_units"] or 0 for r in rows)
    total_units    = sum(r["total_units"]    or 0 for r in rows)
    portfolio_occupancy = round(
        (total_occupied / total_units * 100), 1
    ) if total_units > 0 else 0.0

    return {
        "portfolio": {
            "total_units":       total_units,
            "vacant_units":      total_vacant,
            "expiring_units":    total_expiring,
            "occupied_units":    total_occupied,
            "occupancy_rate":    portfolio_occupancy,
        },
        "count":      len(rows),
        "properties": rows,
    }