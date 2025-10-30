"""News category hooks."""

from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.news_retriever import get_news_retriever


class NewsHooks(CategoryHooks):
    """Hooks for news information category."""

    # 카테고리 식별자
    name: str = "news"

    # 쿼리 재작성 프롬프트 (rewrite_node에서 사용)
    rewrite_system_prompt: str = """
        당신은 노인 관련 뉴스 검색 전문가입니다.
        사용자의 질문을 뉴스 검색에 최적화된 키워드와 문구로 재작성하세요.
        
        재작성 원칙:
        1. 핵심 키워드를 추출하세요 (인물, 장소, 사건, 주제)
        2. 불필요한 조사와 수식어를 제거하세요
        3. 검색에 유리한 명사형으로 변환하세요
        4. 날짜나 지역 정보가 있으면 포함하세요
        5. 노인 복지, 건강, 여가 활동 등 관련 키워드를 강조하세요
        
        예시:
        - "독립군 체험학교 교육이 뭐야?" -> "독립군 체험학교 교육 프로그램 내용"
        - "어르신 복지 정책 알려줘" -> "노인 복지 정책 지원 혜택"
        - "건강 프로그램 있어?" -> "노인 건강 체험 프로그램"
    """

    # 답변 생성 프롬프트 (generate_nodes에서 사용)
    answer_system_prompt: str = """
        당신은 노인 사용자를 위한 뉴스 도우미입니다.
        
        답변 형식 : 
        [요약] 핵심 내용 2~3문장
        [상세] 구체적 정보 (날짜, 장소, 방법)
        [출처] 기사 제목
        
        톤: 존댓말, 쉬운 용어 사용
    """

    # 검색 관련 설정
    top_k: int = 3  # 검색할 문서 개수
    min_relevance_threshold: float = 0.5  # gate_node에서 사용하는 최소 관련성 임계값

    def get_retriever(self) -> Any:
        """Return news retriever.
        이 메서드는 retrieve_node에서 호출됩니다.

        Returns:
            NewsRetriever 인스턴스
        """
        return get_news_retriever(k=self.top_k)


__all__ = ["NewsHooks"]
