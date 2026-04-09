# ============================================================================
# tools/yardi.py — Yardi Voyager simulation layer
# All reads/writes go to PostgreSQL via RealDictCursor.
# Schema field names follow the finalized SQL schema (single source of truth).
# Backward-compatible aliases provided for nodes.py.
# ============================================================================

from db import get_conn, dict_cursor


LEASABLE_STATUSES = {"vacant", "expiring_soon"}


# ── Properties ────────────────────────────────────────────────────────────────

def get_all_properties() -> list[dict]:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM properties WHERE status = 'active' ORDER BY name")
        return cur.fetchall()


def get_property(property_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM properties WHERE property_id = %s", (property_id,))
        return cur.fetchone()


def get_mall_by_code(mall_code: str) -> dict | None:
    """Alias — looks up property by short code (e.g. 'MOE')."""
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM properties WHERE code = %s", (mall_code,))
        return cur.fetchone()


def is_ejari_required(mall_code: str) -> bool:
    """Returns True if the mall requires EJARI registration (Dubai only)."""
    prop = get_mall_by_code(mall_code)
    if not prop:
        return False
    return bool(prop.get("ejari_applicable", False))


def is_rera_applicable(mall_code: str) -> bool:
    prop = get_mall_by_code(mall_code)
    if not prop:
        return False
    return bool(prop.get("rera_applicable", False))


# ── Units ─────────────────────────────────────────────────────────────────────

def get_available_units(
    size_min: float,
    size_max: float,
    category: str,
    preferred_mall: str | None = None,
) -> list[dict]:
    """
    Return available units matching size and category.
    Uses Postgres native TEXT[] @> operator for category matching.
    Falls back to all size-matched units if no category match found.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        q = """
            SELECT u.*, p.name AS mall_name, p.code AS mall_code,
                   p.ejari_applicable, p.rera_applicable
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE u.status IN ('vacant', 'expiring_soon')
              AND u.sqm BETWEEN %s AND %s
              AND u.category_fit @> ARRAY[%s]::TEXT[]
        """
        params = [size_min, size_max, category.lower()]

        if preferred_mall:
            q += " AND LOWER(p.name) LIKE %s"
            params.append(f"%{preferred_mall.lower()}%")

        q += " ORDER BY p.name, u.unit_id"
        cur.execute(q, params)
        results = cur.fetchall()

        if results:
            return results

        # Fallback — all size-matched available units
        q2 = """
            SELECT u.*, p.name AS mall_name, p.code AS mall_code,
                   p.ejari_applicable, p.rera_applicable
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE u.status IN ('vacant', 'expiring_soon')
              AND u.sqm BETWEEN %s AND %s
            ORDER BY p.name, u.unit_id
        """
        params2 = [size_min, size_max]
        if preferred_mall:
            q2 += " AND LOWER(p.name) LIKE %s"
            params2.append(f"%{preferred_mall.lower()}%")
        cur.execute(q2, params2)
        return cur.fetchall()


def get_all_units() -> list[dict]:
    """Return all units with their property info."""
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT u.*, p.name AS mall_name, p.code AS mall_code,
                   p.ejari_applicable, p.rera_applicable
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            ORDER BY p.name, u.unit_id
        """)
        return cur.fetchall()


def get_unit(unit_id: str) -> dict | None:
    """Return a single unit with property info."""
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT u.*, p.name AS mall_name, p.code AS mall_code,
                   p.ejari_applicable, p.rera_applicable
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE u.unit_id = %s
        """, (unit_id,))
        return cur.fetchone()


def get_unit_by_id(unit_id: str) -> dict | None:
    """Alias for get_unit() — backward compatible."""
    return get_unit(unit_id)


def update_unit_status(unit_id: str, new_status: str) -> bool:
    valid = {
        "vacant", "expiring_soon", "reserved_informally",
        "signed_unoccupied", "held_strategically", "occupied",
    }
    if new_status not in valid:
        raise ValueError(f"Invalid unit status: '{new_status}'")
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "UPDATE units SET status = %s WHERE unit_id = %s",
            (new_status, unit_id),
        )
        return cur.rowcount == 1


def lock_unit(unit_id: str) -> bool:
    """Mark a unit as reserved_informally (lock for deal)."""
    return update_unit_status(unit_id, "reserved_informally")


# ── Pricing ───────────────────────────────────────────────────────────────────

def get_pricing_rule(mall_code_or_property_id: str, category: str) -> dict | None:
    """
    Fetch pricing rule by mall code (e.g. 'MOE') or property_id (e.g. 'prop_MOE').
    Category match is case-insensitive.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)
        # Try property_id first, then code lookup
        cur.execute("""
            SELECT pr.* FROM pricing_rules pr
            JOIN properties p ON pr.property_id = p.property_id
            WHERE (pr.property_id = %s OR p.code = %s)
              AND LOWER(pr.category) = LOWER(%s)
        """, (mall_code_or_property_id, mall_code_or_property_id, category))
        return cur.fetchone()


