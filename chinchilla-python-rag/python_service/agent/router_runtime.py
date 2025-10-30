"""Runtime registry: category -> hooks & compiled graph cache."""

from typing import Any, Dict, Tuple

from agent.categories.base import CategoryHooks
from agent.categories.jobs import JobsHooks
from agent.categories.welfare import WelfareHooks
from agent.graph import build_graph


# ============================================================================
# Category Registry (팀원이 카테고리 추가 시 여기에 등록)
# ============================================================================


def get_all_hooks() -> Dict[str, CategoryHooks]:
    """Get all registered category hooks.

    팀원이 새 카테고리를 추가할 때:
    1. agent/categories/{category}.py 생성
    2. {Category}Hooks 클래스 정의
    3. 여기에 등록

    Returns:
        Dict mapping category name to hooks instance
    """
    return {
        "jobs": JobsHooks(),
        "welfare": WelfareHooks(),
        # "news": NewsHooks(),         # 팀원이 추가
    }


# ============================================================================
# Runtime Initialization (서버 시작 시 1회 실행)
# ============================================================================


def get_runtime() -> Tuple[Dict[str, Any], Dict[str, CategoryHooks]]:
    """Initialize runtime: build graphs for all categories.

    Returns:
        Tuple of (compiled_graphs, hooks)
        - compiled_graphs: {category: compiled LangGraph}
        - hooks: {category: CategoryHooks instance}
    """
    hooks_registry = get_all_hooks()
    graphs_cache = {}

    for category, hooks in hooks_registry.items():
        print(f"[INIT] Building graph for category: {category}")
        graphs_cache[category] = build_graph(hooks)

    print(f"[INIT] Runtime ready with {len(graphs_cache)} categories")
    return graphs_cache, hooks_registry


__all__ = ["get_runtime", "get_all_hooks"]
