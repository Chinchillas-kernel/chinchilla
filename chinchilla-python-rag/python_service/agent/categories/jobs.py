"""Jobs category hooks."""
from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.jobs_retriever import get_jobs_retriever


class JobsHooks(CategoryHooks):
    """Hooks for elderly job matching category."""

    name: str = "jobs"

    rewrite_system_prompt: str = (
        "î xx D© ı‡ Ä…î–t‰. ¨©êX »X| Ä… \T ¸¨\ ï}X|. "
        ": ¿Ì(ƒ/‹/l), ¡4 §Ã‹, ‡©‹ Ò."
    )

    answer_system_prompt: str = (
        "î ‹»¥ D© Ë$4∏‰. U\ ¸p 8@ hÿ, "
        "¿– (/¸X¨mD lp<\ ıX|."
    )

    top_k: int = 8
    min_relevance_threshold: float = 0.4

    def get_retriever(self) -> Any:
        """Return jobs retriever with profile-aware filtering."""
        return get_jobs_retriever(k=self.top_k)


__all__ = ["JobsHooks"]
