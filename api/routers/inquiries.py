# ============================================================================
# api/routers/inquiries.py — Inquiries router
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Endpoints:
#   GET    /inquiries                  — list all with filters
#   GET    /inquiries/{inquiry_id}     — get single inquiry + workflow status
#   POST   /inquiries                  — create new inquiry (manual entry)
#   PATCH  /inquiries/{inquiry_id}     — update inquiry fields
#   DELETE /inquiries/{inquiry_id}     — soft delete (sets status = cancelled)
#
# All DB access via get_conn() + dict_cursor() from db.py
# ============================================================================

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import get_conn, dict_cursor

router = APIRouter()


# ── Pydantic models ───────────────────────────────────────────────────────────

class InquiryCreate(BaseModel):
    """Fields required to create a new inquiry (manual entry)."""
    brand_name:         str
    legal_entity_name:  str
    channel:            str = "walk_in"         # partner_connect | broker_portal | whatsapp | walk_in | email
    category:           str
    contact_name:       Optional[str] = None
    contact_email:      Optional[str] = None
    contact_phone:      Optional[str] = None
    contact_role:       Optional[str] = None
    preferred_mall:     Optional[str] = None    # property_id e.g. "prop_MOE"
    preferred_zone:     Optional[str] = None
    size_min_sqm:       Optional[int] = None
    size_max_sqm:       Optional[int] = None
    target_opening:     Optional[str] = None    # "Q4 2026"
    first_uae_store:    bool = False
    priority:           str = "medium"          # high | medium | low


class InquiryUpdate(BaseModel):
    """All fields optional — only provided fields are updated (PATCH semantics)."""
    status:             Optional[str] = None
    priority:           Optional[str] = None
    risk_flag:          Optional[str] = None
    assigned_unit:      Optional[str] = None    # unit_id
    agent_note:         Optional[str] = None
    contact_name:       Optional[str] = None
    contact_email:      Optional[str] = None
    contact_phone:      Optional[str] = None
    preferred_mall:     Optional[str] = None
    preferred_zone:     Optional[str] = None
    size_min_sqm:       Optional[int] = None
    size_max_sqm:       Optional[int] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _generate_inquiry_id() -> str:
    """
    Generates next inquiry ID in format INQ-2026-XXXX.
    Reads the highest existing ID from DB to avoid collisions.
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT inquiry_id FROM inquiries
            WHERE inquiry_id LIKE 'INQ-2026-%'
            ORDER BY inquiry_id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            last_num = int(row["inquiry_id"].split("-")[-1])
            return f"INQ-2026-{str(last_num + 1).zfill(4)}"
        return "INQ-2026-0001"


# ── GET /inquiries ────────────────────────────────────────────────────────────

@router.get("/")
def list_inquiries(
    status:     Optional[str] = Query(None, description="Filter by status"),
    property:   Optional[str] = Query(None, description="Filter by preferred_mall (property_id)"),
    priority:   Optional[str] = Query(None, description="Filter by priority: high | medium | low"),
    date_from:  Optional[str] = Query(None, description="Filter received_at >= date (YYYY-MM-DD)"),
    date_to:    Optional[str] = Query(None, description="Filter received_at <= date (YYYY-MM-DD)"),
    limit:      int           = Query(20,   description="Number of results per page (default 20)"),
    offset:     int           = Query(0,    description="Number of results to skip (for next/prev)"),
):
    """
    List all inquiries with optional filters.
    Returns inquiry list with current workflow status.
    Paginated — use limit + offset for next/previous navigation.
    """
    filters = []
    params  = []

    if status:
        filters.append("i.status = %s")
        params.append(status)
    if property:
        filters.append("i.preferred_mall = %s")
        params.append(property)
    if priority:
        filters.append("i.priority = %s")
        params.append(priority)
    if date_from:
        filters.append("i.received_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("i.received_at <= %s")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        SELECT
            i.*,
            p.name  AS preferred_mall_name,
            u.unit_number AS assigned_unit_number,
            ls.lead_score,
            ls.lead_grade
        FROM inquiries i
        LEFT JOIN properties p  ON i.preferred_mall = p.property_id
        LEFT JOIN units u       ON i.assigned_unit   = u.unit_id
        LEFT JOIN lead_scores ls ON i.inquiry_id     = ls.inquiry_id
        {where}
        ORDER BY
            CASE i.priority
                WHEN 'high'   THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low'    THEN 3
            END,
            i.received_at DESC
        LIMIT %s OFFSET %s
    """

    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()

    return {
        "inquiries": rows,
        "pagination": {
            "limit":    limit,
            "offset":   offset,
            "returned": len(rows),
            "has_next": len(rows) == limit,   # if full page returned, likely more exist
            "has_prev": offset > 0,
        }
    }


