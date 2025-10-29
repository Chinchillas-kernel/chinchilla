# 노인 행정도우미 RAG Agent 시스템

LangChain, LangGraph, Upstage API, ChromaDB를 활용한 멀티 카테고리 RAG 기반 에이전트 시스템

## 프로젝트 개요

**목표**: RAG를 이용하여 Knowledge Base와 Web Search를 활용, 정확한 지식 기반 답변을 제공하는 카테고리별 에이전트 시스템

**핵심 특징**:
- ✅ LangChain + LangGraph 기반 RAG 파이프라인
- ✅ Upstage Solar-Pro LLM + Solar-Embedding
- ✅ ChromaDB 벡터 저장소
- ✅ 1-2초 이내 응답 시간
- ✅ 카테고리별 확장 가능한 아키텍처
- ✅ 근거 문서(sources) 제공

## 시스템 구조

```
python_service/
├── app/
│   ├── main.py          # FastAPI 엔트리포인트
│   ├── config.py        # 환경 설정
│   └── schemas.py       # 요청/응답 스키마
├── agent/
│   ├── graph.py         # LangGraph 워크플로우 빌더
│   ├── router.py        # 요청 디스패치
│   ├── router_runtime.py # 런타임 레지스트리
│   ├── categories/      # 카테고리별 훅
│   │   ├── base.py      # CategoryHooks 베이스
│   │   └── jobs.py      # JobsHooks 구현
│   ├── nodes/           # 공통 노드 (팩토리 패턴)
│   │   ├── rewrite.py   # 쿼리 재작성
│   │   ├── retrieve.py  # 문서 검색
│   │   ├── gate.py      # 웹서치 분기
│   │   ├── websearch.py # 웹 검색
│   │   ├── merge.py     # 문서 병합
│   │   └── generate.py  # 답변 생성
│   └── retrievers/      # 카테고리별 리트리버
│       ├── job_retriever.py
│       └── jobs_retriever.py
├── tools/               # 데이터 수집 ETL
├── scripts/             # 테스트 스크립트
├── data/
│   ├── chroma_jobs/     # 벡터 저장소
│   └── raw/             # 원본 데이터
└── claudedocs/          # 문서
    ├── ARCHITECTURE.md  # 아키텍처 설명
    └── TEAM_GUIDE.md    # 팀원 가이드
```

## 빠른 시작

### 1. 환경 설정

```bash
cd python_service

# 가상환경 생성 (Python 3.11)
conda create -n rag-agent python=3.11
conda activate rag-agent

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
```

`.env` 파일 수정:
```bash
UPSTAGE_API_KEY=your_key_here
SERP_API_KEY=your_key_here  # optional
CHROMA_DIR=data/chroma_jobs
```

### 2. 데이터 준비 (이미 완료된 경우 스킵)

```bash
# Jobs 카테고리 데이터 수집 및 벡터화
python tools/work_data.py
```

### 3. 로컬 테스트

```bash
# 워크플로우 테스트 (서버 없이)
python scripts/test_agent.py
```

### 4. 서버 실행

```bash
# 개발 모드
python app/main.py

# 또는
uvicorn app.main:app --reload --port 8000
```

### 5. API 테스트

```bash
# Health check
curl http://localhost:8000/health

# Jobs 쿼리
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "category": "jobs",
    "payload": {
      "query": "서울 용산구에서 경비 일자리 찾고 있습니다",
      "profile": {
        "age": 65,
        "gender": "male",
        "location": "서울 용산구"
      }
    }
  }'
```

## API 사용법

### 엔드포인트

- `GET /` - 서비스 정보
- `GET /health` - 헬스 체크
- `POST /agent/query` - 메인 쿼리 엔드포인트

### 요청 형식

```json
{
  "category": "jobs",
  "payload": {
    "query": "사용자 질문",
    "profile": {
      "age": 65,
      "gender": "male",
      "location": "서울 용산구"
    }
  }
}
```

### 응답 형식

