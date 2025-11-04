"""Rewrite node: query optimization using LLM."""
from typing import Callable, Dict, Any


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
            # Use cached LLM instance from hooks
            llm = hooks.llm

            messages = [{"role": "system", "content": system_prompt}]

            history = state.get("history") or []
            # 최근 6턴까지만 포함하여 프롬프트 길이 제한
            for turn in history[-6:]:
                role = turn.get("role") if isinstance(turn, dict) else getattr(turn, "role", None)
                content = turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", None)
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": str(content)})

            messages.append({"role": "user", "content": f"질문: {query}\n\n검색 쿼리:"})

            response = llm.invoke(messages)
            rewritten = response.content.strip()

            return {"rewritten_query": rewritten}

        except Exception as e:
            print(f"[WARN] Rewrite failed: {e}, using original query")
            return {"rewritten_query": query}

    return rewrite_node


__all__ = ["make_rewrite_node"]
