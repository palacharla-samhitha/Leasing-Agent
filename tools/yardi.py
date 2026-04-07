import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load(filename):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


LEASABLE_STATUSES = {"vacant", "expiring_soon"}


def get_available_units(size_min, size_max, category, preferred_mall=None):
    units = _load("units.json")
    results = []
    for unit in units:
        if unit["status"] not in LEASABLE_STATUSES:
            continue
        if not (size_min <= unit["size_sqm"] <= size_max):
            continue
        category_lower = category.lower()
        matched = any(
            c.lower() in category_lower or category_lower in c.lower()
            for c in unit.get("category_fit", [])
        )
        if not matched:
            continue
        unit = unit.copy()
        unit["_preferred"] = (
            preferred_mall is not None
            and unit["mall"].lower() == preferred_mall.lower()
        )
        results.append(unit)
    results.sort(key=lambda u: (not u["_preferred"], u["base_rent_aed_sqm"]))
    return results


def get_unit_by_id(unit_id):
    for unit in _load("units.json"):
        if unit["unit_id"] == unit_id:
            return unit
    return None


def get_all_units():
    return _load("units.json")


def lock_unit(unit_id):
    unit = get_unit_by_id(unit_id)
    if not unit:
        print(f"  [Yardi] Unit {unit_id} not found.")
        return False
    if unit["status"] not in LEASABLE_STATUSES:
        print(f"  [Yardi] Unit {unit_id} not available (status: {unit['status']}).")
        return False
    print(f"  [Yardi] Unit {unit_id} locked for deal.")
    return True


def get_pricing_rule(mall_code, category):
    data = _load("pricing.json")
    category_lower = category.lower()
    for rule in data["pricing_rules"]:
        if rule["mall_code"].lower() != mall_code.lower():
            continue
        rule_cat = rule["category"].lower()
        if rule_cat in category_lower or category_lower in rule_cat:
            return rule
    return None


def get_rera_cap():
    return _load("pricing.json")["rera_rent_increase_cap_pct"]


def validate_rent(proposed_rent, mall_code, category):
    rule = get_pricing_rule(mall_code, category)
    if not rule:
        return False, f"No pricing rule found for {mall_code} / {category}"
    lo = rule["base_rent_aed_sqm_min"]
    hi = rule["base_rent_aed_sqm_max"]
    if lo <= proposed_rent <= hi:
        return True, f"AED {proposed_rent} is within range ({lo}-{hi})"
    return False, f"AED {proposed_rent} is outside allowed range ({lo}-{hi})"


def get_mall_by_code(mall_code):
    for mall in _load("malls.json"):
        if mall["mall_code"].lower() == mall_code.lower():
            return mall
    return None


def get_all_malls():
    return _load("malls.json")


def is_ejari_required(mall_code):
    mall = get_mall_by_code(mall_code)
    if not mall:
        return False
    return mall.get("ejari_applicable", False)


def is_rera_applicable(mall_code):
    mall = get_mall_by_code(mall_code)
    if not mall:
        return False
    return mall.get("rera_applicable", False)


def get_governing_law(mall_code):
    mall = get_mall_by_code(mall_code)
    if not mall:
        return "UAE Law"
    country = mall.get("country", "UAE")
    laws = {
        "UAE":     "UAE Law / Dubai Courts",
        "Bahrain": "Bahrain Law / Bahrain Courts",
        "Oman":    "Oman Law / Muscat Courts",
        "Egypt":   "Egyptian Law / Cairo Courts",
        "KSA":     "KSA Law / Saudi Courts",
    }
    return laws.get(country, "UAE Law")


def get_all_leases():
    return _load("leases.json")


def get_lease_by_id(lease_id):
    for lease in _load("leases.json"):
        if lease["lease_id"] == lease_id:
            return lease
    return None


def get_lease_by_unit(unit_id):
    matches = [l for l in _load("leases.json") if l["unit_id"] == unit_id]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda l: l.get("lease_start_date", ""),
        reverse=True
    )[0]


def create_draft_lease(deal):
    unit_id = deal.get("selected_unit_id", "UNK")
    yardi_deal_id = f"YRD-{unit_id}-2026-DRAFT"
    print(f"  [Yardi] Draft lease record created -> {yardi_deal_id}")
    return yardi_deal_id


def get_all_inquiries():
    return _load("inquiries.json")


def get_inquiry_by_id(inquiry_id):
    for inq in _load("inquiries.json"):
        if inq["inquiry_id"] == inquiry_id:
            return inq
    return None


def get_inquiries_by_status(status):
    return [i for i in _load("inquiries.json") if i.get("status") == status]
