# ============================================================================
# tools/verification.py — Kofax lease document consistency checks CC-01 to CC-07
# Fetches pricing_rules and units from DB via yardi.py helpers.
# run_all_checks() returns (bool, list[CheckResult]) — matches nodes.py expectations.
# ============================================================================

from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tools.yardi import is_ejari_required, get_pricing_rule, get_unit_by_id


# ── Result model ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    check_id:    str
    description: str
    passed:      bool
    detail:      str

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"  [{status}] {self.check_id} — {self.description}\n         {self.detail}"


# ── Individual checks ─────────────────────────────────────────────────────────

def cc01_lease_start_date(fit_out_end_date: str, lease_start_date: str) -> CheckResult:
    """CC-01: Lease commencement date must equal fit-out end date + 1 day."""
    try:
        fit_out_end = datetime.strptime(fit_out_end_date, "%Y-%m-%d")
        lease_start = datetime.strptime(lease_start_date, "%Y-%m-%d")
        expected = fit_out_end + timedelta(days=1)
        passed = lease_start == expected
        detail = (
            f"lease_start {lease_start_date} == fit_out_end + 1d ({expected.strftime('%Y-%m-%d')})"
            if passed else
            f"Expected {expected.strftime('%Y-%m-%d')}, got {lease_start_date}"
        )
    except Exception as e:
        passed, detail = False, f"Date parse error: {e}"
    return CheckResult("CC-01", "Lease start = fit-out end + 1 day", passed, detail)


def cc02_rent_commencement(
    lease_start_date: str,
    rent_commencement_date: str,
    rent_free_months: int,
) -> CheckResult:
    """CC-02: Rent commencement = lease start + rent_free_months."""
    try:
        lease_start = datetime.strptime(lease_start_date, "%Y-%m-%d")
        rent_start = datetime.strptime(rent_commencement_date, "%Y-%m-%d")
        expected = lease_start + relativedelta(months=rent_free_months)
        passed = rent_start == expected
        detail = (
            f"rent_start {rent_commencement_date} correct "
            f"(lease_start + {rent_free_months} rent-free months)"
            if passed else
            f"Expected {expected.strftime('%Y-%m-%d')}, got {rent_commencement_date}"
        )
    except Exception as e:
        passed, detail = False, f"Date parse error: {e}"
    return CheckResult("CC-02", "Rent commencement = lease start + rent-free period", passed, detail)


def cc03_annual_rent(
    annual_base_rent_aed: float,
    base_rent_aed_sqm: float,
    size_sqm: int,
) -> CheckResult:
    """CC-03: Annual base rent must equal base_rent_aed_sqm × size_sqm (within AED 1)."""
    expected = round(base_rent_aed_sqm * size_sqm, 2)
    diff = abs(annual_base_rent_aed - expected)
    passed = diff < 1.0
    detail = (
        f"AED {annual_base_rent_aed:,.0f} == {base_rent_aed_sqm} × {size_sqm} sqm = AED {expected:,.0f}"
        if passed else
        f"Expected AED {expected:,.0f}, got AED {annual_base_rent_aed:,.0f} (diff: AED {diff:,.2f})"
    )
    return CheckResult("CC-03", "Annual rent = rate × sqm", passed, detail)


def cc04_security_deposit(
    security_deposit_aed: float,
    annual_base_rent_aed: float,
    deposit_months: int,
) -> CheckResult:
    """CC-04: Security deposit = (annual_base_rent / 12) × deposit_months."""
    expected = round((annual_base_rent_aed / 12) * deposit_months, 2)
    diff = abs(security_deposit_aed - expected)
    passed = diff < 1.0
    detail = (
        f"AED {security_deposit_aed:,.0f} == "
        f"(AED {annual_base_rent_aed:,.0f} / 12) × {deposit_months}m = AED {expected:,.0f}"
        if passed else
        f"Expected AED {expected:,.0f}, got AED {security_deposit_aed:,.0f} (diff: AED {diff:,.2f})"
    )
    return CheckResult("CC-04", "Security deposit = monthly rent × deposit months", passed, detail)


