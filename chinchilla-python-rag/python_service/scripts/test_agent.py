#!/usr/bin/env python3
"""Test script for agent workflow (without FastAPI server)."""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def test_jobs_category():
    """Test jobs category end-to-end."""
    print("=" * 60)
    print("Testing Jobs Category")
    print("=" * 60)

    from agent.router_runtime import get_runtime
    from app.schemas import JobsRequest, JobsPayload, JobsProfile

    # Initialize runtime
    graphs, hooks = get_runtime()
    print(f"✓ Runtime initialized with categories: {list(graphs.keys())}")

    # Create request
    req = JobsRequest(
        category="jobs",
        payload=JobsPayload(
            query="서울 용산구에서 경비 일자리 찾고 있습니다",
            profile=JobsProfile(
                age=65,
                gender="male",
                location="서울 용산구",
            ),
        ),
    )

    # Dispatch
    from agent.router import dispatch

    print("\n" + "-" * 60)
    print("Executing workflow...")
    print("-" * 60)

    try:
        response = dispatch(req, graphs=graphs, hooks=hooks)

        print("\n✓ Workflow completed successfully!\n")
        print("=" * 60)
        print("ANSWER")
        print("=" * 60)
        print(response.answer)

        print("\n" + "=" * 60)
        print(f"SOURCES ({len(response.sources)} documents)")
        print("=" * 60)

        for i, source in enumerate(response.sources[:3], 1):
            print(f"\n[Source {i}]")
            print(f"Content: {source['content'][:150]}...")
            print(f"Metadata: {source['metadata']}")

        print("\n" + "=" * 60)
        print("METADATA")
        print("=" * 60)
        print(response.metadata)

    except Exception as e:
        print(f"\n✗ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_jobs_category()

    if success:
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ Tests failed")
        print("=" * 60)
        sys.exit(1)
