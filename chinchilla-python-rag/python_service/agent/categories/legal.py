"""
법률 상담 카테고리 훅
노인 법률 상담을 위한 CategoryHooks 구현
"""

from typing import Any

from agent.categories.base import CategoryHooks
from agent.retrievers.legal_retriever import LegalRetriever


class LegalHooks(CategoryHooks):
    """노인 법률 상담 카테고리를 위한 훅"""

    name: str = "legal"

    # 쿼리 재작성 시스템 프롬프트
    rewrite_system_prompt: str = (
        "당신은 노인 법률 상담 전문가입니다. "
        "사용자의 질문을 법률 문서 검색에 최적화된 형태로 재작성하세요.\n\n"
        "재작성 시 포함할 요소:\n"
        "- 관련 법률명 (예: 기초연금법, 노인복지법, 치매관리법)\n"
        "- 핵심 키워드 (예: 신청 자격, 지원 금액, 급여 종류)\n"
        "- 법률 용어로 변환 (예: '돈' → '급여', '신청' → '수급권')\n"
        "- 구체적인 조건 (예: 연령, 소득, 거주지)\n\n"
        "예시:\n"
        "- 원본: '65세 이상 노인이 받을 수 있는 돈은?'\n"
        "- 재작성: '65세 이상 노인 기초연금 급여 자격 요건'\n\n"
        "간결하고 명확하게 재작성하세요."
    )

    # 답변 생성 시스템 프롬프트
    answer_system_prompt: str = (
        "당신은 노인을 위한 친절하고 전문적인 법률 상담 AI입니다.\n\n"
        "답변 작성 규칙:\n"
        "1. 쉽고 친절한 언어 사용 (어려운 법률 용어는 쉽게 풀어서 설명)\n"
        "2. 관련 법률 조항을 명확히 인용 (예: '노인복지법 제26조에 따르면...')\n"
        "3. 신청 자격을 구체적으로 안내\n"
        "4. 신청 방법과 절차를 단계별로 설명\n"
        "5. 필요한 서류와 준비물 안내\n"
        "6. 문의처 안내 (해당되는 경우)\n"
        "7. 주의사항이나 추가 정보 제공\n\n"
        "답변 형식:\n"
        "- 서론: 질문에 대한 직접적인 답\n"
        "- 본론: 법률 근거와 상세 설명\n"
        "- 결론: 신청 방법 또는 다음 단계 안내\n\n"
        "제공된 법률 문서를 바탕으로 정확하고 유용한 답변을 작성하세요."
    )

    # Gate 노드 프롬프트 (웹 검색 필요 여부 판단)
    gate_system_prompt: str = (
        "당신은 검색 결과 평가 전문가입니다.\n\n"
        "검색된 법률 문서를 평가하여 웹 검색이 추가로 필요한지 판단하세요.\n\n"
        "vectorstore (법률 문서 검색) 선택 기준:\n"
        "- 법률 조항, 규정, 제도 설명이 충분함\n"
        "- 신청 자격, 절차, 방법이 명확히 나와있음\n"
        "- 법적 권리, 의무에 대한 정보가 있음\n"
        "- 역사적 또는 일반적인 법률 해석\n\n"
        "websearch (웹 검색) 선택 기준:\n"
        "- 최신 정책 변경 또는 시행령 개정 내용 필요\n"
        "- 구체적인 신청 기관 위치나 연락처 필요\n"
        "- 최근 판례나 실제 사례 필요\n"
        "- 지역별 특화 서비스나 조례 정보 필요\n"
        "- 실시간 마감일이나 공지사항 필요\n\n"
        '반환 형식: {"datasource": "vectorstore"} 또는 {"datasource": "websearch"}'
    )

    # 검색 파라미터
    top_k: int = 5
    min_relevance_threshold: float = 0.6  # 법률은 높은 정확도 필요
    fetch_k: int = 20  # MMR을 위한 초기 검색 개수

    def __init__(self):
        """리트리버 팩토리 초기화"""
        self.retriever_factory = LegalRetriever()

    def get_retriever(self, payload: dict = None) -> Any:
        """
        법률 문서 검색 리트리버 반환

        Args:
            payload: 요청 페이로드 (query, profile 포함)

        Returns:
            LangChain BaseRetriever 인스턴스
        """
        if payload is None:
            payload = {}

        # 프로필 추출
        profile = payload.get("profile")

        # 리트리버 생성
        retriever = self.retriever_factory.get_retriever(
            profile=profile,
            search_type="mmr",  # 다양성을 위한 MMR
            k=self.top_k,
            fetch_k=self.fetch_k,
        )

        return retriever


__all__ = ["LegalHooks"]
