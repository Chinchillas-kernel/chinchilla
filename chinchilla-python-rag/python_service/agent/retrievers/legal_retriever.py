"""
법률 문서 검색 리트리버
노인 법률 상담을 위한 ChromaDB 기반 리트리버
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever
from langchain_upstage import UpstageEmbeddings

try:
    from app.config import settings
except Exception as exc:
    raise RuntimeError(
        "Failed to import app.config.settings. Ensure PYTHONPATH is set."
    ) from exc


class LegalRetriever:
    """
    노인 법률 문서 검색 리트리버

    ChromaDB에 저장된 법률 문서를 검색하는 리트리버를 생성합니다.
    프로필 기반 필터링을 지원합니다.
    """

    def __init__(
        self,
        collection_name: str = "elderly_legal",
        persist_directory: Optional[str] = None,
    ):
        """
        리트리버 초기화

        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_directory: ChromaDB 저장 경로 (None이면 기본 경로 사용)
        """
        self.collection_name = collection_name

        # ChromaDB 경로 설정
        if persist_directory:
            self.persist_directory = Path(persist_directory)
        else:
            chroma_base = Path(settings.chroma_dir).parent
            self.persist_directory = chroma_base / "chroma_legal"

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
                f"Run 'python tools/legal_data.py' first. Error: {e}"
            ) from e

        # Vectorstore 초기화
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def get_retriever(
        self,
        profile: Optional[dict] = None,
        search_type: str = "mmr",
        k: int = 5,
        fetch_k: int = 20,
    ) -> BaseRetriever:
        """
        검색 리트리버 생성

        Args:
            profile: 사용자 프로필 (예: {"age": 70, "region": "서울"})
            search_type: 검색 방식 ("similarity" 또는 "mmr")
            k: 반환할 문서 개수
            fetch_k: MMR을 위한 초기 검색 개수

        Returns:
            BaseRetriever 인스턴스
        """
        search_kwargs = {
            "k": k,
        }

        # MMR 설정
        if search_type == "mmr":
            search_kwargs["fetch_k"] = fetch_k

        # 프로필 기반 필터링 (선택적)
        if profile:
            filter_dict = self._build_filter(profile)
            if filter_dict:
                search_kwargs["filter"] = filter_dict
                print(f"[INFO] Applying filter: {filter_dict}")

        retriever = self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
        )

        return retriever

    def _build_filter(self, profile: dict) -> Optional[dict]:
        """
        프로필 기반 필터 생성

        Args:
            profile: 사용자 프로필

        Returns:
            ChromaDB 필터 딕셔너리 또는 None
        """
        filter_dict = {}

        # 나이 기반 필터링 (예시)
        age = profile.get("age")
        if age and age < 60:
            # 60세 미만이면 장애인복지법도 포함
            filter_dict["category"] = {"$in": ["복지서비스", "경제지원"]}

        # 지역 기반 필터링 (메타데이터에 region이 있다면)
        region = profile.get("region")
        if region:
            # 지역별 조례가 메타데이터에 있다면
            pass  # 구현 가능

        # 관심 카테고리 지정 (예시)
        interest = profile.get("interest")
        if interest:
            category_map = {
                "연금": "경제지원",
                "의료": "의료건강",
                "주거": "주거",
                "복지": "복지서비스",
            }
            if interest in category_map:
                filter_dict["category"] = category_map[interest]

        return filter_dict if filter_dict else None

    def search(
        self,
        query: str,
        k: int = 5,
        profile: Optional[dict] = None,
    ) -> list:
        """
        직접 검색 (디버깅용)

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수
            profile: 사용자 프로필

        Returns:
            검색 결과 리스트
        """
        retriever = self.get_retriever(profile=profile, k=k)
        results = retriever.invoke(query)
        return results


# 테스트 및 디버깅용
if __name__ == "__main__":
    """리트리버 테스트"""

    print("\n" + "=" * 70)
    print("🔍 법률 리트리버 테스트")
    print("=" * 70 + "\n")

    # 리트리버 초기화
    try:
        legal_retriever = LegalRetriever()
    except Exception as e:
        print(f"❌ 리트리버 초기화 실패: {e}")
        print("💡 'python tools/legal_data.py --reset' 먼저 실행하세요")
        exit(1)

    # 테스트 쿼리
    test_queries = [
        {
            "query": "기초연금 신청 자격은 무엇인가요?",
            "profile": {"age": 68},
        },
        {
            "query": "노인복지시설의 종류는?",
            "profile": None,
        },
        {
            "query": "치매 환자를 위한 지원은?",
            "profile": {"age": 75},
        },
        {
            "query": "주택 임대차 계약 갱신",
            "profile": {"age": 70},
        },
    ]

    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        profile = test_case["profile"]

        print(f"[테스트 {i}] {query}")
        if profile:
            print(f"   프로필: {profile}")
        print("-" * 70)

        try:
            # 검색
            results = legal_retriever.search(query, k=3, profile=profile)

            if results:
                print(f"✅ {len(results)}개 문서 검색됨\n")

                for j, doc in enumerate(results, 1):
                    law_name = doc.metadata.get("law_name", "Unknown")
                    category = doc.metadata.get("category", "")
                    chunk_size = doc.metadata.get("chunk_size", 0)

                    print(f"   {j}. 📚 {law_name} [{category}]")
                    print(f"      크기: {chunk_size}자")
                    print(f"      내용: {doc.page_content[:150]}...\n")
            else:
                print("❌ 검색 결과 없음\n")

        except Exception as e:
            print(f"❌ 검색 실패: {e}\n")

        print()

    print("=" * 70)
    print("✅ 테스트 완료!")
    print("=" * 70 + "\n")