```json
{
  "answer": "답변 내용...",
  "sources": [
    {
      "content": "문서 내용 발췌...",
      "metadata": {
        "job_title": "경비원",
        "organization": "OO관리공단",
        "relevance_score": 0.85
      }
    }
  ],
  "metadata": {
    "category": "jobs",
    "rewritten_query": "서울 용산구 경비 일자리"
  }
}
```

## 워크플로우

```
Client Request
    ↓
FastAPI (/agent/query)
    ↓
Router.dispatch()
    ↓
LangGraph Workflow
    ↓
┌─────────────────────────────┐
│  rewrite → retrieve → gate  │
│      ↓           ↓          │
│  (문서 충분)  (문서 부족)   │
│      ↓           ↓          │
│  generate    websearch      │
│                 ↓           │
│              merge          │
│                 ↓           │
│              generate       │
└─────────────────────────────┘
    ↓
{answer, sources}
```

## 카테고리 추가

팀원이 새 카테고리를 추가하는 방법은 [`claudedocs/TEAM_GUIDE.md`](./claudedocs/TEAM_GUIDE.md) 참고

### 간단 요약

1. **데이터 수집**: `tools/{category}_data.py`
2. **리트리버 구현**: `agent/retrievers/{category}_retriever.py`
3. **훅 정의**: `agent/categories/{category}.py`
4. **스키마 등록**: `app/schemas.py`
5. **런타임 등록**: `agent/router_runtime.py`

공통 그래프, 노드, 라우터는 수정 불필요!

## 기술 스택

| Component | Technology |
|-----------|------------|
| Framework | FastAPI, Pydantic v2 |
| Orchestration | LangGraph 0.2.59 |
| LLM | Upstage Solar-Pro |
| Embedding | Upstage Solar-Embedding-1-Large |
| Vector Store | ChromaDB 0.5.23 |
| Web Search | SerpAPI (optional) |
| Pattern | Factory + Hooks Injection |

## 프로젝트 요구사항

✅ **필수 요구사항 달성**:
1. LangChain framework 활용
2. Upstage API 사용
3. ChromaDB로 Vector Database 구축
4. 1-2초 내 응답 (Retrieve → Generate)
5. LangGraph로 Agent Workflow 작성
6. RAG 아키텍처 흐름도 작성

## 성능 목표

- **응답 시간**: Retrieve → Generate 1-2초 이내 ✅
- **정확도**: 프로필 기반 필터링으로 관련 문서만 검색 ✅
- **신뢰성**: 근거 문서(sources) 제공 ✅

## 개발 가이드

### 로컬 개발

```bash
# 가상환경 활성화
conda activate rag-agent

# 서버 실행 (hot reload)
uvicorn app.main:app --reload

# 테스트
python scripts/test_agent.py
```

### 코드 품질

```bash
# Linting
pylint app/ agent/

# Type checking
mypy app/ agent/

# Formatting
black app/ agent/
```

## 문서

- [`claudedocs/ARCHITECTURE.md`](./claudedocs/ARCHITECTURE.md) - 상세 아키텍처 설명
- [`claudedocs/TEAM_GUIDE.md`](./claudedocs/TEAM_GUIDE.md) - 카테고리 추가 가이드

## 팀 구성

- **일자리 매칭**: JobsHooks 구현 완료 ✅
- **복지 정보**: 팀원 추가 예정
- **뉴스**: 팀원 추가 예정
- **사기 대응**: 팀원 추가 예정

## 트러블슈팅

### ChromaDB 로딩 실패
```
RuntimeError: Failed to load collection 'elderly_jobs'
```
→ `python tools/work_data.py` 실행하여 데이터 인덱싱

### API 키 오류
```
ValueError: UPSTAGE_API_KEY not provided
```
→ `.env` 파일 확인 및 키 입력

### 임포트 오류
```
ModuleNotFoundError
```
→ `pip install -r requirements.txt` 재실행

## 라이선스

MIT License

## 기여

팀원은 `claudedocs/TEAM_GUIDE.md` 참고하여 카테고리 추가
