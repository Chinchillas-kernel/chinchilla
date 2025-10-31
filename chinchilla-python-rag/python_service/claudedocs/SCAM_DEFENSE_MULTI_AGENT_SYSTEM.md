# 금융 사기 탐지 및 대응 멀티 에이전트 시스템

## 📋 개요

RAG(Retrieval-Augmented Generation)와 Web Search를 활용하여 정확한 지식 기반 답변을 제공하는 금융 사기 탐지 및 대응 에이전트 시스템입니다.

### 핵심 특징

- **멀티 에이전트 아키텍처**: 분석 → 판단 → 조언의 3단계 에이전트 파이프라인
- **다중 데이터 소스**: RAG (ChromaDB) + 실시간 패턴 매칭 + 웹 검색
- **실시간 사기 DB 연동**: 최신 사기 수법 및 트렌드 반영
- **고정밀 패턴 매칭**: 로컬 사기 패턴 DB를 활용한 즉각적인 위험 탐지

---

## 🏗️ 시스템 아키텍처

```
사용자 메시지
    ↓
┌─────────────────────────────────────────────────────┐
│  Stage 0: 실시간 패턴 분석 (FraudPatternMatcher)      │
│  - 로컬 패턴 DB 매칭                                   │
│  - 키워드 추출 & 위험도 점수 계산                        │
│  - 연락처/URL 분석                                     │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  데이터 수집 (병렬 처리)                               │
│  ┌─────────────────┐  ┌──────────────────┐          │
│  │  RAG 검색        │  │  웹 검색          │          │
│  │  (ChromaDB)     │  │  (SERP API)      │          │
│  │  - 지식 베이스   │  │  - 최신 사기 수법 │          │
│  │  - 사기 패턴     │  │  - 신고 사례     │          │
│  └─────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  Agent 1: 분석 Agent (Analysis)                      │
│  - 의심 요소 추출                                      │
│  - 사기 패턴 종합 분석                                 │
│  - 발신자/연락처 특이사항 분석                          │
│  - 최신 트렌드 반영                                    │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  Agent 2: 판단 Agent (Verdict)                       │
│  - 위험도 평가 (매우높음/높음/중간/낮음)                │
│  - 사기 유형 분류                                      │
│  - 신뢰도 점수 산출                                    │
│  - 즉시 행동 & 금지 행동 도출                          │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  Agent 3: 조언 Agent (Counsel)                       │
│  - 구조화된 대응 가이드 생성                           │
│  - 우선순위별 행동 지침                                │
│  - 신고 방법 & 예방 팁                                 │
│  - 출처 명시 (RAG + 패턴 + 웹)                         │
└─────────────────────────────────────────────────────┘
    ↓
최종 답변 (구조화된 사기 대응 가이드)
```

---

## 🔧 주요 컴포넌트

### 1. FraudPatternMatcher (실시간 패턴 분석)

**파일**: `agent/tools/fraud_patterns.py`

#### 기능

- 로컬 사기 패턴 DB를 사용한 즉각적인 매칭
- 고위험/중위험 키워드 탐지
- 사기 유형별 점수 계산
- 긴급 플래그 탐지
- 연락처 & URL 추출 및 분석

#### 주요 메서드

```python
def analyze_message(message: str) -> Dict[str, Any]:
    """
    의심 메시지 종합 분석

    Returns:
        {
            "risk_level": "매우높음|높음|중간|낮음",
            "risk_score": int,
            "matched_keywords": List[str],
            "suspected_scam_types": List[Dict],
            "urgent_flags": List[str],
            "contact_analysis": Dict
        }
    """
```

#### 위험도 계산 로직

```
위험도 점수 = (고위험 키워드 * 10) + (중위험 키워드 * 5) + 사기 유형 매칭 점수

- 점수 >= 50: 매우높음 🚨
- 점수 >= 30: 높음 ⚠️
- 점수 >= 15: 중간 ⚡
- 점수 < 15: 낮음 ℹ️
```

---

### 2. RealtimeScamDatabase (실시간 사기 DB)

**파일**: `agent/tools/fraud_patterns.py`

#### 기능

- 웹 검색을 통한 최신 사기 트렌드 수집
- 특정 전화번호/URL 사기 여부 검증
- 실시간 신고 사례 조회

#### 주요 메서드

```python
def search_recent_scams(
    scam_type: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> List[Document]:
    """최신 사기 사례 웹 검색"""

def search_scam_verification(phone_or_url: str) -> List[Document]:
    """특정 번호/URL 사기 여부 검증"""
```

#### 요구사항

- SERP API Key 필요 (환경변수: `SERP_API_KEY`)
- 미설정 시 웹 검색 기능 비활성화 (RAG + 패턴 매칭만 사용)

---

### 3. ScamDefenseHooks (멀티 에이전트 컨트롤러)

**파일**: `agent/categories/scam_defense.py`

