"""LangGraph workflow builder - common graph with hooks injection."""
from typing import Any, Dict, TypedDict
from langgraph.graph import StateGraph, END

from agent.categories.base import CategoryHooks
from agent.nodes import (
    make_rewrite_node,
    make_retrieve_node,
    make_grade_node,
    make_generate_node,
)


# ============================================================================
# State Definition (공통)
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
    retry_count: int  # Track rewrite attempts

    # Retrieved data
    documents: list
    web_documents: list

    # Output
    answer: str
    sources: list


# ============================================================================
# Graph Builder (팩토리 패턴)
# ============================================================================

def build_graph(hooks: CategoryHooks) -> Any:
    """Build LangGraph workflow with category-specific hooks.

    새로운 플로우:
    rewrite → retrieve → grade → yes/no 분기
      - yes → generate
      - no → rewrite (재시도, max 2회)

    Args:
        hooks: CategoryHooks instance (e.g., JobsHooks, WelfareHooks)

    Returns:
        Compiled LangGraph ready for .invoke(state)
    """
    # Create nodes with hooks injection
    rewrite_node = make_rewrite_node(hooks)
    retrieve_node = make_retrieve_node(hooks)
    grade_node = make_grade_node(hooks)
    generate_node = make_generate_node(hooks)

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)

    # Entry point
    workflow.set_entry_point("rewrite")

    # rewrite → retrieve
    workflow.add_edge("rewrite", "retrieve")

    # retrieve → grade (conditional edge)
    def route_after_grade(state: Dict[str, Any]) -> str:
        """Route based on grade result and retry count."""
        # Call grade node to get decision
        decision = grade_node(state)

        if decision == "yes":
            return "generate"

        # decision == "no" → check retry count
        retry_count = state.get("retry_count", 0)
        max_retries = 2

        if retry_count < max_retries:
            print(f"[ROUTE] Rewriting query (attempt {retry_count + 1}/{max_retries})")
            # Increment retry count
            state["retry_count"] = retry_count + 1
            return "rewrite"
        else:
            print(f"[ROUTE] Max retries reached, proceeding to generate")
            return "generate"

    workflow.add_conditional_edges(
        "retrieve",
        route_after_grade,
        {
            "rewrite": "rewrite",
            "generate": "generate",
        },
    )

    # generate → END
    workflow.add_edge("generate", END)

    return workflow.compile()


__all__ = ["AgentState", "build_graph"]
