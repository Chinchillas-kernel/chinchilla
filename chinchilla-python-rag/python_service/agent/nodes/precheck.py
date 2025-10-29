"""Precheck node: input validation and safety checks."""
from typing import Callable, Dict, Any


def make_precheck_node(hooks: Any) -> Callable:
    """Factory: create precheck node with hooks.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> updated state
    """

    def precheck_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input and perform safety checks.

        Args:
            state: Agent state dict

        Returns:
            Updated state with validation results
        """
        query = state.get("query", "")

        # Basic validation
        if not query or len(query.strip()) < 2:
            return {
                "error": "Query too short",
                "should_stop": True,
            }

        # Length check
        if len(query) > 1000:
            return {
                "error": "Query too long (max 1000 chars)",
                "should_stop": True,
            }

        # Passed validation
        return {
            "should_stop": False,
            "error": None,
        }

    return precheck_node


__all__ = ["make_precheck_node"]