#### 멀티 에이전트 파이프라인

##### Agent 0: 실시간 패턴 분석 (전처리)

```python
def _run_realtime_pattern_analysis(query: str) -> Dict:
    """로컬 패턴 DB 매칭 및 위험도 즉시 평가"""
```

##### Agent 1: 분석 Agent

```python
def _run_analysis(
    query: str,
    rag_context: str,
    web_context: str,
    pattern_analysis: Dict
) -> str:
    """의심 문자 종합 분석"""
```

**출력 형식**:

```
### 📋 분석 단계 결과

#### 1. 핵심 의심 요소
- [bullet list]

#### 2. 실시간 패턴 매칭
- 매칭된 사기 유형: [리스트]
- 매칭된 키워드: [리스트]

#### 3. 발신자/연락처 특이사항
- [분석 내용]

#### 4. 최신 사기 트렌드 (웹 검색)
- [웹 검색 결과 요약]
```

##### Agent 2: 판단 Agent

```python
def _run_verdict(
    query: str,
    rag_context: str,
    web_context: str,
    analysis: str,
    pattern_analysis: Dict
) -> Dict:
    """사기 여부 판별 및 위험도 평가"""
```

**출력 형식** (JSON):

```json
{
  "risk_level": "매우높음|높음|중간|낮음",
  "risk_icon": "🚨|⚠️|⚡|ℹ️",
  "scam_type": "사기 유형 추정",
  "confidence": "판단 근거 요약",
  "key_evidence": ["근거1", "근거2"],
  "immediate_actions": ["즉시 행동1", "행동2"],
  "do_not_do": ["금지 행동1", "행동2"]
}
```

##### Agent 3: 조언 Agent

```python
def _run_counsel(
    query: str,
    rag_context: str,
    web_context: str,
    analysis: str,
    verdict: Dict,
    pattern_analysis: Dict
) -> str:
    """대응 방법 제시"""
```

**출력 형식**:

```
### 🎯 최종 대응 가이드

#### 1. 위험도 판단
{risk_icon} **{risk_level}** - {한줄 요약}

#### 2. 사기 유형 및 수법
- 유형: {scam_type}
- 주요 수법: [설명]

#### 3. ✅ 즉시 해야 할 대응 방법
1. [구체적 행동 1]
2. [구체적 행동 2]

#### 4. ❌ 절대 하지 말아야 할 행동
1. [금지 행동 1]
2. [금지 행동 2]

#### 5. 📞 신고 방법 및 연락처
- 경찰청 사이버안전국: 182
- 금융감독원: 1332
- 한국인터넷진흥원: 118

#### 6. 💡 예방 팁
- [예방법 1]
- [예방법 2]

#### 7. 📚 참고 출처
- RAG 검색: [출처]
- 실시간 패턴: [매칭 결과]
- 웹 검색: [최신 정보]
```

---

### 4. Enhanced Web Search (강화된 웹 검색)

**파일**: `agent/nodes/websearch.py`

#### 기능

- 사기 탐지 카테고리 전용 강화 검색
- 패턴 분석 결과 기반 타겟팅 검색
- 일반 웹 검색 + 특화 검색 병행

```python
def _enhanced_scam_websearch(state: Dict, hooks: Any) -> Dict:
    """
    1. 실시간 패턴 분석 수행
    2. 패턴 기반 강화 웹 검색
    3. 일반 웹 검색 추가
    """
```

---

## 📊 데이터 소스

### 1. RAG (ChromaDB)

**위치**: `data/chroma_scam_defense/`

**컬렉션**: `scam_defense`

**데이터**:

- `data/scam_defense/scam_knowledge_base.json`: 사기 지식 베이스 (10개 문서)
- `data/scam_defense/scam_patterns.json`: 사기 패턴 DB (6개 유형)

**검색 방식**: Solar Embedding + 유사도 검색 (Top-K=8)

### 2. 실시간 패턴 매칭

**위치**: `data/scam_defense/scam_patterns.json`

**패턴 구조**:

```json
{
  "financial_scams": [
    {
      "type": "보이스피싱",
      "category": "금융기관 사칭",
      "danger_level": "매우높음",
      "patterns": ["OTP", "보안카드", "계좌 정지"],
      "sender_patterns": ["KB국민은행", "신한은행"],
      "response_actions": [...],
      "prevention_tips": [...]
    }
  ],
  "keywords": {
    "high_risk": ["OTP", "안전계좌", "선입금"],
    "medium_risk": ["대출", "투자", "수익 보장"]
  },
  "legitimate_contacts": {
    "경찰청 사이버안전국": "182",
    "금융감독원": "1332"
  }
}
```

### 3. 웹 검색 (SERP API)

**검색 쿼리 예시**:

- `"{사기_유형} {키워드} 최신 수법 신고"`
- `"{전화번호} 사기 신고 후기"`
- `"보이스피싱 사기 최신 수법"`

