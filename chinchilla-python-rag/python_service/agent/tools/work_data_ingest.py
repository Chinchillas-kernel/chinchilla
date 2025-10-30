#!/usr/bin/env python3
"""Utilities for chunking and embedding Senuri job data into ChromaDB."""
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
from bs4 import BeautifulSoup
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings
from tqdm import tqdm

try:
    from app.config import settings
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Failed to import app.config.settings. Ensure PYTHONPATH is set.") from exc

@dataclass
class JobRecord:
    job_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class ChunkRecord:
    chunk_id: str
    job_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[Sequence[float]] = None


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _strip_html(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        if not value.strip():
            return ""
        text_in = value
    else:
        if pd.isna(value):
            return ""
        text_in = str(value)

    soup = BeautifulSoup(text_in, "html.parser")
    text = soup.get_text(separator="\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\r?\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_multiline(value: str) -> str:
    if not value:
        return ""
    text = value.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_location(raw: Any) -> tuple[Optional[str], Optional[str]]:
    if not raw:
        return None, None
    text = str(raw).strip()
    if not text:
        return None, None
    parts = text.split()
    if not parts:
        return None, None
    province = parts[0]
    city = " ".join(parts[1:]) if len(parts) > 1 else None
    return province, city


def _extract_min_age(*values: Any) -> Optional[int]:
    min_age: Optional[int] = None
    for value in values:
        if not value:
            continue
        matches = re.findall(r"\d+", str(value))
        for match in matches:
            try:
                number = int(match)
            except ValueError:
                continue
            if number <= 0:
                continue
            if min_age is None or number < min_age:
                min_age = number
    return min_age


def _normalize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        cleaned[key] = value
    return cleaned


def load_jobs(merged_csv: Path, limit: int = 0) -> List[JobRecord]:
    if not merged_csv.exists():
        raise FileNotFoundError(f"Merged CSV not found: {merged_csv}")

    df = pd.read_csv(merged_csv, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if limit > 0:
        df = df.head(limit)

    job_records: List[JobRecord] = []
    for row in df.to_dict(orient="records"):
        job_id = str(row.get("jobId", "")).strip()
        if not job_id:
            continue

        title = (row.get("wantedTitle") or row.get("recrtTitle") or "").strip()
        organization = (row.get("plbizNm") or row.get("oranNm") or "").strip()
        work_region = row.get("workPlcNm")
        detail_address = row.get("plDetAddr")
        employment_type = row.get("emplymShpNm") or row.get("emplymShp")
        deadline_status = row.get("deadline")
        open_date = row.get("frDd")
        close_date = row.get("toDd")
        application_method = row.get("acptMthd") or row.get("acptMthdCd")
        min_age = _extract_min_age(row.get("age"), row.get("ageLim"))
        province, city = _extract_location(work_region)
        contact_person = row.get("clerk")
        contact_phone = row.get("clerkContt")
        homepage = row.get("homepage")

        list_dates = []
        if open_date:
            list_dates.append(open_date)
        if close_date:
            list_dates.append(close_date)
        application_period = " ~ ".join(list_dates) if list_dates else None

        det_cnts = _clean_multiline(_strip_html(row.get("detCnts")))
        etc_itm = _clean_multiline(_strip_html(row.get("etcItm")))

        lines: List[str] = []
        if title:
            lines.append(f"채용 공고: {title}")
        if organization:
            lines.append(f"기관명: {organization}")
        if work_region:
            lines.append(f"근무지역: {work_region}")
        if detail_address:
            lines.append(f"상세주소: {detail_address}")
        if min_age:
            lines.append(f"연령: {min_age}세 이상")
        if row.get("clltPrnnum"):
            lines.append(f"모집인원: {row['clltPrnnum']}명")
        if employment_type:
            lines.append(f"고용형태: {employment_type}")
        if application_period:
            lines.append(f"접수기간: {application_period}")
        if deadline_status:
            lines.append(f"접수상태: {deadline_status}")
        if application_method:
            lines.append(f"접수방법: {application_method}")
        if etc_itm:
            lines.append(f"우대사항: {etc_itm}")
        contact_parts = []
        if contact_person:
            contact_parts.append(f"담당자: {contact_person}")
        if contact_phone:
            contact_parts.append(f"연락처: {contact_phone}")
        if homepage:
            contact_parts.append(f"홈페이지: {homepage}")
        if contact_parts:
            lines.append(" | ".join(contact_parts))
        if det_cnts:
            lines.append("")
            lines.append("상세 내용:")
            lines.append(det_cnts)

        document_text = "\n".join([line for line in lines if line is not None]).strip()
        if not document_text:
            continue

        metadata = _normalize_metadata(
            {
                "job_id": job_id,
                "title": title,
                "organization": organization,
                "region_province": province,
                "region_city": city,
                "min_age": min_age,
                "deadline_status": deadline_status,
                "open_date": open_date,
                "close_date": close_date,
                "application_method": application_method,
                "employment_type": employment_type,
                "source": "senuri",
            }
        )

        job_records.append(JobRecord(job_id=job_id, text=document_text, metadata=metadata))

    return job_records


def dump_job_texts(path: Path, jobs: Iterable[JobRecord]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in jobs:
            payload = {
                "doc_id": record.job_id,
                "text": record.text,
                "metadata": record.metadata,
            }
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")


def chunk_jobs(
    jobs: Sequence[JobRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> List[ChunkRecord]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunk_records: List[ChunkRecord] = []
    for job in jobs:
        splits = splitter.split_text(job.text)
        if not splits:
            splits = [job.text]
        total_chunks = len(splits)
        for idx, chunk_text in enumerate(splits):
            chunk_id = f"{job.job_id}#{idx}"
            metadata = dict(job.metadata)
            metadata.update({"job_id": job.job_id, "chunk_index": idx, "chunk_count": total_chunks})
            chunk_records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    job_id=job.job_id,
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
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY not configured. Set environment variable or .env entry.")

    client = chromadb.PersistentClient(
        path=str(db_path.absolute()),
        settings=Settings(anonymized_telemetry=False),
    )

    if reset_collection:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(name=collection_name)

    embeddings_model = UpstageEmbeddings(api_key=api_key, model="solar-embedding-1-large")

    updated_chunks: List[ChunkRecord] = []
    unique_job_ids = sorted({chunk.job_id for chunk in chunks})
    for job_id in unique_job_ids:
        try:
            collection.delete(where={"job_id": job_id})
        except Exception:
            continue

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
            updated_chunks.append(
                ChunkRecord(
                    chunk_id=item.chunk_id,
                    job_id=item.job_id,
                    text=item.text,
                    metadata=item.metadata,
                    embedding=vector,
                )
            )

    return updated_chunks


def dump_chunks(path: Path, chunks: Sequence[ChunkRecord]) -> None:
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "job_id": chunk.job_id,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding,
        }
        for chunk in chunks
    ]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chunk and embed Senuri job data into ChromaDB.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of jobs for debugging (0 = all)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=600,
        help="Character length for each chunk",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=120,
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
        default="elderly_jobs",
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

    raw_dir = Path(settings.jobs_data_dir)
    merged_csv = raw_dir / "senuri_jobs_merged.csv"
    processed_dir = _ensure_dir(Path("data/processed"))
    job_texts_path = processed_dir / "job_texts.jsonl"
    embedded_chunks_path = processed_dir / "embedded_chunks.json"
    db_dir = Path(args.db_dir) if args.db_dir else Path(settings.chroma_dir)
    _ensure_dir(db_dir)

    print(f"[INFO] Loading jobs from {merged_csv} ...")
    jobs = load_jobs(merged_csv, limit=args.limit)
    if not jobs:
        print("[WARN] No jobs loaded; aborting.")
        return 1
    print(f"[INFO] Loaded {len(jobs)} jobs")

    print(f"[INFO] Writing normalized job texts to {job_texts_path}")
    dump_job_texts(job_texts_path, jobs)

    print(
        f"[INFO] Chunking with chunk_size={args.chunk_size}, overlap={args.chunk_overlap}"
    )
    chunks = chunk_jobs(jobs, args.chunk_size, args.chunk_overlap)
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

    print("[INFO] Completed Senuri job ingestion pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
