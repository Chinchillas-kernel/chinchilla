"""
금융 사기 패턴 검색 리트리버
사기 문자 탐지 및 대응을 위한 ChromaDB 기반 리트리버
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Any, Tuple

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_upstage import UpstageEmbeddings

try:
    from app.config import settings
except Exception as exc:
    raise RuntimeError(
        "Failed to import app.config.settings. Ensure PYTHONPATH is set."
    ) from exc


class ScamRetrieverWrapper(BaseRetriever):
    """
    사기 패턴 검색을 위한 래퍼
    similarity_search_with_score를 호출하여 관련도 점수를 메타데이터에 주입
    """
    vectorstore: Chroma
    search_kwargs: dict

    def _get_relevant_documents(
        self, query: Any, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """
        쿼리를 받아서 문서를 검색하고 관련도 점수를 메타데이터에 추가
        """
        actual_query = ""
        if isinstance(query, dict):
            actual_query = query.get("query", "")
        elif isinstance(query, str):
            actual_query = query

        if not actual_query:
            return []

        # 점수와 함께 검색
        results_with_scores: List[Tuple[Document, float]] = (
            self.vectorstore.similarity_search_with_score(
                query=actual_query,
                k=self.search_kwargs.get("k", 8),
                filter=self.search_kwargs.get("filter"),
            )
        )

        # 관련도 점수를 메타데이터에 주입
        final_docs = []
        for doc, score in results_with_scores:
            doc.metadata["relevance_score"] = score
            final_docs.append(doc)

        return final_docs


class ScamDefenseRetriever:
    """
    금융 사기 패턴 검색 리트리버

    ChromaDB에 저장된 사기 패턴 및 지식 베이스를 검색하는 리트리버
    """

    def __init__(
        self,
        collection_name: str = "scam_defense",
        persist_directory: Optional[str] = None,
    ):
        """
        리트리버 초기화
        """
        self.collection_name = collection_name

        # ChromaDB 경로 설정
        if persist_directory:
            self.persist_directory = Path(persist_directory)
        else:
            # 기본 경로: data/chroma_scam_defense
            self.persist_directory = Path("data/chroma_scam_defense")

        # Embeddings 초기화
        self.embeddings = UpstageEmbeddings(
            api_key=settings.upstage_api_key, model="solar-embedding-1-large"
        )

        # ChromaDB 클라이언트
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory.absolute()),
            settings=Settings(anonymized_telemetry=False),
        )

        # 컬렉션 존재 확인
        try:
            self.collection = self.client.get_collection(self.collection_name)
            print(
                f"[INFO] Loaded collection: {self.collection_name} ({self.collection.count()} docs)"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load collection '{self.collection_name}'. "
                f"Run vector DB build script first. Error: {e}"
            ) from e

        # Vectorstore 초기화
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def get_retriever(
        self,
        scam_type: Optional[str] = None,
        search_type: str = "similarity",
        k: int = 8,
        fetch_k: int = 20,
    ) -> BaseRetriever:
        """
        검색 리트리버 생성
        점수 주입 및 딕셔너리 입력을 처리하는 래퍼를 반환
        """
        search_kwargs = {"k": k}

        # 사기 유형별 필터링
        if scam_type:
            filter_dict = {"scam_type": scam_type}
            search_kwargs["filter"] = filter_dict

        # 래퍼 반환
        return ScamRetrieverWrapper(
            vectorstore=self.vectorstore, search_kwargs=search_kwargs
        )

    def search(
        self,
        query: str,
        k: int = 8,
        scam_type: Optional[str] = None,
    ) -> list:
        """
        직접 검색 (디버깅용)
        """
        retriever = self.get_retriever(scam_type=scam_type, k=k)
        results = retriever.invoke(query)
        return results


def get_scam_defense_retriever(
    profile: Optional[dict] = None,
    config: Optional[dict] = None,
) -> BaseRetriever:
    """
    사기 탐지 리트리버 생성 팩토리 함수

    Args:
        profile: 사용자 프로필 (사기 유형 필터링 등)
        config: 추가 설정 (k, search_type 등)

    Returns:
        BaseRetriever: 사기 패턴 검색 리트리버
    """
    retriever_obj = ScamDefenseRetriever()

    # 설정 파라미터
    k = 8
    scam_type = None

    if config:
        k = config.get("k", 8)

    if profile:
        scam_type = profile.get("scam_type")

    return retriever_obj.get_retriever(scam_type=scam_type, k=k)
