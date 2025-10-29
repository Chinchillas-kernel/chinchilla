"""Retriever facade for the elderly jobs vector store."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from langchain.schema import Document

from app.schemas import JobsProfile
from agent.retrievers.job_retriever import ElderlyJobRetriever


PROVINCE_ALIASES = {
    "서울": "서울",
    "서울시": "서울",
    "서울특별시": "서울",
    "부산": "부산",
    "부산광역시": "부산",
    "대구": "대구",
    "대구광역시": "대구",
    "인천": "인천",
    "인천광역시": "인천",
    "광주": "광주",
    "광주광역시": "광주",
    "대전": "대전",
    "대전광역시": "대전",
    "울산": "울산",
    "울산광역시": "울산",
    "세종": "세종",
    "세종특별자치시": "세종",
    "경기": "경기",
    "경기도": "경기",
    "강원": "강원",
    "강원도": "강원",
    "충북": "충북",
    "충청북": "충북",
    "충청북도": "충북",
    "충남": "충남",
    "충청남": "충남",
    "충청남도": "충남",
    "전북": "전북",
    "전라북": "전북",
    "전라북도": "전북",
    "전남": "전남",
    "전라남": "전남",
    "전라남도": "전남",
    "경북": "경북",
    "경상북": "경북",
    "경상북도": "경북",
    "경남": "경남",
    "경상남": "경남",
    "경상남도": "경남",
    "제주": "제주",
    "제주도": "제주",
    "제주특별자치도": "제주",
}


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _normalize_province_token(token: str) -> str:
    token_no_space = token.replace(" ", "")
    if token in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[token]
    if token_no_space in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[token_no_space]
    trimmed = re.sub(
        r"(특별자치도|특별자치시|광역시|특별시|자치도)$",
        "",
        token_no_space,
    )
    trimmed = re.sub(r"(도|시)$", "", trimmed)
    if trimmed in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[trimmed]
    return trimmed or token


def _normalize_location(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    cleaned = re.sub(r"[,/]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None, None
    parts = cleaned.split(" ")
    province = _normalize_province_token(parts[0])
    city = " ".join(parts[1:]) if len(parts) > 1 else None
    return province or None, city or None


def _build_filters(profile: JobsProfile) -> Optional[Dict[str, Any]]:
    conditions: List[Dict[str, Any]] = []
    province, city = _normalize_location(profile.location)
    if province:
        conditions.append({"region_province": province})
    if city:
        conditions.append({"region_city": city})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _filter_by_age(docs: Iterable[Document], age: Optional[int]) -> List[Document]:
    if not age:
        return list(docs)
    filtered: List[Document] = []
    for doc in docs:
        min_age = _coerce_int(doc.metadata.get("min_age"))
        if min_age is None or min_age <= age:
            filtered.append(doc)
    return filtered


@dataclass
class JobsRetrievalInput:
    query: str
    profile: Optional[JobsProfile] = None


@dataclass
class JobsRetrievalResult:
    query: str
    profile: Optional[JobsProfile] = None
    filters: Optional[Dict[str, Any]] = None
    documents: List[Document] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "profile": (
                self.profile.model_dump() if self.profile and hasattr(self.profile, "model_dump")
                else self.profile
            ),
            "filters": self.filters,
            "documents": [
                {"page_content": doc.page_content, "metadata": dict(doc.metadata)}
                for doc in self.documents
            ],
        }


class JobsRetrieverPipeline:
    """Wrapper around :class:`ElderlyJobRetriever` with profile-aware filtering."""

    def __init__(
        self,
        *,
        top_k: int = 8,
        fetch_multiplier: int = 3,
        collection_name: str = "elderly_jobs",
        db_path: Optional[str] = None,
        retriever: Optional[ElderlyJobRetriever] = None,
    ) -> None:
        self.top_k = max(1, top_k)
        self.fetch_multiplier = max(1, fetch_multiplier)
        self.collection_name = collection_name
        self._db_path = db_path
        self._inject_retriever = retriever

    @cached_property
    def _retriever(self) -> ElderlyJobRetriever:
        if self._inject_retriever is not None:
            return self._inject_retriever
        return ElderlyJobRetriever(
            db_path=self._db_path,
            collection_name=self.collection_name,
        )

    def _ensure_profile(self, profile: Union[JobsProfile, Dict[str, Any]]) -> JobsProfile:
        if isinstance(profile, JobsProfile):
            return profile
        return JobsProfile(**profile)

    def invoke(self, payload: Union[Dict[str, Any], JobsRetrievalInput]) -> JobsRetrievalResult:
        if isinstance(payload, dict):
            query = payload.get("query")
            profile = payload.get("profile")
        else:
            query = payload.query
            profile = payload.profile
        if not query:
            raise ValueError("query is required for jobs retrieval")

        # Profile is now optional (for Level 3+ no-filter searches)
        if profile is None:
            # No profile: retrieve without any filters
            raw_docs = self._retriever.retrieve(query, n_results=self.top_k, filters=None)
            return JobsRetrievalResult(
                query=query,
                profile=None,
                filters=None,
                documents=raw_docs,
            )

        # Profile provided: apply filters
        normalized_profile = self._ensure_profile(profile)
        filters = _build_filters(normalized_profile)
        fetch_k = self.top_k * self.fetch_multiplier
        raw_docs = self._retriever.retrieve(query, n_results=fetch_k, filters=filters)
        ranked_docs = _filter_by_age(raw_docs, normalized_profile.age)[: self.top_k]
        return JobsRetrievalResult(
            query=query,
            profile=normalized_profile,
            filters=filters,
            documents=ranked_docs,
        )

    __call__ = invoke


def get_jobs_retriever(
    *,
    k: int = 8,
    fetch_multiplier: int = 3,
    collection_name: str = "elderly_jobs",
    db_path: Optional[str] = None,
) -> JobsRetrieverPipeline:
    """Factory used by category hooks."""

    return JobsRetrieverPipeline(
        top_k=k,
        fetch_multiplier=fetch_multiplier,
        collection_name=collection_name,
        db_path=db_path,
    )


__all__ = [
    "JobsRetrieverPipeline",
    "JobsRetrievalResult",
    "JobsRetrievalInput",
    "get_jobs_retriever",
]
