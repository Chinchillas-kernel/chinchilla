"""Base class for category-specific hooks."""
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from pydantic import BaseModel
import requests


class SimpleLLM:
    """Simple LLM wrapper that directly calls Upstage API without Pydantic issues."""

    def __init__(self, api_key: str, model: str = "solar-pro"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.upstage.ai/v1/solar/chat/completions"

    def invoke(self, messages: List[Dict[str, str]]) -> Any:
        """Call Upstage API directly."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        result = response.json()

        # Return object with .content attribute to match ChatUpstage interface
        class Response:
            def __init__(self, content: str):
                self.content = content

        return Response(result["choices"][0]["message"]["content"])


# Global LLM instance
_GLOBAL_LLM = None


def get_global_llm() -> SimpleLLM:
    """Get or create global LLM instance."""
    global _GLOBAL_LLM
    if _GLOBAL_LLM is None:
        from app.config import settings
        _GLOBAL_LLM = SimpleLLM(
            api_key=settings.upstage_api_key,
            model="solar-pro",
        )
    return _GLOBAL_LLM


class CategoryHooks(BaseModel, ABC):
    """Base class for category-specific configuration and behavior.

    Each category (jobs, welfare, news, etc.) should:
    1. Extend this class
    2. Define category-specific prompts
    3. Implement get_retriever() factory method
    """

    name: str  # Category identifier (e.g., "jobs", "welfare")

    # Prompts (override in subclass)
    rewrite_system_prompt: str = (
        "너는 검색 쿼리 최적화 전문가다. "
        "사용자 질문을 검색에 적합하게 재작성하라."
    )

    answer_system_prompt: str = (
        "너는 전문 상담원이다. "
        "제공된 문서를 바탕으로 정확하게 답변하라."
    )

    # Optional: category-specific scoring/filtering
    min_relevance_threshold: float = 0.3
    top_k: int = 5

    @property
    def llm(self) -> Any:
        """Get global LLM instance.

        Uses a module-level singleton to completely avoid Pydantic validation issues.
        All categories share the same LLM instance for efficiency.
        """
        return get_global_llm()

    @abstractmethod
    def get_retriever(self) -> Any:
        """Return category-specific retriever instance.

        Returns:
            Retriever object with .invoke({"query": str, ...}) method
        """
        raise NotImplementedError("Subclass must implement get_retriever()")

    class Config:
        arbitrary_types_allowed = True


__all__ = ["CategoryHooks"]
