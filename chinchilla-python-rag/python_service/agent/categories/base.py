"""Base class for category-specific hooks."""
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel


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