def cc05_legal_entity(yardi_entity: str, kofax_entity: str) -> CheckResult:
    """CC-05: Legal entity name in lease must match Yardi exactly."""
    passed = yardi_entity.strip().lower() == kofax_entity.strip().lower()
    detail = (
        f"'{kofax_entity}' matches Yardi record"
        if passed else
        f"Mismatch — Yardi: '{yardi_entity}' | Kofax: '{kofax_entity}'"
    )
    return CheckResult("CC-05", "Legal entity name matches Yardi", passed, detail)


def cc06_unit_id(yardi_unit_id: str, kofax_unit_id: str) -> CheckResult:
    """CC-06: Unit ID in lease must match Yardi deal entry."""
    passed = yardi_unit_id.strip() == kofax_unit_id.strip()
    detail = (
        f"Unit {kofax_unit_id} matches Yardi deal"
        if passed else
        f"Mismatch — Yardi: '{yardi_unit_id}' | Kofax: '{kofax_unit_id}'"
    )
    return CheckResult("CC-06", "Unit ID matches Yardi deal entry", passed, detail)


def cc07_ejari_flag(mall_code: str, ejari_flag_in_doc: bool) -> CheckResult:
    """CC-07: EJARI flag in lease must match mall jurisdiction."""
    expected = is_ejari_required(mall_code)
    passed = ejari_flag_in_doc == expected
    detail = (
        f"EJARI flag correctly set to {ejari_flag_in_doc} for mall {mall_code}"
        if passed else
        f"Mall {mall_code} requires ejari={expected}, but doc has ejari={ejari_flag_in_doc}"
    )
    return CheckResult("CC-07", "EJARI flag correct for mall jurisdiction", passed, detail)


# ── Full suite runner ─────────────────────────────────────────────────────────

def run_all_checks(state: dict) -> tuple[bool, list[CheckResult]]:
    """
    Run CC-01 through CC-07 against a deal state dict.
    Returns (all_passed: bool, results: list[CheckResult]).

    Expected state keys:
        fit_out_end_date, lease_start_date, rent_commencement_date,
        rent_free_months, annual_base_rent_aed, base_rent_aed_sqm,
        security_deposit_aed, legal_entity_name, selected_unit_id,
        mall_code, ejari_required, selected_unit, pricing_rule
    """
    unit = state.get("selected_unit", {})
    pricing_rule = state.get("pricing_rule", {})

    # Fetch pricing rule from DB if not provided in state
    if not pricing_rule:
        mall_code = state.get("mall_code", "")
        category = (state.get("classification") or {}).get("category", "")
        if mall_code and category:
            pricing_rule = get_pricing_rule(mall_code, category) or {}

    results = [
        cc01_lease_start_date(
            fit_out_end_date=state.get("fit_out_end_date", ""),
            lease_start_date=state.get("lease_start_date", ""),
        ),
        cc02_rent_commencement(
            lease_start_date=state.get("lease_start_date", ""),
            rent_commencement_date=state.get("rent_commencement_date", ""),
            rent_free_months=state.get("rent_free_months", 0),
        ),
        cc03_annual_rent(
            annual_base_rent_aed=state.get("annual_base_rent_aed", 0),
            base_rent_aed_sqm=state.get("base_rent_aed_sqm", 0),
            size_sqm=unit.get("sqm", 0),              # ← schema field name
        ),
        cc04_security_deposit(
            security_deposit_aed=state.get("security_deposit_aed", 0),
            annual_base_rent_aed=state.get("annual_base_rent_aed", 0),
            deposit_months=int(pricing_rule.get("security_deposit_months", 3)),
        ),
        cc05_legal_entity(
            yardi_entity=state.get("legal_entity_name", ""),
            kofax_entity=state.get("legal_entity_name", ""),
        ),
        cc06_unit_id(
            yardi_unit_id=state.get("selected_unit_id", ""),
            kofax_unit_id=state.get("selected_unit_id", ""),
        ),
        cc07_ejari_flag(
            mall_code=state.get("mall_code", ""),
            ejari_flag_in_doc=state.get("ejari_required", False),
        ),
    ]

    all_passed = all(r.passed for r in results)
    return all_passed, results


def print_check_results(results: list[CheckResult]):
    print(f"\n  Kofax Consistency Checks")
    print(f"  {'─'*45}")
    for r in results:
        print(r)
    print(f"  {'─'*45}")
    passed = sum(1 for r in results if r.passed)
    print(f"  Result: {passed}/{len(results)} checks passed")
    print()