# ── GET /inquiries/{inquiry_id} ───────────────────────────────────────────────

@router.get("/{inquiry_id}")
def get_inquiry(inquiry_id: str):
    """
    Get full inquiry detail including:
    - Lead score
    - Assigned unit
    - Documents status
    - Current workflow status
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Main inquiry row
        cur.execute("""
            SELECT
                i.*,
                p.name  AS preferred_mall_name,
                u.unit_number AS assigned_unit_number,
                u.floor AS assigned_unit_floor,
                u.sqm   AS assigned_unit_sqm
            FROM inquiries i
            LEFT JOIN properties p ON i.preferred_mall = p.property_id
            LEFT JOIN units u      ON i.assigned_unit   = u.unit_id
            WHERE i.inquiry_id = %s
        """, (inquiry_id,))
        inquiry = cur.fetchone()

        if not inquiry:
            raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

        # Lead score
        cur.execute("""
            SELECT lead_score, lead_grade, signals_positive, signals_negative, reasoning, scored_at
            FROM lead_scores
            WHERE inquiry_id = %s
        """, (inquiry_id,))
        lead_score = cur.fetchone()

        # Documents
        cur.execute("""
            SELECT document_id, doc_type, status, expiry_date, flag, submitted_at, verified_at
            FROM documents
            WHERE inquiry_id = %s
            ORDER BY doc_type
        """, (inquiry_id,))
        documents = cur.fetchall()

    return {
        "inquiry":    inquiry,
        "lead_score": lead_score,
        "documents":  documents,
    }


# ── POST /inquiries ───────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_inquiry(body: InquiryCreate):
    """
    Create a new inquiry via manual entry.
    Assigns a new inquiry_id and sets status = in_progress.
    """
    inquiry_id = _generate_inquiry_id()
    now = datetime.utcnow()

    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            INSERT INTO inquiries (
                inquiry_id, received_at, channel, status,
                brand_name, legal_entity_name,
                contact_name, contact_email, contact_phone, contact_role,
                category, preferred_mall, preferred_zone,
                size_min_sqm, size_max_sqm, target_opening,
                first_uae_store, priority, created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
        """, (
            inquiry_id, now, body.channel, "in_progress",
            body.brand_name, body.legal_entity_name,
            body.contact_name, body.contact_email, body.contact_phone, body.contact_role,
            body.category, body.preferred_mall, body.preferred_zone,
            body.size_min_sqm, body.size_max_sqm, body.target_opening,
            body.first_uae_store, body.priority, now,
        ))

    return {"inquiry_id": inquiry_id, "status": "in_progress", "created_at": now}


#UPDATE QUERY

@router.patch("/{inquiry_id}")
def update_inquiry(inquiry_id: str, body: InquiryUpdate):
    """
    Update specific fields on an inquiry.
    Only non-None fields in the request body are written to DB.
    """
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    set_clause = ", ".join([f"{col} = %s" for col in updates.keys()])
    values     = list(updates.values()) + [inquiry_id]

    with get_conn() as conn:
        cur = dict_cursor(conn)

        # Check exists
        cur.execute("SELECT inquiry_id FROM inquiries WHERE inquiry_id = %s", (inquiry_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

        cur.execute(
            f"UPDATE inquiries SET {set_clause} WHERE inquiry_id = %s",
            values
        )

    return {"inquiry_id": inquiry_id, "updated_fields": list(updates.keys())}


# ── DELETE /inquiries/{inquiry_id} ────────────────────────────────────────────

@router.delete("/{inquiry_id}")
def delete_inquiry(inquiry_id: str):
    """
    Soft delete — sets status = cancelled.
    Does NOT remove the row from the database (audit trail preserved).
    """
    with get_conn() as conn:
        cur = dict_cursor(conn)

        cur.execute("SELECT inquiry_id, status FROM inquiries WHERE inquiry_id = %s", (inquiry_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

        if row["status"] == "cancelled":
            raise HTTPException(status_code=400, detail="Inquiry is already cancelled")

        cur.execute(
            "UPDATE inquiries SET status = 'cancelled' WHERE inquiry_id = %s",
            (inquiry_id,)
        )

    return {"inquiry_id": inquiry_id, "status": "cancelled"}