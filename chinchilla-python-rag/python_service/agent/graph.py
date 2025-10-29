"""LangGraph workflow builder - common graph with hooks injection."""
from typing import Any, Dict, TypedDict
from langgraph.graph import StateGraph, END

from agent.categories.base import CategoryHooks
from agent.nodes import (
    make_rewrite_node,
    make_retrieve_node,
    make_gate_node,
    make_websearch_node,
    make_merge_node,
    make_generate_node,
)


# ============================================================================
# State Definition (õµ)
# ============================================================================

class AgentState(TypedDict, total=False):
    """Shared state for agent workflow across all categories."""

    # Input
    category: str
    query: str
    profile: Dict[str, Any]  # Optional, category-specific

    # Workflow
    rewritten_query: str
    should_stop: bool
    error: str

    # Retrieved data
    documents: list
    web_documents: list

    # Output
    answer: str
    sources: list


# ============================================================================
# Graph Builder () ¬ (4)
# ============================================================================

def build_graph(hooks: CategoryHooks) -> Any:
    """Build LangGraph workflow with category-specific hooks.

    Args:
        hooks: CategoryHooks instance (e.g., JobsHooks, WelfareHooks)

    Returns:
        Compiled LangGraph ready for .invoke(state)
    """
    # Create nodes with hooks injection
    rewrite_node = make_rewrite_node(hooks)
    retrieve_node = make_retrieve_node(hooks)
    gate_node = make_gate_node(hooks)
    websearch_node = make_websearch_node(hooks)
    merge_node = make_merge_node(hooks)
    generate_node = make_generate_node(hooks)

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("websearch", websearch_node)
    workflow.add_node("merge", merge_node)
    workflow.add_node("generate", generate_node)

    # Define edges
    workflow.set_entry_point("rewrite")
    workflow.add_edge("rewrite", "retrieve")

    # Conditional edge: gate decides websearch or generate
    workflow.add_conditional_edges(
        "retrieve",
        gate_node,  # Decision function
        {
            "websearch": "websearch",
            "generate": "generate",
        },
    )

    workflow.add_edge("websearch", "merge")
    workflow.add_edge("merge", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


__all__ = ["AgentState", "build_graph"]
