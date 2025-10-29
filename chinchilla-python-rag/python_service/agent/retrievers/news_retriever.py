"""News retriever with MMR search and relevance filtering.
뉴스 데이터를 ChromaDB에서 검색하는  리트리버를 제공.
Upstaege Embeddings를 사용하여 의미론적 검색을 수행.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import chromadb
from langchain.schema import Document
from langchain_upstage import UpstageEmbeddings

from app.config import settings


@dataclass
class NewsRetrievalResult:
    """뉴스 검색 결과를 담는 컨테이너.

    Attributes:
        query: 검색에 사용된 쿼리 문자열
        documents: 검색된 Document 객체 리스트
    """

    query: str
    documents: List[Document] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """결과를 딕셔너리로 변환.

        Returns:
            쿼리와 문서 리스트를 포함한 딕셔너리
        """
        return {
            "query": self.query,
            "documents": [
                {"page_content": doc.page_content, "metadata": dict(doc.metadata)}
                for doc in self.documents
            ],
        }


class NewsRetriever:
    """뉴스 문서 검색을 위한 리트리버 클래스

    ChromaDB를 사용하여 벡터 검색을 수행,
    Upstage Embeddings로 쿼리를 임베딩
    """

    def __init__(
        self,
        db_path: str = "data/chroma_news",
        collection_name: str = "news",
        k: int = 5,
    ):
        """뉴스 리트리버 초기화.

        Args:
            db_path: ChromaDB 영구 저장소 경로
            collection_name: 사용할 컬렉션 이름
            k: 검색할 문서 개수
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.k = k

        # ChromaDB 클라이언트 및 컬렉션 초기화
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(collection_name)

        # Upstage Embeddings 초기화
        self.embeddings = UpstageEmbeddings(
            api_key=settings.upstage_api_key,
            model="solar-embedding-1-large",
        )

    def _embed_query(self, query: str) -> List[float]:
        """쿼리 텍스트를 Upstage Embeddings로 임베딩.

        Args:
            query: 임베딩할 쿼리 텍스트

        Returns:
            임베딩 벡터 (float 리스트)
        """
        return self.embeddings.embed_query(query)

    def retrieve(
        self,
        query: str,
        n_results: Optional[int] = None,
    ) -> List[Document]:
        """관련 뉴스 문서를 검색.

        Args:
            query: 검색 쿼리
            n_results: 검색할 결과 개수 (기본값: self.k)

        Returns:
            관련성 높은 Document 객체 리스트
        """
        if n_results is None:
            n_results = self.k

        # 쿼리 임베딩 생성
        query_embedding = self._embed_query(query)

        # ChromaDB에서 검색 수행
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        # LangChain Document로 변환
        documents = []
        if results["documents"] and results["documents"][0]:
            for doc, meta in zip(
                results["documents"][0],
                (
                    results["metadatas"][0]
                    if results["metadatas"]
                    else [{}] * len(results["documents"][0])
                ),
            ):
                documents.append(
                    Document(
                        page_content=doc,
                        metadata=meta or {},
                    )
                )

        return documents

    def invoke(self, payload: Dict[str, Any]) -> NewsRetrievalResult:
        """LangChain 호환 인터페이스로 검색 수행.
        이 메서드는 LangGraph 노드에서 호출될 때 사용됨

        Args:
            payload: "query" 키를 포함한 딕셔너리

        Returns:
            검색된 문서를 포함한 NewsRetrievalResult

        Raises:
            ValueError: query가 payload에 없을 경우
        """
        query = payload.get("query")
        if not query:
            raise ValueError("query is required for new retrieval")

        # 문서 검색 수행
        documents = self.retrieve(query)

        return NewsRetrievalResult(
            query=query,
            documents=documents,
        )

    # invoke() 메서드를 __call__로도 호출 가능하게
    __call__ = invoke


def get_news_retriever(
    k: int = 5,
    db_path: str = "data/chroma_news",
    collection_name: str = "news",
) -> NewsRetriever:
    """뉴스 리트리버 인스턴스를 생성하는 팩토리 함수.
    이 함수는 카테고리 훅에서 호출됨

    Args:
        k: 검색할 문서 개수
        db_path: ChromaDB 저장소 경로
        collection_name: 컬렉션 이름

    Returns:
        설정된 NewsRetriever 인스턴스

    Example:
        >>> retriever = get_news_retriever(k=10)
        >>> result = retriever.invoke({"query": "노인 복지 정책"})
        >>> print(f"찾은 문서: {len(result.documents)}개")
    """
    return NewsRetriever(
        db_path=db_path,
        collection_name=collection_name,
        k=k,
    )


__all__ = [
    "NewsRetriever",
    "NewsRetrievalResult",
    "get_news_retriever",
]
