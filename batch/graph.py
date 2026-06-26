"""LangGraph graph construction for the batch pipeline.

Two-layer architecture:
1. BatchOrchestrator: load_batch -> fan_out (Send) -> summarize_batch
2. Per-student pipeline: prompt0 -> prompt1 -> prompt2 -> finalize

The per-student pipeline runs inside student_agent_node using simple
sequential function calls (not a compiled subgraph) for full isolation.
"""

from langgraph.graph import StateGraph, END

from state import BatchState, StudentState
from nodes import (
    load_batch_node, fan_out_fn, student_agent_node, summarize_batch_node,
)


def build_batch_orchestrator() -> StateGraph:
    """Build the compiled batch orchestrator graph.

    Returns a compiled LangGraph that accepts a BatchState with:
    - input_file: path to CSV/JSON
    - batch_id: optional batch identifier
    """
    builder = StateGraph(BatchState)

    builder.add_node("load_batch", load_batch_node)
    builder.add_node("student_agent", student_agent_node)
    builder.add_node("summarize", summarize_batch_node)

    builder.set_entry_point("load_batch")

    # Fan-out: load_batch returns list of Send commands
    builder.add_conditional_edges(
        "load_batch",
        fan_out_fn,
        {"student_agent": "student_agent"},
    )

    builder.add_edge("student_agent", "summarize")
    builder.add_edge("summarize", END)

    return builder.compile()


# Module-level instance for convenience
app = build_batch_orchestrator()
