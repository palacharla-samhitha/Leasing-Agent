# ============================================================================
# tools/ejari.py — EJARI registration simulation
# Writes to ejari_registrations table via RealDictCursor.
# file_ejari() signature matches what nodes.py expects.
# ============================================================================

import uuid
from datetime import date, datetime
from db import get_conn, dict_cursor
from tools.yardi import is_ejari_required


# ── Reference generation ──────────────────────────────────────────────────────

def generate_ejari_reference(mall_code: str, inquiry_id: str) -> str:
    """
    Generate a mock EJARI reference number.
    Format: EJARI-DXB-{YEAR}-{MALL_CODE}-{SUFFIX}
    """
    year = datetime.today().year
    suffix = inquiry_id.split("-")[-1]
    return f"EJARI-DXB-{year}-{mall_code}-{suffix}"


# ── Eligibility ───────────────────────────────────────────────────────────────

def check_ejari_required(mall_code: str) -> tuple[bool, str]:
    """
    Returns (required: bool, reason: str).
    """
    required = is_ejari_required(mall_code)
    if required:
        return True, f"Mall {mall_code} is in Dubai — EJARI mandatory."
    return False, f"Mall {mall_code} is outside Dubai — EJARI not applicable."


# ── Filing ────────────────────────────────────────────────────────────────────

def file_ejari(
    mall_code: str,
    inquiry_id: str,
    legal_entity_name: str,
    unit_id: str,
    lease_start_date: str,
    lease_expiry_date: str,
    annual_rent_aed: float,
    kofax_doc_ref: str,
) -> dict:
    """
    Simulate submitting a lease to the EJARI portal.
    Writes to ejari_registrations table for Dubai properties.
    Returns result dict matching nodes.py expectations:
    {
        "success":   bool,
        "ejari_ref": str | None,
        "filed_at":  str,
        "message":   str
    }
    """
    required, reason = check_ejari_required(mall_code)

    if not required:
        return {
            "success": True,
            "ejari_ref": None,
            "filed_at": datetime.now().isoformat(),
            "message": reason,
        }

    # Validate required fields
    missing_fields = [
        f for f, v in {
            "legal_entity_name": legal_entity_name,
            "unit_id": unit_id,
            "lease_start_date": lease_start_date,
            "lease_expiry_date": lease_expiry_date,
            "annual_rent_aed": annual_rent_aed,
            "kofax_doc_ref": kofax_doc_ref,
        }.items() if not v
    ]

    if missing_fields:
        msg = f"EJARI filing failed — missing fields: {', '.join(missing_fields)}"
        return {
            "success": False,
            "ejari_ref": None,
            "filed_at": datetime.now().isoformat(),
            "message": msg,
        }

    ejari_ref = generate_ejari_reference(mall_code, inquiry_id)
    today = date.today().isoformat()
    filed_at = datetime.now().isoformat()

    # Look up property_id from mall_code
    from tools.yardi import get_mall_by_code
    prop = get_mall_by_code(mall_code)
    property_id = prop["property_id"] if prop else None

    # Write to DB
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            """
            INSERT INTO ejari_registrations
              (registration_number, lease_id, property_id, unit_id,
               tenant_legal_name, annual_rent, registration_date,
               status, message, filed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                ejari_ref,
                None,               # lease_id nullable for POC
                property_id,
                unit_id,
                legal_entity_name,
                annual_rent_aed,
                today,
                "Registered",
                "Successfully registered with Dubai Land Department",
            ),
        )

    return {
        "success": True,
        "ejari_ref": ejari_ref,
        "filed_at": filed_at,
        "message": f"EJARI registration successful. Ref: {ejari_ref}",
    }


def get_ejari_registration(lease_id: str) -> dict | None:
    """Retrieve an existing EJARI registration by lease_id."""
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM ejari_registrations WHERE lease_id = %s", (lease_id,)
        )
        return cur.fetchone()


def get_ejari_certificate(ejari_ref: str) -> dict:
    """Simulate retrieving the EJARI certificate after filing."""
    if not ejari_ref:
        return {"success": False, "certificate": None, "message": "No EJARI ref provided."}
    return {
        "success": True,
        "ejari_ref": ejari_ref,
        "certificate": f"CERT-{ejari_ref}",
        "issued_at": datetime.now().isoformat(),
        "message": "Certificate ready.",
    }