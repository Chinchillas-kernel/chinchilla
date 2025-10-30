#!/usr/bin/env python3
"""Ingest cultural & lifestyle welfare data into a Chroma vector store."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import chromadb
import pandas as pd
from chromadb.config import Settings
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageDocumentParseLoader, UpstageEmbeddings
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings


ENCODING_CANDIDATES = ("utf-8", "utf-8-sig", "cp949", "euc-kr")
SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".pdf"}
JOB_PREFIXES = ("senuri_", "senuri-", "jobs_")


@dataclass
class RawDocument:
    doc_id: str
    text: str
    metadata: Dict[str, Any]


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = json.dumps(value, ensure_ascii=False)
    return sanitized


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    for encoding in ENCODING_CANDIDATES:
        try:
            df = pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError(path.name, b"", 0, 0, "Unknown encoding")

    records = df.to_dict(orient="records")
    return [{k: (v or "") for k, v in row.items()} for row in records]


def _read_text(path: Path) -> str:
    for encoding in ENCODING_CANDIDATES:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(path.name, b"", 0, 0, "Unknown encoding")


def _read_json(path: Path) -> List[Dict[str, Any]]:
    text = _read_text(path)
    data = json.loads(text)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item if isinstance(item, dict) else {"value": item} for item in data]
    return [{"value": data}]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    text = _read_text(path)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"value": line}
        if not isinstance(payload, dict):
            payload = {"value": payload}
        records.append(payload)
    return records


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text


def _records_to_documents(records: Iterable[Dict[str, Any]], *, base_id: str, source: str) -> List[RawDocument]:
    docs: List[RawDocument] = []
    for index, record in enumerate(records):
        fields = [f"{key}: {_stringify(value)}" for key, value in record.items() if _stringify(value)]
        if not fields:
            continue
        doc_id = f"{base_id}-{index}"
        text = "\n".join(fields)
        metadata = _sanitize_metadata({"doc_id": doc_id, "source_path": source, "record_index": index})
        docs.append(RawDocument(doc_id=doc_id, text=text, metadata=metadata))
    return docs


def _load_pdf(path: Path, raw_dir: Path) -> List[RawDocument]:
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY not configured for PDF parsing.")

    loader = UpstageDocumentParseLoader(str(path), api_key=api_key)
    documents = loader.load()
    docs: List[RawDocument] = []
    for index, item in enumerate(documents):
        text = item.page_content.strip()
        if not text:
            continue
        doc_id = f"{path.stem}-{index}"
        metadata = _sanitize_metadata({
            "doc_id": doc_id,
            "source_path": str(path.relative_to(raw_dir)),
            **{k: v for k, v in item.metadata.items() if v},
        })
        docs.append(RawDocument(doc_id=doc_id, text=text, metadata=metadata))
    return docs


def load_raw_documents(raw_dir: Path) -> List[RawDocument]:
    documents: List[RawDocument] = []
    for path in sorted(raw_dir.glob("**/*")):
        if not path.is_file():
            continue
        if not path.suffix.lower() in SUPPORTED_SUFFIXES:
            continue
        if any(path.name.startswith(prefix) for prefix in JOB_PREFIXES):
            continue

        rel_path = str(path.relative_to(raw_dir))
        base_id = path.stem
        if path.suffix.lower() == ".csv":
            records = _read_csv(path)
            documents.extend(_records_to_documents(records, base_id=base_id, source=rel_path))
        elif path.suffix.lower() == ".json":
            records = _read_json(path)
            documents.extend(_records_to_documents(records, base_id=base_id, source=rel_path))
        elif path.suffix.lower() == ".jsonl":
            records = _read_jsonl(path)
            documents.extend(_records_to_documents(records, base_id=base_id, source=rel_path))
        elif path.suffix.lower() == ".pdf":
            documents.extend(_load_pdf(path, raw_dir))

    return documents


def chunk_documents(
    documents: Sequence[RawDocument],
    *,
    chunk_size: int,
    chunk_overlap: int,
    progress: bool = False,
) -> List[RawDocument]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks: List[RawDocument] = []
    iterable: Iterable[RawDocument] = documents
    if progress:
        iterable = tqdm(documents, desc="Chunking", unit="doc")

    for doc in iterable:
        splits = splitter.split_text(doc.text) or [doc.text]
        total = len(splits)
        for index, text in enumerate(splits):
            chunk_id = f"{doc.doc_id}#chunk{index}"
            metadata = dict(doc.metadata)
            metadata.update({"chunk_index": index, "chunk_total": total})
            metadata = _sanitize_metadata(metadata)
            chunks.append(RawDocument(doc_id=chunk_id, text=text, metadata=metadata))
    return chunks


def embed_chunks(
    chunks: Sequence[RawDocument],
    *,
    collection_name: str,
    db_dir: Path,
    batch_size: int,
    reset: bool,
    progress: bool = False,
) -> None:
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY not configured.")

    client = chromadb.PersistentClient(
        path=str(db_dir.absolute()),
        settings=Settings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(name=collection_name)
    embeddings = UpstageEmbeddings(api_key=api_key, model="embedding-query")

    doc_ids = sorted({chunk.metadata.get("doc_id") for chunk in chunks if chunk.metadata.get("doc_id")})
    for doc_id in doc_ids:
        try:
            collection.delete(where={"doc_id": doc_id})
        except Exception:
            continue

    batch_indices: Iterable[int] = range(0, len(chunks), batch_size)
    if progress:
        batch_indices = tqdm(batch_indices, desc="Embedding", unit="batch")

    for start in batch_indices:
        batch = chunks[start : start + batch_size]
        texts = [item.text for item in batch]
        vectors = embeddings.embed_documents(texts)
        collection.upsert(
            ids=[item.doc_id for item in batch],
            embeddings=vectors,
            metadatas=[item.metadata for item in batch],
            documents=texts,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build welfare Chroma index from raw datasets.")
    default_raw_dir = Path(settings.welfare_data_dir)
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=str(default_raw_dir),
        help="Input data directory",
    )
    parser.add_argument("--db-dir", type=str, default=str(settings.welfare_chroma_dir), help="Chroma persistence directory")
    parser.add_argument("--collection", type=str, default="welfare_programs", help="Chroma collection name")
    parser.add_argument("--chunk-size", type=int, default=600, help="Chunk size for text splitting")
    parser.add_argument("--chunk-overlap", type=int, default=120, help="Chunk overlap for text splitting")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    parser.add_argument("--reset", action="store_true", help="Drop existing collection before ingesting")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    raw_dir = Path(args.raw_dir).resolve()
    if not raw_dir.exists():
        raise SystemExit(f"Raw data directory not found: {raw_dir}")

    separator = "=" * 70
    print(separator)
    print("📚 복지 문서 ChromaDB 로딩 파이프라인")
    print(separator)
    print(f"원본 데이터 디렉터리 : {raw_dir}")
    print(f"Chroma 저장 경로     : {args.db_dir}")
    print(f"컬렉션 이름          : {args.collection}")
    print(f"청크 크기 / 겹침     : {args.chunk_size} / {args.chunk_overlap}")
    print(separator)

    print("\n[STEP 1] Loading documents...")
    print(f"[INFO] Loading welfare records from {raw_dir}")
    documents = load_raw_documents(raw_dir)
    if not documents:
        print("[WARN] No welfare records found. Aborting.")
        return 1
    print(f"[SUCCESS] Loaded {len(documents)} documents")

    print(
        f"\n[STEP 2] Chunking documents (chunk_size={args.chunk_size}, overlap={args.chunk_overlap})"
    )
    chunks = chunk_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        progress=True,
    )
    print(f"[SUCCESS] Generated {len(chunks)} chunks")

    db_dir = Path(args.db_dir).resolve()
    db_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"\n[STEP 3] Embedding into Chroma directory={db_dir}, collection={args.collection}"
    )
    embed_chunks(
        chunks,
        collection_name=args.collection,
        db_dir=db_dir,
        batch_size=args.batch_size,
        reset=args.reset,
        progress=True,
    )

    print("[SUCCESS] Welfare Chroma index updated successfully")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
