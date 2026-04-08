from agent.state import get_initial_state
from agent.nodes import node_intake, node_unit_match, node_hot_draft
import json

inq = json.load(open("data/inquiries.json"))[0]
state = get_initial_state(inq)
state = node_intake(state)
state = node_unit_match(state)
print("Matched units:", len(state["matched_units"]))
print("Assigned unit:", inq.get("assigned_unit"))

from tools.yardi import get_unit_by_id
assigned = get_unit_by_id(inq.get("assigned_unit"))
print("Assigned unit found:", assigned is not None)
print("Top match unit_id:", state["matched_units"][0].get("unit_id") if state["matched_units"] else "NONE")
top = get_unit_by_id(state["matched_units"][0].get("unit_id")) if state["matched_units"] else None
print("Top match found in Yardi:", top is not None)

state = node_hot_draft(state)
print("HoT draft:", state.get("hot_draft") is not None)
print("Errors:", state["errors"])