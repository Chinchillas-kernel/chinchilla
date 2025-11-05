"""Scam defense category hooks - Ultra-fast version (1-2s response)."""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import hashlib

from langchain.schema import Document

from agent.categories.base import CategoryHooks
from agent.retrievers.scam_retriever import get_scam_defense_retriever


# ========== 설정 및 캐싱 ========== #

_BASE_DIR = Path(__file__).resolve().parents[2]
_REAL_TIME_DATA_PATH = _BASE_DIR / "data" / "scam_defense" / "scam_patterns.json"
_REAL_TIME_DATA_CACHE: Optional[Dict[str, Any]] = None
_QUERY_CACHE: Dict[str, Any] = {}  # 쿼리 결과 캐시
_CACHE_SIZE_LIMIT = 100

_DANGER_LEVEL_ORDER = {
    "매우높음": 4,
    "높음": 3,
    "중간": 2,
    "낮음": 1,
    "정보": 0,
    "high_risk": 3,
    "medium_risk": 2,
    "low_risk": 1,
}

MAX_PREVIEW = 400  # 축소
MAX_SOURCE_PREVIEW = 150  # 축소
MAX_SOURCES = 3  # 축소


# ========== 유틸리티 함수 ========== #


@lru_cache(maxsize=2048)
def _digits_only(value: Optional[str]) -> str:
    """Extract and cache digits."""
    return "".join(ch for ch in (value or "") if ch.isdigit())


@lru_cache(maxsize=1)
def _load_real_time_data() -> Dict[str, Any]:
    """Load and cache scam dataset (싱글톤)."""
    global _REAL_TIME_DATA_CACHE

    if _REAL_TIME_DATA_CACHE is not None:
        return _REAL_TIME_DATA_CACHE

    try:
        raw = _REAL_TIME_DATA_PATH.read_text(encoding="utf-8")
        _REAL_TIME_DATA_CACHE = json.loads(raw)
    except Exception:
        _REAL_TIME_DATA_CACHE = {}

    return _REAL_TIME_DATA_CACHE


def _hash_query(query: str, sender: Optional[str]) -> str:
    """쿼리 해시 생성 (캐시 키)."""
    key = f"{query}|{sender or ''}"
    return hashlib.md5(key.encode()).hexdigest()


