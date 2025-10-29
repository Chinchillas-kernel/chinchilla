#!/usr/bin/env python3
"""Quick manual test for the elderly jobs retriever pipeline."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict


def _ensure_project_root() -> None:
    import sys

    root = Path(__file__).resolve().parents[2]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_project_root()

from agent.retrievers.jobs_retriever import (  # noqa: E402  # pylint: disable=wrong-import-position
    JobsRetrievalInput,
    JobsRetrieverPipeline,
    get_jobs_retriever,
)

try:
    from app.config import settings  # noqa: E402  # pylint: disable=wrong-import-position
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Failed to import app.config.settings. Ensure PYTHONPATH is correct.") from exc


def ensure_api_key() -> None:
    if os.getenv("UPSTAGE_API_KEY"):
        return
    api_key = getattr(settings, "upstage_api_key", "")
    if api_key:
        os.environ["UPSTAGE_API_KEY"] = api_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a sample jobs retrieval query.")
    parser.add_argument("query", type=str, help="User query text")
    parser.add_argument("--age", type=int, default=65, help="User age")
    parser.add_argument("--gender", type=str, default="other", help="User gender")
    parser.add_argument("--location", type=str, default=None, help="User location (예: 서울 용산구)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--fetch-multiplier", type=int, default=3, help="Over-fetch multiplier before age filtering")
    parser.add_argument("--db-path", type=str, default=None, help="Override Chroma DB directory")
    return parser.parse_args()


def run_retrieval(args: argparse.Namespace) -> Dict[str, Any]:
    ensure_api_key()
    pipeline: JobsRetrieverPipeline = get_jobs_retriever(
        k=args.top_k,
        fetch_multiplier=args.fetch_multiplier,
        db_path=args.db_path,
    )
    result = pipeline.invoke(
        JobsRetrievalInput(
            query=args.query,
            profile={
                "age": args.age,
                "gender": args.gender,
                "location": args.location,
            },
        )
    )
    return result.to_dict()


def main() -> int:
    args = parse_args()
    try:
        payload = run_retrieval(args)
    except Exception as exc:  # pragma: no cover
        print(f"[ERROR] Retrieval failed: {exc}")
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
