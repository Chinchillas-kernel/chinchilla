# 노인 일자리 매칭 에이전트 구현 가이드

## 개요

LangChain, LangGraph, Upstage API, ChromaDB를 활용한 RAG 기반 노인 일자리 매칭 에이전트

## 구현 완료 사항

### 1. 데이터 파이프라인
- ✅ 공공데이터 수집 (`tools/work_data.py`)
- ✅ 청킹 및 임베딩
- ✅ ChromaDB 벡터 저장소 구축

### 2. 에이전트 아키텍처
- ✅ LangGraph 워크플로우 (`agent/graph.py`)
- ✅ 카테고리별 훅 시스템 (`agent/categories/jobs.py`)
- ✅ State 관리 및 노드 정의

### 3. 핵심 노드
- ✅ `rewrite_node`: 쿼리 재작성 (Upstage LLM)
- ✅ `retrieve_node`: 문서 검색 (ChromaDB + 프로필 필터링)
- ✅ `gate_node`: 웹 검색 분기 판단
- ✅ `websearch_node`: SerpAPI 웹 검색
- ✅ `merge_node`: 문서 병합 및 중복 제거
- ✅ `generate_node`: 최종 답변 생성 (Upstage LLM)

### 4. API 엔드포인트
- ✅ FastAPI 앱 (`app/main.py`)
- ✅ `/agent/query` POST 엔드포인트
- ✅ 요청 검증 (Pydantic)
- ✅ 라우터 디스패치 로직

## 아키텍처 흐름

```
Client Request
    ↓
FastAPI (/agent/query)
    ↓
Router.dispatch()
    ↓
select_hooks("jobs") → JobsHooks
    ↓
req_to_state() → AgentState
    ↓
build_graph() → Compiled LangGraph
    ↓
┌─────────────────────────────────────┐
│     LangGraph Workflow              │
│                                     │
│  rewrite → retrieve → gate          │
│                ↓         ↓          │
│          (문서 충분?) (문서 부족)  │
│                ↓         ↓          │
│            generate  websearch      │
│                         ↓          │
│                      merge         │
│                         ↓          │
│                    generate        │
└─────────────────────────────────────┘
    ↓
{answer, sources}
    ↓
JSON Response
```

## 프로필 기반 필터링

### 지역 필터링
- `location`: "서울 용산구" → `{region_province: "서울", region_city: "용산구"}`
- ChromaDB 메타데이터 필터 적용

### 나이 필터링
- `age`: 65 → 검색 후 `min_age <= 65` 필터링
- 후처리 방식 (ChromaDB 비교 연산자 제한)

## 실행 방법

### 1. 환경 설정

```bash
cd python_service

# .env 파일 생성
cp .env.example .env

# API 키 입력
# UPSTAGE_API_KEY=your_key_here
# SERP_API_KEY=your_key_here (선택)
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 데이터 준비 (이미 완료된 경우 스킵)

```bash
python tools/work_data.py
```

### 4. 로컬 테스트

```bash
# 리트리버 및 워크플로우 테스트
python scripts/test_local.py

# 또는
python tests/test_jobs_agent.py
```

### 5. FastAPI 서버 실행

```bash
# 개발 모드
python app/main.py

# 또는
uvicorn app.main:app --reload --port 8000
```

### 6. API 테스트

```bash
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

## 응답 형식

```json
{
  "answer": "서울 용산구에서 경비 일자리를 찾고 계시는군요. 다음과 같은 일자리가 있습니다:\n\n1. [일자리 정보]...",
  "sources": [
    {
      "content": "일자리 내용...",
      "metadata": {
        "job_title": "경비원",
        "organization": "OO관리공단",
        "region_province": "서울",
        "region_city": "용산구",
        "min_age": 60,
        "relevance_score": 0.85
      }
    }
  ]
}
```

## 성능 목표

- ✅ **응답 시간**: Retrieve → Generate 1-2초 이내
- ✅ **정확도**: 프로필 필터링으로 관련 문서만 검색
- ✅ **신뢰성**: 근거 문서(sources) 제공

## 확장 가능성

### 다른 카테고리 추가

1. `agent/categories/` 에 새 파일 생성 (예: `welfare.py`)
2. Hooks 클래스 정의
3. `agent/graph.py`의 `select_hooks()` 에 추가
4. `app/schemas.py` 에 스키마 추가

```python
# agent/categories/welfare.py
class WelfareHooks(BaseModel):
    name: str = "welfare"
    rewrite_system_prompt: str = "복지 정보 검색 쿼리 최적화..."
    answer_system_prompt: str = "복지 상담원으로서..."

    def get_retriever(self):
        return get_welfare_retriever()
```

## 문제 해결

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
ModuleNotFoundError: No module named 'pydantic_settings'
```
→ `pip install -r requirements.txt` 재실행

## 다음 단계

1. ✅ 기본 구현 완료
2. 🔄 통합 테스트 실행
3. ⏭ 성능 벤치마크
4. ⏭ 프로덕션 배포 (Docker, CI/CD)
5. ⏭ 모니터링 및 로깅 강화
