"""Web search node: supplementary information from web."""
from typing import Callable, Dict, Any
from langchain.schema import Document
from app.config import settings


def make_websearch_node(hooks: Any) -> Callable:
    """Factory: create web search node.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state
    """

    def websearch_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web for additional information.

        Args:
            state: Agent state dict

        Returns:
            Updated state with web_documents
        """
        query = state.get("rewritten_query") or state.get("query", "")

        if not query or not settings.serp_api_key:
            trace = list(state.get("retrieval_trace", []))
            if not query:
                reason = "empty_query"
            else:
                reason = "missing_serp_api_key"
            trace.append(
                {
                    "type": "web_search_skipped",
                    "reason": reason,
                }
            )
            return {"web_documents": [], "retrieval_trace": trace}

        try:
            from langchain_community.utilities import SerpAPIWrapper

            search = SerpAPIWrapper(serpapi_api_key=settings.serp_api_key)
            results = search.run(query)

            # Convert to documents
            web_docs = [
                Document(
                    page_content=results,
                    metadata={
                        "source": "web_search",
                        "query": query,
                        "origin": "web_search",
                    },
                )
            ]

            trace = list(state.get("retrieval_trace", []))
            trace.append(
                {
                    "type": "web_search",
                    "query": query,
                    "doc_count": len(web_docs),
                }
            )

            return {"web_documents": web_docs, "retrieval_trace": trace}

        except Exception as e:
            print(f"[WARN] Web search failed: {e}")
            trace = list(state.get("retrieval_trace", []))
            trace.append(
                {
                    "type": "web_search_error",
                    "query": query,
                    "error": str(e),
                }
            )
            return {"web_documents": [], "retrieval_trace": trace}

    return websearch_node


__all__ = ["make_websearch_node"]
