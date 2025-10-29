"""Agent router: dispatch requests to category-specific workflows."""
from typing import Dict, Any

from app.schemas import AgentRequest, AgentResponse


def dispatch(
    req: AgentRequest,
    graphs: Dict[str, Any],
    hooks: Dict[str, Any],
) -> AgentResponse:
    """Dispatch request to category-specific graph.

    Args:
        req: AgentRequest (discriminated union)
        graphs: Compiled graphs cache {category: graph}
        hooks: Hooks registry {category: hooks}

    Returns:
        AgentResponse with answer and sources

    Raises:
        ValueError: If category not found or execution fails
    """
    # Extract category from discriminated union
    category = req.category

    # Validate category
    if category not in graphs:
        raise ValueError(f"Unknown category: {category}")

    # Get compiled graph
    graph = graphs[category]

    # Build initial state
    state = {
        "category": category,
        "query": req.payload.query,
    }

    # Add profile if exists (for jobs category)
    if hasattr(req.payload, "profile"):
        state["profile"] = req.payload.profile.model_dump()

    # Execute workflow
    try:
        result = graph.invoke(state)

        return AgentResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            metadata={
                "category": category,
                "rewritten_query": result.get("rewritten_query"),
            },
        )

    except Exception as e:
        raise ValueError(f"Workflow execution failed: {e}")


__all__ = ["dispatch"]
