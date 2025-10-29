# 멀티 레벨 검색 전략

## 개요

일자리 매칭 에이전트는 **3단계 복구 전략**을 사용하여 검색 품질을 향상시킵니다.

## 검색 전략 흐름도

```
START
  ↓
rewrite (쿼리 최적화)
  ↓
enhanced_retrieve (Level 0: 전체 필터)
  ↓
grade (관련성 평가)
  ↓
┌─────────────┐
│ grade="yes"?│
└─────┬───────┘
      │
  ┌───┴───┐
  ↓       ↓
 YES      NO
  ↓       ↓
generate  ┌──────────────────┐
          │ Recovery Strategy│
          └────────┬─────────┘
                   │
          ┌────────┴────────┐
          ↓                 ↓
    filter_level < 3?  retry_count < 2?
          ↓                 ↓
         YES               YES
          ↓                 ↓
    widen_filter      increment_retry
          ↓                 ↓
       retrieve          rewrite
          ↓                 ↓
       grade             retrieve
                            ↓
          ┌─────────────────┘
          ↓
       BOTH NO
          ↓
      websearch
          ↓
      generate
```

---

## 1단계: Dense Vector Search (기본)

### Level 0: 전체 필터 적용
**필터**:
- `region_province` + `region_city` (지역)
- `min_age <= user.age` (나이)

**예시**:
```python
profile = {
    "age": 65,
    "location": "서울 용산구"
}

# ChromaDB 필터
filters = {
    "$and": [
        {"region_province": "서울"},
        {"region_city": "용산구"}
    ]
}
```

**품질 평가**:
- High: 5개 이상 문서, 평균 관련도 ≥ 0.7
- Medium: 3개 이상 문서, 평균 관련도 ≥ 0.4
- Low: 그 외

---

## 2단계: Filter Widening (점진적 완화)

### Level 1: 시/군/구 제거, 도/시만 유지
**필터**:
- `region_province` (도/시만)
- `min_age <= user.age`

**예시**:
```python
# "서울 용산구" → "서울"
profile_widened = {
    "age": 65,
    "location": "서울"
}

filters = {
    "region_province": "서울"
}
```

**효과**: 서울 전역의 일자리 검색

---

### Level 2: 지역 제거, 나이만 유지
**필터**:
- `min_age <= user.age`

**예시**:
```python
profile_widened = {
    "age": 65,
    "location": None  # 지역 필터 제거
}

# 나이 필터만 후처리로 적용
```

**효과**: 전국의 해당 연령 일자리 검색

---

### Level 3: 모든 필터 제거
**필터**: 없음 (쿼리만 사용)

**예시**:
```python
# 프로필 필터 없이 순수 쿼리 검색
```

**효과**: 전국 모든 일자리에서 검색

---

## 3단계: Query Rewrite (쿼리 재작성)

### 재작성 전략
1. **동의어 확장**: "경비" → "경비원, 시설관리, 안전관리"
2. **지역 정규화**: "서울특별시" → "서울"
3. **불필요한 단어 제거**: "찾고 있습니다", "원합니다" 등

### 예시
```python
retry_count = 0:
  query = "서울 용산구에서 경비 일자리 찾고 있습니다"
  rewritten = "서울 용산구 경비 일자리"

retry_count = 1:
  query = "서울 용산구 경비 일자리"
  rewritten = "서울 경비원 안전관리 시설관리"
```

**최대 재시도**: 2회

---

## 4단계: Web Search Fallback

### 조건
- Filter widening 실패 (Level 3까지 시도)
- Query rewrite 실패 (2회 재시도)
- 여전히 grade = "no"

### 웹 검색 전략
현재: SerpAPI로 일반 웹 검색

**향후 개선** (공식 API 우선):
1. Senuri API (B552474)
2. WorkNet API
3. 제한된 도메인 웹서치 (`site:work.go.kr`, `site:senuri.go.kr`)

---

## 실행 예시

### 시나리오 1: Level 0에서 성공
```
사용자: "서울 용산구에서 경비 일자리"
프로필: age=65, location="서울 용산구"

[1] rewrite: "서울 용산구 경비 일자리"
[2] retrieve (Level 0): 전체 필터 → 8개 문서 (avg 0.82)
[3] grade: "yes"
[4] generate: "서울 용산구에서 다음과 같은 경비 일자리..."

총 단계: 4
```

---

### 시나리오 2: Filter Widening으로 성공
```
사용자: "용산구 일자리"
프로필: age=70, location="서울 용산구"

[1] rewrite: "용산구 일자리"
[2] retrieve (Level 0): province="서울", city="용산구" → 2개 문서 (avg 0.35)
[3] grade: "no" (low quality)
[4] widen_filter: Level 0→1 (city 제거)
[5] retrieve (Level 1): province="서울" → 7개 문서 (avg 0.68)
[6] grade: "yes"
[7] generate: "서울에서 다음과 같은 일자리..."

총 단계: 7
```

