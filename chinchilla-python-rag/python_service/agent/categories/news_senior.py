"""News category hooks."""

from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.news_retriever import get_news_retriever


class NewsHooks(CategoryHooks):
    """Hooks for news information category."""

    # 카테고리 식별자
    name: str = "news"

    # 쿼리 재작성 프롬프트 (rewrite_node에서 사용)
    rewrite_system_prompt: str = (
        "너는 노인 관련 뉴스 검색 전문가다."
        "사용자 질문을 뉴스 기사 검색에 적합하게 재작성하라."
        "예: 복지정책, 건강 프로그램, 여가 활동, 사회 이슈 등"
        "노인과 관련된 핵심 키워드를 추출하라."
    )

    # 답변 생성 프롬프트 (generate_nodes에서 사용)
    answer_system_prompt: str = (
        "너는 노인을 위한 뉴스 큐레이터다."
        "제공된 뉴스 기사를 바탕으로"
        "핵심 내용, 관련정보, 신청방법(해당시) 등을"
        "출처와 날짜를 명시하라."
    )

    # 검색 관련 설정
    top_k: int = 5  # 검색할 문서 개수
    min_relevance_threshold: float = 0.5  # gate_node에서 사용하는 최소 관련성 임계값

    def get_retriever(self) -> Any:
        """Return news retriever.
        이 메서드는 retrieve_node에서 호출됩니다.

        Returns:
            NewsRetriever 인스턴스
        """
        return get_news_retriever(k=self.top_k)


__all__ = ["NewsHooks"]
