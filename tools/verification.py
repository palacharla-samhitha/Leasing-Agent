# ============================================================================
# tools/verification.py — Kofax consistency checks (CC-01 through CC-07)
# Fetches pricing_rules and units from DB via yardi.py helpers.
# ============================================================================

from tools.yardi import get_unit, get_pricing_rule


def _cc01_rent_within_bounds(lease: dict, pricing: dict) -> dict:
    unit = get_unit(lease.get("unit_id", "")) or {}
    sqm = unit.get("sqm") or 1
    rent_sqm = (lease.get("base_rent_annual") or 0) / sqm
    lo = pricing.get("base_rent_sqm_min") or 0
    hi = pricing.get("base_rent_sqm_max") or float("inf")
    passed = lo <= rent_sqm <= hi
    return {
        "check_id": "CC-01",
        "name": "Rent within pricing bounds",
        "passed": passed,
        "detail": (
            f"Rent/sqm AED {rent_sqm:,.0f}. Allowed: {lo:,.0f}–{hi:,.0f}."
            if passed else
            f"FAIL: AED {rent_sqm:,.0f}/sqm outside range {lo:,.0f}–{hi:,.0f}."
        ),
    }


def _cc02_fit_out_period(lease: dict, pricing: dict) -> dict:
    actual = lease.get("fit_out_months") or 0
    allowed = pricing.get("max_fit_out_months") or 3
    passed = actual <= allowed
    return {
        "check_id": "CC-02",
        "name": "Fit-out period within limit",
        "passed": passed,
        "detail": (
            f"Fit-out: {actual} months (max {allowed})."
            if passed else
            f"FAIL: {actual} months exceeds max {allowed}."
        ),
    }


def _cc03_security_deposit(lease: dict, pricing: dict) -> dict:
    months = pricing.get("security_deposit_months") or 3
    annual = lease.get("base_rent_annual") or 0
    expected = (annual / 12) * months
    actual = lease.get("security_deposit") or 0
    passed = abs(actual - expected) <= expected * 0.01
    return {
        "check_id": "CC-03",
        "name": "Security deposit correct",
        "passed": passed,
        "detail": (
            f"Deposit AED {actual:,.0f} = {months}m × AED {annual/12:,.0f}/m. ✓"
            if passed else
            f"FAIL: Expected AED {expected:,.0f}, found AED {actual:,.0f}."
        ),
    }


def _cc04_turnover_rent(lease: dict, pricing: dict) -> dict:
    actual = lease.get("turnover_rent_pct") or 0
    ceiling = 10.0
    passed = actual <= ceiling
    return {
        "check_id": "CC-04",
        "name": "Turnover rent % within ceiling",
        "passed": passed,
        "detail": (
            f"Turnover rent: {actual}% (ceiling {ceiling}%)."
            if passed else
            f"FAIL: {actual}% exceeds {ceiling}% ceiling."
        ),
    }


def _cc05_escalation(lease: dict, pricing: dict) -> dict:
    actual = lease.get("annual_escalation_pct") or 0
    expected = float(pricing.get("annual_escalation_pct") or 5.0)
    passed = abs(actual - expected) < 0.1
    return {
        "check_id": "CC-05",
        "name": "Annual escalation rate correct",
        "passed": passed,
        "detail": (
            f"Escalation: {actual}% (expected {expected}%). ✓"
            if passed else
            f"FAIL: {actual}% doesn't match rule {expected}%."
        ),
    }


def _cc06_dates_consistent(lease: dict) -> dict:
    from datetime import date
    try:
        start = date.fromisoformat(str(lease.get("start_date", "")))
        commence = date.fromisoformat(str(lease.get("rent_commencement", "")))
        passed = commence >= start
        return {
            "check_id": "CC-06",
            "name": "Rent commencement after lease start",
            "passed": passed,
            "detail": (
                f"Start {start} → Commencement {commence}. ✓"
                if passed else
                f"FAIL: Commencement {commence} before start {start}."
            ),
        }
    except Exception as e:
        return {
            "check_id": "CC-06",
            "name": "Rent commencement after lease start",
            "passed": False,
            "detail": f"FAIL: Could not parse dates — {e}",
        }


def _cc07_unit_availability(lease: dict) -> dict:
    unit = get_unit(lease.get("unit_id", "")) or {}
    status = unit.get("status", "unknown")
    blocked = {"signed_unoccupied", "held_strategically", "occupied"}
    passed = status not in blocked
    return {
        "check_id": "CC-07",
        "name": "Unit available for leasing",
        "passed": passed,
        "detail": (
            f"Unit status '{status}' — available. ✓"
            if passed else
            f"FAIL: Unit status '{status}' — not available for leasing."
        ),
    }


def run_all_checks(lease: dict) -> dict:
    """
    Run CC-01 through CC-07 against a lease dict.
    Fetches pricing rule from DB automatically using property_id + category.
    """
    pricing = get_pricing_rule(
        lease.get("property_id", ""),
        lease.get("category", ""),
    ) or {}

    checks = [
        _cc01_rent_within_bounds(lease, pricing),
        _cc02_fit_out_period(lease, pricing),
        _cc03_security_deposit(lease, pricing),
        _cc04_turnover_rent(lease, pricing),
        _cc05_escalation(lease, pricing),
        _cc06_dates_consistent(lease),
        _cc07_unit_availability(lease),
    ]

    failed = [c for c in checks if not c["passed"]]
    return {
        "total_checks": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "all_passed": len(failed) == 0,
        "checks": checks,
    }