#!/usr/bin/env python3
"""Build an elderly comprehensive welfare service vector index."""

from __future__ import annotations

import argparse
import json
import os
import re
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

from app.config import settings

ENCODING_CANDIDATES = ("utf-8", "utf-8-sig", "cp949", "euc-kr")
SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".pdf"}

SERVICE_KEYWORDS: Dict[str, Sequence[str]] = {
    "건강의료": ("건강", "의료", "진료", "검진", "병원", "보건", "재활"),
    "돌봄지원": ("돌봄", "요양", "방문", "재가", "보호", "시설", "케어"),
    "경제생활": ("급여", "지원금", "수당", "연금", "일자리", "소득", "후원"),
    "주거환경": ("주거", "주택", "거주", "환경개선", "임대"),
    "문화여가": ("문화", "여가", "체험", "강좌", "교실", "프로그램"),
    "상담권익": ("상담", "권익", "학대", "보호", "법률", "정보제공"),
}

TARGET_KEYWORDS: Dict[str, Sequence[str]] = {
    "노인": ("노인", "어르신", "고령", "65세"),
    "치매": ("치매", "인지", "기억"),
    "저소득": ("저소득", "기초", "수급", "긴급"),
    "장애": ("장애", "중증", "장애인"),
    "돌봄가족": ("보호자", "가족", "돌봄가족"),
}

CHANNEL_KEYWORDS: Dict[str, Sequence[str]] = {
    "전화": ("전화", "콜센터", "상담전화"),
    "온라인": ("온라인", "인터넷", "웹", "모바일", "앱"),
    "방문": ("방문", "현장", "센터", "기관"),
}


@dataclass
class WelfareRecord:
    """Single welfare document entry before chunking."""

    record_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class WelfareChunk:
    """Chunked welfare record ready for vectorization."""

    chunk_id: str
    record_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[Sequence[float]] = None


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value in (None, ""):
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = json.dumps(value, ensure_ascii=False)
    return sanitized


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_stringify(item) for item in value if _stringify(item))
    return str(value).strip()


def _slugify_key(key: str) -> str:
    token = re.sub(r"[^0-9A-Za-z가-힣]+", "_", key.strip().lower())
    return token.strip("_") or "field"


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def _extract_year(text: str) -> str:
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else ""


def _detect_labels(text: str, mapping: Dict[str, Sequence[str]]) -> List[str]:
    lowered = text.lower()
    hits = []
    for label, keywords in mapping.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            hits.append(label)
    return sorted(set(hits))


def _collect_keyword_hits(text: str) -> List[str]:
    lowered = text.lower()
    hits = set()
    for collection in (SERVICE_KEYWORDS, TARGET_KEYWORDS, CHANNEL_KEYWORDS):
        for keywords in collection.values():
            for keyword in keywords:
                if keyword.lower() in lowered:
                    hits.add(keyword)
    return sorted(hits)