def _clean_cache():
    """캐시 크기 제한."""
    global _QUERY_CACHE
    if len(_QUERY_CACHE) > _CACHE_SIZE_LIMIT:
        # 가장 오래된 절반 제거
        keys = list(_QUERY_CACHE.keys())
        for key in keys[: _CACHE_SIZE_LIMIT // 2]:
            _QUERY_CACHE.pop(key, None)


class ScamDefenseHooks(CategoryHooks):
    """금융 사기 탐지 초고속 버전 (1-2초 목표)

    최적화:
    - 병렬 처리 (RAG + 패턴 분석 동시 실행)
    - 단일 LLM 호출 (Agent 통합)
    - 쿼리 캐싱
    - ChromaDB 최적화
    """

    name: str = "scam_defense"
    web_search_enabled: bool = False
    top_k: int = 5  # 축소 (속도↑)
    min_relevance_threshold: float = 0.5  # 상향 (정확도 유지)

    _retriever: Any = None
    _executor: ThreadPoolExecutor = None

    # ========== 통합 프롬프트 (단일 LLM 호출) ========== #

    rewrite_system_prompt: str = (
        "의심 메시지를 사기 패턴 검색 쿼리로 재작성하라.\n"
        "핵심 키워드만 추출 (OTP, 계좌이체, 본인확인, 카드정지, 보이스피싱 등)\n"
        "예: 'KB은행 OTP 알려주세요' → '금융기관 사칭 OTP 개인정보 요구'\n"
        "쿼리만 반환."
    )

    # 통합 답변 생성 프롬프트 (Agent 3개 → 1개로 통합)
    unified_system_prompt: str = (
        "너는 금융사기 방지 전문 상담사다. "
        "제공된 Knowledge Base(RAG)와 웹 검색 결과를 바탕으로 "
        "구조화된 답변을 제공하라.\n\n"
        "답변 구성:\n"
        "1. 사기 여부 판단 및 위험도 평가 (매우높음/높음/중간/낮음)\n"
        "2. 사기 유형 및 수법 설명\n"
        "3. 즉시 해야 할 대응 방법 (우선순위별 번호 목록)\n"
        "4. 절대 하지 말아야 할 행동 (번호 목록)\n"
        "5. 신고 방법 및 연락처\n"
        "6. 예방 팁 및 주의사항\n"
        "7. 참고한 출처 (Knowledge Base, 실시간 웹 검색)\n\n"
        "답변 형식:\n"
        "- 위험도 아이콘 사용 (🚨 매우위험, ⚠️ 위험, ⚡ 주의, ℹ️ 안전)\n"
        "- 명확하고 실행 가능한 조언\n"
        "- 이해하기 쉬운 언어 사용\n"
        "- 웹 검색으로 얻은 최신 정보 우선 반영\n\n"
        "정확한 출처 문서를 근거로 답변하되, 의심스러운 경우 신중한 태도를 유지하라."
    )

    answer_system_prompt: str = ""  # 사용 안 함 (unified_system_prompt 사용)

    # ========== Helper 메서드 (간소화) ========== #

    @staticmethod
    def format_documents(documents: List[Document]) -> str:
        """문서 포매팅 (간소화)."""
        if not documents:
            return "없음"

        formatted = []
        for idx, doc in enumerate(documents[:5], 1):  # 최대 5개
            meta = doc.metadata or {}
            label = meta.get("scam_type") or meta.get("title") or f"문서{idx}"
            content = doc.page_content.strip()[:MAX_PREVIEW]  # 축소
            formatted.append(f"[{label}] {content}")

        return "\n\n".join(formatted)

    @staticmethod
    def prepare_sources(documents: List[Document]) -> List[Dict[str, Any]]:
        """출처 준비 (간소화)."""
        if not documents:
            return []

        sources = []
        for idx, doc in enumerate(documents[:MAX_SOURCES], 1):
            meta = doc.metadata or {}
            sources.append(
                {
                    "content": doc.page_content.strip()[:MAX_SOURCE_PREVIEW],
                    "metadata": {
                        "source": meta.get("scam_type")
                        or meta.get("title")
                        or f"doc{idx}",
                        "danger_level": meta.get("danger_level"),
                    },
                }
            )
        return sources

    # ========== 실시간 패턴 분석 (최적화) ========== #

    def analyze_realtime_patterns(
        self, query: str, sender: Optional[str] = None
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """실시간 패턴 분석 (캐시 + 최적화)."""
        # 캐시 확인
        cache_key = _hash_query(query, sender)
        if cache_key in _QUERY_CACHE:
            return _QUERY_CACHE[cache_key]

        dataset = _load_real_time_data()
        if not dataset:
            result = ([], {})
            _QUERY_CACHE[cache_key] = result
            return result

        query_lower = query.strip().lower()
        if not query_lower:
            result = ([], {})
            _QUERY_CACHE[cache_key] = result
            return result

        sender_lower = (sender or "").strip().lower()
        query_digits = _digits_only(query)
        sender_digits = _digits_only(sender)

        pattern_docs = []
        scam_matches = []
        highest_score = -1
        highest_level = None

        # 1. 사기 패턴 매칭 (최적화)
        for scam in dataset.get("financial_scams", [])[:20]:  # 최대 20개만
            patterns = [
                p for p in scam.get("patterns", []) if p and p.lower() in query_lower
            ]
            sender_patterns = [
                p
                for p in scam.get("sender_patterns", [])
                if p
                and (
                    p.lower() in query_lower
                    or (sender_lower and p.lower() in sender_lower)
                )
            ]

            if not patterns and not sender_patterns:
                continue

            scam_type = scam.get("type", "알 수 없음")
            danger = scam.get("danger_level", "정보")
            score = _DANGER_LEVEL_ORDER.get(danger, -1)

            if score > highest_score:
                highest_score = score
                highest_level = danger

            # 간소화된 문서 생성
            content = f"유형: {scam_type} | 위험도: {danger}"
            if patterns:
                content += f"\n패턴: {', '.join(patterns[:3])}"  # 최대 3개

            pattern_docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": "실시간알림",
                        "scam_type": scam_type,
                        "danger_level": danger,
                        "origin": "web_search",
                    },
                )
            )

            scam_matches.append(
                {
                    "scam_type": scam_type,
                    "danger_level": danger,
                    "matched_patterns": patterns[:3],  # 축소
                }
            )

        # 2. 키워드 매칭 (간소화)
        keyword_matches = {}
        for risk_level, keywords in (dataset.get("keywords") or {}).items():
            hits = [
                k for k in keywords[:10] if k and k.lower() in query_lower
            ]  # 최대 10개
            if hits:
                keyword_matches[risk_level] = hits[:3]  # 축소
                score = _DANGER_LEVEL_ORDER.get(risk_level, -1)
                if score > highest_score:
                    highest_score = score
                    highest_level = risk_level

        # 3. 공식 연락처 (간소화)
        legitimate_matches = []
        for org, phone in list((dataset.get("legitimate_contacts") or {}).items())[
            :5
        ]:  # 최대 5개
            norm_phone = _digits_only(phone)
            if (org and org.lower() in query_lower) or (
                norm_phone
                and (norm_phone in query_digits or norm_phone in sender_digits)
            ):
                legitimate_matches.append({"organization": org, "phone": phone})
                pattern_docs.append(
                    Document(
                        page_content=f"{org} 공식: {phone}",
                        metadata={"source": "공식연락처", "origin": "web_search"},
                    )
                )

        # 결과 요약
        pattern_analysis = {
            "query": query.strip()[:100],  # 축소
            "sender": (sender or "").strip()[:50],
            "risk_summary": {
                "highest_level": highest_level,
                "score": highest_score,
                "is_high_risk": highest_score >= 3,
            },
            "scam_matches": scam_matches[:5],  # 최대 5개
            "keyword_matches": keyword_matches,
            "legitimate_contacts": legitimate_matches[:3],  # 최대 3개
        }

        result = (pattern_docs[:5], pattern_analysis)  # 최대 5개 문서

        # 캐시 저장
        _QUERY_CACHE[cache_key] = result
        _clean_cache()

        return result

    def _format_pattern_analysis(self, pattern: Dict[str, Any]) -> str:
        """패턴 포매팅 (간소화)."""
        if not pattern:
            return "매칭 없음"

        lines = []
        risk = pattern.get("risk_summary", {})

        if level := risk.get("highest_level"):
            lines.append(f"위험도: {level}")

        if matches := pattern.get("scam_matches", [])[:3]:  # 최대 3개
            lines.append("매칭 유형:")
            for m in matches:
                lines.append(f"- {m['scam_type']} ({m['danger_level']})")

        if kws := pattern.get("keyword_matches"):
            lines.append("위험 키워드:")
            for level, words in list(kws.items())[:2]:  # 최대 2개
                lines.append(f"- {level}: {', '.join(words[:3])}")

        return "\n".join(lines) if lines else "매칭 없음"

    def get_web_documents(
        self, query: str, state: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """웹 문서 검색."""
        sender = state.get("sender") if state else None
        documents, _ = self.analyze_realtime_patterns(query, sender)
        return documents

    def get_retriever(self) -> Any:
        """Retriever 반환 (캐싱 + 최적화)."""
        if self._retriever is None:
            # ChromaDB 최적화 설정
            self._retriever = get_scam_defense_retriever(
                config={
                    "k": self.top_k,
                    "search_type": "similarity",  # MMR보다 빠름
                    "fetch_k": self.top_k * 2,  # 배치 최적화
                }
            )
        return self._retriever

    # ========== 병렬 처리 유틸리티 ========== #

    def _get_executor(self) -> ThreadPoolExecutor:
        """Thread pool 싱글톤."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=3)
        return self._executor

    def _parallel_retrieve(
        self, query: str, state: Optional[Dict[str, Any]]
    ) -> Tuple[List[Document], List[Document], Dict[str, Any]]:
        """병렬 검색: RAG + 패턴 분석 동시 실행."""
        executor = self._get_executor()
        sender = state.get("sender") if state else None

        # 병렬 실행
        rag_future = executor.submit(self.get_retriever().get_relevant_documents, query)
        pattern_future = executor.submit(self.analyze_realtime_patterns, query, sender)

        # 결과 수집 (타임아웃 1초)
        try:
            rag_docs = rag_future.result(timeout=1.0)
        except Exception:
            rag_docs = []

        try:
            pattern_docs, pattern_analysis = pattern_future.result(timeout=1.0)
        except Exception:
            pattern_docs, pattern_analysis = [], {}

        return rag_docs, pattern_docs, pattern_analysis

    # ========== 단일 LLM 호출 (통합 Agent) ========== #

    def _generate_unified_answer(
        self,
        query: str,
        rag_docs: List[Document],
        pattern_docs: List[Document],
        pattern: Dict[str, Any],
    ) -> str:
        """통합 답변 생성 (단일 LLM 호출)."""
        # 컨텍스트 준비
        rag_ctx = self.format_documents(rag_docs) if rag_docs else "관련 정보 없음"
        pattern_ctx = self._format_pattern_analysis(pattern)

        # 단일 프롬프트로 통합
        user_content = (
            f"**의심 메시지:**\n{query}\n\n"
            f"**발신자:** {pattern.get('sender', '미제공')}\n\n"
            f"**실시간 패턴 분석:**\n{pattern_ctx}\n\n"
            f"**Knowledge Base (과거 사례):**\n{rag_ctx}\n\n"
            f"**실시간 사기 DB:**\n{self.format_documents(pattern_docs) if pattern_docs else '매칭 없음'}\n\n"
            "위 정보를 바탕으로 즉시 대응 가이드를 작성하라."
        )

        # LLM 호출 (단일)
        messages = [
            {"role": "system", "content": self.unified_system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            return f"⚠️ 오류 발생: {str(e)}\n긴급 상담: 경찰청 182 | 금융감독원 1332"

    # ========== 메인 진입점 ========== #

    def generate_answer(self, query, documents, web_documents, state):
        """
        초고속 답변 생성 (목표: 1-2초)

        최적화:
        1. 병렬 검색 (RAG + 패턴)
        2. 단일 LLM 호출 (Agent 통합)
        3. 캐싱 전략
        4. 문서 축소
        """
        import time

        start = time.time()

        print(f"[INFO] 🚀 사기 탐지 시작")

        # 1. 병렬 검색 (RAG + 패턴 분석)
        rag_docs, pattern_docs, pattern_analysis = self._parallel_retrieve(query, state)

        print(
            f"[INFO] ⏱️ 검색 완료: {time.time() - start:.2f}s | RAG: {len(rag_docs)}, 패턴: {len(pattern_docs)}"
        )

        # 2. 단일 LLM 호출 (통합 Agent)
        answer = self._generate_unified_answer(
            query, rag_docs, pattern_docs, pattern_analysis
        )

        # 3. 출처 준비
        all_docs = (rag_docs or []) + (pattern_docs or [])
        sources = self.prepare_sources(all_docs)

        elapsed = time.time() - start
        print(f"[INFO] ✅ 완료: {elapsed:.2f}s")

        return {
            "answer": answer,
            "sources": sources,
            "pattern_analysis": pattern_analysis,
            "elapsed_time": elapsed,
        }


__all__ = ["ScamDefenseHooks"]
