"""Category hooks for cultural & lifestyle welfare guidance."""

from __future__ import annotations

from typing import Any

from agent.categories.base import CategoryHooks
from agent.retrievers.welfare_retriever import get_welfare_retriever


class WelfareHooks(CategoryHooks):
    """Hooks that fine-tune the generic workflow for welfare programs."""

    name: str = "welfare"

    rewrite_system_prompt: str = (
        "너는 문화·생활 복지 정보를 찾는 검색 전문가다. "
        "사용자의 상담 요청을 핵심 키워드, 지역, 대상 정보를 포함한 "
        "짧은 한국어 검색 쿼리로 재작성하라."
    )

    answer_system_prompt: str = (
        "너는 문화·생활 복지 전문 상담사다. "
        "주어진 문서에서 확인한 사실만 사용해 프로그램 명, 대상, 위치, 신청 방법을 "
        "항목 별로 정리하고, 필요한 경우 주의사항을 덧붙여라."
    )

    top_k: int = 5
    min_relevance_threshold: float = 0.25

    def get_retriever(self) -> Any:  # pragma: no cover - simple factory
        return get_welfare_retriever(top_k=self.top_k)


__all__ = ["WelfareHooks"]
