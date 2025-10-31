"""Scam defense category hooks."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.schema import Document

from agent.categories.base import CategoryHooks
from agent.retrievers.scam_retriever import get_scam_defense_retriever


_BASE_DIR = Path(__file__).resolve().parents[2]
_REAL_TIME_DATA_PATH = _BASE_DIR / "data" / "scam_defense" / "scam_patterns.json"
_REAL_TIME_DATA_CACHE: Optional[Dict[str, Any]] = None
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


def _digits_only(value: Optional[str]) -> str:
    """Extract digits from string for loose phone-number matching."""
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isdigit())


def _load_real_time_data() -> Dict[str, Any]:
    """Load scam alert dataset once and cache it."""
    global _REAL_TIME_DATA_CACHE

    if _REAL_TIME_DATA_CACHE is not None:
        return _REAL_TIME_DATA_CACHE

    dataset: Dict[str, Any] = {}
    try:
        raw = _REAL_TIME_DATA_PATH.read_text(encoding="utf-8")
        dataset = json.loads(raw)
        _REAL_TIME_DATA_CACHE = dataset
    except FileNotFoundError:
        print(f"[WARN] Real-time scam dataset not found: {_REAL_TIME_DATA_PATH}")
        _REAL_TIME_DATA_CACHE = {}
    except json.JSONDecodeError as exc:
        print(f"[WARN] Failed to parse scam_patterns.json: {exc}")
        _REAL_TIME_DATA_CACHE = {}

    return _REAL_TIME_DATA_CACHE


class ScamDefenseHooks(CategoryHooks):
    """Hooks for financial scam detection and response category.
    
    금융 사기 탐지 및 대응 카테고리
    - 멀티 에이전트: 분석 Agent → 판단 Agent → 조언 Agent
    - RAG 기반 지식 검색 (Knowledge Base)
    - 웹 검색을 통한 실시간 사기 DB 연동
    """

    name: str = "scam_defense"
    web_search_enabled: bool = False

    rewrite_system_prompt: str = (
        "너는 금융사기 탐지 전문가다. "
        "사용자가 받은 의심스러운 메시지를 사기 패턴 검색에 적합하게 분석하라.\n\n"
        "재작성 시 포함할 요소:\n"
        "- 핵심 사기 키워드 추출 (예: OTP, 계좌이체, 본인확인, 카드정지)\n"
        "- 사기 유형 식별 (예: 보이스피싱, 대출사기, 투자사기, 피싱)\n"
        "- 발신자 패턴 (예: 금융기관 사칭, 공공기관 사칭)\n"
        "- 요구사항 분석 (예: 개인정보 요구, 금전 요구)\n\n"
        "예시:\n"
        "- 원본: 'KB은행입니다. OTP 알려주세요'\n"
        "- 재작성: '금융기관 사칭 보이스피싱 OTP 개인정보 요구'\n\n"
        "다른 어떤 설명이나 서식 없이 재작성된 검색 쿼리만 반환하라."
    )

    answer_system_prompt: str = (
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

    top_k: int = 8
    min_relevance_threshold: float = 0.4
    
    # ------------------------------------------------------------------ #
    # Helper utilities                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_documents(documents: List[Document]) -> str:
        """Render documents as structured context for analysis agents."""
        if not documents:
            return "없음"

        formatted: List[str] = []
        for idx, doc in enumerate(documents, 1):
            metadata = doc.metadata or {}
            label = (
                metadata.get("title")
                or metadata.get("source")
                or metadata.get("scam_type")
                or metadata.get("doc_id")
                or f"문서 {idx}"
            )

            preview = doc.page_content.strip()
            if len(preview) > 600:
                preview = preview[:600] + "..."

            formatted.append(f"[{label}]\n{preview}\n")

        return "\n".join(formatted)

    @staticmethod
    def prepare_sources(documents: List[Document]) -> List[Dict[str, Any]]:
        """Prepare compact source payload for the final answer."""
        if not documents:
            return []

        prepared: List[Dict[str, Any]] = []
        for idx, doc in enumerate(documents[:5], 1):
            meta = dict(doc.metadata or {})
            preview = doc.page_content.strip()
            if len(preview) > 200:
                preview = preview[:200] + "..."

            meta.setdefault(
                "source",
                meta.get("title")
                or meta.get("scam_type")
                or meta.get("doc_id")
                or f"doc_{idx}",
            )

            prepared.append(
                {
                    "content": preview,
                    "metadata": meta,
                }
            )

        return prepared

    # ------------------------------------------------------------------ #
    # Real-time scam DB integration                                       #
    # ------------------------------------------------------------------ #

    def analyze_realtime_patterns(
        self, query: str, sender: Optional[str] = None
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """Run local pattern analysis to simulate real-time alerts."""
        dataset = _load_real_time_data()
        if not dataset:
            return [], {}

        query_text = (query or "").strip()
        query_lower = query_text.lower()
        sender_text = (sender or "").strip()
        sender_lower = sender_text.lower()

        query_digits = _digits_only(query_text)
        sender_digits = _digits_only(sender_text)

        pattern_documents: List[Document] = []
        scam_matches: List[Dict[str, Any]] = []
        sender_matches: List[Dict[str, Any]] = []
        legitimate_matches: List[Dict[str, Any]] = []
        seen_sender_values = set()

        for scam in dataset.get("financial_scams", []):
            patterns = [p for p in scam.get("patterns", []) if p]
            sender_patterns = [p for p in scam.get("sender_patterns", []) if p]

            matched_patterns = [
                pattern
                for pattern in patterns
                if pattern.lower() in query_lower
            ]

            matched_sender_patterns: List[str] = []
            for candidate in sender_patterns:
                candidate_lower = candidate.lower()
                if candidate_lower in query_lower or (
                    sender_lower and candidate_lower in sender_lower
                ):
                    matched_sender_patterns.append(candidate)
                    if candidate not in seen_sender_values:
                        sender_matches.append(
                            {
                                "value": candidate,
                                "match_type": "pattern_sender",
                                "scam_type": scam.get("type"),
                            }
                        )
                        seen_sender_values.add(candidate)

            if not matched_patterns and not matched_sender_patterns:
                continue

            scam_type = scam.get("type", "알 수 없음")
            danger_level = scam.get("danger_level", "정보")
            response_actions = scam.get("response_actions") or []
            prevention_tips = scam.get("prevention_tips") or []

            lines = [
                f"사기 유형: {scam_type}",
                f"위험도: {danger_level}",
            ]
            if matched_patterns:
                lines.append("")
                lines.append("매칭된 패턴:")
                lines.extend(f"- {item}" for item in matched_patterns)
            if matched_sender_patterns:
                lines.append("")
                lines.append("매칭된 발신자 패턴:")
                lines.extend(f"- {item}" for item in matched_sender_patterns)

            if response_actions:
                lines.append("")
                lines.append("권장 대응:")
                lines.extend(f"- {action}" for action in response_actions)

            if prevention_tips:
                lines.append("")
                lines.append("예방 팁:")
                lines.extend(f"- {tip}" for tip in prevention_tips)

            metadata = {
                "source": "real_time_alert",
                "origin": "web_search",
                "doc_id": scam.get("id"),
                "scam_type": scam_type,
                "danger_level": danger_level,
                "matched_patterns": matched_patterns,
                "matched_sender_patterns": matched_sender_patterns,
            }

            pattern_documents.append(
                Document(page_content="\n".join(lines).strip(), metadata=metadata)
            )
            scam_matches.append(
                {
                    "id": scam.get("id"),
                    "scam_type": scam_type,
                    "danger_level": danger_level,
                    "matched_patterns": matched_patterns,
                    "matched_sender_patterns": matched_sender_patterns,
                }
            )

        keyword_matches: Dict[str, List[str]] = {}
        for risk_level, keyword_list in (dataset.get("keywords") or {}).items():
            hits = [
                keyword
                for keyword in keyword_list
                if keyword and keyword.lower() in query_lower
            ]
            if not hits:
                continue

            keyword_matches[risk_level] = hits
            content = (
                f"위험도 {risk_level} 키워드 매칭: {', '.join(hits)}\n"
                "해당 표현이 포함된 연락은 금융사기 가능성이 높으므로 즉시 대응이 필요합니다."
            )
            metadata = {
                "source": "real_time_keyword",
                "origin": "web_search",
                "risk_level": risk_level,
                "matched_keywords": hits,
            }
            pattern_documents.append(
                Document(page_content=content.strip(), metadata=metadata)
            )

        legitimate_contacts = dataset.get("legitimate_contacts") or {}
        for organization, phone in legitimate_contacts.items():
            matched_on = None
            normalized_phone = _digits_only(phone)

            if organization and organization.lower() in query_lower:
                matched_on = "organization"
            elif normalized_phone and (
                normalized_phone in query_digits
                or normalized_phone in sender_digits
            ):
                matched_on = "phone"

            if not matched_on:
                continue

            legitimate_matches.append(
                {
                    "organization": organization,
                    "phone": phone,
                    "matched_on": matched_on,
                }
            )

            derived_value = organization if matched_on == "organization" else phone
            if derived_value and derived_value not in seen_sender_values:
                sender_matches.append(
                    {
                        "value": derived_value,
                        "match_type": "legitimate_contact",
                    }
                )
                seen_sender_values.add(derived_value)

            content = (
                f"{organization} 공식 연락처: {phone}\n"
                "연락처가 상이하거나 다른 계좌로 송금을 요구하면 즉시 의심하세요."
            )
            metadata = {
                "source": "official_contact",
                "origin": "web_search",
                "organization": organization,
                "phone": phone,
            }
            pattern_documents.append(
                Document(page_content=content.strip(), metadata=metadata)
            )

        highest_level = None
        highest_score = -1
        for match in scam_matches:
            level = match.get("danger_level")
            score = _DANGER_LEVEL_ORDER.get(level, -1)
            if score > highest_score:
                highest_score = score
                highest_level = level

        for keyword_level in keyword_matches.keys():
            score = _DANGER_LEVEL_ORDER.get(keyword_level, -1)
            if score > highest_score:
                highest_score = score
                highest_level = keyword_level

        scam_type_candidates = sorted(
            {
                match.get("scam_type")
                for match in scam_matches
                if match.get("scam_type")
            }
        )

        pattern_analysis = {
            "query": query_text,
            "sender": sender_text,
            "scam_matches": scam_matches,
            "keyword_matches": keyword_matches,
            "legitimate_contacts": legitimate_matches,
            "sender_matches": sender_matches,
            "risk_summary": {
                "highest_level": highest_level,
                "score": highest_score,
                "scam_type_candidates": scam_type_candidates,
                "keyword_levels": list(keyword_matches.keys()),
                "is_high_risk": bool(
                    highest_score >= 3 or "high_risk" in keyword_matches
                ),
            },
        }

        return pattern_documents, pattern_analysis

    def _format_pattern_analysis(self, pattern_analysis: Dict[str, Any]) -> str:
        """Render realtime pattern analysis as structured text."""
        if not pattern_analysis:
            return "매칭된 패턴 없음"

        lines: List[str] = []
        risk_summary = pattern_analysis.get("risk_summary") or {}
        highest_level = risk_summary.get("highest_level")
        if highest_level:
            lines.append(f"- 추정 위험도: {highest_level}")
        elif risk_summary.get("is_high_risk"):
            lines.append("- 추정 위험도: 높음")

        scam_matches = pattern_analysis.get("scam_matches") or []
        if scam_matches:
            lines.append("매칭된 사기 유형:")
            for match in scam_matches:
                scam_type = match.get("scam_type", "불명")
                danger = match.get("danger_level", "정보")
                entry = f"- {scam_type} (위험도 {danger})"
                patterns = match.get("matched_patterns") or []
                if patterns:
                    entry += f" | 패턴: {', '.join(patterns)}"
                sender_patterns = match.get("matched_sender_patterns") or []
                if sender_patterns:
                    entry += f" | 발신자: {', '.join(sender_patterns)}"
                lines.append(entry)

        keyword_matches = pattern_analysis.get("keyword_matches") or {}
        if keyword_matches:
            lines.append("위험 키워드 매칭:")
            for risk_level, keywords in keyword_matches.items():
                lines.append(f"- {risk_level}: {', '.join(keywords)}")

        legitimate_contacts = pattern_analysis.get("legitimate_contacts") or []
        if legitimate_contacts:
            lines.append("공식 연락처 일치:")
            for contact in legitimate_contacts:
                org = contact.get("organization")
                phone = contact.get("phone")
                matched_on = contact.get("matched_on")
                lines.append(f"- {org} ({phone}) - {matched_on} 일치")

        return "\n".join(lines) if lines else "매칭된 패턴 없음"

    def get_web_documents(
        self, query: str, state: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Retrieve matches from the real-time scam dataset."""
        sender = None
        if state and isinstance(state, dict):
            sender = state.get("sender")

        documents, _ = self.analyze_realtime_patterns(
            query=query, sender=sender
        )
        return documents[:5]
    
    # ===== 멀티 에이전트 프롬프트 ===== #
    
    analysis_system_prompt: str = (
        "너는 사기 분석 Agent다. "
        "사용자 메시지, Knowledge Base(RAG 검색), 실시간 웹 검색 결과를 종합하여 "
        "사기 징후를 구조적으로 정리하라.\n\n"
        "출력 형식:\n"
        "### 📋 분석 단계 결과\n\n"
        "#### 1. 핵심 의심 요소\n"
        "- [메시지에서 발견된 의심스러운 요소들]\n\n"
        "#### 2. Knowledge Base 매칭\n"
        "- [RAG 검색으로 찾은 관련 사기 유형과 패턴]\n\n"
        "#### 3. 발신자/연락처 특이사항\n"
        "- [발신자 정보 분석]\n\n"
        "#### 4. 요구/지시 사항 분석\n"
        "- [메시지에서 요구하는 행동 분석]\n\n"
        "#### 5. 최신 사기 트렌드 (웹 검색)\n"
        "- [실시간 웹 검색으로 발견된 유사 사례 및 최신 정보]\n\n"
        "명확하고 객관적으로 작성하라."
    )
    
    verdict_system_prompt: str = (
        "너는 사기 판단 Agent다. "
        "분석 Agent의 결과, Knowledge Base, 웹 검색 결과를 종합해 위험도를 판단하라.\n\n"
        "출력 형식은 다음 JSON을 엄격히 따르라:\n"
        "{\n"
        '  "risk_level": "매우높음|높음|중간|낮음",\n'
        '  "risk_icon": "🚨|⚠️|⚡|ℹ️",\n'
        '  "scam_type": "사기 유형 추정 (구체적으로)",\n'
        '  "confidence": "판단 근거 요약 (1-2문장)",\n'
        '  "key_evidence": ["근거1", "근거2", "근거3"],\n'
        '  "immediate_actions": ["즉시 취해야 할 행동1", "행동2"],\n'
        '  "do_not_do": ["절대 하지 말아야 할 행동1", "행동2"]\n'
        "}\n\n"
        "주의사항:\n"
        "- 반드시 유효한 JSON만 출력하라\n"
        "- JSON 외의 다른 텍스트는 절대 출력하지 말라\n"
        "- Knowledge Base의 정보를 우선 참고하라\n"
        "- 웹 검색에서 발견된 최신 사례를 반영하라"
    )
    
    counsel_system_prompt: str = (
        "너는 사기 대응 조언 Agent다. "
        "분석 Agent와 판단 Agent의 결과를 바탕으로 "
        "사용자에게 실용적이고 명확한 대응 가이드를 제공하라.\n\n"
        "출력 형식:\n"
        "### 🎯 최종 대응 가이드\n\n"
        "#### 1. 위험도 판단\n"
        "{risk_icon} **{risk_level}** - {한줄 요약}\n\n"
        "#### 2. 사기 유형 및 수법\n"
        "- 유형: {scam_type}\n"
        "- 주요 수법: [설명]\n"
        "- 최근 유사 사례: [웹 검색 결과 반영]\n\n"
        "#### 3. ✅ 즉시 해야 할 대응 방법 (우선순위 순)\n"
        "1. [구체적 행동 1]\n"
        "2. [구체적 행동 2]\n"
        "3. [구체적 행동 3]\n\n"
        "#### 4. ❌ 절대 하지 말아야 할 행동\n"
        "1. [금지 행동 1]\n"
        "2. [금지 행동 2]\n\n"
        "#### 5. 📞 신고 방법 및 연락처\n"
        "- 경찰청 사이버안전국: 182 (24시간)\n"
        "- 금융감독원: 1332\n"
        "- 한국인터넷진흥원: 118\n"
        "- 범죄신고: 112\n\n"
        "#### 6. 💡 예방 팁 및 주의사항\n"
        "- [예방법 1]\n"
        "- [예방법 2]\n"
        "- [예방법 3]\n\n"
        "#### 7. 📚 참고 출처\n"
        "- RAG 검색: [출처]\n"
        "- 실시간 패턴: [매칭 결과]\n"
        "- 웹 검색: [최신 정보]\n\n"
        "모든 조언은 실행 가능하고 구체적으로 작성하라."
    )

    def get_retriever(self) -> Any:
        """Return scam defense retriever."""
        config = {"k": self.top_k}
        return get_scam_defense_retriever(config=config)

    # ------------------------------------------------------------------ #
    # 멀티 에이전트 시스템 구현                                             #
    # ------------------------------------------------------------------ #

    def _call_llm(self, system_prompt: str, user_content: str) -> str:
        """Utility to invoke shared LLM with prompts."""
        llm = self.llm
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        response = llm.invoke(messages)
        return response.content.strip()

    def _run_analysis(
        self,
        query: str,
        rag_context: str,
        web_context: str,
        pattern_analysis: Dict[str, Any],
    ) -> str:
        """
        Agent 1: 분석 단계
        의심 문자 종합 분석
        """
        pattern_summary = self._format_pattern_analysis(pattern_analysis)
        sender_text = pattern_analysis.get("sender") or "제공되지 않음"
        user_content = (
            f"=== 사용자 메시지 ===\n{query}\n\n"
            f"=== 발신자 정보 ===\n{sender_text}\n\n"
            f"=== 실시간 패턴 분석 ===\n{pattern_summary}\n\n"
            f"=== Knowledge Base (RAG 검색) ===\n{rag_context}\n\n"
            f"=== 실시간 사기 DB (웹 검색) ===\n{web_context}\n\n"
            "위 정보를 종합하여 분석 결과를 출력 형식에 맞춰 작성하라."
        )
        return self._call_llm(self.analysis_system_prompt, user_content)

    def _run_verdict(
        self, 
        query: str,
        rag_context: str,
        web_context: str,
        analysis: str,
        pattern_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Agent 2: 판단 단계
        사기 여부 판별 및 위험도 평가
        """
        pattern_summary = self._format_pattern_analysis(pattern_analysis)
        user_content = (
            f"=== 사용자 메시지 ===\n{query}\n\n"
            f"=== 분석 Agent 결과 ===\n{analysis}\n\n"
            f"=== 실시간 패턴 분석 ===\n{pattern_summary}\n\n"
            f"=== Knowledge Base (RAG 검색) ===\n{rag_context}\n\n"
            f"=== 실시간 사기 DB (웹 검색) ===\n{web_context}\n\n"
            "위 지침의 JSON 형식으로만 응답하라. JSON 외의 텍스트는 출력하지 말라."
        )
        raw = self._call_llm(self.verdict_system_prompt, user_content)

        # JSON 파싱
        parsed: Dict[str, Any] = {
            "risk_level": "중간",
            "risk_icon": "⚡",
            "scam_type": "의심 사례",
            "confidence": raw,
            "key_evidence": [],
            "immediate_actions": [],
            "do_not_do": [],
        }
        
        try:
            # JSON만 추출 (앞뒤 텍스트 제거)
            raw_stripped = raw.strip()
            if raw_stripped.startswith("```json"):
                raw_stripped = raw_stripped[7:]
            if raw_stripped.startswith("```"):
                raw_stripped = raw_stripped[3:]
            if raw_stripped.endswith("```"):
                raw_stripped = raw_stripped[:-3]
            raw_stripped = raw_stripped.strip()
            
            parsed_json = json.loads(raw_stripped)
            if isinstance(parsed_json, dict):
                parsed.update(parsed_json)
                print(f"[INFO] Verdict Agent - Risk: {parsed['risk_level']}, Type: {parsed['scam_type']}")
        except Exception as e:
            print(f"[WARN] Verdict JSON parsing failed: {e}")
        
        return parsed

    def _run_counsel(
        self,
        query: str,
        rag_context: str,
        web_context: str,
        analysis: str,
        verdict: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
    ) -> str:
        """
        Agent 3: 조언 단계
        대응 방법 제시
        """
        verdict_text = (
            f"위험도: {verdict.get('risk_icon', '⚡')} {verdict.get('risk_level', '중간')}\n"
            f"사기 유형 추정: {verdict.get('scam_type', '불명')}\n"
            f"판단 근거: {verdict.get('confidence', '')}\n"
            f"핵심 근거: {', '.join(verdict.get('key_evidence', []) or [])}\n"
            f"즉시 행동: {', '.join(verdict.get('immediate_actions', []) or [])}\n"
            f"금지 행동: {', '.join(verdict.get('do_not_do', []) or [])}"
        )
        pattern_summary = self._format_pattern_analysis(pattern_analysis)
        
        user_content = (
            f"=== 사용자 메시지 ===\n{query}\n\n"
            f"=== 분석 Agent 결과 ===\n{analysis}\n\n"
            f"=== 판단 Agent 결과 ===\n{verdict_text}\n\n"
            f"=== 실시간 패턴 분석 ===\n{pattern_summary}\n\n"
            f"=== Knowledge Base (RAG 검색) ===\n{rag_context}\n\n"
            f"=== 실시간 사기 DB (웹 검색) ===\n{web_context}\n\n"
            "위 정보를 바탕으로 최종 대응 가이드를 counsel_system_prompt의 출력 형식에 맞춰 작성하라.\n"
            "모든 섹션을 포함하고, 실행 가능한 구체적 조언을 제공하라."
        )
        return self._call_llm(self.counsel_system_prompt, user_content)

    def generate_answer(self, query, documents, web_documents, state):
        """
        Override: 멀티 에이전트 파이프라인으로 답변 생성
        
        Pipeline:
        1. 분석 Agent - 의심 문자 분석
        2. 판단 Agent - 사기 판별
        3. 조언 Agent - 대응 방법 제시
        
        데이터 소스:
        - Knowledge Base: ChromaDB 기반 지식 베이스 (RAG)
        - 실시간 사기 DB: 웹 검색을 통한 최신 사기 트렌드
        """
        print(f"\n[INFO] ===== 멀티 에이전트 사기 탐지 시작 =====")
        print(f"[INFO] Query: {query[:100]}...")
        
        # 문서 컨텍스트 준비
        documents = list(documents or [])
        web_documents = list(web_documents or [])
        pattern_analysis: Dict[str, Any] = {}
        sender = None
        if state and isinstance(state, dict):
            pattern_analysis = state.get("pattern_analysis") or {}
            sender = state.get("sender")
        if not pattern_analysis:
            extra_docs, pattern_analysis = self.analyze_realtime_patterns(
                query=query, sender=sender
            )
            if extra_docs:
                web_documents.extend(extra_docs)

        all_docs = documents + web_documents
        rag_context = self.format_documents(documents)
        web_context = self.format_documents(web_documents) if web_documents else "없음"
        
        print(f"[INFO] Documents - Knowledge Base: {len(documents)}, Web Search: {len(web_documents)}")
        
        # 1. 분석 Agent
        print(f"[INFO] Agent 1: 분석 시작...")
        analysis = self._run_analysis(
            query, rag_context, web_context, pattern_analysis
        )
        
        # 2. 판단 Agent
        print(f"[INFO] Agent 2: 판단 시작...")
        verdict = self._run_verdict(
            query, rag_context, web_context, analysis, pattern_analysis
        )
        
        # 3. 조언 Agent
        print(f"[INFO] Agent 3: 조언 생성 시작...")
        counsel = self._run_counsel(
            query, rag_context, web_context, analysis, verdict, pattern_analysis
        )
        
        # 출처 준비
        sources = self.prepare_sources(all_docs)
        
        print(f"[INFO] ===== 멀티 에이전트 사기 탐지 완료 =====\n")
        
        return {
            "answer": counsel,
            "sources": sources,
            "analysis": analysis,
            "verdict": verdict,
            "pattern_analysis": pattern_analysis,
        }


__all__ = ["ScamDefenseHooks"]
