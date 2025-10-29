# 팀원을 위한 카테고리 추가 가이드

이 문서는 팀원들이 새로운 카테고리(복지, 뉴스, 사기 대응 등)를 추가하는 방법을 설명합니다.

## 공통 인프라 구조

공통 로직은 이미 구현되어 있습니다:

### 이미 구현된 것 (건드리지 마세요)
- ✅ `agent/graph.py` - LangGraph 빌드 로직
- ✅ `agent/nodes/` - 9개 공통 노드 (팩토리 패턴)
- ✅ `agent/router.py` - 디스패치 로직
- ✅ `agent/router_runtime.py` - 런타임 레지스트리
- ✅ `app/main.py` - FastAPI 엔트리포인트

### 팀원이 작업할 것
1. 카테고리별 데이터 수집 (`tools/` 디렉토리)
2. 카테고리별 훅 정의 (`agent/categories/`)
3. 카테고리별 스키마 정의 (`app/schemas.py`)
4. 런타임 등록 (`agent/router_runtime.py`)

---

## 새 카테고리 추가 4단계

### 예시: `welfare` (복지) 카테고리 추가

#### **Step 1: 데이터 수집 및 벡터화**

`tools/welfare_data.py` 생성:

```python
"""Welfare data collection and indexing."""
import chromadb
from langchain_upstage import UpstageEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import settings

def collect_welfare_data():
    """Collect welfare data from API/web."""
    # TODO: 복지 API 호출 로직
    data = []
    return data

def build_welfare_vectorstore():
    """Build ChromaDB vector store for welfare."""
    # 1. 데이터 수집
    raw_data = collect_welfare_data()

    # 2. 청킹
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = []
    for item in raw_data:
        chunks.extend(splitter.split_text(item["content"]))

    # 3. 임베딩 + ChromaDB 저장
    embeddings = UpstageEmbeddings(
        api_key=settings.upstage_api_key,
        model="solar-embedding-1-large",
    )

    client = chromadb.PersistentClient(path="data/chroma_welfare")
    collection = client.get_or_create_collection("welfare")

    for i, chunk in enumerate(chunks):
        embedding = embeddings.embed_query(chunk)
        collection.add(
            ids=[f"doc_{i}"],
            embeddings=[embedding],
            documents=[chunk],
        )

    print(f"✓ Indexed {len(chunks)} welfare documents")

if __name__ == "__main__":
    build_welfare_vectorstore()
```

실행:
```bash
python tools/welfare_data.py
```

---

#### **Step 2: 리트리버 구현**

`agent/retrievers/welfare_retriever.py` 생성:

```python
"""Welfare retriever."""
import chromadb
from langchain_upstage import UpstageEmbeddings
from langchain.schema import Document
from app.config import settings

class WelfareRetriever:
    def __init__(self, db_path="data/chroma_welfare", k=5):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection("welfare")
        self.embeddings = UpstageEmbeddings(
            api_key=settings.upstage_api_key,
            model="solar-embedding-1-large",
        )
        self.k = k

    def invoke(self, payload: dict) -> dict:
        """Retrieve welfare documents."""
        query = payload["query"]

        # Embed query
        query_embedding = self.embeddings.embed_query(query)

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.k,
        )

        # Convert to Documents
        documents = [
            Document(
                page_content=doc,
                metadata=meta,
            )
            for doc, meta in zip(
                results["documents"][0],
                results["metadatas"][0],
            )
        ]

        return {"documents": documents}

def get_welfare_retriever(k=5):
    return WelfareRetriever(k=k)
```

---

#### **Step 3: 카테고리 훅 정의**

`agent/categories/welfare.py` 생성:

```python
"""Welfare category hooks."""
from typing import Any
from agent.categories.base import CategoryHooks
from agent.retrievers.welfare_retriever import get_welfare_retriever

class WelfareHooks(CategoryHooks):
    """Hooks for welfare information category."""

    name: str = "welfare"

    rewrite_system_prompt: str = (
        "너는 복지 정보 검색 전문가다. "
        "사용자 질문을 복지 제도 검색에 적합하게 재작성하라. "
        "예: 연령, 소득, 거주지, 복지 유형 등."
    )

    answer_system_prompt: str = (
        "너는 복지 상담원이다. "
        "제공된 복지 제도 정보를 바탕으로 "
        "신청 방법, 자격 요건, 지원 내용을 명확히 답변하라."
    )

    top_k: int = 5
    min_relevance_threshold: float = 0.5

    def get_retriever(self) -> Any:
        """Return welfare retriever."""
        return get_welfare_retriever(k=self.top_k)

__all__ = ["WelfareHooks"]
```

