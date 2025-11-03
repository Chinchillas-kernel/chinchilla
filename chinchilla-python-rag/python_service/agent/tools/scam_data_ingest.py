#!/usr/bin/env python3
"""Build a ChromaDB vector store for scam-defense content."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings

try:
    from app.config import settings
except Exception as exc:  # pragma: no cover - configuration guard
    raise RuntimeError(
        "Failed to import app.config.settings. Check PYTHONPATH."
    ) from exc


DEFAULT_DATA_DIR = Path("data/scam_defense")
DEFAULT_DB_PATH = Path("data/chroma_scam_defense")
DEFAULT_COLLECTION = "scam_defense"
DEFAULT_BATCH_SIZE = 16


def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Clean metadata by removing empty values and normalizing types."""
    cleaned: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value in (None, "", []):
            continue
        if isinstance(value, (list, tuple, set)):
            joined = ", ".join(str(item).strip() for item in value if item)
            if joined:
                cleaned[key] = joined
            continue
        cleaned[key] = str(value).strip()
    return cleaned


def _load_json(path: Path) -> Any:
    if not path.exists():
        print(f"[WARN] JSON file not found: {path}")
        return None
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON file {path}: {e}")
        return None


def _collect_knowledge_base(path: Path) -> Iterable[Dict[str, Any]]:
    payload = _load_json(path)
    if not payload:
        return []

    if isinstance(payload, dict) and isinstance(
        payload.get("scam_knowledge_base"), list
    ):
        items = payload["scam_knowledge_base"]
    elif isinstance(payload, list):
        items = payload
    else:
        print(f"[WARN] Unexpected knowledge base format in {path}")
        return []

    records: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        doc_id = str(item.get("id") or f"kb_{index:04d}")
        title = (item.get("title") or "").strip()
        category = (item.get("category") or "").strip()
        danger_level = (item.get("danger_level") or "").strip() or "정보"
        scam_type = (item.get("type") or "").strip()
        content = (item.get("content") or "").strip()

        if not content:
            continue

        # Format content with metadata headers
        lines = [
            f"제목: {title or '제목 없음'}",
            f"카테고리: {category or '정보'}",
            f"위험도: {danger_level}",
            f"사기 유형: {scam_type or '미확인'}",
            "",
            content,
        ]

        records.append(
            {
                "id": doc_id,
                "content": "\n".join(lines),
                "metadata": _clean_metadata(
                    {
                        "doc_id": doc_id,
                        "source": "knowledge_base",
                        "title": title,
                        "category": category,
                        "danger_level": danger_level,
                        "scam_type": scam_type,
                    }
                ),
            }
        )
    print(f"[INFO] Collected {len(records)} knowledge base records from {path}")
    return records


def _collect_patterns(path: Path) -> Iterable[Dict[str, Any]]:
    """Collect scam pattern data."""
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return []

    records: List[Dict[str, Any]] = []

    for index, item in enumerate(payload.get("financial_scams", []) or []):
        if not isinstance(item, dict):
            continue
        doc_id = str(item.get("id") or f"pattern_{index:04d}")
        scam_type = (item.get("type") or "알 수 없음").strip()
        category = (item.get("category") or "기타").strip()
        danger_level = (item.get("danger_level") or "중간").strip()
        patterns = item.get("patterns") or []
        sender_patterns = item.get("sender_patterns") or []
        response_actions = item.get("response_actions") or []
        prevention_tips = item.get("prevention_tips") or []

        lines: List[str] = [
            f"사기 유형: {scam_type}",
            f"분류: {category}",
            f"위험도: {danger_level}",
            "",
            "의심 패턴:",
        ]
        lines.extend(f"- {pattern}" for pattern in patterns)
        lines.append("")
        lines.append("발신자 패턴:")
        lines.extend(f"- {pattern}" for pattern in sender_patterns)
        lines.append("")
        lines.append("대응 방법:")
        lines.extend(f"- {action}" for action in response_actions)
        lines.append("")
        lines.append("예방 팁:")
        lines.extend(f"- {tip}" for tip in prevention_tips)

        records.append(
            {
                "id": doc_id,
                "content": "\n".join(lines),
                "metadata": _clean_metadata(
                    {
                        "doc_id": doc_id,
                        "source": "scam_pattern",
                        "scam_type": scam_type,
                        "category": category,
                        "danger_level": danger_level,
                        "patterns": patterns,
                        "sender_patterns": sender_patterns,
                    }
                ),
            }
        )

    for risk_level, keywords in (payload.get("keywords") or {}).items():
        if not keywords:
            continue
        doc_id = f"keywords_{risk_level}"
        records.append(
            {
                "id": doc_id,
                "content": f"위험도: {risk_level}\n키워드: {', '.join(keywords)}",
                "metadata": _clean_metadata(
                    {
                        "doc_id": doc_id,
                        "source": "keywords",
                        "risk_level": risk_level,
                        "keywords": keywords,
                    }
                ),
            }
        )

    contact_index = 0
    for organization, phone in (payload.get("legitimate_contacts") or {}).items():
        if not organization and not phone:
            continue
        if organization:
            doc_id = f"contact_{organization}"
        else:
            doc_id = f"contact_{contact_index:idx:04d}"
            contact_index += 1

        records.append(
            {
                "id": doc_id,
                "content": f"기관명: {organization}\n연락처: {phone}",
                "metadata": _clean_metadata(
                    {
                        "doc_id": doc_id,
                        "source": "legitimate_contact",
                        "organization": organization,
                        "phone": phone,
                    }
                ),
            }
        )
    print(f"[INFO] Collected {len(records)} scam pattern records from {path}")
    return records