def _build_record(
    *,
    record_id: str,
    text: str,
    source_path: str,
    source_kind: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[WelfareRecord]:
    text = _normalize_whitespace(text)
    if not text:
        return None

    categories = _detect_labels(text, SERVICE_KEYWORDS)
    targets = _detect_labels(text, TARGET_KEYWORDS)
    channels = _detect_labels(text, CHANNEL_KEYWORDS)

    metadata: Dict[str, Any] = {
        "record_id": record_id,
        "source_path": source_path,
        "source_kind": source_kind,
        "primary_category": categories[0] if categories else "기타",
        "service_categories": categories,
        "target_groups": targets,
        "delivery_channels": channels,
        "keyword_hits": _collect_keyword_hits(text),
        "service_year": _extract_year(source_path),
        "language": "ko",
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    metadata = _sanitize_metadata(metadata)
    return WelfareRecord(record_id=record_id, text=text, metadata=metadata)


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    for encoding in ENCODING_CANDIDATES:
        try:
            df = pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError(path.name, b"", 0, 0, "Unknown encoding")

    return df.to_dict(orient="records")


def _read_json(path: Path) -> List[Dict[str, Any]]:
    for encoding in ENCODING_CANDIDATES:
        try:
            payload = json.loads(path.read_text(encoding=encoding))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError(path.name, b"", 0, 0, "Unknown encoding")

    if isinstance(payload, list):
        return [item if isinstance(item, dict) else {"value": item} for item in payload]
    if isinstance(payload, dict):
        return [payload]
    return [{"value": payload}]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for encoding in ENCODING_CANDIDATES:
        try:
            lines = path.read_text(encoding=encoding).splitlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError(path.name, b"", 0, 0, "Unknown encoding")

    for line in lines:
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


def _structured_records_to_welfare(
    *,
    base_id: str,
    rows: Iterable[Dict[str, Any]],
    source_path: str,
    source_kind: str,
    limit: int = 0,
) -> List[WelfareRecord]:
    records: List[WelfareRecord] = []
    for index, row in enumerate(rows):
        fields = []
        extra_meta: Dict[str, Any] = {"source_file_index": index}
        for key, value in row.items():
            text_value = _stringify(value)
            if not text_value:
                continue
            fields.append(f"{key}: {text_value}")
            extra_meta[_slugify_key(key)] = text_value

        if not fields:
            continue

        record_id = f"{base_id}-{index:04d}"
        text = "\n".join(fields)
        record = _build_record(
            record_id=record_id,
            text=text,
            source_path=source_path,
            source_kind=source_kind,
            extra_metadata=extra_meta,
        )
        if record:
            records.append(record)
        if limit and len(records) >= limit:
            break

    return records


def _load_pdf_pages(path: Path) -> Sequence[Document]:
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if api_key:
        try:
            loader = UpstageDocumentParseLoader(str(path), api_key=api_key)
            return loader.load()
        except Exception as error:  # pragma: no cover - network based fallback
            print(
                f"[WARN] Upstage PDF parsing failed ({error}). Falling back to local parser."
            )

    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "PyPDFLoader is required for PDF parsing fallback. Install langchain-community."
        ) from exc

    loader = PyPDFLoader(str(path))
    try:
        return loader.load()
    except Exception as error:
        print(f"[WARN] PyPDFLoader failed ({error}). Trying PDFMinerLoader.")

    try:
        from langchain_community.document_loaders import PDFMinerLoader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "PDF parsing failed. Install pdfminer.six or provide UPSTAGE_API_KEY."
        ) from exc

    loader = PDFMinerLoader(str(path))
    return loader.load()


def _pdf_to_welfare_records(
    path: Path, raw_dir: Path, limit: int = 0
) -> List[WelfareRecord]:
    relative = str(path.relative_to(raw_dir))
    documents = _load_pdf_pages(path)
    if not documents:
        return []

    full_text = "\n\n".join(doc.page_content or "" for doc in documents)
    extra = {
        "record_title": path.stem,
        "total_pages": len(documents),
    }
    record = _build_record(
        record_id=f"{path.stem}-pdf",
        text=full_text,
        source_path=relative,
        source_kind="pdf",
        extra_metadata=extra,
    )
    return [record] if record else []


def load_welfare_documents(raw_dir: Path, limit: int = 0) -> List[WelfareRecord]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")

    loaded: List[WelfareRecord] = []
    files = sorted(path for path in raw_dir.glob("**/*") if path.is_file())

    for path in files:
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        relative = str(path.relative_to(raw_dir))
        base_id = path.stem

        if path.suffix.lower() == ".csv":
            rows = _read_csv(path)
            records = _structured_records_to_welfare(
                base_id=base_id,
                rows=rows,
                source_path=relative,
                source_kind="csv",
                limit=limit - len(loaded) if limit else 0,
            )
        elif path.suffix.lower() == ".json":
            rows = _read_json(path)
            records = _structured_records_to_welfare(
                base_id=base_id,
                rows=rows,
                source_path=relative,
                source_kind="json",
                limit=limit - len(loaded) if limit else 0,
            )
        elif path.suffix.lower() == ".jsonl":
            rows = _read_jsonl(path)
            records = _structured_records_to_welfare(
                base_id=base_id,
                rows=rows,
                source_path=relative,
                source_kind="jsonl",
                limit=limit - len(loaded) if limit else 0,
            )
        else:  # PDF
            records = _pdf_to_welfare_records(path, raw_dir, limit=limit)

        loaded.extend(records)

        if limit and len(loaded) >= limit:
            return loaded[:limit]

    return loaded


def dump_records(path: Path, records: Iterable[WelfareRecord]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "record_id": record.record_id,
                "text": record.text,
                "metadata": record.metadata,
            }
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")


