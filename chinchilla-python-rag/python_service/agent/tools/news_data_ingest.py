#!/usr/bin/env python3
"""Utilities for chunking and embedding News data into ChromaDB."""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings
from tqdm import tqdm

try:
    from app.config import settings
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "Failed to import app.config.settings. Ensure PYTHONPATH is set."
    ) from exc


@dataclass
class NewsRecord:
    link: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class ChunkRecord:
    chunk_id: str
    link: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[Sequence[float]] = None


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        cleaned[key] = value
    return cleaned


def load_news(merged_json: Path, limit: int = 0) -> List[NewsRecord]:
    """JSON 파일에서 뉴스 데이터 로드"""
    if not merged_json.exists():
        raise FileNotFoundError(f"Merged JSON not found: {merged_json}")

    with open(merged_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if limit > 0:
        data = data[:limit]

    news_records: List[NewsRecord] = []
    for item in data:
        link = str(item.get("link", "")).strip()
        if not link:
            continue

        title = item.get("title", "").strip()
        full_content = item.get("full_content", "").strip()

        if not full_content:
            continue

        # 텍스트 구성
        lines: List[str] = []
        if title:
            lines.append(f"제목: {title}")

        category = item.get("category", "")
        if category:
            lines.append(f"카테고리: {category}")

        keyword = item.get("keyword", "")
        if keyword:
            lines.append(f"키워드: {keyword}")

        pub_date = item.get("pub_date", "")
        if pub_date:
            lines.append(f"발행일: {pub_date}")

        source = item.get("source", "")
        if source:
            lines.append(f"출처: {source}")

        lines.append("")
        lines.append("본문:")
        lines.append(full_content)

        document_text = "\n".join(lines).strip()

        metadata = _normalize_metadata(
            {
                "link": link,
                "title": title,
                "category": category,
                "keyword": keyword,
                "pub_date": pub_date,
                "source": source,
            }
        )

        news_records.append(
            NewsRecord(link=link, text=document_text, metadata=metadata)
        )

    return news_records


def dump_news_texts(path: Path, news: Iterable[NewsRecord]) -> None:
    """뉴스 텍스트를 JSONL 형식으로 저장"""
    with path.open("w", encoding="utf-8") as handle:
        for record in news:
            payload = {
                "link": record.link,
                "text": record.text,
                "metadata": record.metadata,
            }
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")


def chunk_news(
    news: Sequence[NewsRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> List[ChunkRecord]:
    """뉴스를 청크로 분할"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunk_records: List[ChunkRecord] = []
    for news_item in news:
        splits = splitter.split_text(news_item.text)
        if not splits:
            splits = [news_item.text]
        total_chunks = len(splits)
        for idx, chunk_text in enumerate(splits):
            chunk_id = f"{news_item.link}#{idx}"
            metadata = dict(news_item.metadata)
            metadata.update(
                {
                    "link": news_item.link,
                    "chunk_index": idx,
                    "chunk_count": total_chunks,
                }
            )
            chunk_records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    link=news_item.link,
                    text=chunk_text,
                    metadata=_normalize_metadata(metadata),
                )
            )
    return chunk_records


def embed_and_ingest(
    chunks: Sequence[ChunkRecord],
    collection_name: str,
    db_path: Path,
    batch_size: int,
    reset_collection: bool,
) -> List[ChunkRecord]:
    """임베딩 생성 및 ChromaDB 저장 (증분 업데이트)"""
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise RuntimeError(
            "UPSTAGE_API_KEY not configured. Set environment variable or .env entry."
        )

    client = chromadb.PersistentClient(
        path=str(db_path.absolute()),
        settings=Settings(anonymized_telemetry=False),
    )

    if reset_collection:
        try:
            client.delete_collection(collection_name)
            print(f"[INFO] Deleted existing collection: {collection_name}")
        except Exception:
            pass

    collection = client.get_or_create_collection(name=collection_name)

    embeddings_model = UpstageEmbeddings(
        api_key=api_key, model="solar-embedding-1-large"
    )

    updated_chunks: List[ChunkRecord] = []

    # 증분 업데이트: 기존 뉴스 링크 삭제 후 재추가
    unique_links = sorted({chunk.link for chunk in chunks})
    print(f"[INFO] Processing {len(unique_links)} unique news articles")

    for link in unique_links:
        try:
            collection.delete(where={"link": link})
        except Exception:
            continue

    # 배치 단위로 임베딩 및 저장
    for start in tqdm(
        range(0, len(chunks), batch_size), desc="Embedding", unit="batch"
    ):
        batch = list(chunks[start : start + batch_size])
        texts = [item.text for item in batch]
        vectors = embeddings_model.embed_documents(texts)

        collection.upsert(
            ids=[item.chunk_id for item in batch],
            embeddings=vectors,
            metadatas=[item.metadata for item in batch],
            documents=texts,
        )

        for item, vector in zip(batch, vectors):
            updated_chunks.append(
                ChunkRecord(
                    chunk_id=item.chunk_id,
                    link=item.link,
                    text=item.text,
                    metadata=item.metadata,
                    embedding=vector,
                )
            )

    return updated_chunks


def dump_chunks(path: Path, chunks: Sequence[ChunkRecord]) -> None:
    """청크를 JSON 파일로 저장"""
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "link": chunk.link,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding,
        }
        for chunk in chunks
    ]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chunk and embed News data into ChromaDB."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of news for debugging (0 = all)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Character length for each chunk",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=50,
        help="Overlap size between chunks",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="news",
        help="ChromaDB collection name",
    )
    parser.add_argument(
        "--db-dir",
        type=str,
        default=None,
        help="Override ChromaDB directory path",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing collection before ingesting",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    raw_dir = Path(settings.data_raw_dir)
    merged_json = raw_dir / "news" / "news_merged.json"
    processed_dir = _ensure_dir(Path("data/processed"))
    news_texts_path = processed_dir / "news_texts.jsonl"
    embedded_chunks_path = processed_dir / "news_embedded_chunks.json"
    db_dir = Path(args.db_dir) if args.db_dir else Path(settings.chroma_news_dir)
    _ensure_dir(db_dir)

    print(f"[INFO] Loading news from {merged_json} ...")
    news = load_news(merged_json, limit=args.limit)
    if not news:
        print("[WARN] No news loaded; aborting.")
        return 1
    print(f"[INFO] Loaded {len(news)} news articles")

    print(f"[INFO] Writing normalized news texts to {news_texts_path}")
    dump_news_texts(news_texts_path, news)

    print(
        f"[INFO] Chunking with chunk_size={args.chunk_size}, overlap={args.chunk_overlap}"
    )
    chunks = chunk_news(news, args.chunk_size, args.chunk_overlap)
    print(f"[INFO] Generated {len(chunks)} chunks")

    print(
        f"[INFO] Embedding and ingesting into ChromaDB at {db_dir} (collection={args.collection})"
    )
    embedded_chunks = embed_and_ingest(
        chunks,
        collection_name=args.collection,
        db_path=db_dir,
        batch_size=args.batch_size,
        reset_collection=args.reset,
    )

    print(f"[INFO] Saving embedded chunks to {embedded_chunks_path}")
    dump_chunks(embedded_chunks_path, embedded_chunks)

    print("[INFO] Completed News ingestion pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
