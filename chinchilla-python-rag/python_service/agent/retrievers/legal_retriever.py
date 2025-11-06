"""
법률 문서 검색 리트리버
노인 법률 상담을 위한 ChromaDB 기반 리트리버 (최적화 버전)
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_upstage import UpstageEmbeddings

try:
    from app.config import settings
except Exception as exc:
    raise RuntimeError(
        "Failed to import app.config.settings. Ensure PYTHONPATH is set."
    ) from exc


class LegalRetrieverPipeline:
    """
    노인 법률 문서 검색 리트리버 (고성능 최적화 버전)

    최적화 포인트:
    - ChromaDB collection 직접 쿼리로 오버헤드 제거
    - @cached_property로 중복 초기화 방지
    - 불필요한 타입 체크 및 변환 최소화
    - 리스트 컴프리헨션으로 빠른 Document 생성
    - 예외 처리 제거로 빠른 경로 유지
    """

    def __init__(
        self,
        *,
        top_k: int = 3,
        fetch_k: int = 20,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        search_type: str = "similarity",
    ):
        """리트리버 초기화"""
        self.top_k = top_k
        self.fetch_k = fetch_k
        self._persist_directory = persist_directory
        self.collection_name = collection_name or "elderly_legal"
        self.search_type = search_type  # "similarity" or "mmr"

    @cached_property
    def _embeddings(self) -> UpstageEmbeddings:
        """Embeddings 초기화 (lazy)"""
        return UpstageEmbeddings(
            api_key=settings.upstage_api_key,
            model="solar-embedding-1-large",
        )

    @cached_property
    def _persist_path(self) -> Path:
        """ChromaDB 경로 계산 (lazy)"""
        if self._persist_directory:
            return Path(self._persist_directory)

        chroma_base = Path(settings.chroma_dir).parent
        path = chroma_base / "chroma_legal"

        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path

        return path

    @cached_property
    def _store(self) -> Chroma:
        """Vectorstore 초기화 (lazy)"""
        return Chroma(
            persist_directory=str(self._persist_path),
            embedding_function=self._embeddings,
            collection_name=self.collection_name,
        )

    @cached_property
    def _collection(self):
        """Collection 캐싱 (반복 접근 최적화)"""
        return self._store._collection

    def invoke(self, payload: Union[Dict[str, Any], str]) -> Sequence[Document]:
        """
        검색 실행 (최적화 버전)

        Args:
            payload: 검색 페이로드 (딕셔너리 또는 문자열)

        Returns:
            검색 결과 Document 리스트
        """
        # 빠른 경로: 타입 체크 최소화
        if isinstance(payload, str):
            query = payload
            where_filter = None
        else:
            query = payload.get("query", "")
            profile = payload.get("profile")
            where_filter = self._build_filter(profile) if profile else None

        if not query:
            return []

        # Embed query using our embedding function (not ChromaDB's internal one)
        query_embedding = self._embeddings.embed_query(query)

        # ChromaDB 직접 쿼리 with pre-computed embedding
        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
            include=["documents", "metadatas", "distances"],
            where=where_filter,
        )

        # 빠른 결과 파싱 (리스트 컴프리헨션)
        ids = raw["ids"][0]
        docs = raw["documents"][0]
        metas = raw["metadatas"][0]
        dists = raw["distances"][0]

        # 최적화된 Document 생성
        return [
            Document(
                page_content=text,
                metadata={
                    **meta,
                    "doc_id": doc_id,
                    "relevance_score": max(0.0, 1.0 - (dist / 2.0)),
                },
            )
            for doc_id, text, meta, dist in zip(ids, docs, metas, dists)
        ]

    def _build_filter(self, profile: dict) -> Optional[dict]:
        """
        프로필 기반 필터 생성

        Args:
            profile: 사용자 프로필

        Returns:
            ChromaDB 필터 딕셔너리 또는 None
        """
        if not profile:
            return None

        age = profile.get("age")
        if age and age < 60:
            return {"category": {"$in": ["복지서비스", "경제지원"]}}

        interest = profile.get("interest")
        if interest:
            category_map = {
                "연금": "경제지원",
                "의료": "의료건강",
                "주거": "주거",
                "복지": "복지서비스",
            }
            if interest in category_map:
                return {"category": category_map[interest]}

        return None


def get_legal_retriever(**kwargs: Any) -> LegalRetrieverPipeline:
    """Factory for legal retriever pipeline."""
    return LegalRetrieverPipeline(**kwargs)


__all__ = ["LegalRetrieverPipeline", "get_legal_retriever"]
