#!/usr/bin/env python3
"""
금융 사기 데이터 수집 및 ChromaDB 연동 유틸리티

data/scam_defense의 사기 패턴, 지식베이스, CSV 데이터를 
청크로 분할하고 임베딩하여 ChromaDB에 저장
"""
from __future__ import annotations

import argparse
import csv
import json
import os
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
except Exception as exc:
    raise RuntimeError(
        "Failed to import app.config.settings. Ensure PYTHONPATH is set."
    ) from exc


@dataclass
class ScamRecord:
    """사기 데이터 레코드"""
    record_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class ChunkRecord:
    """청크 레코드"""
    chunk_id: str
    record_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[Sequence[float]] = None


def _ensure_dir(path: Path) -> Path:
    """디렉토리 생성"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """메타데이터 정규화"""
    cleaned: Dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        cleaned[key] = value
    return cleaned


def load_knowledge_base(json_path: Path) -> List[ScamRecord]:
    """지식 베이스 JSON 로드"""
    if not json_path.exists():
        print(f"[WARN] Knowledge base not found: {json_path}")
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records: List[ScamRecord] = []
    
    # knowledge_base는 배열 형태
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "knowledge_base" in data:
        items = data["knowledge_base"]
    else:
        print(f"[WARN] Unexpected JSON structure in {json_path}")
        return []

    for idx, item in enumerate(items):
        scam_type = item.get("scam_type", "").strip()
        description = item.get("description", "").strip()
        examples = item.get("examples", [])
        prevention = item.get("prevention", [])

        if not description:
            continue

        # 텍스트 구성
        lines: List[str] = [f"사기 유형: {scam_type}"]
        lines.append("")
        lines.append("설명:")
        lines.append(description)

        if examples:
            lines.append("")
            lines.append("사례:")
            for ex in examples:
                lines.append(f"- {ex}")

        if prevention:
            lines.append("")
            lines.append("예방 방법:")
            for prev in prevention:
                lines.append(f"- {prev}")

        document_text = "\n".join(lines).strip()

        metadata = _normalize_metadata({
            "source": "knowledge_base",
            "scam_type": scam_type,
            "data_type": "knowledge",
        })

        record_id = f"kb_{idx}_{scam_type}"
        records.append(ScamRecord(
            record_id=record_id,
            text=document_text,
            metadata=metadata
        ))

    return records


def load_scam_patterns(json_path: Path) -> List[ScamRecord]:
    """사기 패턴 JSON 로드"""
    if not json_path.exists():
        print(f"[WARN] Scam patterns not found: {json_path}")
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records: List[ScamRecord] = []

    # scam_patterns는 배열 형태
    if isinstance(data, list):
        patterns = data
    elif isinstance(data, dict) and "scam_patterns" in data:
        patterns = data["scam_patterns"]
    else:
        print(f"[WARN] Unexpected JSON structure in {json_path}")
        return []

    for idx, pattern in enumerate(patterns):
        pattern_name = pattern.get("pattern_name", "").strip()
        scam_type = pattern.get("scam_type", "").strip()
        keywords = pattern.get("keywords", [])
        description = pattern.get("description", "").strip()

        if not pattern_name and not description:
            continue

        # 텍스트 구성
        lines: List[str] = [f"패턴명: {pattern_name}"]
        lines.append(f"사기 유형: {scam_type}")

        if keywords:
            lines.append(f"키워드: {', '.join(keywords)}")

        if description:
            lines.append("")
            lines.append("설명:")
            lines.append(description)

        document_text = "\n".join(lines).strip()

        metadata = _normalize_metadata({
            "source": "pattern",
            "pattern_name": pattern_name,
            "scam_type": scam_type,
            "data_type": "pattern",
            "keywords": keywords,
        })

        record_id = f"pattern_{idx}_{scam_type}"
        records.append(ScamRecord(
            record_id=record_id,
            text=document_text,
            metadata=metadata
        ))

    return records


def load_csv_data(csv_path: Path, source_name: str) -> List[ScamRecord]:
    """CSV 데이터 로드 (경찰청, 과기부 등)"""
    if not csv_path.exists():
        print(f"[WARN] CSV not found: {csv_path}")
        return []

    records: List[ScamRecord] = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                # CSV 컬럼에 따라 텍스트 구성
                lines: List[str] = []
                metadata: Dict[str, Any] = {
                    "source": source_name,
                    "data_type": "csv",
                }

                # 모든 컬럼을 텍스트로 변환
                for key, value in row.items():
                    if value and value.strip():
                        clean_key = key.strip()
                        clean_value = value.strip()
                        lines.append(f"{clean_key}: {clean_value}")
                        # 메타데이터에도 추가
                        metadata[clean_key] = clean_value

                if not lines:
                    continue

                document_text = "\n".join(lines).strip()
                record_id = f"{source_name}_{idx}"

                records.append(ScamRecord(
                    record_id=record_id,
                    text=document_text,
                    metadata=_normalize_metadata(metadata)
                ))

    except Exception as e:
        print(f"[ERROR] Failed to load CSV {csv_path}: {e}")
        return []

    return records


def load_all_scam_data(scam_dir: Path, limit: int = 0) -> List[ScamRecord]:
    """모든 사기 데이터 로드"""
    all_records: List[ScamRecord] = []

    # 1. Knowledge Base 로드
    kb_path = scam_dir / "scam_knowledge_base.json"
    kb_records = load_knowledge_base(kb_path)
    print(f"[INFO] Loaded {len(kb_records)} knowledge base records")
    all_records.extend(kb_records)

    # 2. Scam Patterns 로드
    pattern_path = scam_dir / "scam_patterns.json"
    pattern_records = load_scam_patterns(pattern_path)
    print(f"[INFO] Loaded {len(pattern_records)} scam pattern records")
    all_records.extend(pattern_records)

    # 3. CSV 파일들 로드
    csv_files = [
        ("경찰청_보이스피싱 현황_20241231.csv", "police_voicephishing"),
        ("경찰청_사이버 금융범죄 현황_20240430.csv", "police_cyber_finance"),
        ("과학기술정보통신부_통신빅데이터플랫폼_휴대전화 스팸트랩 문자 수집 내역.csv", "msit_spam"),
        ("한국인터넷진흥원_피싱사이트 URL_20231231.csv", "kisa_phishing"),
    ]

    for csv_file, source_name in csv_files:
        csv_path = scam_dir / csv_file
        csv_records = load_csv_data(csv_path, source_name)
        print(f"[INFO] Loaded {len(csv_records)} records from {csv_file}")
        all_records.extend(csv_records)

    if limit > 0:
        all_records = all_records[:limit]

    return all_records


def dump_scam_texts(path: Path, records: Iterable[ScamRecord]) -> None:
    """사기 데이터를 JSONL 형식으로 저장"""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "record_id": record.record_id,
                "text": record.text,
                "metadata": record.metadata,
            }
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")


def chunk_scam_data(
    records: Sequence[ScamRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> List[ChunkRecord]:
    """사기 데이터를 청크로 분할"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunk_records: List[ChunkRecord] = []
    for record in records:
        splits = splitter.split_text(record.text)
        if not splits:
            splits = [record.text]
        total_chunks = len(splits)
        
        for idx, chunk_text in enumerate(splits):
            chunk_id = f"{record.record_id}#{idx}"
            metadata = dict(record.metadata)
            metadata.update({
                "record_id": record.record_id,
                "chunk_index": idx,
                "chunk_count": total_chunks,
            })
            chunk_records.append(ChunkRecord(
                chunk_id=chunk_id,
                record_id=record.record_id,
                text=chunk_text,
                metadata=_normalize_metadata(metadata),
            ))
    
    return chunk_records