def get_all_pricing_rules(property_id: str | None = None) -> list[dict]:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        if property_id:
            cur.execute(
                "SELECT * FROM pricing_rules WHERE property_id = %s ORDER BY category",
                (property_id,)
            )
        else:
            cur.execute("SELECT * FROM pricing_rules ORDER BY property_id, category")
        return cur.fetchall()


def validate_rent(proposed_rent: float, mall_code: str, category: str) -> tuple[bool, str]:
    rule = get_pricing_rule(mall_code, category)
    if not rule:
        return False, f"No pricing rule found for {mall_code} / {category}"
    lo = float(rule["base_rent_sqm_min"])
    hi = float(rule["base_rent_sqm_max"])
    if lo <= proposed_rent <= hi:
        return True, f"AED {proposed_rent} is within range ({lo}–{hi})"
    return False, f"AED {proposed_rent} is outside allowed range ({lo}–{hi})"


# ── Vacancy Plan ──────────────────────────────────────────────────────────────

def get_vacancy_plan(unit_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM vacancy_plan WHERE unit_id = %s", (unit_id,))
        return cur.fetchone()


# ── Inquiries ─────────────────────────────────────────────────────────────────

def get_inquiry(inquiry_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM inquiries WHERE inquiry_id = %s", (inquiry_id,))
        return cur.fetchone()


def get_inquiry_by_id(inquiry_id: str) -> dict | None:
    """Alias for get_inquiry()."""
    return get_inquiry(inquiry_id)


def get_all_inquiries(status: str | None = None) -> list[dict]:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        if status:
            cur.execute(
                "SELECT * FROM inquiries WHERE status = %s ORDER BY received_at DESC",
                (status,)
            )
        else:
            cur.execute("SELECT * FROM inquiries ORDER BY received_at DESC")
        return cur.fetchall()


def get_inquiries_by_status(status: str) -> list[dict]:
    return get_all_inquiries(status)


def update_inquiry_status(
    inquiry_id: str,
    new_status: str,
    assigned_unit: str | None = None,
) -> bool:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        if assigned_unit:
            cur.execute(
                "UPDATE inquiries SET status=%s, assigned_unit=%s WHERE inquiry_id=%s",
                (new_status, assigned_unit, inquiry_id),
            )
        else:
            cur.execute(
                "UPDATE inquiries SET status=%s WHERE inquiry_id=%s",
                (new_status, inquiry_id),
            )
        return cur.rowcount == 1


# ── Leases ────────────────────────────────────────────────────────────────────

def create_lease(lease_data: dict) -> str:
    cols = ", ".join(lease_data.keys())
    placeholders = ", ".join(["%s"] * len(lease_data))
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            f"INSERT INTO leases ({cols}) VALUES ({placeholders})",
            list(lease_data.values()),
        )
    return lease_data["lease_id"]


def get_lease(lease_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM leases WHERE lease_id = %s", (lease_id,))
        return cur.fetchone()


def get_lease_by_id(lease_id: str) -> dict | None:
    return get_lease(lease_id)


def get_lease_by_inquiry(inquiry_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM leases WHERE inquiry_id = %s", (inquiry_id,))
        return cur.fetchone()


def create_draft_lease(deal: dict) -> str:
    """Simulate creating a draft lease record. Returns a mock Yardi deal ID."""
    unit_id = deal.get("selected_unit_id", "UNK")
    yardi_deal_id = f"YRD-{unit_id}-2026-DRAFT"
    print(f"  [Yardi] Draft lease record created -> {yardi_deal_id}")
    return yardi_deal_id