# RAG Agent 아키텍처 문서

## 시스템 개요

노인 행정도우미 시스템은 **카테고리별 훅 주입 + 공통 그래프 재사용** 패턴을 사용하는 확장 가능한 RAG 기반 멀티 카테고리 에이전트입니다.

### 핵심 설계 원칙

1. **공통 로직 재사용**: 모든 카테고리가 동일한 LangGraph 워크플로우 사용
2. **훅 주입 패턴**: 카테고리별 차이점은 Hooks 클래스로 주입
3. **팩토리 패턴**: 노드는 hooks를 받아 런타임에 생성
4. **Discriminated Union**: Pydantic으로 타입 안전한 요청 처리

---

## 아키텍처 다이어그램

### 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (Spring)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓ POST /agent/query
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI (app/main.py)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. Request Validation (Pydantic Discriminated Union)    │   │
│  │     → JobsRequest | WelfareRequest | NewsRequest ...     │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              Router (agent/router.py)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  dispatch(req, graphs, hooks)                            │   │
│  │    → Extract category from discriminated union           │   │
│  │    → Get compiled graph from cache                       │   │
│  │    → Build initial state                                 │   │
│  │    → Execute graph.invoke(state)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│         LangGraph Workflow (agent/graph.py)                     │
│                                                                 │
│  START                                                          │
│    ↓                                                            │
│  ┌───────────┐   hooks.rewrite_system_prompt                   │
│  │  rewrite  │ ──────────────────────────────────→ Upstage LLM │
│  └─────┬─────┘                                                  │
│        ↓                                                        │
│  ┌────────────┐  hooks.get_retriever()                         │
│  │  retrieve  │ ──────────────────────────────→ ChromaDB       │
│  └─────┬──────┘                                                 │
│        ↓                                                        │
│  ┌──────────┐   hooks.min_relevance_threshold                  │
│  │   gate   │ ────────────────────────────────→ Decision       │
│  └─────┬────┘                                                   │
│        │                                                        │
│    ┌───┴───┐                                                   │
│    ↓       ↓                                                   │
│  문서 충분  문서 부족                                          │
│    │       │                                                   │
│    │    ┌──────────┐                                           │
│    │    │websearch │ ───────────────────────→ SerpAPI         │
│    │    └────┬─────┘                                           │
│    │         ↓                                                 │
│    │    ┌────────┐                                             │
│    │    │ merge  │ (deduplicate)                               │
│    │    └────┬───┘                                             │
│    │         │                                                 │
│    └────┬────┘                                                 │
│         ↓                                                      │
│  ┌─────────────┐  hooks.answer_system_prompt                  │
│  │  generate   │ ──────────────────────────────→ Upstage LLM  │
│  └──────┬──────┘                                               │
│         ↓                                                      │
│       END                                                      │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 컴포넌트 상세

### 1. FastAPI Layer (`app/`)

#### `app/main.py`
- FastAPI 앱 초기화
- `get_runtime()` 호출 → 모든 카테고리 그래프 빌드 (서버 시작 시 1회)
- `/agent/query` 엔드포인트 등록

#### `app/schemas.py`
- Discriminated Union 패턴으로 카테고리별 요청 타입 정의
- Pydantic이 자동으로 `category` 필드로 라우팅

```python
AgentRequest = Union[
    JobsRequest,      # category: "jobs"
    WelfareRequest,   # category: "welfare"
    # ... 팀원이 추가
]
```

#### `app/config.py`
- `.env` 파일 읽기 (Pydantic Settings)
- API 키, 디렉토리 경로 관리

---

### 2. Router Layer (`agent/router*.py`)

#### `agent/router_runtime.py`
- **런타임 레지스트리**: 카테고리 → (Hooks, Graph) 매핑
- `get_runtime()`: 서버 시작 시 모든 그래프를 미리 빌드하여 캐시

```python
def get_all_hooks():
    return {
        "jobs": JobsHooks(),
        "welfare": WelfareHooks(),  # 팀원이 추가
    }

def get_runtime():
    hooks = get_all_hooks()
    graphs = {cat: build_graph(hook) for cat, hook in hooks.items()}
    return graphs, hooks
```

#### `agent/router.py`
- `dispatch(req, graphs, hooks)`: 요청 디스패치
- 카테고리 추출 → 그래프 선택 → State 빌드 → 실행

---

### 3. Graph Layer (`agent/graph.py`)

#### `AgentState` (TypedDict)
모든 카테고리가 공유하는 상태 구조:

```python
class AgentState(TypedDict, total=False):
    category: str           # 카테고리 식별
    query: str              # 원본 쿼리
    profile: Dict           # 카테고리별 프로필 (optional)
    rewritten_query: str    # 재작성된 쿼리
    documents: list         # 검색된 문서
    web_documents: list     # 웹 검색 문서
    answer: str             # 최종 답변
    sources: list           # 근거 문서
```

#### `build_graph(hooks)`
- 훅을 받아 LangGraph 빌드
- 노드 팩토리에 hooks 주입
- 엣지 정의 및 컴파일

---

### 4. Nodes Layer (`agent/nodes/`)

모든 노드는 **팩토리 패턴**:

```python
def make_{node}_node(hooks: CategoryHooks) -> Callable:
    def {node}_node(state: dict) -> dict:
        # hooks에서 필요한 설정 가져오기
        # 노드 로직 실행
        return updated_state
    return {node}_node
```

