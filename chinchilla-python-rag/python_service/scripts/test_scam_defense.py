#!/usr/bin/env python3
"""Utility script for exercising the scam defense agent."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List, Tuple

# Disable Chroma telemetry noise (only affects local runs)
os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "false")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()


# ============================================================================
# Formatting helpers
# ============================================================================


def _print_header(title: str, width: int = 80) -> None:
    """Utility to print section headers."""
    bar = "=" * width
    print(f"\n{bar}\n{title}\n{bar}")


def _print_sources(sources: Iterable[dict]) -> None:
    """Pretty-print top sources returned by the agent."""
    for idx, source in enumerate(list(sources)[:3], 1):
        if not isinstance(source, dict):
            continue
        metadata = source.get("metadata", {}) or {}
        label = (
            metadata.get("source")
            or metadata.get("scam_type")
            or metadata.get("doc_id")
            or f"doc_{idx}"
        )
        preview = str(source.get("content", "")).strip().replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:120] + "..."
        print(f"  [{idx}] {label}: {preview}")


# ============================================================================
# Smoke tests (optional)
# ============================================================================


def run_retriever_smoke_test() -> None:
    """Validate the scam defense retriever with representative queries."""
    _print_header("Scam Defense Retriever Smoke Test")

    from agent.retrievers.scam_retriever import get_scam_defense_retriever

    retriever = get_scam_defense_retriever(config={"k": 5})
    print("✓ Retriever initialised (k=5)")

    queries: Tuple[Tuple[str, str], ...] = (
        ("보이스피싱", "금융감독원에서 안전계좌로 이체하라는데 이게 사기인가요?"),
        ("대출 사기", "무담보 대출인데 선입금 수수료를 요구합니다. 정상인가요?"),
    )

    for label, query in queries:
        print(f"\n[Case] {label}")
        print(f" Query : {query}")
        documents = retriever.invoke({"query": query}) or []
        print(f" → Retrieved {len(documents)} documents")

        for idx, doc in enumerate(documents[:2], 1):
            meta = doc.metadata or {}
            source_label = (
                meta.get("source_type")
                or meta.get("source")
                or meta.get("scam_type")
                or f"doc_{idx}"
            )
            snippet = doc.page_content.strip().replace("\n", " ")
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."
            print(f"   [{idx}] {source_label}: {snippet}")

    print("\n✓ Retriever smoke test complete.")


def run_demo_scenarios(graphs, hooks) -> None:
    """Run the full scam defense workflow against curated demo scenarios."""
    _print_header("Scam Defense Demo Scenarios")

    from agent.router import dispatch
    from app.schemas import ScamDefensePayload, ScamDefenseRequest

    scenarios = (
        {
            "name": "보이스피싱 의심",
            "query": (
                "이 문자가 사기인가요? 서울중앙지검이라고 하면서 제 계좌가 범죄에 "
                "연루되었다고 안전계좌로 송금을 요구합니다."
            ),
            "sender": "010-1234-5678",
        },
        {
            "name": "대출 사기 의심",
            "query": (
                "무담보 대출을 해준다면서 100% 승인이라며 수수료 50만원을 먼저 보내라고 "
                "합니다. 믿어도 될까요?"
            ),
            "sender": "010-5678-1234",
        },
        {
            "name": "정상 알림 확인",
            "query": (
                "KB국민은행에서 거래내역 알림이 왔는데 앱에서 확인하라는 내용입니다. "
                "사기 가능성이 있을까요?"
            ),
            "sender": "1588-0000",
        },
    )

    for scenario in scenarios:
        _print_header(f"Scenario: {scenario['name']}", width=70)

        request = ScamDefenseRequest(
            category="scam_defense",
            payload=ScamDefensePayload(
                query=scenario["query"],
                sender=scenario["sender"],
            ),
        )

        start = time.time()
        response = dispatch(request, graphs=graphs, hooks=hooks)
        duration = time.time() - start

        print(f"Elapsed: {duration:.2f}s")
        print("\nAnswer:\n")
        print(response.answer)

        print("\nSources:")
        print(f" total = {len(response.sources)}")
        if response.sources:
            _print_sources(response.sources)

        verdict = response.metadata.get("verdict") if response.metadata else None
        if verdict:
            print(
                f"\nVerdict: {verdict.get('risk_icon', '⚡')} "
                f"{verdict.get('risk_level', 'N/A')} - {verdict.get('scam_type', 'N/A')}"
            )

    print("\n✓ Demo scenarios complete.")


# ============================================================================
# Interactive session
# ============================================================================


def interactive_session(graphs, hooks) -> None:
    """Allow a user to manually enter scam defense questions."""
    from agent.router import dispatch
    from app.schemas import ScamDefensePayload, ScamDefenseRequest

    _print_header("Scam Defense Interactive Session")
    print("Enter suspect messages to analyse (press Enter with blank query to exit).\n")

    while True:
        try:
            query = input("의심 메시지 입력 (종료: Enter): ").strip()
        except EOFError:
            print("\n종료합니다.")
            break

        if not query:
            print("종료합니다.")
            break

        sender = input("발신자 정보 (선택 입력, Enter로 건너뛰기): ").strip() or None

        request = ScamDefenseRequest(
            category="scam_defense",
            payload=ScamDefensePayload(query=query, sender=sender),
        )

        start = time.time()
        response = dispatch(request, graphs=graphs, hooks=hooks)
        duration = time.time() - start

        print(f"\n⏱️  처리 시간: {duration:.2f}s\n")
        print(response.answer)

        print("\n--- 참고 출처 ---")
        if response.sources:
            _print_sources(response.sources)
        else:
            print(" 관련 출처 없음")

        verdict = response.metadata.get("verdict") if response.metadata else None
        if verdict:
            print(
                f"\n판단 요약: {verdict.get('risk_icon', '⚡')} "
                f"{verdict.get('risk_level', 'N/A')} - {verdict.get('scam_type', 'N/A')}"
            )

        print("\n" + "-" * 60 + "\n")


# ============================================================================
# CLI entrypoint
# ============================================================================


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scam defense agent test utility.",
        epilog=(
            "Examples:\n"
            "  python scripts/test_scam_defense.py --interactive    # manual queries\n"
            "  python scripts/test_scam_defense.py --demo --smoke    # run demos + retriever smoke test"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive Q&A session.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run curated demo scenarios.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run retriever smoke test.",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    # Load runtime once (used by both demo and interactive modes)
    graphs = hooks = None
    if args.demo or args.interactive:
        from agent.router_runtime import get_runtime

        graphs, hooks = get_runtime()
        print(f"✓ Runtime ready with categories: {list(graphs.keys())}")

    if args.smoke:
        run_retriever_smoke_test()

    if args.demo and graphs and hooks:
        run_demo_scenarios(graphs, hooks)

    if args.interactive and graphs and hooks:
        interactive_session(graphs, hooks)

    if not any([args.smoke, args.demo, args.interactive]):
        # Default to interactive session if no flags provided
        from agent.router_runtime import get_runtime

        graphs, hooks = get_runtime()
        print(f"✓ Runtime ready with categories: {list(graphs.keys())}")
        interactive_session(graphs, hooks)

    print("\n✓ Scam defense utility finished.")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual script
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print("\n✗ Scam defense utility failed.")
        print(f"Reason: {exc}")
        import traceback

        traceback.print_exc()
        raise SystemExit(1)
