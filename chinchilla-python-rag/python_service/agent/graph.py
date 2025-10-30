"""LangGraph workflow builder - common graph with hooks injection."""

from typing import Any, Dict, TypedDict
from langgraph.graph import StateGraph, END

from agent.categories.base import CategoryHooks
from agent.nodes import (
    make_rewrite_node,
    make_grade_node,
    make_websearch_node,
    make_generate_node,
    make_enhanced_retrieve_node,
    make_filter_widen_node,
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
    filter_level: int  # Track filter widening level (0-3)
    grade_decision: str  # "yes" or "no" from grade node
    search_quality: str  # "high", "medium", "low"
    avg_relevance_score: float

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
    """Build LangGraph workflow with multi-level search strategy.

    Enhanced flow:
    1. rewrite → enhanced_retrieve → grade
    2. If grade="no":
       a. If filter_level < 3: widen_filter → retrieve
       b. Else if retry_count < 2: increment_retry → rewrite
       c. Else: fallback_answer → END
    3. If grade="yes": generate

    Args:
        hooks: CategoryHooks instance (e.g., JobsHooks, WelfareHooks)

    Returns:
        Compiled LangGraph ready for .invoke(state)
    """
    # Create nodes with hooks injection
    rewrite_node = make_rewrite_node(hooks)
    enhanced_retrieve_node = make_enhanced_retrieve_node(hooks)
    grade_node = make_grade_node(hooks)
    filter_widen_node = make_filter_widen_node(hooks)
    websearch_node = make_websearch_node(hooks)
    generate_node = make_generate_node(hooks)

    # Helper nodes
    def increment_retry(state: Dict[str, Any]) -> Dict[str, Any]:
        """Increment retry counter and reset filter level."""
        retry_count = state.get("retry_count", 0)
        return {
            "retry_count": retry_count + 1,
            "filter_level": 0,  # Reset filter level on retry
        }

    # def fallback_answer_node(state: AgentState) -> dict:
    #     """Generates a fallback message when no answer can be found."""
    #     print(
    #         "[FALLBACK] No relevant documents found after all retries. Returning fallback message."
    #     )
    #     return {
    #         "answer": "죄송합니다. 해당 질문에 대한 답변을 할 수 없습니다",
    #         "sources": [],
    #     }

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("retrieve", enhanced_retrieve_node)
    workflow.add_node("grade", grade_node)
    workflow.add_node("widen_filter", filter_widen_node)
    workflow.add_node("increment_retry", increment_retry)
    workflow.add_node("websearch", websearch_node)
    workflow.add_node("generate", generate_node)
    # workflow.add_node("fallback_answer", fallback_answer_node)

    # Entry point
    workflow.set_entry_point("rewrite")

    # Edges
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("retrieve", "grade")

    # Complex routing after grade
    def route_after_grade(state: Dict[str, Any]) -> str:
        """Multi-level search strategy routing.

        Strategy:
        1. If documents are relevant (grade=yes) → generate
        2. If not relevant (grade=no):
           a. Try filter widening (if filter_level < 3)
           b. Try query rewrite (if retry_count < 2)
           c. Provide fallback message
        """
        grade_decision = state.get("grade_decision", "no")
        retry_count = state.get("retry_count", 0)
        filter_level = state.get("filter_level", 0)
        quality = state.get("search_quality", "low")

        # Success case: documents are relevant
        if grade_decision == "yes":
            print("[ROUTE] Grade=YES → generate")
            return "generate"

        # Documents not relevant, try recovery strategies
        print(
            f"[ROUTE] Grade=NO, quality={quality}, filter_level={filter_level}, retry={retry_count}"
        )

        # Strategy 1: Widen filters (if not exhausted)
        if filter_level < 3:
            print(f"[ROUTE] → widen_filter (current level: {filter_level})")
            return "widen_filter"

        # Strategy 2: Rewrite query (if retries available)
        if retry_count < 2:
            print(f"[ROUTE] → increment_retry (attempt {retry_count + 1}/2)")
            return "increment_retry"

        # Strategy 3: All strategies exhausted, provide fallback message
        print("[ROUTE] → websearch (all strategies failed)")
        return "websearch"

    workflow.add_conditional_edges(
        "grade",
        route_after_grade,
        {
            "widen_filter": "widen_filter",
            "increment_retry": "increment_retry",
            "websearch": "websearch",
            "generate": "generate",
        },
    )

    # widen_filter → retrieve (loop back with widened filters)
    workflow.add_edge("widen_filter", "retrieve")

    # increment_retry → rewrite (loop back with new query)
    workflow.add_edge("increment_retry", "rewrite")

    # websearch → generate (merge web results)
    workflow.add_edge("websearch", "generate")

    # fallback → END
    # workflow.add_edge("fallback_answer", END)

    # generate → END
    workflow.add_edge("generate", END)

    return workflow.compile()


__all__ = ["AgentState", "build_graph"]