---

### 시나리오 3: Query Rewrite로 성공
```
사용자: "일자리 찾아줘"
프로필: age=68, location="부산"

[1] rewrite: "일자리"
[2] retrieve (Level 0): province="부산" → 1개 문서 (avg 0.25)
[3] grade: "no"
[4] widen_filter: Level 0→1 → 2개 문서 (avg 0.28)
[5] grade: "no"
[6] widen_filter: Level 1→2 (location 제거) → 3개 문서 (avg 0.32)
[7] grade: "no"
[8] widen_filter: Level 2→3 (모든 필터 제거) → 5개 문서 (avg 0.40)
[9] grade: "no"
[10] increment_retry: retry_count 0→1, reset filter_level
[11] rewrite: "노인 일자리 채용 모집"
[12] retrieve (Level 0): province="부산" → 6개 문서 (avg 0.75)
[13] grade: "yes"
[14] generate: "부산에서 다음과 같은 일자리..."

총 단계: 14
```

---

### 시나리오 4: Web Search Fallback
```
사용자: "아르바이트"
프로필: age=72, location=None

[1] rewrite: "아르바이트"
[2] retrieve (Level 0): 2개 문서 (avg 0.20)
[3] grade: "no"
[4-9] widen_filter: Level 0→1→2→3 → 여전히 low quality
[10] increment_retry: retry_count 0→1
[11] rewrite: "단기 근무 시니어"
[12] retrieve (Level 0): 3개 문서 (avg 0.30)
[13-18] widen_filter: Level 0→1→2→3 → low quality
[19] increment_retry: retry_count 1→2
[20] rewrite: "노인 단기 일자리"
[21] retrieve (Level 0): 3개 문서 (avg 0.35)
[22-27] widen_filter: Level 0→1→2→3 → low quality
[28] websearch: SerpAPI 검색
[29] generate: "웹 검색 결과를 바탕으로..."

총 단계: 29 (max 재시도)
```

---

## 성능 메트릭

### 검색 품질 기준
```python
def assess_search_quality(documents, threshold=0.4):
    if count >= 5 and avg_score >= 0.7:
        return "high"
    elif count >= 3 and avg_score >= threshold:
        return "medium"
    else:
        return "low"
```

### 최대 재시도 제한
- **Filter widening**: 3 levels (0→1→2→3)
- **Query rewrite**: 2 retries
- **Total max iterations**: ~30 (재귀 한도 방지)

---

## 향후 개선 사항

### 1. Hybrid Search (BM25 + Dense)
```python
# BM25 for keyword matching
bm25_results = bm25_index.search(query)

# Dense for semantic matching
dense_results = chroma.search(embedding)

# Rerank combined results
final_results = rerank(bm25_results + dense_results)
```

### 2. 공식 API 연동
```python
# Senuri API
senuri_results = fetch_senuri_api(query, profile)

# WorkNet API
worknet_results = fetch_worknet_api(query, profile)

# Merge with local results
all_results = local + senuri + worknet
reranked = rerank_by_relevance(all_results)
```

### 3. 동적 Threshold 조정
```python
# 재시도마다 threshold 낮추기
if retry_count == 0:
    threshold = 0.4
elif retry_count == 1:
    threshold = 0.3
else:
    threshold = 0.2
```

### 4. 사용자 피드백 학습
```python
# 사용자가 "관련 없음" 피드백 시
# → 해당 문서의 관련도 점수 하향 조정
# → Grade 모델 파인튜닝 데이터로 활용
```

---

## 로깅

### Filter Widening 로그
```
[FILTER_WIDEN] Level 1: Drop city, keep province + age
[RETRIEVE] Level 1: Province only (서울)
[RETRIEVE] Found 7 docs, avg score: 0.68, quality: medium
```

### Routing 로그
```
[ROUTE] Grade=NO, quality=low, filter_level=0, retry=0
[ROUTE] → widen_filter (current level: 0)

[ROUTE] Grade=NO, quality=low, filter_level=3, retry=0
[ROUTE] → increment_retry (attempt 1/2)

[ROUTE] Grade=NO, quality=low, filter_level=3, retry=2
[ROUTE] → websearch (fallback)
```

---

## 설정 파라미터

```python
# JobsHooks
top_k = 8
min_relevance_threshold = 0.4

# Graph
max_filter_levels = 3
max_query_retries = 2
recursion_limit = 25  # LangGraph default
```
