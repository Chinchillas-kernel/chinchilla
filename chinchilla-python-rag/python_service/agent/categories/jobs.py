"""Jobs category hooks."""
from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.jobs_retriever import get_jobs_retriever


class JobsHooks(CategoryHooks):
    """Hooks for elderly job matching category."""

    name: str = "jobs"

    rewrite_system_prompt: str = (
        "너는 노인 채용 공고 검색요원이다. 사용자의 질의를 검색 친화 쿼리로 축약하라. "
        "예: 지역(도/시/구), 직무 키워드, 고용형태 등."
    )

    answer_system_prompt: str = (
        "너는 시니어 채용 컨설턴트다. 정확한 근거 문서와 함께, "
        "지원 절차/주의사항을 구조적으로 답하라."
    )

    top_k: int = 8
    min_relevance_threshold: float = 0.4

    def get_retriever(self) -> Any:
        """Return jobs retriever with profile-aware filtering."""
        return get_jobs_retriever(k=self.top_k)


__all__ = ["JobsHooks"]
