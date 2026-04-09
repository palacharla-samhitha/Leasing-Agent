# ============================================================================
# tools/ejari.py — EJARI registration simulation
# Writes to ejari_registrations table. Reads back via RealDictCursor.
# ============================================================================

import uuid
from datetime import date
from db import get_conn, dict_cursor


def file_ejari(
    lease_id: str,
    property_id: str,
    unit_id: str,
    tenant_legal_name: str,
    annual_rent: float,
    ejari_applicable: bool,
) -> dict:
    """
    Simulate filing EJARI with Dubai Land Department.
    Non-Dubai properties skip registration and return success with no ref.
    """
    if not ejari_applicable:
        return {
            "filed": True,
            "ejari_applicable": False,
            "ejari_ref": None,
            "message": "Property is outside Dubai — EJARI registration not required.",
            "certificate": None,
        }

    reg_number = _generate_ejari_ref(unit_id)
    today = date.today().isoformat()

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
                reg_number, lease_id, property_id, unit_id,
                tenant_legal_name, annual_rent, today,
                "Registered",
                "Successfully registered with Dubai Land Department",
            ),
        )

    return {
        "filed": True,
        "ejari_applicable": True,
        "ejari_ref": reg_number,
        "message": "Successfully registered with Dubai Land Department",
        "certificate": {
            "registration_number": reg_number,
            "lease_id": lease_id,
            "unit_id": unit_id,
            "tenant_legal_name": tenant_legal_name,
            "annual_rent": annual_rent,
            "registration_date": today,
            "status": "Registered",
            "issuing_authority": "Dubai Land Department",
        },
    }


def get_ejari_registration(lease_id: str) -> dict | None:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM ejari_registrations WHERE lease_id = %s", (lease_id,)
        )
        return cur.fetchone()


def _generate_ejari_ref(unit_id: str) -> str:
    year = date.today().year
    suffix = str(uuid.uuid4().int)[:4]
    unit_clean = unit_id.replace("-", "").upper()
    return f"EJARI-{year}-{unit_clean}-{suffix}"