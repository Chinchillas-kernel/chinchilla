"""Retrieve node: document retrieval from vector store."""
from typing import Callable, Dict, Any


def make_retrieve_node(hooks: Any) -> Callable:
    """Factory: create retrieve node with category-specific retriever.

    Args:
        hooks: CategoryHooks instance with get_retriever() method

    Returns:
        Node function: state -> updated state
    """

    def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant documents.

        Args:
            state: Agent state dict

        Returns:
            Updated state with documents
        """
        query = state.get("rewritten_query") or state.get("query", "")

        if not query:
            return {"documents": []}

        try:
            # Get category-specific retriever
            retriever = hooks.get_retriever()

            # Build retriever input (category-specific)
            retriever_input = {"query": query}

            # Add profile if exists (for jobs category)
            if "profile" in state:
                retriever_input["profile"] = state["profile"]

            # Invoke retriever
            result = retriever.invoke(retriever_input)

            # Extract documents (handle different return types)
            if hasattr(result, "documents"):
                documents = result.documents
            elif isinstance(result, list):
                documents = result
            else:
                documents = []

            return {"documents": documents}

        except Exception as e:
            print(f"[ERROR] Retrieval failed: {e}")
            return {"documents": []}

    return retrieve_node


__all__ = ["make_retrieve_node"]
