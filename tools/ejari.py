"""
tools/ejari.py

EJARI filing simulation.
EJARI is the Dubai Land Department's mandatory tenancy contract
registration system. All Dubai commercial leases must be registered.

In POC mode: generates a reference number and simulates the filing.
In production: would call the EJARI portal REST API.
"""

import uuid
from datetime import datetime
from typing import Optional
from tools.yardi import get_mall_by_code, is_ejari_required


# ══════════════════════════════════════════════════════════════════════════
# EJARI ELIGIBILITY
# ══════════════════════════════════════════════════════════════════════════

def check_ejari_required(mall_code: str) -> tuple[bool, str]:
    """
    Determine whether EJARI registration is required for this mall.
    Returns (required: bool, reason: str).
    """
    mall = get_mall_by_code(mall_code)
    if not mall:
        return False, f"Mall {mall_code} not found."

    if mall.get("ejari_applicable"):
        return True, f"{mall['mall_name']} is in Dubai — EJARI mandatory."
    else:
        country = mall.get("country", "unknown")
        emirate = mall.get("emirate", country)
        return False, f"{mall['mall_name']} is in {emirate} — EJARI not applicable."


# ══════════════════════════════════════════════════════════════════════════
# REFERENCE GENERATION
# ══════════════════════════════════════════════════════════════════════════

def generate_ejari_reference(mall_code: str, inquiry_id: str) -> str:
    """
    Generate a mock EJARI reference number.
    Format: EJARI-DXB-{YEAR}-{MALL_CODE}-{SUFFIX}

    In production: returned by the EJARI portal API after successful submission.
    """
    year   = datetime.today().year
    suffix = inquiry_id.split("-")[-1]  # last 4 digits of inquiry ID
    return f"EJARI-DXB-{year}-{mall_code}-{suffix}"


# ══════════════════════════════════════════════════════════════════════════
# FILING
# ══════════════════════════════════════════════════════════════════════════

def file_ejari(
    mall_code: str,
    inquiry_id: str,
    legal_entity_name: str,
    unit_id: str,
    lease_start_date: str,
    lease_expiry_date: str,
    annual_rent_aed: float,
    kofax_doc_ref: str
) -> dict:
    """
    Simulate submitting a lease to the EJARI portal for registration.

    Returns a filing result dict:
    {
        "success":    bool,
        "ejari_ref":  str | None,
        "filed_at":   str,
        "message":    str
    }
    """
    required, reason = check_ejari_required(mall_code)

    if not required:
        print(f"  [EJARI] Not required — {reason}")
        return {
            "success":   True,
            "ejari_ref": None,
            "filed_at":  datetime.now().isoformat(),
            "message":   reason
        }

    # Validate required fields before filing
    missing_fields = []
    if not legal_entity_name: missing_fields.append("legal_entity_name")
    if not unit_id:            missing_fields.append("unit_id")
    if not lease_start_date:   missing_fields.append("lease_start_date")
    if not lease_expiry_date:  missing_fields.append("lease_expiry_date")
    if not annual_rent_aed:    missing_fields.append("annual_rent_aed")
    if not kofax_doc_ref:      missing_fields.append("kofax_doc_ref")

    if missing_fields:
        msg = f"EJARI filing failed — missing fields: {', '.join(missing_fields)}"
        print(f"  [EJARI] {msg}")
        return {
            "success":   False,
            "ejari_ref": None,
            "filed_at":  datetime.now().isoformat(),
            "message":   msg
        }

    # Simulate successful filing
    ejari_ref = generate_ejari_reference(mall_code, inquiry_id)
    filed_at  = datetime.now().isoformat()

    print(f"  [EJARI] Filing submitted for {legal_entity_name}")
    print(f"  [EJARI] Unit       : {unit_id}")
    print(f"  [EJARI] Lease term : {lease_start_date} → {lease_expiry_date}")
    print(f"  [EJARI] Annual rent: AED {annual_rent_aed:,.0f}")
    print(f"  [EJARI] Doc ref    : {kofax_doc_ref}")
    print(f"  [EJARI] Reference  : {ejari_ref}  ✓")

    return {
        "success":   True,
        "ejari_ref": ejari_ref,
        "filed_at":  filed_at,
        "message":   f"EJARI registration successful. Ref: {ejari_ref}"
    }


def get_ejari_certificate(ejari_ref: str) -> dict:
    """
    Simulate retrieving the EJARI certificate after filing.
    In production: poll the EJARI API until certificate is ready.
    """
    if not ejari_ref:
        return {"success": False, "certificate": None, "message": "No EJARI ref provided."}

    print(f"  [EJARI] Certificate retrieved for {ejari_ref}")
    return {
        "success":     True,
        "ejari_ref":   ejari_ref,
        "certificate": f"CERT-{ejari_ref}",
        "issued_at":   datetime.now().isoformat(),
        "message":     "Certificate ready."
    }