#### 노드 목록

| 노드 | 역할 | Hooks 사용 |
|------|------|-----------|
| `precheck` | 입력 검증 | - |
| `rewrite` | 쿼리 재작성 | `rewrite_system_prompt` |
| `retrieve` | 문서 검색 | `get_retriever()` |
| `gate` | 웹서치 분기 | `min_relevance_threshold` |
| `websearch` | 웹 검색 | - |
| `merge` | 문서 병합 | - |
| `plan` | 쿼리 분해 (optional) | - |
| `generate` | 답변 생성 | `answer_system_prompt` |
| `safety` | 안전 필터 | - |

---

### 5. Categories Layer (`agent/categories/`)

#### `base.py` - `CategoryHooks` (ABC)
모든 카테고리가 상속해야 하는 베이스 클래스:

```python
class CategoryHooks(BaseModel, ABC):
    name: str                      # 카테고리 이름
    rewrite_system_prompt: str     # 쿼리 재작성 프롬프트
    answer_system_prompt: str      # 답변 생성 프롬프트
    min_relevance_threshold: float # 관련도 임계값
    top_k: int                     # 검색 개수

    @abstractmethod
    def get_retriever(self) -> Any:
        """카테고리별 리트리버 반환"""
        raise NotImplementedError
```

#### 카테고리별 구현 예시
- `jobs.py` - `JobsHooks`
- `welfare.py` - `WelfareHooks` (팀원이 추가)
- `news.py` - `NewsHooks` (팀원이 추가)

---

### 6. Retrievers Layer (`agent/retrievers/`)

카테고리별 벡터 검색 로직:

```python
class CategoryRetriever:
    def __init__(self, db_path, collection_name):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(collection_name)
        self.embeddings = UpstageEmbeddings(...)

    def invoke(self, payload: dict) -> dict:
        query = payload["query"]
        # ... 검색 로직
        return {"documents": [...]}
```

---

## 데이터 흐름

### 1. 요청 단계

```
Client → FastAPI → Pydantic Validation
                 → Discriminated Union 라우팅
                 → JobsRequest | WelfareRequest | ...
```

### 2. 디스패치 단계

```
dispatch(req, graphs, hooks)
  → category 추출
  → graphs[category] 선택 (미리 컴파일된 그래프)
  → initial_state 생성
  → graph.invoke(state)
```

### 3. 그래프 실행 단계

```
rewrite (LLM) → retrieve (ChromaDB) → gate (분기)
                                        ↓
                            문서 충분? 문서 부족?
                                ↓           ↓
                            generate    websearch → merge → generate
```

### 4. 응답 단계

```
{answer, sources, metadata} → AgentResponse → JSON → Client
```

---

## 확장성

### 새 카테고리 추가 시

1. **데이터 레이어**: `tools/{category}_data.py` (수집 + 벡터화)
2. **리트리버 레이어**: `agent/retrievers/{category}_retriever.py`
3. **훅 레이어**: `agent/categories/{category}.py` (Hooks 정의)
4. **스키마 레이어**: `app/schemas.py` (Request 추가 + Union 등록)
5. **런타임 레이어**: `agent/router_runtime.py` (레지스트리 등록)

**공통 그래프, 노드, 라우터는 수정 불필요!**

---

## 성능 최적화

### 그래프 캐싱
- 서버 시작 시 `get_runtime()` → 모든 그래프 미리 컴파일
- 요청마다 그래프 재빌드 없음 → **빠른 응답**

### 벡터 검색 최적화
- ChromaDB 영구 저장소 사용
- Upstage Solar Embedding (1024 dim)
- 프로필 기반 메타데이터 필터링 (jobs)

### LLM 호출 최적화
- Upstage Solar-Pro (빠른 응답)
- 2단계만 LLM 호출 (rewrite + generate)

---

## 보안 및 안전

### 입력 검증
- Pydantic strict validation
- `precheck` 노드 (길이, 형식 검사)

### 안전 필터
- `safety` 노드 (답변 필터링)
- 카테고리별 정책 확장 가능

### API 키 관리
- `.env` 파일 (git ignore)
- Pydantic Settings 자동 로드

---

## 모니터링 및 로깅

### 현재 구현
- 콘솔 로그 (print)
- 에러 핸들링 (try-except)

### 향후 개선
- Structured logging (JSON)
- LangSmith 연동 (LangChain 추적)
- 메트릭 수집 (Prometheus)
- 분산 추적 (OpenTelemetry)

---

## 기술 스택 요약

| Layer | Technology |
|-------|------------|
| Framework | FastAPI, Pydantic v2 |
| Orchestration | LangGraph |
| LLM | Upstage Solar-Pro |
| Embedding | Upstage Solar-Embedding-1-Large |
| Vector Store | ChromaDB (persistent) |
| Web Search | SerpAPI (optional) |
| Validation | Pydantic Discriminated Union |
| Pattern | Factory + Hooks Injection |

---

## 참고 문서

- [팀원 가이드](./TEAM_GUIDE.md) - 카테고리 추가 방법
- [구현 가이드](./IMPLEMENTATION_GUIDE.md) - 상세 구현 내역
- LangGraph: https://langchain-ai.github.io/langgraph/
- Upstage API: https://developers.upstage.ai/
