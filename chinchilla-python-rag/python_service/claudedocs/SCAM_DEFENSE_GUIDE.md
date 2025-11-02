# 금융 사기 탐지 및 대응 에이전트 사용 가이드

## 🛡️ 개요

금융 사기 탐지 및 대응 에이전트는 **사용자가 의심스러운 메시지를 질문하면** AI가 분석하여 답변하는 시스템입니다.

### 주요 기능

1. **의심 문자 분석** - 사용자가 받은 메시지 분석
2. **사기 판별** - 사기 패턴 DB와 매칭하여 위험도 평가
3. **대응 방법 제시** - 즉시 취해야 할 행동 및 신고 방법 안내

---

## 📁 구현 구조 (TEAM_GUIDE.md 기준)

### Step 1: 데이터 수집 및 벡터화 ✅

```
scripts/build_scam_vectordb.py       # 벡터 DB 구축 스크립트
data/scam_defense/
  ├── scam_patterns.json              # 사기 패턴 DB
  └── scam_knowledge_base.json        # 사기 대응 지식 베이스
data/chroma_scam_defense/             # ChromaDB 벡터 저장소
```

**데이터 구조:**

- 보이스피싱 (금융기관/공공기관 사칭)
- 대출 사기
- 투자 사기
- 스미싱/피싱
- 메신저 피싱

### Step 2: 리트리버 구현 ✅

```python
# agent/retrievers/scam_retriever.py
class ScamDefenseRetriever:
    """사기 패턴 검색 리트리버"""
    - ChromaDB 기반 벡터 검색
    - 사기 유형별 필터링 지원
    - 관련도 점수 포함
```

### Step 3: 카테고리 훅 정의 ✅

```python
# agent/categories/scam_defense.py
class ScamDefenseHooks(CategoryHooks):
    """금융 사기 탐지 및 대응 카테고리"""

    # 쿼리 재작성 프롬프트
    rewrite_system_prompt: 사기 키워드 추출 및 패턴 분석

    # 답변 생성 프롬프트
    answer_system_prompt: 구조화된 답변 제공
      1. 사기 여부 판단 및 위험도 평가
      2. 사기 유형 및 수법 설명
      3. 즉시 해야 할 대응 방법
      4. 절대 하지 말아야 할 행동
      5. 신고 방법 및 연락처
      6. 예방 팁
```

### Step 4: 스키마 및 런타임 등록 ✅

```python
# app/schemas.py
class ScamDefensePayload(BaseModel):
    query: str        # 의심 메시지 (필수)
    sender: str       # 발신자 정보 (선택)

class ScamDefenseRequest(BaseModel):
    category: Literal["scam_defense"]
    payload: ScamDefensePayload

# agent/router_runtime.py
"scam_defense": ScamDefenseHooks()  # 런타임 등록
```

---

## ⚙️ 멀티 에이전트 파이프라인 (분석 → 판단 → 조언)

1. **분석 에이전트** *(rewrite 노드)*  
   - 의심 메시지를 사기 키워드, 발신자 패턴, 요구 행동 중심의 검색 쿼리로 재작성합니다.
2. **판단 에이전트** *(enhanced_retrieve + grade 노드)*  
   - ChromaDB에서 유사 패턴을 탐색하고 관련도 점수에 따라 필터 완화·재작성 재시도·웹 검색을 자동 수행합니다.
3. **조언 에이전트** *(generate 노드)*  
   - 위험도 아이콘, 사기 유형, 즉시 조치, 금지 행동, 신고 채널, 예방 팁을 포함한 답변을 생성합니다.

---

## 🔄 실시간 사기 DB 연동

- `scripts/build_scam_vectordb.py`를 실행하면 `data/scam_defense/`의 JSON/CSV를 임베딩하여 `data/chroma_scam_defense/`에 저장합니다.
- 벡터 저장소는 PersistentClient 기반으로 런타임에서 바로 읽어오기 때문에 데이터 갱신 후 재시작 없이 최신 내용을 활용할 수 있습니다.
- `agent/retrievers/scam_retriever.py`는 `similarity_search_with_score`를 이용해 관련도를 주입하고 사기 유형별 필터링을 지원합니다.

---

## 🚀 사용 방법

### 1. 로컬 테스트 (Python 스크립트)

```python
# 사용자가 질문 → 에이전트가 답변
from agent.router_runtime import get_runtime
from agent.router import dispatch
from app.schemas import ScamDefenseRequest, ScamDefensePayload

# 런타임 초기화
graphs, hooks = get_runtime()

# 사용자 질문 생성
req = ScamDefenseRequest(
    category="scam_defense",
    payload=ScamDefensePayload(
        query="KB국민은행입니다. 카드가 정지되어 OTP번호를 알려주세요.",
        sender="02-1234-5678"
    )
)

# 에이전트가 답변 생성
response = dispatch(req, graphs=graphs, hooks=hooks)
print(response.answer)
```

**실행:**