def chunk_welfare_documents(
    records: Sequence[WelfareRecord],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> List[WelfareChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n제", "\n\n□", "\n\n◦", "\n\n", "\n", " ", ""],
    )

    chunks: List[WelfareChunk] = []
    for record in tqdm(records, desc="Chunking", unit="record"):
        parts = splitter.split_text(record.text) or [record.text]
        total = len(parts)
        for index, part in enumerate(parts):
            chunk_id = f"{record.record_id}#chunk_{index:04d}"
            metadata = dict(record.metadata)
            metadata.update(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": index,
                    "chunk_count": total,
                    "chunk_size": len(part),
                }
            )
            chunks.append(
                WelfareChunk(
                    chunk_id=chunk_id,
                    record_id=record.record_id,
                    text=part,
                    metadata=_sanitize_metadata(metadata),
                )
            )
    return chunks


def embed_and_ingest(
    chunks: Sequence[WelfareChunk],
    *,
    collection_name: str,
    db_path: Path,
    batch_size: int,
    reset_collection: bool,
) -> List[WelfareChunk]:
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
        api_key=api_key,
        model="solar-embedding-1-large",
    )

    unique_records = sorted({chunk.record_id for chunk in chunks})
    for record_id in unique_records:
        try:
            collection.delete(where={"record_id": record_id})
        except Exception:
            continue

    embedded_chunks: List[WelfareChunk] = []
    for start in tqdm(range(0, len(chunks), batch_size), desc="Embedding", unit="batch"):
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
            embedded_chunks.append(
                WelfareChunk(
                    chunk_id=item.chunk_id,
                    record_id=item.record_id,
                    text=item.text,
                    metadata=item.metadata,
                    embedding=vector,
                )
            )

    return embedded_chunks


def dump_chunks(path: Path, chunks: Sequence[WelfareChunk]) -> None:
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "record_id": chunk.record_id,
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
        description="Chunk and embed elderly comprehensive welfare documents into ChromaDB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of raw records for debugging (0 = all)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=900,
        help="Text chunk size",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=180,
        help="Overlap size between chunks",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=24,
        help="Embedding batch size",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="elderly_welfare_services",
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
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=str(settings.welfare_data_dir),
        help="Raw welfare data directory",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    raw_dir = Path(args.raw_dir).resolve()
    processed_dir = _ensure_dir(Path("data/processed"))
    normalized_text_path = processed_dir / "welfare_texts.jsonl"
    embedded_chunks_path = processed_dir / "welfare_embedded_chunks.json"

    if args.db_dir:
        db_dir = Path(args.db_dir)
    else:
        db_dir = Path(settings.welfare_chroma_dir)
        if not db_dir.is_absolute():
            db_dir = Path(__file__).resolve().parents[2] / db_dir
    _ensure_dir(db_dir)

    print("=" * 70)
    print("📚 노인 종합 복지 서비스 ChromaDB 로딩 파이프라인")
    print("=" * 70)
    print(f"원본 데이터 디렉터리 : {raw_dir}")
    print(f"Chroma 저장 경로     : {db_dir}")
    print(f"컬렉션 이름          : {args.collection}")
    print(f"청크 크기 / 겹침     : {args.chunk_size} / {args.chunk_overlap}")
    print("=" * 70 + "\n")

    print("[STEP 1] Loading welfare documents...")
    records = load_welfare_documents(raw_dir, limit=args.limit)
    if not records:
        print("[ERROR] No welfare documents loaded; aborting.")
        return 1
    print(f"[SUCCESS] Loaded {len(records)} records\n")

    print(f"[STEP 2] Writing normalized texts to {normalized_text_path}")
    dump_records(normalized_text_path, records)
    print("[SUCCESS] Texts saved\n")

    print("[STEP 3] Chunking records...")
    chunks = chunk_welfare_documents(
        records,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"[SUCCESS] Generated {len(chunks)} chunks\n")

    print("[STEP 4] Embedding and ingesting into ChromaDB...")
    embedded_chunks = embed_and_ingest(
        chunks,
        collection_name=args.collection,
        db_path=db_dir,
        batch_size=args.batch_size,
        reset_collection=args.reset,
    )
    print(f"[SUCCESS] Embedded and stored {len(embedded_chunks)} chunks\n")

    print(f"[STEP 5] Saving embedded chunks to {embedded_chunks_path}")
    dump_chunks(embedded_chunks_path, embedded_chunks)
    print("[SUCCESS] Embedded chunks saved\n")

    print("=" * 70)
    print("🎉 노인 종합 복지 서비스 로딩 완료!")
    print("=" * 70)
    print(f"총 문서 수: {len(records)}")
    print(f"총 청크 수: {len(chunks)}")
    print(f"ChromaDB 경로: {db_dir}")
    print(f"컬렉션명: {args.collection}")
    print("=" * 70)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
