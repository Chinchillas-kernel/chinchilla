#!/usr/bin/env python3
"""Local test script for jobs agent (without FastAPI server)."""
import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ensure environment variables are loaded
from dotenv import load_dotenv

load_dotenv()


def test_retriever():
    """Test retriever in isolation."""
    print("=" * 50)
    print("Testing Retriever")
    print("=" * 50)

    from agent.retrievers.jobs_retriever import get_jobs_retriever

    retriever = get_jobs_retriever(k=5)
    print("✓ Retriever initialized")

    result = retriever.invoke(
        {
            "query": "경비 일자리",
            "profile": {"age": 65, "gender": "male", "location": "서울 용산구"},
        }
    )

    print(f"✓ Retrieved {len(result.documents)} documents")
    for i, doc in enumerate(result.documents[:3], 1):
        print(f"\n[Doc {i}]")
        print(f"Content: {doc.page_content[:150]}...")
        print(f"Metadata: {doc.metadata}")


def test_full_workflow():
    """Test full agent workflow."""
    print("\n" + "=" * 50)
    print("Testing Full Workflow")
    print("=" * 50)

    from agent.graph import select_hooks, req_to_state, build_graph

    # Sample request
    req = {
        "category": "jobs",
        "payload": {
            "query": "서울 용산구에서 경비 일자리 찾고 있습니다",
            "profile": {"age": 65, "gender": "male", "location": "서울 용산구"},
        },
    }

    print("\n1. Selecting hooks...")
    hooks = select_hooks("jobs")
    print(f"   ✓ Hooks: {hooks.name}")

    print("\n2. Creating state...")
    state = req_to_state(req, hooks)
    print(f"   ✓ Query: {state['query']}")

    print("\n3. Building graph...")
    graph = build_graph(hooks)
    print("   ✓ Graph compiled")

    print("\n4. Executing workflow...")
    result = graph.invoke(state)
    print("   ✓ Workflow complete")

    print("\n" + "=" * 50)
    print("RESULT")
    print("=" * 50)
    print(f"\nAnswer:\n{result.get('answer', 'N/A')}")
    print(f"\nSources: {len(result.get('sources', []))} documents")


if __name__ == "__main__":
    # Test retriever first
    test_retriever()

    # Then test full workflow
    test_full_workflow()

    print("\n✓ All tests passed!")
