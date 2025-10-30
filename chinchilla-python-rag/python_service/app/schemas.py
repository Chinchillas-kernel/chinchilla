"""Pydantic schemas for agent requests using discriminated union pattern."""
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field


# ============================================================================
# Jobs Category Schemas
# ============================================================================

class JobsProfile(BaseModel):
    """Profile info required for jobs category."""
    age: int
    gender: Literal["male", "female", "other"] = "other"
    location: Optional[str] = None


class JobsPayload(BaseModel):
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

# class NewsPayload(BaseModel):
#     """Payload for news queries."""
#     query: str
#     date_from: Optional[str] = None


# class NewsRequest(BaseModel):
#     """News category request."""
#     category: Literal["news"]
#     payload: NewsPayload


# ============================================================================
# Discriminated Union (카테고리 추가 시 여기에 등록)
# ============================================================================

class WelfarePayload(BaseModel):
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


AgentRequest = Union[
    JobsRequest,
    WelfareRequest,
    # NewsRequest,     # 팀원이 추가
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
    "JobsProfile",
    "JobsPayload",
    "JobsRequest",
    "WelfarePayload",
    "WelfareRequest",
    "AgentRequest",
    "AgentResponse",
]
