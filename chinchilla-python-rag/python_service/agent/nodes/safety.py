"""Safety node: final answer filtering and safety checks."""
from typing import Callable, Dict, Any


def make_safety_node(hooks: Any) -> Callable:
    """Factory: create safety node for answer filtering.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state
    """

    def safety_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply safety filters to generated answer.

        Args:
            state: Agent state dict

        Returns:
            Updated state with filtered answer
        """
        answer = state.get("answer", "")

        # Basic safety checks (extend as needed)
        # 1. Check for harmful content keywords
        # 2. Filter personal information
        # 3. Apply content policy

        # Simple passthrough for now
        # Teams can implement category-specific safety rules
        return {"answer": answer}

    return safety_node


__all__ = ["make_safety_node"]
