"""Plan node: decompose complex queries (optional)."""
from typing import Callable, Dict, Any


def make_plan_node(hooks: Any) -> Callable:
    """Factory: create plan node for complex query decomposition.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state
    """

    def plan_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Decompose complex queries into sub-queries (optional).

        Args:
            state: Agent state dict

        Returns:
            Updated state with plan/sub-queries
        """
        # Simple passthrough for now
        # Teams can implement query decomposition if needed
        return {"plan": None}

    return plan_node


__all__ = ["make_plan_node"]
