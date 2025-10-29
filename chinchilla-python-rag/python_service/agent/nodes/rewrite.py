"""Rewrite node: query optimization using LLM."""
from typing import Callable, Dict, Any
from langchain_upstage import ChatUpstage
from app.config import settings


def make_rewrite_node(hooks: Any) -> Callable:
    """Factory: create rewrite node with category-specific prompt.

    Args:
        hooks: CategoryHooks instance with rewrite_system_prompt

    Returns:
        Node function: state -> updated state
    """

    def rewrite_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Rewrite query for better retrieval.

        Args:
            state: Agent state dict

        Returns:
            Updated state with rewritten_query
        """
        query = state.get("query", "")

        if not query:
            return {"rewritten_query": ""}

        # Use category-specific system prompt
        system_prompt = hooks.rewrite_system_prompt

        try:
            llm = ChatUpstage(
                api_key=settings.upstage_api_key,
                model="solar-pro",
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"È8: {query}\n\n€É ü¬:"},
            ]

            response = llm.invoke(messages)
            rewritten = response.content.strip()

            return {"rewritten_query": rewritten}

        except Exception as e:
            print(f"[WARN] Rewrite failed: {e}, using original query")
            return {"rewritten_query": query}

    return rewrite_node


__all__ = ["make_rewrite_node"]
