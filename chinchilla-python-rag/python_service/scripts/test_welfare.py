#!/usr/bin/env python3
"""Quick welfare category smoke test."""

from __future__ import annotations

import argparse
import time

from agent.router import dispatch
from agent.router_runtime import get_runtime
from app.schemas import WelfarePayload, WelfareRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a welfare retrieval smoke test")
    parser.add_argument(
        "--query",
        default="서울 강남구에 있는 경로당 목록 보여줘",
        help="질문 내용",
    )
    parser.add_argument(
        "--location",
        default="서울 강남구",
    )
    parser.add_argument(
        "--audience",
        default="만 70세 여성 어르신",
        help="대상자 정보 (입력하지 않으려면 빈 문자열)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    audience = args.audience.strip() or None
    location = args.location.strip() or None

    print("에이전트 런타임 초기화 중...")
    graphs, hooks = get_runtime()
    print("런타임 준비 완료.")

    request = WelfareRequest(
        category="welfare",
        payload=WelfarePayload(
            query=args.query,
            location=location,
            audience=audience,
        ),
    )

    print("\n[질문]")
    print(request.payload.query)
    if location:
        print(f" - 지역: {location}")
    if audience:
        print(f" - 대상: {audience}")
    print("-" * 50)

    start = time.perf_counter()
    response = dispatch(request, graphs=graphs, hooks=hooks)
    duration = time.perf_counter() - start

    print("\n[답변]")
    print(response.answer)

    if response.sources:
        print("\n[출처]")
        for idx, source in enumerate(response.sources, 1):
            snippet = source.get("content") or ""
            print(f"{idx}. {snippet[:120]}{'...' if len(snippet) > 120 else ''}")

    print("\n" + "-" * 50)
    print(f"⏱️  총 소요 시간: {duration:.2f}초")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
