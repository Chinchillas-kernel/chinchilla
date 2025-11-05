"""Category hooks for elderly comprehensive welfare guidance."""

from __future__ import annotations

from typing import Any

from agent.categories.base import CategoryHooks
from agent.retrievers.welfare_retriever import get_welfare_retriever


class WelfareHooks(CategoryHooks):
    """Hooks that fine-tune the workflow for elderly welfare services."""

    name: str = "welfare"

    rewrite_system_prompt: str = (
        "너는 노인 종합 복지 서비스 정보를 찾는 검색 전문가다. "
        "사용자의 상담 요청을 지원 유형(건강, 돌봄, 경제 등), 대상 특징, 지역 정보를 포함한 "
        "핵심 한국어 검색 쿼리로 재작성하라."
    )

    answer_system_prompt: str = (
        "너는 노인 종합 복지 상담사다. "
        "검증된 문서에서 파악한 사실만 사용하여 서비스 개요, 지원 대상, 제공 내용, 신청 절차, 문의처를 "
        "항목별로 정리하고 필요한 경우 주의사항·비고를 덧붙여라."
    )

    top_k: int = 3
    min_relevance_threshold: float = 0.25

    def get_retriever(self) -> Any:  # pragma: no cover - simple factory
        return get_welfare_retriever(top_k=self.top_k)


__all__ = ["WelfareHooks"]
