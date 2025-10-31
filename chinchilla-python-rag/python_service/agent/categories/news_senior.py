"""News category hooks."""

from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.news_retriever import get_news_retriever


class NewsHooks(CategoryHooks):
    """Hooks for news information category."""

    # 카테고리 식별자
    name: str = "news"
    _retriever: Any = None  # 캐시 추가

    # 쿼리 재작성 프롬프트 (rewrite_node에서 사용)
    rewrite_system_prompt: str = """
        노인 뉴스 검색용 쿼리로 재작성:
        - 핵심 키워드만 추출 (명사형)
        - 조사 제거, 날짜/지역 포함
        - 예: "복지 정책 알려줘" -> "노인 복지 정책 지원"
    """

    # 답변 생성 프롬프트 (generate_nodes에서 사용)
    answer_system_prompt: str = """
        노인용 뉴스 답변 작성 : 
        [요약] 핵심 내용 2문장
        [상세] 날짜 / 장소/ 방법
        [출처] 기사명
        
        톤: 존댓말, 쉬운 용어 사용
    """

    # 검색 관련 설정
    top_k: int = 3  # 검색할 문서 개수
    min_relevance_threshold: float = 0.3  # gate_node에서 사용하는 최소 관련성 임계값

    def get_retriever(self) -> Any:
        """Return news retriever.
        이 메서드는 retrieve_node에서 호출됩니다.

        Returns:
            NewsRetriever 인스턴스
        """
        if self._retriever is None:
            self._retriever = get_news_retriever(k=self.top_k)
        return self._retriever


__all__ = ["NewsHooks"]
