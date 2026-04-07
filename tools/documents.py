"""
tools/documents.py

Document loading and verification logic.
Reads from data/documents.json and data/tenants.json.
Determines which documents are required, checks validity,
and flags expired or missing items for Gate 2 review.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load(filename: str) -> list | dict:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════
# REQUIRED DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════

def get_required_documents(tenant_type: str) -> list[str]:
    """
    Return the list of required documents for a given tenant type.
    tenant_type: 'standard_retail' | 'new_to_uae_brand' | 'f&b'
    """
    data = _load("documents.json")
    required = data.get("required_documents", {})

    # fallback to standard_retail if type not found
    return required.get(tenant_type, required.get("standard_retail", []))


def determine_tenant_type(inquiry: dict) -> str:
    """
    Derive document requirement type from the inquiry.
    """
    category = inquiry.get("category", "").lower()
    is_new   = inquiry.get("first_uae_store", False)

    if "f&b" in category or "cafe" in category or "restaurant" in category:
        return "f&b"
    if is_new:
        return "new_to_uae_brand"
    return "standard_retail"


# ══════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ══════════════════════════════════════════════════════════════════════════

def get_verification_scenario(inquiry_id: str) -> Optional[dict]:
    """
    Look up the pre-built verification scenario for this inquiry.
    Returns None if no scenario exists.
    """
    data = _load("documents.json")
    for scenario in data.get("verification_scenarios", []):
        if scenario["inquiry_id"] == inquiry_id:
            return scenario
    return None


def verify_documents(inquiry_id: str) -> dict:
    """
    Run document verification for a given inquiry.

    Returns a result dict:
    {
        "valid":    [...],   # list of valid doc dicts
        "expired":  [...],   # list of expired doc dicts
        "missing":  [...],   # list of missing doc type strings
        "outcome":  str,     # "approved" | "conditional_approval" | "blocked"
        "notes":    str,
        "all_clear": bool
    }
    """
    scenario = get_verification_scenario(inquiry_id)

    if not scenario:
        return {
            "valid":     [],
            "expired":   [],
            "missing":   [],
            "outcome":   "approved",
            "notes":     "No verification scenario found — assumed clean.",
            "all_clear": True
        }

    submitted   = scenario.get("documents_submitted", [])
    valid       = [d for d in submitted if d["status"] == "valid"]
    expired     = [d for d in submitted if d["status"] == "expired"]
    missing     = scenario.get("missing_documents", [])
    outcome     = scenario.get("gate_2_outcome", "approved")
    notes       = scenario.get("gate_2_notes", "")
    all_clear   = outcome == "approved" and not expired and not missing

    return {
        "valid":     valid,
        "expired":   expired,
        "missing":   missing,
        "outcome":   outcome,
        "notes":     notes,
        "all_clear": all_clear
    }


def is_document_expired(doc: dict) -> bool:
    """Check if a document's expiry date has passed."""
    expiry = doc.get("expiry_date")
    if not expiry:
        return False
    try:
        return datetime.strptime(expiry, "%Y-%m-%d") < datetime.today()
    except ValueError:
        return False


def check_poa_valid(inquiry_id: str) -> tuple[bool, str]:
    """
    Specifically check whether the Power of Attorney is valid.
    Returns (is_valid, message).
    """
    scenario = get_verification_scenario(inquiry_id)
    if not scenario:
        return True, "No scenario — assuming valid."

    for doc in scenario.get("documents_submitted", []):
        if doc["doc_type"] == "power_of_attorney":
            if doc["status"] == "expired":
                return False, (
                    f"PoA held by {doc.get('holder', 'unknown')} "
                    f"expired on {doc.get('expiry_date', 'unknown')}"
                )
            return True, f"PoA valid — holder: {doc.get('holder', 'unknown')}"

    return False, "Power of Attorney not submitted."


# ══════════════════════════════════════════════════════════════════════════
# TENANT DATA
# ══════════════════════════════════════════════════════════════════════════

def get_tenant_by_inquiry(inquiry_id: str) -> Optional[dict]:
    """Fetch tenant record matching an inquiry_id."""
    for tenant in _load("tenants.json"):
        if tenant.get("inquiry_id") == inquiry_id:
            return tenant
    return None


def get_tenant_by_entity(legal_entity_name: str) -> Optional[dict]:
    """Fetch tenant record by legal entity name (case-insensitive)."""
    name_lower = legal_entity_name.lower()
    for tenant in _load("tenants.json"):
        if tenant.get("legal_entity_name", "").lower() == name_lower:
            return tenant
    return None


# ══════════════════════════════════════════════════════════════════════════
# PRINT HELPERS
# ══════════════════════════════════════════════════════════════════════════

def print_document_report(result: dict, brand_name: str = ""):
    """Print a formatted document verification report to terminal."""
    print(f"\n  Document Verification Report" + (f" — {brand_name}" if brand_name else ""))
    print(f"  {'─'*45}")

    if result["valid"]:
        print("  Valid documents:")
        for d in result["valid"]:
            expiry = f"  (expires {d['expiry_date']})" if d.get("expiry_date") else ""
            print(f"    VALID   {d['doc_type']}{expiry}")

    if result["expired"]:
        print("\n  Expired documents:")
        for d in result["expired"]:
            print(f"    EXPIRED {d['doc_type']}  — expired: {d.get('expiry_date', 'unknown')}")
            if d.get("flag"):
                print(f"            {d['flag']}")

    if result["missing"]:
        print("\n  Missing documents:")
        for doc in result["missing"]:
            print(f"    MISSING {doc}")

    print(f"\n  Outcome : {result['outcome'].upper()}")
    print(f"  Notes   : {result['notes']}")
    print(f"  {'─'*45}")