```bash
python scripts/test_scam_defense.py
```

---

### 2. FastAPI 서버 사용

**서버 시작:**

```bash
python app/main.py
# 서버 실행: http://localhost:8000
```

**사용자가 HTTP 요청으로 질문:**

```bash
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "category": "scam_defense",
    "payload": {
      "query": "검찰청입니다. 계좌가 사기에 연루되어 안전계좌로 이체가 필요합니다.",
      "sender": "검찰청"
    }
  }'
```

**에이전트 응답 예시:**

```json
{
  "answer": "🚨 매우위험: 검찰청 사칭 보이스피싱입니다...",
  "sources": [...],
  "metadata": {...}
}
```

---

## 📝 질문 예시 (사용자가 이렇게 질문하면 에이전트가 답변)

### 예시 1: 보이스피싱

**사용자 질문:**

```json
{
  "category": "scam_defense",
  "payload": {
    "query": "신한은행입니다. 보안카드 번호 전체를 알려주세요.",
    "sender": "1588-1234"
  }
}
```

**에이전트 답변:**

- 🚨 위험도: 매우높음
- 유형: 금융기관 사칭 보이스피싱
- 대응: 즉시 전화 끊기, 공식 대표번호로 확인
- 신고: 금융감독원(1332), 경찰청(182)

---

### 예시 2: 대출 사기

**사용자 질문:**

```json
{
  "category": "scam_defense",
  "payload": {
    "query": "무담보 대출 100% 승인! 신용등급 무관. 수수료 50만원 선입금하세요.",
    "sender": "금융지원센터"
  }
}
```

**에이전트 답변:**

- ⚠️ 위험도: 높음
- 유형: 불법 대출 사기
- 특징: 선입금 요구, 과장된 승인률
- 주의: 정식 금융기관은 선입금 요구 안 함

---

### 예시 3: 정상 메시지

**사용자 질문:**

```json
{
  "category": "scam_defense",
  "payload": {
    "query": "GS25 편의점 5,000원 결제되었습니다. 카드 이용내역 확인하세요.",
    "sender": "KB국민은행"
  }
}
```

**에이전트 답변:**

- ℹ️ 위험도: 낮음
- 일반적인 카드 사용 알림 메시지
- 의심스러우면 앱에서 직접 확인 권장

---

## 🔄 에이전트 워크플로우

```
사용자 질문
    ↓
1. rewrite_node      # 사기 키워드 추출
    ↓
2. retrieve_node     # 사기 패턴 DB 검색
    ↓
3. grade_node        # 검색 결과 품질 평가
    ↓
4. generate_node     # 구조화된 답변 생성
    ↓
에이전트 답변
```

**공통 노드 활용:**

- ✅ 쿼리 재작성 (검색 최적화)
- ✅ 벡터 검색 (유사 사기 패턴 찾기)
- ✅ 관련도 평가 (품질 검증)
- ✅ 답변 생성 (구조화된 응답)

---

## ✅ 체크리스트

### 구현 완료 항목

- [x] `scripts/build_scam_vectordb.py` - 벡터 DB 구축
- [x] `data/scam_defense/` - 사기 패턴 및 지식 베이스
- [x] `data/chroma_scam_defense/` - ChromaDB 벡터 저장소
- [x] `agent/retrievers/scam_retriever.py` - 리트리버 구현
- [x] `agent/categories/scam_defense.py` - Hooks 클래스
- [x] `app/schemas.py` - ScamDefensePayload, ScamDefenseRequest
- [x] `agent/router_runtime.py` - scam_defense 등록
- [x] `scripts/test_scam_defense.py` - 테스트 스크립트

### 테스트 방법

1. **벡터 DB 구축** (최초 1회만)

   ```bash
   python scripts/build_scam_vectordb.py
   ```

2. **로컬 테스트**

   ```bash
   python scripts/test_scam_defense.py
   ```

3. **FastAPI 서버 테스트**

   ```bash
   # 터미널 1: 서버 실행
   python app/main.py

   # 터미널 2: 테스트 요청
   curl -X POST http://localhost:8000/agent/query \
     -H "Content-Type: application/json" \
     -d '{"category": "scam_defense", "payload": {"query": "테스트 메시지"}}'
   ```

---

## 🎓 핵심 원칙

> **사용자가 질문 → 에이전트가 답변**

1. 사용자는 의심스러운 메시지를 **질문**으로 제공
2. 에이전트는 사기 DB를 검색하여 **답변** 생성
3. 자동 실행 없음, 항상 사용자 요청 기반

---

## 📞 신고 연락처

- 금융감독원: **1332**
- 경찰청(사이버범죄): **182**
- 한국인터넷진흥원: **118**

---

## 🔗 참고 자료

- LangChain 문서: https://python.langchain.com/
- LangGraph 문서: https://langchain-ai.github.io/langgraph/
- Upstage API: https://developers.upstage.ai/
- ChromaDB: https://docs.trychroma.com/
