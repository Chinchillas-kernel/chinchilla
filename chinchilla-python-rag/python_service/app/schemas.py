"""Pydantic schemas for agent requests using discriminated union pattern."""

from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field


# ============================================================================
# Conversation History (공통)
# ============================================================================


class ConversationMessage(BaseModel):
    """단일 대화 메시지 (역할 + 내용)."""

    role: Literal["user", "assistant"]
    content: str


class ConversationHistoryMixin(BaseModel):
    """대화 이력을 포함하는 믹스인."""

    history: List[ConversationMessage] = Field(
        default_factory=list,
        description="이전 대화 메시지 목록 (오래된 순서)",
    )


# ============================================================================
# Jobs Category Schemas
# ============================================================================


class JobsProfile(BaseModel):
    """Profile info required for jobs category."""

    age: int
    gender: Literal["male", "female", "other"] = "other"
    location: Optional[str] = None


class JobsPayload(ConversationHistoryMixin):
    """Payload for jobs queries."""

    query: str
    profile: JobsProfile


class JobsRequest(BaseModel):
    """Jobs category request."""

    category: Literal["jobs"]
    payload: JobsPayload


# ============================================================================
# Welfare Category Schemas (팀원이 추가할 예시)
# ============================================================================

# class WelfarePayload(BaseModel):
#     """Payload for welfare queries."""
#     query: str
#     age: Optional[int] = None
#     income: Optional[int] = None


# class WelfareRequest(BaseModel):
#     """Welfare category request."""
#     category: Literal["welfare"]
#     payload: WelfarePayload


# ============================================================================
# News Category Schemas (팀원이 추가할 예시)
# ============================================================================


class NewsPayload(ConversationHistoryMixin):
    """Payload for news queries."""

    query: str  # 필수: 사용자 질문 (예: "노인 복지 정책 뉴스")
    category: Optional[str] = None  # 선택: 뉴스 카테고리 (복지, 건강, 여가 등)
    date_from: Optional[str] = None  # 선택: 검색 시작 날짜 (YYYY-MM-DD)
    date_to: Optional[str] = None  # 선택: 검색 종료 날짜 (YYYY-MM-DD)


class NewsRequest(BaseModel):
    """News category request."""

    category: Literal["news"]
    payload: NewsPayload


# ============================================================================
# Legal Category Schemas (노인 법률 상담)
# ============================================================================


class LegalProfile(BaseModel):
    """Profile info for legal category."""

    age: Optional[int] = Field(
        None,
        description="사용자 나이 (예: 68)",
        ge=0,
        le=120,
    )
    region: Optional[str] = Field(
        None,
        description="거주 지역 (예: '서울', '경기 수원')",
        examples=["서울", "경기 수원", "부산"],
    )
    interest: Optional[str] = Field(
        None,
        description="관심 분야 (예: '연금', '의료', '주거', '복지')",
        examples=["연금", "의료", "주거", "복지"],
    )
    income: Optional[int] = Field(
        None,
        description="월 소득 (원 단위, 예: 1000000)",
        ge=0,
    )


class LegalPayload(ConversationHistoryMixin):
    """Payload for legal queries."""

    query: str = Field(
        ...,
        description="법률 상담 질문",
        examples=[
            "기초연금 신청 자격이 어떻게 되나요?",
            "노인복지시설의 종류는 무엇인가요?",
            "치매 환자를 위한 지원 제도는?",
        ],
    )
    profile: Optional[LegalProfile] = Field(
        None,
        description="사용자 프로필 (선택사항)",
    )


class LegalRequest(BaseModel):
    """Legal category request."""

    category: Literal["legal"]
    payload: LegalPayload


# ============================================================================
# Discriminated Union (카테고리 추가 시 여기에 등록)
# ============================================================================


class WelfarePayload(ConversationHistoryMixin):
    """Payload for welfare category queries."""

    query: str = Field(..., description="상담을 원하는 내용")
    location: Optional[str] = Field(
        default=None,
        description="관심 지역 (예: 서울, 부산 해운대구)",
    )
    audience: Optional[str] = Field(
        default=None,
        description="대상자 정보 (예: 독거노인, 치매 어르신)",
    )


class WelfareRequest(BaseModel):
    """Welfare category request."""

    category: Literal["welfare"]
    payload: WelfarePayload


# ============================================================================
# Scam Defense Category Schemas (금융 사기 탐지 및 대응)
# ============================================================================


class ScamDefensePayload(ConversationHistoryMixin):
    """Payload for scam defense queries."""

    query: str = Field(
        ...,
        description="의심스러운 메시지 또는 사기 의심 내용 (필수)",
        examples=[
            "안녕하세요. KB국민은행입니다. 고객님의 카드가 정지되어 본인확인이 필요합니다.",
            "검찰청입니다. 고객님 계좌가 금융사기에 연루되어 안전계좌로 이체가 필요합니다.",
        ],
    )
    sender: Optional[str] = Field(
        None,
        description="발신자 정보 (전화번호 또는 발신자명)",
        examples=["02-1234-5678", "KB국민은행", "검찰청"],
    )


class ScamDefenseRequest(BaseModel):
    """Scam defense category request."""

    category: Literal["scam_defense"]
    payload: ScamDefensePayload


AgentRequest = Union[
    JobsRequest,
    WelfareRequest,  # 팀원이 추가
    NewsRequest,
    LegalRequest,
    ScamDefenseRequest,  # 금융 사기 탐지 및 대응
]


# ============================================================================
# Response Schema (공통)
# ============================================================================


class AgentResponse(BaseModel):
    """Standard agent response."""

    answer: str
    sources: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


__all__ = [
    "ConversationMessage",
    "ConversationHistoryMixin",
    "JobsProfile",
    "JobsPayload",
    "JobsRequest",
    "WelfarePayload",
    "WelfareRequest",
    "AgentRequest",
    "AgentResponse",
    # Legal
    "LegalProfile",
    "LegalPayload",
    "LegalRequest",
    "NewsPayload",
    "NewsRequest",
    # Scam Defense
    "ScamDefensePayload",
    "ScamDefenseRequest",
]
