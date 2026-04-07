# agent/graph.py
# LangGraph graph definition for the AI Leasing Agent
# Wires all nodes together and defines human interrupt gates

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import LeasingAgentState
from agent.nodes import (
    node_intake,
    node_unit_match,
    node_hot_draft,
    node_doc_request,
    node_doc_verify,
    node_lease_gen,
    node_ejari,
)


# ── Routing functions ─────────────────────────────────────────────────────────
# These decide which node to go to next based on the gate decision

def route_gate_1(state: LeasingAgentState) -> str:
    """After Gate 1 — approve goes forward, reject loops back to unit match."""
    decision = state.get("gate_decision")
    if decision == "reject":
        return "node_unit_match"
    return "node_doc_request"


def route_gate_2(state: LeasingAgentState) -> str:
    """After Gate 2 — approve goes forward, reject loops back to doc request."""
    decision = state.get("gate_decision")
    if decision == "reject":
        return "node_doc_request"
    return "node_lease_gen"


def route_gate_3(state: LeasingAgentState) -> str:
    """After Gate 3 — approve goes forward, reject loops back to lease gen."""
    decision = state.get("gate_decision")
    if decision == "reject":
        return "node_lease_gen"
    return "node_ejari"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph():
    """
    Builds and compiles the LangGraph leasing agent graph.
    Returns a compiled graph ready to run.
    
    Human gates are implemented as interrupts BEFORE the gate nodes.
    The graph pauses at each gate, surfaces state to Streamlit,
    waits for human input, then resumes.
    """

    # Initialise the graph with our state type
    builder = StateGraph(LeasingAgentState)

    # ── Add all nodes ─────────────────────────────────────────────────────────
    builder.add_node("node_intake", node_intake)
    builder.add_node("node_unit_match", node_unit_match)
    builder.add_node("node_hot_draft", node_hot_draft)
    builder.add_node("gate_1", lambda state: state)       # passthrough — human decides
    builder.add_node("node_doc_request", node_doc_request)
    builder.add_node("node_doc_verify", node_doc_verify)
    builder.add_node("gate_2", lambda state: state)       # passthrough — human decides
    builder.add_node("node_lease_gen", node_lease_gen)
    builder.add_node("gate_3", lambda state: state)       # passthrough — human decides
    builder.add_node("node_ejari", node_ejari)

    # ── Set entry point ───────────────────────────────────────────────────────
    builder.set_entry_point("node_intake")

    # ── Add edges ─────────────────────────────────────────────────────────────
    # Straight edges — no branching
    builder.add_edge("node_intake", "node_unit_match")
    builder.add_edge("node_unit_match", "node_hot_draft")
    builder.add_edge("node_hot_draft", "gate_1")
    builder.add_edge("node_doc_request", "node_doc_verify")
    builder.add_edge("node_doc_verify", "gate_2")
    builder.add_edge("node_lease_gen", "gate_3")
    builder.add_edge("node_ejari", END)

    # ── Conditional edges — gate routing ──────────────────────────────────────
    builder.add_conditional_edges(
        "gate_1",
        route_gate_1,
        {
            "node_unit_match": "node_unit_match",
            "node_doc_request": "node_doc_request",
        }
    )

    builder.add_conditional_edges(
        "gate_2",
        route_gate_2,
        {
            "node_doc_request": "node_doc_request",
            "node_lease_gen": "node_lease_gen",
        }
    )

    builder.add_conditional_edges(
        "gate_3",
        route_gate_3,
        {
            "node_lease_gen": "node_lease_gen",
            "node_ejari": "node_ejari",
        }
    )

    # ── Memory saver — enables interrupt and resume ───────────────────────────
    memory = MemorySaver()

    # ── Compile with interrupt points at each gate ────────────────────────────
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["gate_1", "gate_2", "gate_3"]
    )

    return graph


# ── Singleton graph instance ──────────────────────────────────────────────────
# Import this in app.py — don't call build_graph() multiple times

leasing_graph = build_graph()