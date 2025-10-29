"""Integration test for jobs agent workflow."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.graph import select_hooks, req_to_state, build_graph


def test_jobs_agent_basic():
    """Test basic jobs agent workflow."""
    # Sample request
    req = {
        "category": "jobs",
        "payload": {
            "query": "서울에서 경비 일자리 찾고 있어요",
            "profile": {
                "age": 65,
                "gender": "male",
                "location": "서울 용산구",
            },
        },
    }

    # Step 1: Select hooks
    hooks = select_hooks("jobs")
    print(f"✓ Hooks selected: {hooks.name}")

    # Step 2: Convert to state
    state = req_to_state(req, hooks)
    print(f"✓ State created: query='{state['query']}'")

    # Step 3: Build graph
    graph = build_graph(hooks)
    print("✓ Graph compiled")

    # Step 4: Execute workflow
    try:
        result = graph.invoke(state)
        print(f"✓ Workflow executed successfully")
        print(f"\nAnswer: {result.get('answer', 'N/A')}")
        print(f"\nSources: {len(result.get('sources', []))} documents")

        # Display sources
        for i, source in enumerate(result.get("sources", [])[:3], 1):
            print(f"\n[Source {i}]")
            print(f"Content: {source['content'][:100]}...")
            print(f"Metadata: {source['metadata']}")

    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        raise


if __name__ == "__main__":
    test_jobs_agent_basic()
