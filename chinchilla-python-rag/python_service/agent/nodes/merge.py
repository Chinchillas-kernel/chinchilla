"""Merge node: combine and deduplicate documents."""
from typing import Callable, Dict, Any, List
from langchain.schema import Document


def _deduplicate_docs(docs: List[Document]) -> List[Document]:
    """Remove duplicate documents based on content fingerprint."""
    if not docs:
        return []

    seen = set()
    unique = []

    for doc in docs:
        # Use first 100 chars as fingerprint
        fingerprint = doc.page_content[:100].strip()

        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(doc)

    return unique


def make_merge_node(hooks: Any) -> Callable:
    """Factory: create merge node.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state
    """

    def merge_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Merge and deduplicate documents from multiple sources.

        Args:
            state: Agent state dict

        Returns:
            Updated state with merged documents
        """
        retrieved_docs = state.get("documents", [])
        web_docs = state.get("web_documents", [])

        # Combine
        all_docs = retrieved_docs + web_docs

        # Deduplicate
        merged = _deduplicate_docs(all_docs)

        return {"documents": merged}

    return merge_node


__all__ = ["make_merge_node"]
