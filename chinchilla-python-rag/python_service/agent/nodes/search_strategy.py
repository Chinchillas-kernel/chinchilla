"""Multi-level search strategy nodes for enhanced retrieval."""
from typing import Dict, Any, Callable, List
from langchain.schema import Document


# ============================================================================
# Quality Assessment
# ============================================================================

def assess_search_quality(documents: List[Document], min_threshold: float = 0.4) -> Dict[str, Any]:
    """Assess the quality of search results.

    Returns:
        dict with:
        - quality: "high", "medium", "low"
        - avg_score: average relevance score
        - count: number of documents
    """
    if not documents:
        return {"quality": "low", "avg_score": 0.0, "count": 0}

    scores = [doc.metadata.get("relevance_score", 0) for doc in documents]
    avg_score = sum(scores) / len(scores) if scores else 0
    count = len(documents)

    # Quality criteria
    if count >= 5 and avg_score >= 0.7:
        quality = "high"
    elif count >= 3 and avg_score >= min_threshold:
        quality = "medium"
    else:
        quality = "low"

    return {
        "quality": quality,
        "avg_score": avg_score,
        "count": count,
    }


# ============================================================================
# Filter Widening Strategy
# ============================================================================

def make_filter_widen_node(hooks: Any) -> Callable:
    """Factory: create filter widen node to relax search constraints.

    Widening strategy:
    1. Drop city filter (keep province)
    2. Drop province filter (keep age)
    3. Drop age constraint (fetch all)

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state with relaxed filters
    """

    def filter_widen_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Progressively widen search filters.

        Args:
            state: Agent state dict

        Returns:
            Updated state with filter_level
        """
        profile = state.get("profile", {})
        current_level = state.get("filter_level", 0)

        # Determine next filter level
        next_level = current_level + 1

        if next_level == 1:
            print("[FILTER_WIDEN] Level 1: Drop city, keep province + age")
        elif next_level == 2:
            print("[FILTER_WIDEN] Level 2: Drop province, keep age only")
        elif next_level >= 3:
            print("[FILTER_WIDEN] Level 3: Drop all filters, fetch all")
            next_level = 3

        return {
            "filter_level": next_level,
            "filters_widened": True,
        }

    return filter_widen_node


# ============================================================================
# Enhanced Retriever with Filter Levels
# ============================================================================

def make_enhanced_retrieve_node(hooks: Any) -> Callable:
    """Factory: create enhanced retrieve node with filter widening support.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state with documents
    """

    def enhanced_retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve with progressive filter widening.

        Args:
            state: Agent state dict

        Returns:
            Updated state with documents and search_quality
        """
        query = state.get("rewritten_query") or state.get("query", "")
        profile = state.get("profile", {})
        filter_level = state.get("filter_level", 0)

        if not query:
            return {"documents": [], "search_quality": "low"}

        try:
            # Get retriever
            retriever = hooks.get_retriever()

            # Build retriever input based on filter level
            retriever_input = {"query": query}

            if profile and filter_level == 0:
                # Level 0: Full profile filtering
                retriever_input["profile"] = profile
                print(f"[RETRIEVE] Level 0: Full filters (location + age)")

            elif profile and filter_level == 1:
                # Level 1: Province only (drop city)
                location = profile.get("location", "")
                if location:
                    province = location.split()[0]  # First word as province
                    modified_profile = {
                        **profile,
                        "location": province,  # Only province
                    }
                    retriever_input["profile"] = modified_profile
                    print(f"[RETRIEVE] Level 1: Province only ({province})")
                else:
                    retriever_input["profile"] = profile

            elif profile and filter_level == 2:
                # Level 2: Age only (drop location)
                modified_profile = {
                    "age": profile.get("age"),
                    "gender": profile.get("gender", "other"),
                    "location": None,  # Drop location
                }
                retriever_input["profile"] = modified_profile
                print(f"[RETRIEVE] Level 2: Age only ({profile.get('age')})")

            else:
                # Level 3+: No filters, just query (no profile)
                print(f"[RETRIEVE] Level 3+: No filters (pure semantic search)")
                # Don't add profile to retriever_input - let it be None

            # Invoke retriever
            result = retriever.invoke(retriever_input)

            # Extract documents
            if hasattr(result, "documents"):
                documents = result.documents
            elif isinstance(result, list):
                documents = result
            else:
                documents = []

            # Assess quality
            quality_info = assess_search_quality(documents, hooks.min_relevance_threshold)

            print(f"[RETRIEVE] Found {quality_info['count']} docs, "
                  f"avg score: {quality_info['avg_score']:.2f}, "
                  f"quality: {quality_info['quality']}")

            return {
                "documents": documents,
                "search_quality": quality_info["quality"],
                "avg_relevance_score": quality_info["avg_score"],
            }

        except Exception as e:
            print(f"[ERROR] Enhanced retrieval failed: {e}")
            return {"documents": [], "search_quality": "low"}

    return enhanced_retrieve_node


__all__ = [
    "make_filter_widen_node",
    "make_enhanced_retrieve_node",
    "assess_search_quality",
]
