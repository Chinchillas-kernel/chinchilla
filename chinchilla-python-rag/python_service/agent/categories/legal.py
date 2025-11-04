"""
법률 상담 카테고리 훅
노인 법률 상담을 위한 CategoryHooks 구현
"""

from typing import Any

from agent.categories.base import CategoryHooks
from agent.retrievers.legal_retriever import get_legal_retriever


class LegalHooks(CategoryHooks):
    """노인 법률 상담 카테고리를 위한 훅"""

    name: str = "legal"

    # 쿼리 재작성 시스템 프롬프트
    rewrite_system_prompt: str = (
        "당신은 노인 법률 상담 전문가입니다."
        "사용자의 질문을 법률 문서에 최적화된 형태로 재작성하세요. \n"
    )

    # 답변 생성 시스템 프롬프트
    answer_system_prompt: str = (
        "당신은 법률 상담 AI입니다. 제공된 법률 문서를 바탕으로 사용자의 질문에 답변하세요. 노인이 이해하기 쉽도록 5줄 정도로 친절하고 명확하게 설명해야 합니다."
    )

    # Gate 노드 프롬프트 (웹 검색 필요 여부 판단)
    gate_system_prompt: str = (
        "당신은 검색 결과 평가 전문가입니다.\n"
        "검색된 법률 문서를 평가하여 웹 검색이 추가로 필요한지 판단하세요.\n\n"
        "vectorstore는 법률 조항, 규정, 제도 등 일반적인 법률 정보에 적합합니다.\n"
        "websearch는 최신 정책, 구체적인 기관 정보, 최근 판례 등 실시간/외부 정보에 적합합니다.\n\n"
        '반환 형식: {"datasource": "vectorstore"} 또는 {"datasource": "websearch"}'
    )

    # 검색 파라미터
    top_k: int = 3
    min_relevance_threshold: float = 0.3  # 법률은 높은 정확도 필요
    fetch_k: int = 10  # MMR을 위한 초기 검색 개수

    def get_retriever(self) -> Any:
        """
        법률 문서 검색 리트리버 반환

        Returns:
            LegalRetrieverPipeline with .invoke(dict) method
        """
        return get_legal_retriever(
            top_k=self.top_k,
            search_type="mmr",  # 다양성을 위한 MMR
            fetch_k=self.fetch_k,
        )


__all__ = ["LegalHooks"]
