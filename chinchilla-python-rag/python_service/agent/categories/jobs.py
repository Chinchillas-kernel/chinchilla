"""Jobs category hooks."""

from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.jobs_retriever import get_jobs_retriever


class JobsHooks(CategoryHooks):
    """Hooks for elderly job matching category."""

    name: str = "jobs"

    rewrite_system_prompt: str = (
        "” xx D© õà €É”Ðtä. ¬©X ÈX| €É \T ü¬\ •}X|. "
        ": Àí(Ä/Ü/l), Á4 ¤ÌÜ, à©Ü ñ."
    )

    answer_system_prompt: str = (
        "” ÜÈ´ D© è$4¸ä. U\ üp 8@ hØ, "
        "ÀÐ (/üX¬mD lp<\ õX|."
    )

    top_k: int = 8
    min_relevance_threshold: float = 0.4

    def get_retriever(self) -> Any:
        """Return jobs retriever with profile-aware filtering."""
        return get_jobs_retriever(k=self.top_k)


__all__ = ["JobsHooks"]

