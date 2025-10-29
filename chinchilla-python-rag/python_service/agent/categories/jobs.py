"""Jobs category hooks."""

from pydantic import BaseModel
from agent.retrievers.jobs_retriever import get_jobs_retriever


class JobsHooks(BaseModel):
    name: str = "jobs"
    rewrite_system_prompt: str = (
        "너는 노인 채용 공고 검색요원이다. 사용자의 질의를 검색 친화 쿼리로 축약하라. "
        "예: 지역(도/시/구), 직무 키워드, 고용형태 등."
    )
    answer_system_prompt: str = (
        "너는 시니어 채용 컨설턴트다. 정확한 근거 문서와 함께, 지원 절차/주의사항을 구조적으로 답하라."
    )

    def get_retriever(self):
        return get_jobs_retriever(k=8)  # Chroma 인덱스 로드/설정
