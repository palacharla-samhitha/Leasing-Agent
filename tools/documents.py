# ============================================================================
# tools/documents.py — Document checklist & verification
# Reads from the `documents` table. All rows return as dicts via RealDictCursor.
# ============================================================================

from db import get_conn, dict_cursor


REQUIRED_DOCS = [
    "trade_license",
    "vat_certificate",
    "emirates_id",
    "memorandum_of_association",
    "board_resolution",
]

OPTIONAL_DOCS = [
    "power_of_attorney",
    "parent_guarantee",
]


def get_documents_for_inquiry(inquiry_id: str) -> list[dict]:
    with get_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT * FROM documents WHERE inquiry_id = %s ORDER BY doc_type",
            (inquiry_id,),
        )
        return cur.fetchall()


def get_document_checklist(inquiry_id: str) -> dict:
    docs = get_documents_for_inquiry(inquiry_id)
    submitted = {d["doc_type"]: d for d in docs}

    expired, missing, warnings = [], [], []

    for req in REQUIRED_DOCS:
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


def verify_documents(inquiry_id: str) -> dict:
    checklist = get_document_checklist(inquiry_id)
    issues = (
        checklist["expired"]
        + [{"doc_type": m, "flag": "Document not submitted"} for m in checklist["missing"]]
        + checklist["warnings"]
    )
    return {
        "inquiry_id": inquiry_id,
        "passed": checklist["all_clear"],
        "issues": issues,
        "expired_count": len(checklist["expired"]),
        "missing_count": len(checklist["missing"]),
    }


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