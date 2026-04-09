# ============================================================================
# tools/documents.py — Document checklist & verification
# Reads from the `documents` table via RealDictCursor.
# Backward-compatible functions provided for nodes.py.
# ============================================================================

from db import get_conn, dict_cursor


REQUIRED_DOCS = {
    "standard_retail": [
        "trade_license",
        "vat_certificate",
        "emirates_id",
        "memorandum_of_association",
        "board_resolution",
    ],
    "new_to_uae_brand": [
        "trade_license",
        "vat_certificate",
        "emirates_id",
        "memorandum_of_association",
        "board_resolution",
        "parent_guarantee",
    ],
    "f&b": [
        "trade_license",
        "vat_certificate",
        "emirates_id",
        "memorandum_of_association",
        "board_resolution",
        "power_of_attorney",
    ],
}


# ── Tenant type & required docs ───────────────────────────────────────────────

def determine_tenant_type(inquiry: dict) -> str:
    """Derive document requirement type from the inquiry."""
    category = inquiry.get("category", "").lower()
    is_new = inquiry.get("first_uae_store", False)

    if "f&b" in category or "cafe" in category or "restaurant" in category:
        return "f&b"
    if is_new:
        return "new_to_uae_brand"
    return "standard_retail"


def get_required_documents(tenant_type: str) -> list[str]:
    """Return the list of required documents for a given tenant type."""
    return REQUIRED_DOCS.get(tenant_type, REQUIRED_DOCS["standard_retail"])


# ── DB reads ──────────────────────────────────────────────────────────────────

def get_documents_for_inquiry(inquiry_id: str) -> list[dict]:
    """Return all documents submitted for an inquiry."""
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM documents WHERE inquiry_id = %s ORDER BY doc_type",
            (inquiry_id,),
        )
        return cur.fetchall()


def get_verification_scenario(inquiry_id: str) -> dict | None:
    """
    Build a verification scenario dict from the documents table.
    Matches the shape nodes.py expects from the old JSON version.
    Returns None if no documents found for this inquiry.
    """
    docs = get_documents_for_inquiry(inquiry_id)
    if not docs:
        return None

    submitted = [d for d in docs if d["status"] != "missing"]
    missing = [d["doc_type"] for d in docs if d["status"] == "missing"]
    expired = [d for d in submitted if d["status"] == "expired"]
    valid = [d for d in submitted if d["status"] == "valid"]

    has_issues = bool(expired or missing)
    if not has_issues:
        outcome = "approved"
        notes = "All documents valid."
    elif expired and not missing:
        outcome = "conditional_approval"
        notes = f"{len(expired)} document(s) expired — renewal required."
    else:
        outcome = "blocked"
        notes = f"{len(missing)} document(s) missing, {len(expired)} expired."

    return {
        "inquiry_id": inquiry_id,
        "documents_submitted": submitted,
        "missing_documents": missing,
        "gate_2_outcome": outcome,
        "gate_2_notes": notes,
    }


# ── Verification ──────────────────────────────────────────────────────────────

def verify_documents(inquiry_id: str) -> dict:
    """
    Run document verification for a given inquiry.
    Returns result dict matching the shape nodes.py expects.
    """
    scenario = get_verification_scenario(inquiry_id)

    if not scenario:
        return {
            "valid": [],
            "expired": [],
            "missing": [],
            "outcome": "approved",
            "notes": "No documents found — assumed clean.",
            "all_clear": True,
        }

    submitted = scenario.get("documents_submitted", [])
    valid = [d for d in submitted if d["status"] == "valid"]
    expired = [d for d in submitted if d["status"] == "expired"]
    missing = scenario.get("missing_documents", [])
    outcome = scenario.get("gate_2_outcome", "approved")
    notes = scenario.get("gate_2_notes", "")
    all_clear = outcome == "approved" and not expired and not missing

    return {
        "valid": valid,
        "expired": expired,
        "missing": missing,
        "outcome": outcome,
        "notes": notes,
        "all_clear": all_clear,
    }


def get_document_checklist(inquiry_id: str) -> dict:
    """Build a checklist summary for an inquiry."""
    docs = get_documents_for_inquiry(inquiry_id)
    submitted = {d["doc_type"]: d for d in docs}
    required = REQUIRED_DOCS["standard_retail"]

    expired, missing, warnings = [], [], []

    for req in required:
        if req not in submitted:
            missing.append(req)
        elif submitted[req]["status"] == "expired":
            expired.append({
                "doc_type": req,
                "expiry_date": str(submitted[req].get("expiry_date", "")),
                "flag": submitted[req].get("flag") or "Document expired",
            })
        elif submitted[req]["status"] == "warning":
            warnings.append({
                "doc_type": req,
                "flag": submitted[req].get("flag") or "",
            })

    return {
        "inquiry_id": inquiry_id,
        "submitted": docs,
        "expired": expired,
        "missing": missing,
        "warnings": warnings,
        "all_clear": not expired and not missing and not warnings,
    }


# ── Writes ────────────────────────────────────────────────────────────────────

def save_document(doc: dict) -> str:
    """Insert a document record. Returns document_id."""
    cols = ", ".join(doc.keys())
    placeholders = ", ".join(["%s"] * len(doc))
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            f"INSERT INTO documents ({cols}) VALUES ({placeholders})",
            list(doc.values()),
        )
    return doc["document_id"]


def mark_document_verified(document_id: str, verified_by: str = "agent") -> bool:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            """
            UPDATE documents
               SET status = 'valid', verified_by = %s, verified_at = NOW()
             WHERE document_id = %s
            """,
            (verified_by, document_id),
        )
        return cur.rowcount == 1