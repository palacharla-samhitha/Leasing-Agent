"""
tools/test_tools.py

Quick smoke test for all 4 tool files.
Run from project root:
    python tools/test_tools.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib, tools.yardi as _y
print("yardi functions:", [f for f in dir(_y) if not f.startswith("_")])

from tools.yardi import (
    get_available_units, get_pricing_rule,
    is_ejari_required, validate_rent,
    get_inquiry_by_id, get_governing_law
)
from tools.documents import (
    verify_documents, check_poa_valid,
    print_document_report, determine_tenant_type,
    get_required_documents
)
from tools.ejari import (
    check_ejari_required, file_ejari,
    get_ejari_certificate
)
from tools.verification import run_all_checks, print_check_results

SEP = "\n" + "="*55


# ── 1. Yardi — unit matching ───────────────────────────────────────────────
print(SEP)
print("TEST 1 — Unit matching: Summit Gear Co.")
units = get_available_units(
    size_min=200, size_max=300,
    category="premium outdoor & adventure gear",
    preferred_mall="Mall of the Emirates"
)
print(f"  Units found: {len(units)}")
for u in units:
    pref = "PREFERRED" if u.get("_preferred") else ""
    print(f"  {u['unit_id']} | {u['mall']} | {u['size_sqm']}sqm | "
          f"AED {u['base_rent_aed_sqm']}/sqm | {u['status']} {pref}")


# ── 2. Yardi — pricing rule ────────────────────────────────────────────────
print(SEP)
print("TEST 2 — Pricing rule: MOE / sports & outdoor")
rule = get_pricing_rule("MOE", "sports & outdoor")
if rule:
    print(f"  Target rent : AED {rule['base_rent_aed_sqm_target']}/sqm")
    print(f"  Range       : AED {rule['base_rent_aed_sqm_min']} – {rule['base_rent_aed_sqm_max']}")
    print(f"  Fit-out     : {rule['standard_fit_out_months']} months (max {rule['max_fit_out_months']})")
    print(f"  RERA cap    : 5% (Dubai)")


# ── 3. Yardi — rent validation ─────────────────────────────────────────────
print(SEP)
print("TEST 3 — Rent validation")
for rent in [2600, 1500, 3800]:
    valid, msg = validate_rent(rent, "MOE", "sports & outdoor")
    print(f"  AED {rent}/sqm → {'OK' if valid else 'INVALID'} — {msg}")


# ── 4. Yardi — EJARI + governing law ──────────────────────────────────────
print(SEP)
print("TEST 4 — EJARI flag + governing law per mall")
for code in ["MOE", "CCA", "CCB"]:
    ejari = is_ejari_required(code)
    law   = get_governing_law(code)
    print(f"  {code} — EJARI: {ejari} | Law: {law}")


# ── 5. Documents — Summit Gear (conditional approval) ─────────────────────
print(SEP)
print("TEST 5 — Document verification: Summit Gear (INQ-2026-0041)")
result = verify_documents("INQ-2026-0041")
print_document_report(result, "Summit Gear Co.")

poa_valid, poa_msg = check_poa_valid("INQ-2026-0041")
print(f"  PoA check: {'VALID' if poa_valid else 'INVALID'} — {poa_msg}")


# ── 6. Documents — NovaSkin (blocked) ─────────────────────────────────────
print(SEP)
print("TEST 6 — Document verification: NovaSkin (INQ-2026-0037)")
result = verify_documents("INQ-2026-0037")
print_document_report(result, "NovaSkin")


# ── 7. Documents — Brew & Bloom (approved) ────────────────────────────────
print(SEP)
print("TEST 7 — Document verification: Brew & Bloom (INQ-2026-0039)")
inq = get_inquiry_by_id("INQ-2026-0039")
tenant_type = determine_tenant_type(inq)
required    = get_required_documents(tenant_type)
print(f"  Tenant type : {tenant_type}")
print(f"  Required docs: {', '.join(required)}")
result = verify_documents("INQ-2026-0039")
print_document_report(result, "Brew & Bloom")


# ── 8. EJARI — Dubai mall (should file) ───────────────────────────────────
print(SEP)
print("TEST 8 — EJARI filing: MOE (Dubai — should file)")
ejari_result = file_ejari(
    mall_code          = "MOE",
    inquiry_id         = "INQ-2026-0041",
    legal_entity_name  = "Summit Gear Trading LLC",
    unit_id            = "MOE-L1-042",
    lease_start_date   = "2026-08-16",
    lease_expiry_date  = "2029-08-15",
    annual_rent_aed    = 689000,
    kofax_doc_ref      = "KFX-2026-0041"
)
if ejari_result["success"] and ejari_result["ejari_ref"]:
    cert = get_ejari_certificate(ejari_result["ejari_ref"])
    print(f"  Certificate : {cert['certificate']}")


# ── 9. EJARI — Ajman mall (should skip) ───────────────────────────────────
print(SEP)
print("TEST 9 — EJARI filing: CCA (Ajman — should skip)")
file_ejari(
    mall_code="CCA", inquiry_id="INQ-2026-0099",
    legal_entity_name="Test Co.", unit_id="CCA-GF-003",
    lease_start_date="2026-09-01", lease_expiry_date="2028-09-01",
    annual_rent_aed=224000, kofax_doc_ref="KFX-2026-0099"
)


# ── 10. Verification — CC-01 to CC-07 ─────────────────────────────────────
print(SEP)
print("TEST 10 — Kofax consistency checks: Summit Gear deal")
mock_state = {
    "fit_out_end_date":        "2026-08-15",
    "lease_start_date":        "2026-08-16",
    "rent_commencement_date":  "2026-08-16",
    "rent_free_months":        0,
    "annual_base_rent_aed":    689000.0,
    "base_rent_aed_sqm":       2600.0,
    "selected_unit":           {"size_sqm": 265},
    "security_deposit_aed":    172250.0,
    "pricing_rule":            {"security_deposit_months": 3},
    "legal_entity_name":       "Summit Gear Trading LLC",
    "selected_unit_id":        "MOE-L1-042",
    "mall_code":               "MOE",
    "ejari_required":          True,
}
all_passed, results = run_all_checks(mock_state)
print_check_results(results)
print(f"  Overall: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")

print(SEP)
print("All tool tests complete.")