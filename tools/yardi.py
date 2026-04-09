# ============================================================================
# tools/yardi.py — Yardi Voyager simulation layer
# All reads/writes go to PostgreSQL. Function signatures unchanged.
# COPY THIS FILE TO: tools/yardi.py (replace entire contents)
# ============================================================================

from db import get_conn, dict_cursor


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


# ── Units ─────────────────────────────────────────────────────────────────────

def get_available_units(
    size_min: float,
    size_max: float,
    category: str,
    preferred_mall: str | None = None,
) -> list[dict]:
    """
    Return units that are vacant or expiring_soon within the size range.
    Category matching uses Postgres native array operator @>.
    Falls back to all size-matched units if no category match found.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Try category-aware query first (TEXT[] @> ARRAY[...])
        q = """
            SELECT u.*, p.name AS mall_name,
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

        # Fallback — return all size-matched available units
        q_fallback = """
            SELECT u.*, p.name AS mall_name,
                   p.ejari_applicable, p.rera_applicable
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE u.status IN ('vacant', 'expiring_soon')
              AND u.sqm BETWEEN %s AND %s
            ORDER BY p.name, u.unit_id
        """
        params_fb = [size_min, size_max]
        if preferred_mall:
            q_fallback += " AND LOWER(p.name) LIKE %s"
            params_fb.append(f"%{preferred_mall.lower()}%")

        cur.execute(q_fallback, params_fb)
        return cur.fetchall()


def get_unit(unit_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            """
            SELECT u.*, p.name AS mall_name,
                   p.ejari_applicable, p.rera_applicable
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE u.unit_id = %s
            """,
            (unit_id,),
        )
        return cur.fetchone()


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


# ── Inquiries ─────────────────────────────────────────────────────────────────

def get_inquiry(inquiry_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM inquiries WHERE inquiry_id = %s", (inquiry_id,)
        )
        return cur.fetchone()


def get_all_inquiries(status: str | None = None) -> list[dict]:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        if status:
            cur.execute(
                "SELECT * FROM inquiries WHERE status = %s ORDER BY received_at DESC",
                (status,),
            )
        else:
            cur.execute("SELECT * FROM inquiries ORDER BY received_at DESC")
        return cur.fetchall()


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


# ── Pricing ───────────────────────────────────────────────────────────────────

def get_pricing_rule(property_id: str, category: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            """
            SELECT * FROM pricing_rules
            WHERE property_id = %s AND LOWER(category) = LOWER(%s)
            """,
            (property_id, category),
        )
        return cur.fetchone()


def get_all_pricing_rules(property_id: str | None = None) -> list[dict]:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        if property_id:
            cur.execute(
                "SELECT * FROM pricing_rules WHERE property_id = %s ORDER BY category",
                (property_id,),
            )
        else:
            cur.execute("SELECT * FROM pricing_rules ORDER BY property_id, category")
        return cur.fetchall()


# ── Vacancy Plan ──────────────────────────────────────────────────────────────

def get_vacancy_plan(unit_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM vacancy_plan WHERE unit_id = %s", (unit_id,)
        )
        return cur.fetchone()


# ── Leases ────────────────────────────────────────────────────────────────────

def create_lease(lease_data: dict) -> str:
    """Insert a new lease record. Returns the lease_id."""
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


def get_lease_by_inquiry(inquiry_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM leases WHERE inquiry_id = %s", (inquiry_id,)
        )
        return cur.fetchone()