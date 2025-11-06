# 노인 행정도우미 RAG Agent 프로젝트

노년층 행정·생활 지원을 위한 멀티 카테고리 RAG( Retrieval-Augmented Generation ) 에이전트 시스템입니다. Upstage LLM, LangChain, LangGraph, ChromaDB를 결합하여 카테고리별로 정확한 근거 기반 답변을 제공합니다.

## 주요 특징
- LangChain · LangGraph 기반의 재작성 → 검색 → 평가 → 웹 보강 → 생성 파이프라인
- Upstage Solar-Pro LLM & Solar-Embedding 조합으로 한국어 질의 최적화
- 카테고리(일자리, 복지, 뉴스, 법률, 금융사기)별 후크 & 리트리버 확장 구조
- ChromaDB 벡터 스토어와 정책 기반 답변 템플릿 관리(`policies/`)
- FastAPI 서버 + Pydantic v2 스키마 + LangSmith 선택적 연동
- 1~2초 내 응답을 목표로 하는 다단계 검색 품질 관리(필터 확장·재작성·웹 검색)

## 아키텍처 한눈에 보기

```
사용자 요청 → 카테고리 라우팅 → LangGraph 워크플로우 → 답변 + 근거 문서
```

![RAG Workflow](graph.png)

LangGraph는 `rewrite → enhanced_retrieve → grade` 흐름을 기본으로 하며, 필요 시 필터 확장·쿼리 재작성·웹 검색을 순차적으로 시도해 최종 답변을 생성합니다.

## 레포지토리 구조

```
chinchilla-python-rag/
├── Readme.md            # 프로젝트 개요(본 문서)
├── graph.png            # RAG 워크플로우 다이어그램
└── python_service/      # FastAPI 기반 메인 서비스
    ├── app/             # 엔트리포인트, 설정, 스키마
    ├── agent/           # LangGraph 그래프, 노드, 카테고리 훅, 데이터 스크립트
    ├── claudedocs/      # 아키텍처 및 팀 가이드 문서
    ├── data/            # 벡터 스토어 및 원본 데이터 저장소
    ├── policies/        # 카테고리별 정책 및 템플릿(YAML)
    ├── scripts/         # 에이전트 테스트 및 그래프 시각화 스크립트
    ├── tests/           # 단위 테스트
    ├── README.md        # 파이썬 서비스 상세 설명
    └── requirements.txt # Python 의존성 목록
```

## 빠른 시작

### 1. 필수 요건
- Python 3.11 이상 (권장: Conda 환경)
- Upstage API Key (필수), SerpAPI/Naver API Key (선택적 기능에 필요)

### 2. 의존성 설치

```bash
cd python_service
conda create -n rag-agent python=3.11
conda activate rag-agent
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성해 아래 키를 채웁니다(필수/선택 구분).

| KEY | 설명 | 필수 여부 |
| --- | --- | --- |
| `UPSTAGE_API_KEY` | Upstage Solar-Pro API 키 | ✅ |
| `SERP_API_KEY` | SerpAPI 검색 키 | ⚪ (웹 검색 강화 시)|
| `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | 네이버 검색 API 자격 증명 | ⚪ (뉴스/웹 데이터)|
| `LANGSMITH_API_KEY` | LangSmith 트레이싱 | ⚪ |
| `CHROMA_DIR` 등 | 데이터/벡터 저장 경로 커스터마이징 | ⚪ |

추가 옵션은 `python_service/app/config.py`에서 확인할 수 있습니다.

### 4. 데이터 구축 (필요 시)

카테고리별 벡터 스토어가 준비되지 않았다면 `agent/tools` 내 ETL 스크립트를 실행합니다.

```bash
python agent/tools/work_data_ingest.py      # 일자리 데이터
python agent/tools/welfare_data_ingest.py   # 복지 데이터
python agent/tools/news_data_ingest.py      # 뉴스 데이터
python agent/tools/legal_data_ingest.py     # 법률 상담 데이터
python agent/tools/scam_data_ingest.py      # 금융 사기 대응 데이터
```

스크립트는 `data/raw`에 원본을 저장하고 `data/chroma_*` 경로로 임베딩을 적재합니다.

### 5. 로컬 실행 & 테스트

```bash
# FastAPI 서버 실행
uvicorn app.main:app --reload --port 8000

# 에이전트 단위 테스트
python scripts/test_agent.py
python -m pytest tests
```

`GET /health`로 상태를 확인하고, `POST /agent/query`로 카테고리별 질문을 전송할 수 있습니다.

## API 요약

| Endpoint | Method | 설명 |
| --- | --- | --- |
| `/` | GET | 서비스 메타 정보 (버전, 등록 카테고리) |
| `/health` | GET | 시스템 헬스 체크 및 API 키 상태 |
| `/agent/query` | POST | 카테고리별 RAG 질의 (스키마: `app/schemas.py`) |

요청 예시는 `python_service/README.md`와 `scripts/test_*.py`에서 확인할 수 있습니다.

## 품질 관리 워크플로우
- 코드 스타일: `black app/ agent/`
- 정적 분석: `pylint app/ agent/`
- 타입 검사: `mypy app/ agent/`
- LangSmith 트레이싱: `.env`에 `LANGSMITH_API_KEY` 설정 후 재시작

## 참고 문서
- `python_service/README.md` – 세부 사용 설명서 및 API 예시
- `python_service/claudedocs/ARCHITECTURE.md` – 아키텍처 심화 설명
- `python_service/claudedocs/TEAM_GUIDE.md` – 카테고리 추가 절차
- `python_service/policies/` – 답변 템플릿과 정책 정의 YAML

## 기여 가이드
1. 새 카테고리를 추가할 경우 `agent/categories`, `agent/retrievers`, `app/schemas.py`, `agent/router_runtime.py`에 후크를 등록합니다.
2. 관련 데이터 ETL 스크립트를 `agent/tools/`에 추가하고 `data/` 경로 구조를 맞춥니다.
3. `scripts/test_<category>.py` 또는 `tests/`에 검증 코드를 작성합니다.
4. `policies/`에 답변 템플릿을 정의하고 팀 가이드 문서 업데이트를 권장합니다.

## 라이선스

이 프로젝트는 MIT License를 따릅니다.
