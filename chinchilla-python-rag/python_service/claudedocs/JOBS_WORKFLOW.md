# 일자리 매칭 에이전트 워크플로우

## 개요

일자리 매칭 에이전트는 **Grade-based Rewrite Loop** 패턴을 사용합니다.

## 워크플로우 다이어그램

```
START
  ↓
┌─────────────┐
│  rewrite    │ ← 쿼리 재작성 (Upstage LLM)
└──────┬──────┘
       ↓
┌─────────────┐
│  retrieve   │ ← ChromaDB 검색 (프로필 필터링)
└──────┬──────┘
       ↓
┌─────────────┐
│   grade     │ ← 문서 관련성 평가 (LLM)
└──────┬──────┘
       │
   ┌───┴───┐
   ↓       ↓
  yes      no
   ↓       ↓
   │    retry_count < 2?
   │       ↓         ↓
   │      yes       no
   │       ↓         ↓
   │   rewrite    generate
   │       ↑         ↓
   │       └─────────┤
   ↓                 ↓
generate          END
   ↓
 END
```

## 노드 상세

### 1. Rewrite Node
**역할**: 사용자 쿼리를 검색에 최적화된 형태로 재작성

**입력**:
- `state.query`: 원본 사용자 질문

**출력**:
- `state.rewritten_query`: 재작성된 검색 쿼리

**프롬프트** (JobsHooks):
```
너는 노인 채용 공고 검색요원이다.
사용자의 질의를 검색 친화 쿼리로 축약하라.
예: 지역(도/시/구), 직무 키워드, 고용형태 등.
```

**예시**:
- 입력: "서울 용산구에서 경비 일자리 찾고 있습니다"
- 출력: "서울 용산구 경비 일자리"

---

### 2. Retrieve Node
**역할**: ChromaDB에서 관련 일자리 문서 검색

**입력**:
- `state.rewritten_query`: 재작성된 쿼리
- `state.profile`: 사용자 프로필 (나이, 성별, 지역)

**처리**:
1. Upstage Solar-Embedding으로 쿼리 임베딩
2. ChromaDB에서 유사도 검색
3. 프로필 필터링:
   - `region_province`, `region_city` (지역)
   - `min_age <= user.age` (나이)

**출력**:
- `state.documents`: 검색된 문서 리스트 (top_k=8)

---

### 3. Grade Node ⭐ (핵심)
**역할**: 검색된 문서가 사용자 질문과 관련이 있는지 평가

**입력**:
- `state.query`: 원본 질문
- `state.rewritten_query`: 재작성된 쿼리
- `state.documents`: 검색된 문서들

**평가 로직**:
1. **문서 존재 확인**: 문서가 없으면 → `no`
2. **관련도 점수 확인**: `relevance_score < threshold` → `no`
3. **LLM 평가**: 상위 3개 문서를 LLM에게 평가 요청

**LLM 프롬프트**:
```
다음 문서들이 사용자의 질문과 관련이 있는지 평가하세요.

사용자 질문: {rewritten_query}

검색된 문서:
{top 3 documents}

문서가 질문에 답변하는데 도움이 되는 정보를 포함하고 있습니까?
관련이 있으면 "yes", 없으면 "no"만 답변하세요.
```

**출력**:
- `"yes"`: 문서가 관련 있음 → generate로 진행
- `"no"`: 문서가 관련 없음 → rewrite로 재시도

---

### 4. Routing Logic (route_after_grade)
**역할**: Grade 결과에 따라 다음 노드 결정

**분기 로직**:

```python
if grade == "yes":
    return "generate"

if grade == "no":
    if retry_count < max_retries (2):
        state["retry_count"] += 1
        return "rewrite"  # 재시도
    else:
        return "generate"  # 최대 재시도 도달, 현재 문서로 답변
```

**재시도 제한**: 최대 2회 (무한 루프 방지)

---

### 5. Generate Node
**역할**: 검색된 문서를 바탕으로 최종 답변 생성

**입력**:
- `state.query`: 원본 질문
- `state.documents`: 검색된 문서들

**프롬프트** (JobsHooks):
```
너는 시니어 채용 컨설턴트다.
정확한 근거 문서와 함께, 지원 절차/주의사항을 구조적으로 답하라.
```

