"""Retriever pipeline for welfare programs vector store."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_upstage import UpstageEmbeddings

from app.config import settings


@dataclass
class WelfareRetrievalInput:
    """Structured input payload for welfare retrieval."""

    query: str


class WelfareRetrieverPipeline:
    """Thin wrapper around a Chroma retriever for welfare programs."""

    def __init__(
        self,
        *,
        top_k: int = 5,
        search_type: str = "mmr",
        search_kwargs: Optional[Dict[str, Any]] = None,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.top_k = max(1, top_k)
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {}
        self._persist_directory = persist_directory
        self.collection_name = collection_name

    @cached_property
    def _embeddings(self) -> UpstageEmbeddings:
        return UpstageEmbeddings(
            api_key=settings.upstage_api_key,
            model="embedding-query",
        )

    @cached_property
    def _persist_path(self) -> Path:
        if self._persist_directory:
            path = Path(self._persist_directory)
        else:
            default = Path(settings.welfare_chroma_dir)
            if not default.is_absolute():
                default = Path(__file__).resolve().parents[2] / default
            path = default
        return path

    @cached_property
    def _retriever(self):
        store = Chroma(
            persist_directory=str(self._persist_path),
            embedding_function=self._embeddings,
            collection_name=self.collection_name or "welfare_programs",
        )
        kwargs = {"k": self.top_k}
        kwargs.update(self.search_kwargs)
        return store.as_retriever(
            search_type=self.search_type,
            search_kwargs=kwargs,
        )

    def invoke(
        self,
        payload: Union[WelfareRetrievalInput, Dict[str, Any], str],
    ) -> Sequence[Document]:
        if isinstance(payload, WelfareRetrievalInput):
            query = payload.query
        elif isinstance(payload, str):
            query = payload
        else:
            query = str(payload.get("query", ""))

        query = query.strip()
        if not query:
            raise ValueError("query is required for welfare retrieval")

        return self._retriever.invoke(query)


def get_welfare_retriever(**kwargs: Any) -> WelfareRetrieverPipeline:
    """Factory for welfare retriever pipeline."""

    return WelfareRetrieverPipeline(**kwargs)


__all__ = [
    "WelfareRetrieverPipeline",
    "WelfareRetrievalInput",
    "get_welfare_retriever",
]
