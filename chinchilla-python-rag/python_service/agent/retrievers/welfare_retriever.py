"""Retriever pipeline for welfare programs vector store."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

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
            model="solar-embedding-1-large",
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
    def _store(self) -> Chroma:
        return Chroma(
            persist_directory=str(self._persist_path),
            embedding_function=self._embeddings,
            collection_name=self.collection_name or "elderly_welfare_services",
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

        search_params = dict(self.search_kwargs)
        k = int(search_params.pop("k", self.top_k) or self.top_k)

        allowed = {"where", "where_document"}
        extra_params = {k_: v for k_, v in search_params.items() if k_ in allowed}

        collection = self._store._collection

        try:
            raw = collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances", "ids"],
                **extra_params,
            )
        except Exception:
            fallback = self._store.similarity_search_with_relevance_scores(query, k=k)
            results: List[Document] = []
            for doc, score in fallback:
                metadata = dict(doc.metadata or {})
                metadata.setdefault("doc_id", metadata.get("id") or metadata.get("uuid"))
                metadata["relevance_score"] = float(score)
                results.append(Document(page_content=doc.page_content, metadata=metadata))
            return results

        ids = raw.get("ids", [[]])[0] or []
        documents = raw.get("documents", [[]])[0] or []
        metadatas = raw.get("metadatas", [[]])[0] or []
        distances = raw.get("distances", [[]])[0] or []

        results: List[Document] = []
        for doc_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            metadata = dict(metadata or {})
            metadata.setdefault("chunk_id", doc_id)
            metadata.setdefault("record_id", metadata.get("doc_id"))
            metadata.setdefault("source_kind", metadata.get("source"))
            distance = float(distance)
            metadata["relevance_score"] = max(0.0, 1.0 - (distance / 2.0))
            results.append(Document(page_content=text, metadata=metadata))

        return results


def get_welfare_retriever(**kwargs: Any) -> WelfareRetrieverPipeline:
    """Factory for welfare retriever pipeline."""

    return WelfareRetrieverPipeline(**kwargs)


__all__ = [
    "WelfareRetrieverPipeline",
    "WelfareRetrievalInput",
    "get_welfare_retriever",
]
