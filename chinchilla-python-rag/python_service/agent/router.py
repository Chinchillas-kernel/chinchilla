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
        "retry_count": 0,  # Initialize retry counter
        "filter_level": 0,  # Initialize filter level
    }

    # Add profile if exists (for jobs category)
    # Add profile if exists (for jobs category)
    profile = getattr(req.payload, "profile", None)
    if profile is not None:
        if isinstance(profile, BaseModel):
            state["profile"] = profile.model_dump()
        elif isinstance(profile, dict):
            state["profile"] = profile
        else:
            # dict로 강제 변환을 시도 (필요 시 JobsProfile(**profile)로 캐스팅)
            try:
                state["profile"] = dict(profile)
            except Exception:
                # 마지막 방어선: 문자열 등은 무시
                pass

    # Execute workflow
    try:
        # Increase recursion limit for multi-level search strategy
        # Max path: retry(3) * filter_levels(4) * nodes_per_level(4) = ~48 steps
        result = graph.invoke(state, config={"recursion_limit": 50})

        metadata = {
            "category": category,
            "rewritten_query": result.get("rewritten_query"),
        }
        if result.get("retrieval_stats") is not None:
            metadata["retrieval_stats"] = result["retrieval_stats"]

        return AgentResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            metadata=metadata,
        )

    except Exception as e:
        raise ValueError(f"Workflow execution failed: {e}")


__all__ = ["dispatch"]