def embed_and_ingest(
    chunks: Sequence[ChunkRecord],
    collection_name: str,
    db_path: Path,
    batch_size: int,
    reset_collection: bool,
) -> List[ChunkRecord]:
    """임베딩 생성 및 ChromaDB 저장"""
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

    # 증분 업데이트: 기존 레코드 삭제 후 재추가
    unique_records = sorted({chunk.record_id for chunk in chunks})
    print(f"[INFO] Processing {len(unique_records)} unique scam records")

    for record_id in unique_records:
        try:
            collection.delete(where={"record_id": record_id})
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
                    record_id=item.record_id,
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
        description="Chunk and embed Scam Defense data into ChromaDB."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of records for debugging (0 = all)",
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
        default="scam_defense",
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

    scam_dir = Path("data/scam_defense")
    processed_dir = _ensure_dir(Path("data/processed"))
    scam_texts_path = processed_dir / "scam_texts.jsonl"
    embedded_chunks_path = processed_dir / "scam_embedded_chunks.json"
    db_dir = Path(args.db_dir) if args.db_dir else Path("data/chroma_scam_defense")
    _ensure_dir(db_dir)

    print(f"[INFO] Loading scam data from {scam_dir} ...")
    records = load_all_scam_data(scam_dir, limit=args.limit)
    if not records:
        print("[WARN] No scam data loaded; aborting.")
        return 1
    print(f"[INFO] Loaded {len(records)} scam records")

    print(f"[INFO] Writing normalized scam texts to {scam_texts_path}")
    dump_scam_texts(scam_texts_path, records)

    print(
        f"[INFO] Chunking with chunk_size={args.chunk_size}, overlap={args.chunk_overlap}"
    )
    chunks = chunk_scam_data(records, args.chunk_size, args.chunk_overlap)
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

    print("[INFO] Completed Scam Defense ingestion pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