**출력**:
- `state.answer`: 최종 답변
- `state.sources`: 참조 문서 (상위 5개)

---

## 실행 예시

### 시나리오 1: 첫 검색에 성공

```
사용자: "서울 용산구에서 경비 일자리 찾고 있습니다"
프로필: age=65, location="서울 용산구"

[1] rewrite: "서울 용산구 경비 일자리"
[2] retrieve: 8개 문서 검색 (관련도 0.85, 0.82, ...)
[3] grade: "yes" (문서가 질문과 관련 있음)
[4] generate: "서울 용산구에서 경비 일자리를 찾고 계시는군요..."

총 실행: rewrite(1회) → retrieve(1회) → grade(1회) → generate
```

---

### 시나리오 2: 첫 검색 실패, 재시도 성공

```
사용자: "일자리 찾아줘"
프로필: age=70, location="부산"

[1] rewrite: "일자리"
[2] retrieve: 관련도 낮은 문서들 (0.3, 0.25, ...)
[3] grade: "no" (문서가 질문과 관련 없음)
    → retry_count = 1

[4] rewrite: "부산 노인 일자리 채용"
[5] retrieve: 관련도 높은 문서들 (0.88, 0.85, ...)
[6] grade: "yes"
[7] generate: "부산에서 다음과 같은 일자리가 있습니다..."

총 실행: rewrite(2회) → retrieve(2회) → grade(2회) → generate
```

---

### 시나리오 3: 최대 재시도 도달

```
사용자: "아르바이트"
프로필: age=68, location=None

[1] rewrite: "아르바이트"
[2] retrieve: 관련도 낮은 문서들
[3] grade: "no" → retry_count = 1

[4] rewrite: "노인 아르바이트"
[5] retrieve: 여전히 낮은 관련도
[6] grade: "no" → retry_count = 2

[7] rewrite: "시니어 단기 근무"
[8] retrieve: 관련도 낮음
[9] grade: "no" → retry_count = 3 (max)
    → 최대 재시도 도달, generate로 진행

[10] generate: "죄송합니다. 정확히 일치하는 일자리를 찾지 못했습니다..."

총 실행: rewrite(3회) → retrieve(3회) → grade(3회) → generate
```

---

## 상태 관리

### AgentState 필드

```python
{
    "category": "jobs",
    "query": "원본 질문",
    "profile": {"age": 65, "gender": "male", "location": "서울"},
    "rewritten_query": "재작성된 쿼리",
    "retry_count": 0,  # 재시도 횟수
    "documents": [...],  # 검색된 문서들
    "answer": "최종 답변",
    "sources": [...]  # 참조 문서
}
```

---

## 성능 최적화

### 1. 프로필 필터링
- ChromaDB 메타데이터 필터로 지역/나이 필터링
- 불필요한 문서 제외 → 관련도 향상

### 2. Grade 캐싱 (향후 개선)
- 동일 쿼리+문서 조합에 대한 grade 결과 캐싱
- Redis 활용 가능

### 3. 조기 종료
- 첫 grade에서 "yes" 나오면 즉시 generate
- 평균 1-2초 응답 시간

---

## 설정 파라미터

### JobsHooks 설정

```python
class JobsHooks(CategoryHooks):
    top_k: int = 8  # 검색 문서 개수
    min_relevance_threshold: float = 0.4  # 관련도 임계값
```

### Graph 설정

```python
max_retries = 2  # 최대 재시도 횟수
```

---

## 로깅

### Grade 결과 로깅

```
[GRADE] No documents retrieved → rewrite
[GRADE] No documents above threshold (0.4) → rewrite
[GRADE] Documents are relevant → generate
[GRADE] Documents not relevant → rewrite
```

### Route 로깅

```
[ROUTE] Rewriting query (attempt 1/2)
[ROUTE] Rewriting query (attempt 2/2)
[ROUTE] Max retries reached, proceeding to generate
```

---

## 향후 개선 방안

1. **Adaptive Threshold**: 재시도마다 threshold 낮추기
2. **Query Expansion**: 유의어, 동의어 확장
3. **Hybrid Search**: BM25 + Vector 결합
4. **User Feedback Loop**: 사용자 피드백으로 grade 개선
5. **A/B Testing**: Grade vs No-Grade 성능 비교
