"""Gate node: decide whether to use web search."""
from typing import Callable, Dict, Any, Literal


def make_gate_node(hooks: Any) -> Callable:
    """Factory: create gate node with category-specific threshold.

    Args:
        hooks: CategoryHooks instance with min_relevance_threshold

    Returns:
        Node function: state -> routing decision
    """

    def gate_node(state: Dict[str, Any]) -> Literal["websearch", "generate"]:
        """Decide whether to use web search.

        Args:
            state: Agent state dict

        Returns:
            "websearch" if documents are insufficient, "generate" otherwise
        """
        documents = state.get("documents", [])
        threshold = hooks.min_relevance_threshold

        # Check if we have enough relevant documents
        MIN_DOCS = 2

        if len(documents) < MIN_DOCS:
            return "websearch"

        # Check relevance scores
        relevant_docs = [
            doc
            for doc in documents
            if doc.metadata.get("relevance_score", 0) >= threshold
        ]

        if len(relevant_docs) < MIN_DOCS:
            return "websearch"

        return "generate"

    return gate_node


__all__ = ["make_gate_node"]