def _clear_chroma_persistence(db_path: Path) -> None:
    """Remove the Chroma persistence directory to recover from corruption."""
    if not db_path.exists():
        return
    try:
        shutil.rmtree(db_path)
        print(f"[INFO] Cleared Chroma persistence directory: {db_path}")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to clear Chroma persistence directory {db_path}: {exc}"
        ) from exc


def _collect_csv(path: Path) -> Iterable[Dict[str, Any]]:
    """Collect data from CSV files."""
    if not path.exists():
        return []

    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                lines: List[str] = []
                metadata: Dict[str, Any] = {
                    "source": "csv",
                    "csv_source": path.stem,
                    "filename": path.name,
                }
                for key, value in row.items():
                    if value and value.strip():
                        key_norm = key.strip()
                        value_norm = value.strip()
                        lines.append(f"{key_norm}: {value_norm}")
                        metadata[key_norm] = value_norm

                if not lines:
                    continue

                doc_id = f"{path.stem}_{index:04d}"
                records.append(
                    {
                        "id": doc_id,
                        "content": "\n".join(lines),
                        "metadata": _clean_metadata(
                            {
                                "doc_id": doc_id,
                                **metadata,
                            }
                        ),
                    }
                )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[WARN] Failed to parse CSV {path}: {exc}")

    return records


def collect_scam_data(
    data_dir: Path,
    *,
    include_csv: bool = True,
) -> List[Dict[str, Any]]:
    """Collect all scam defense data from the specified directory.

    Args:
        data_dir: Directory containing scam defense data files
        include_csv: Whether to include CSV files in collection

    Returns:
        List of records with id, content, and metadata."""

    print(f"\n Collecting scam-defense data from: {data_dir}")
    records: List[Dict[str, Any]] = []

    # Collect from JSON files
    kb_path = data_dir / "scam_knowledge_base.json"
    records.extend(_collect_knowledge_base(kb_path))

    patterns_path = data_dir / "scam_patterns.json"
    records.extend(_collect_patterns(patterns_path))

    if include_csv:

        csv_files = sorted(data_dir.glob("*.csv"))
        if csv_files:
            print(f"[INFO] Found {len(csv_files)} CSV file(s)")
            for csv_path in csv_files:
                records.extend(_collect_csv(csv_path))
        else:
            print("[INFO] No CSV files found")

    print(f"\n✓ Total collected: {len(records)} records")
    return records