---

#### **Step 4: 스키마 및 런타임 등록**

**4-1. `app/schemas.py` 에 스키마 추가:**

```python
# ============================================================================
# Welfare Category Schemas
# ============================================================================

class WelfarePayload(BaseModel):
    """Payload for welfare queries."""
    query: str
    age: Optional[int] = None
    income: Optional[int] = None
    location: Optional[str] = None

class WelfareRequest(BaseModel):
    """Welfare category request."""
    category: Literal["welfare"]
    payload: WelfarePayload

# ============================================================================
# Discriminated Union (여기에 추가!)
# ============================================================================

AgentRequest = Union[
    JobsRequest,
    WelfareRequest,  # ← 추가!
]
```

**4-2. `agent/router_runtime.py` 에 등록:**

```python
from agent.categories.welfare import WelfareHooks  # ← import 추가

def get_all_hooks() -> Dict[str, CategoryHooks]:
    """Get all registered category hooks."""
    return {
        "jobs": JobsHooks(),
        "welfare": WelfareHooks(),  # ← 추가!
    }
```

---

## 테스트

### 1. 로컬 테스트 (서버 없이)

```python
# scripts/test_welfare.py
from agent.router_runtime import get_runtime
from agent.router import dispatch
from app.schemas import WelfareRequest, WelfarePayload

graphs, hooks = get_runtime()

req = WelfareRequest(
    category="welfare",
    payload=WelfarePayload(
        query="65세 이상 기초연금 신청 방법",
        age=65,
        income=500000,
    ),
)

response = dispatch(req, graphs=graphs, hooks=hooks)
print(response.answer)
```

실행:
```bash
python scripts/test_welfare.py
```

### 2. FastAPI 서버 테스트

서버 실행:
```bash
python app/main.py
```

cURL 테스트:
```bash
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "category": "welfare",
    "payload": {
      "query": "65세 이상 기초연금 신청 방법",
      "age": 65,
      "income": 500000
    }
  }'
```

---

## 체크리스트

새 카테고리 추가 시 확인사항:

- [ ] `tools/{category}_data.py` - 데이터 수집 스크립트 작성
- [ ] `data/chroma_{category}/` - 벡터 저장소 생성
- [ ] `agent/retrievers/{category}_retriever.py` - 리트리버 구현
- [ ] `agent/categories/{category}.py` - Hooks 클래스 정의
- [ ] `app/schemas.py` - 스키마 추가 및 Union에 등록
- [ ] `agent/router_runtime.py` - 런타임 등록
- [ ] `scripts/test_{category}.py` - 테스트 스크립트 작성
- [ ] 로컬 테스트 통과 확인
- [ ] FastAPI 서버 테스트 통과 확인

---

## 공통 노드 활용

팀원이 구현한 훅은 다음 공통 노드들을 자동으로 활용합니다:

1. **rewrite_node** - `rewrite_system_prompt` 사용
2. **retrieve_node** - `get_retriever()` 호출
3. **gate_node** - `min_relevance_threshold` 사용
4. **websearch_node** - 웹 검색 (필요 시)
5. **merge_node** - 문서 병합
6. **generate_node** - `answer_system_prompt` 사용

각 노드는 팩토리 패턴으로 구현되어 있어 **커스터마이징 불필요**합니다.

---

## 문의사항

- 공통 인프라 질문: [담당자]
- 카테고리별 데이터 질문: 각 카테고리 담당자
- 배포 및 운영: [DevOps 담당자]

---

## 참고 자료

- LangChain 문서: https://python.langchain.com/
- LangGraph 문서: https://langchain-ai.github.io/langgraph/
- Upstage API: https://developers.upstage.ai/
- ChromaDB: https://docs.trychroma.com/