**활용**:

- 최신 사기 트렌드 파악
- 특정 번호/URL 검증
- 신고 사례 수집

---

## 🚀 사용 방법

### 1. 환경 설정

```bash
# .env 파일 설정
UPSTAGE_API_KEY=your_upstage_api_key
SERP_API_KEY=your_serp_api_key  # 선택사항 (웹 검색 활성화)
```

### 2. 벡터 DB 구축

```bash
# 사기 패턴 벡터 DB 생성
python scripts/build_scam_vectordb.py
```

### 3. 테스트 실행

```bash
# 통합 테스트
python scripts/test_scam_defense.py
```

#### 테스트 구성

1. **실시간 패턴 매칭 테스트**: `test_fraud_pattern_matcher()`
2. **RAG 검색 테스트**: `test_scam_retriever()`
3. **웹 검색 테스트**: `test_realtime_scam_database()` (SERP API 필요)
4. **멀티 에이전트 워크플로우 테스트**: `test_multi_agent_workflow()`

### 4. API 사용

```python
from app.schemas import ScamDefenseRequest, ScamDefensePayload
from agent.router import dispatch
from agent.router_runtime import get_runtime

# Runtime 초기화
graphs, hooks = get_runtime()

# 요청 생성
request = ScamDefenseRequest(
    category="scam_defense",
    payload=ScamDefensePayload(
        query="KB은행입니다. OTP 번호를 알려주세요.",
        sender="02-1234-5678"
    )
)

# 실행
response = dispatch(request, graphs=graphs, hooks=hooks)

# 결과 확인
print(response.answer)  # 최종 대응 가이드
print(response.sources)  # 참고 문서
print(response.metadata)  # 패턴 분석, 판단 결과 등
```

---

## 📈 성능 특성

### 응답 시간

- **실시간 패턴 분석**: < 0.1초 (로컬 매칭)
- **RAG 검색**: 0.5 ~ 1초
- **웹 검색**: 2 ~ 5초 (SERP API)
- **멀티 에이전트 처리**: 10 ~ 20초 (LLM 호출 3회)

### 정확도

- **패턴 매칭**: 높은 재현율 (Recall), 즉각적 위험 감지
- **RAG 검색**: 정확한 지식 기반 답변
- **웹 검색**: 최신 트렌드 반영

---

## 🔍 주요 사기 유형

### 1. 보이스피싱

#### 금융기관 사칭

- **패턴**: OTP, 보안카드, 계좌 정지
- **위험도**: 매우높음 🚨

#### 공공기관 사칭

- **패턴**: 검찰청, 경찰청, 안전계좌
- **위험도**: 매우높음 🚨

### 2. 대출 사기

- **패턴**: 선입금, 수수료, 100% 승인
- **위험도**: 높음 ⚠️

### 3. 투자 사기

- **패턴**: 고수익 보장, 원금 보장, 월 30% 수익
- **위험도**: 높음 ⚠️

### 4. 피싱

- **패턴**: 택배, 링크 클릭, 개인정보 입력
- **위험도**: 중간 ⚡

### 5. 메신저 피싱

- **패턴**: 지인 사칭, 급해, 계좌번호
- **위험도**: 높음 ⚠️

---

## 🛠️ 확장 가능성

### 1. 패턴 DB 업데이트

```bash
# data/scam_defense/scam_patterns.json 수정 후
python scripts/build_scam_vectordb.py
```

### 2. 지식 베이스 확장

```bash
# data/scam_defense/scam_knowledge_base.json에 문서 추가 후
python scripts/build_scam_vectordb.py
```

### 3. 추가 데이터 소스 통합

- 금융감독원 API
- 경찰청 사기 신고 DB
- 실시간 뉴스 피드

### 4. 추가 에이전트 개발

- 이미지 분석 Agent (스미싱 이미지 검증)
- 음성 분석 Agent (보이스피싱 음성 검증)
- 예측 Agent (사기 트렌드 예측)

---

## 📚 참고 문서

- `ARCHITECTURE.md`: 전체 시스템 아키텍처
- `SCAM_DEFENSE_GUIDE.md`: 사기 방어 기능 가이드
- `SCAM_DEFENSE_CHECKLIST.md`: 구현 체크리스트
- `SCAM_DEFENSE_IMPLEMENTATION_REPORT.md`: 구현 보고서

---

## 🆘 신고 연락처

- **경찰청 사이버안전국**: 182 (24시간)
- **금융감독원**: 1332
- **한국인터넷진흥원**: 118
- **범죄신고**: 112
- **금융위원회**: 02-2100-2114

---

## 📝 라이센스

이 프로젝트는 금융 사기 피해 예방을 목적으로 개발되었습니다.

---

## 👥 기여

금융 사기 패턴 정보 제공 및 시스템 개선 제안을 환영합니다.

**마지막 업데이트**: 2025년 10월 30일