def build_scam_vectorstore(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    db_path: Path = DEFAULT_DB_PATH,
    collection_name: str = DEFAULT_COLLECTION,
    include_csv: bool = True,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int = 0,
    reset: bool = False,
) -> None:
    data_dir = data_dir.resolve()
    db_path = db_path.resolve()
    if not data_dir.exists():
        raise FileNotFoundError(f"Scam-defense data directory not found: {data_dir}")

    print("\n" + "=" * 70)
    print("📚 Scam Defense Vectorstore Builder")
    print(f"- data_dir   : {data_dir}")
    print(f"- db_path    : {db_path}")
    print(f"- collection : {collection_name}")
    print(f"- chunk size : {chunk_size}")
    print(f"- overlap    : {chunk_overlap}")
    if limit:
        print(f"- limit      : {limit}")
    if not include_csv:
        print("- CSV files  : skipped")
    print(f"- batch size : {batch_size}")
    if reset:
        print("- reset mode : enabled")
    print("=" * 70)

    raw_records = collect_scam_data(data_dir, include_csv=include_csv)
    if limit:
        raw_records = raw_records[:limit]
        print(f"[INFO] Limiting to {limit} records")
    if not raw_records:
        print("[WARN] No scam-defense data found. Aborting.")
        return
    print(f"[INFO] Loaded {len(raw_records)} raw records")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks: List[Dict[str, Any]] = []
    for record in raw_records:
        pieces = splitter.split_text(record["content"]) or [record["content"]]
        for index, text in enumerate(pieces):
            chunk_id = f"{record['id']}#chunk{index}"
            metadata = dict(record["metadata"])
            metadata.update({"doc_id": record["id"], "chunk_index": index})
            chunks.append({"id": chunk_id, "content": text, "metadata": metadata})

    if not chunks:
        print("[WARN] No chunks generated. Aborting.")
        return
    print(f"[INFO] Generated {len(chunks)} chunks from {len(raw_records)} records")

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero.")

    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY is not configured.")

    embeddings = UpstageEmbeddings(api_key=api_key, model="solar-embedding-1-large")

    chroma_settings = Settings(anonymized_telemetry=False)
    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=chroma_settings,
    )

    if reset:
        try:
            client.delete_collection(collection_name)
            print(f"[INFO] Deleted existing collection: {collection_name}")
        except Exception as exc:
            print(
                f"[WARN] Unable to delete collection via Chroma API ({exc}). "
                "Clearing persistence directory instead."
            )
            _clear_chroma_persistence(db_path)
            client = chromadb.PersistentClient(
                path=str(db_path),
                settings=chroma_settings,
            )

    try:
        collection = client.get_or_create_collection(collection_name)
    except Exception as exc:
        if "_type" not in str(exc):
            raise
        print(
            "[WARN] Detected incompatible Chroma collection metadata. "
            "Resetting persistence directory and recreating collection."
        )
        _clear_chroma_persistence(db_path)
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=chroma_settings,
        )
        collection = client.get_or_create_collection(collection_name)
    print(f"[INFO] Using collection: {collection_name}")

    existing_ids = [chunk["id"] for chunk in chunks]
    try:
        collection.delete(ids=existing_ids)
    except Exception:
        pass

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        print(f"[INFO] Indexing batch {batch_num}/{total_batches}...", end="\r")

        for chunk in batch:
            try:
                embedding = embeddings.embed_query(chunk["content"])
                collection.add(
                    ids=[chunk["id"]],
                    embeddings=[embedding],
                    documents=[chunk["content"]],
                    metadatas=[chunk["metadata"]],
                )
            except Exception as exc:
                print(f"[ERROR] Failed to index chunk {chunk['id']}: {exc}")

    print(f"\n✓ Successfully indexed {len(chunks)} scam-defense chunks")
    print("\n" + "=" * 70)
    print("✅ Vector store build complete!")
    print("=" * 70)


# ============================================================================
# CLI Interface
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build scam-defense Chroma vector store."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory with scam-defense data files",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Chroma persistence directory",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=DEFAULT_COLLECTION,
        help="Chroma collection name",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=500, help="Chunk size for text splitting"
    )
    parser.add_argument(
        "--chunk-overlap", type=int, default=50, help="Chunk overlap for text splitting"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of chunks to index per Chroma batch",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of source records (0 for all)",
    )
    parser.add_argument(
        "--skip-csv", action="store_true", help="Skip ingesting supplementary CSV files"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before ingesting",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        build_scam_vectorstore(
            data_dir=args.data_dir,
            db_path=args.db_path,
            collection_name=args.collection,
            include_csv=not args.skip_csv,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            batch_size=args.batch_size,
            limit=args.limit,
            reset=args.reset,
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
