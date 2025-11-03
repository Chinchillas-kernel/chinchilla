#!/usr/bin/env python3
"""Local test script for news category (without FastAPI server)."""
import sys
import os
import time
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ensure environment variables are loaded
from dotenv import load_dotenv

load_dotenv()


def test_news_retriever():
    """Test news retriever in isolation."""
    print("=" * 50)
    print("Testing News Retriever")
    print("=" * 50)

    from agent.retrievers.news_retriever import get_news_retriever

    retriever = get_news_retriever(k=5)
    print("News Retriever initialized")

    result = retriever.invoke({"query": "노인 복지 정책"})

    print(f"Retrieved {len(result.documents)} documents")
    for i, doc in enumerate(result.documents[:3], 1):
        print(f"\n[Doc {i}]")
        print(f"Content: {doc.page_content[:200]}...")
        print(f"Metadata: {doc.metadata}")


def test_news_full_workflow():
    """Test full news agent workflow."""
    print("\n" + "=" * 50)
    print("Testing Full News Workflow")
    print("=" * 50)

    from agent.router_runtime import get_runtime
    from agent.router import dispatch
    from app.schemas import NewsRequest, NewsPayload

    # Initialize runtime
    print("\n1. Initializing runtime...")
    graphs, hooks = get_runtime()
    print(f"Runtime ready with categories: {list(graphs.keys())}")

    # Create request
    print("\n2. Creating news request ...")
    req = NewsRequest(
        category="news",
        payload=NewsPayload(
            query="청양문화원 감성시낭송회",
            category="복지",
        ),
    )
    print(f"Request created: {req.payload.query}")

    # Dispatch request
    print("\n Dispatching request ... ")
    start_time = time.time()
    response = dispatch(req, graphs=graphs, hooks=hooks)
    end_time = time.time()
    duration = end_time - start_time
    print("Workflow complete")

    # Display results
    print("\n" + "=" * 50)
    print("RESULT")
    print("=" * 50)
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSources: {len(response.sources)} documents")
    print(f"\nMetadata: {response.metadata}")
    print(f"\n답변 생성 시간: {duration:.2f}초")


if __name__ == "__main__":
    # Test1: Retriever only
    test_news_retriever()

    # Test2: Full workflow with router
    test_news_full_workflow()

    print("\n All news tests passed!")
