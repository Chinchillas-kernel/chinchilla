#!/usr/bin/env python3
"""Utilities for chunking and embedding legal documents into ChromaDB."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from bs4 import BeautifulSoup
from chromadb.config import Settings
from langchain_community.document_loaders import PyPDFLoader
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
class LegalRecord:
    """법률 문서 레코드"""

    doc_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class ChunkRecord:
    """청크 레코드"""

    chunk_id: str
    doc_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[Sequence[float]] = None


# 법률 카테고리 분류
LEGAL_CATEGORIES = {
    "경제지원": ["기초연금법", "국민연금법", "긴급복지지원법"],
    "의료건강": ["노인장기요양보험법", "의료급여법", "국민건강보험법", "치매관리법"],
    "복지서비스": [
        "노인복지법",
        "사회보장기본법",
        "고령친화산업진흥법",
        "장애인복지법",
    ],
    "주거": ["주거급여법", "주택임대차보호법"],
    "법률권리": ["민법"],
}


def _ensure_dir(path: Path) -> Path:
    """디렉토리 생성"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _classify_law(law_name: str) -> str:
    """법률 이름으로 카테고리 분류"""
    for category, laws in LEGAL_CATEGORIES.items():
        for law in laws:
            if law in law_name:
                return category
    return "기타"


def _extract_law_info(law_name: str) -> Dict[str, str]:
    """법률명에서 정보 추출"""
    info = {"short_name": law_name}

    # 약칭 생성
    if "노인" in law_name:
        info["target"] = "노인"
    if "장애인" in law_name:
        info["target"] = "장애인"

    # 키워드 추출
    keywords = []
    keyword_map = {
        "연금": ["연금", "급여", "수급"],
        "복지": ["복지", "서비스", "시설"],
        "의료": ["의료", "건강", "요양"],
        "주택": ["주택", "주거", "임대"],
        "보험": ["보험", "보장"],
    }

    for key, terms in keyword_map.items():
        if any(term in law_name for term in terms):
            keywords.append(key)

    info["keywords"] = ",".join(keywords) if keywords else ""

    return info


def _clean_text(text: str) -> str:
    """텍스트 정리"""
    if not text:
        return ""

    # 공백 정리
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # 특수문자 정리
    text = text.replace("\xa0", " ")
    text = text.replace("\u3000", " ")

    return text.strip()


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


def load_legal_pdfs(pdf_dir: Path, limit: int = 0) -> List[LegalRecord]:
    """
    PDF 디렉토리에서 모든 법률 문서 로드

    Args:
        pdf_dir: PDF 파일들이 있는 디렉토리
        limit: 로드할 파일 수 제한 (0 = 전체)

    Returns:
        LegalRecord 리스트
    """
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {pdf_dir}")

    if limit > 0:
        pdf_files = pdf_files[:limit]

    print(f"[INFO] Found {len(pdf_files)} PDF files")

    legal_records: List[LegalRecord] = []

    for pdf_file in tqdm(pdf_files, desc="Loading PDFs"):
        try:
            # PDF 로드
            loader = PyPDFLoader(str(pdf_file))
            pages = loader.load()

            if not pages:
                print(f"[WARN] Empty PDF: {pdf_file.name}")
                continue

            # 법률명 추출
            law_name = pdf_file.stem
            law_info = _extract_law_info(law_name)
            category = _classify_law(law_name)

            # 전체 텍스트 결합
            full_text = "\n\n".join([page.page_content for page in pages])
            full_text = _clean_text(full_text)

            if not full_text:
                print(f"[WARN] No text extracted from {pdf_file.name}")
                continue

            # 문서 ID 생성
            doc_id = f"law_{len(legal_records):04d}"

            # 메타데이터 생성
            metadata = _normalize_metadata(
                {
                    "doc_id": doc_id,
                    "law_name": law_name,
                    "law_short_name": law_info.get("short_name", law_name),
                    "category": category,
                    "keywords": law_info.get("keywords", ""),
                    "target": law_info.get("target", ""),
                    "total_pages": len(pages),
                    "file_name": pdf_file.name,
                    "source": "legal_pdf",
                }
            )

            legal_records.append(
                LegalRecord(doc_id=doc_id, text=full_text, metadata=metadata)
            )

            print(
                f"[INFO] Loaded: {law_name} ({len(pages)} pages, {len(full_text)} chars)"
            )

        except Exception as e:
            print(f"[ERROR] Failed to load {pdf_file.name}: {e}")
            continue

    return legal_records


def dump_legal_texts(path: Path, records: Iterable[LegalRecord]) -> None:
    """법률 문서 텍스트를 JSONL 파일로 저장"""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "doc_id": record.doc_id,
                "text": record.text,
                "metadata": record.metadata,
            }
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")


def chunk_legal_docs(
    records: Sequence[LegalRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> List[ChunkRecord]:
    """
    법률 문서를 청크로 분할

    Args:
        records: 법률 문서 레코드들
        chunk_size: 청크 크기
        chunk_overlap: 청크 겹침 크기

    Returns:
        ChunkRecord 리스트
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n제", "\n\n", "\n", ".", " ", ""],  # 법률 조항 기준
    )

    chunk_records: List[ChunkRecord] = []

    for record in tqdm(records, desc="Chunking"):
        splits = splitter.split_text(record.text)

        if not splits:
            splits = [record.text]

        total_chunks = len(splits)

        for idx, chunk_text in enumerate(splits):
            chunk_id = f"{record.doc_id}#chunk_{idx}"

            # 메타데이터 복사 및 확장
            metadata = dict(record.metadata)
            metadata.update(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "chunk_count": total_chunks,
                    "chunk_size": len(chunk_text),
                }
            )

            chunk_records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    doc_id=record.doc_id,
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
    """
    청크를 임베딩하고 ChromaDB에 저장

    Args:
        chunks: 청크 레코드들
        collection_name: ChromaDB 컬렉션 이름
        db_path: ChromaDB 저장 경로
        batch_size: 임베딩 배치 크기
        reset_collection: 기존 컬렉션 삭제 여부

    Returns:
        임베딩이 포함된 ChunkRecord 리스트
    """
    # API 키 확인
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise RuntimeError(
            "UPSTAGE_API_KEY not configured. Set environment variable or .env entry."
        )

    # ChromaDB 클라이언트 초기화
    client = chromadb.PersistentClient(
        path=str(db_path.absolute()),
        settings=Settings(anonymized_telemetry=False),
    )

    # 컬렉션 리셋
    if reset_collection:
        try:
            client.delete_collection(collection_name)
            print(f"[INFO] Deleted existing collection: {collection_name}")
        except Exception:
            pass

    # 컬렉션 생성
    collection = client.get_or_create_collection(name=collection_name)

    # Upstage Embeddings 초기화
    embeddings_model = UpstageEmbeddings(
        api_key=api_key, model="solar-embedding-1-large"
    )

    # 기존 문서 삭제 (문서 ID 기준)
    unique_doc_ids = sorted({chunk.doc_id for chunk in chunks})
    for doc_id in unique_doc_ids:
        try:
            collection.delete(where={"doc_id": doc_id})
        except Exception:
            continue

    # 배치로 임베딩 및 저장
    updated_chunks: List[ChunkRecord] = []

    for start in tqdm(
        range(0, len(chunks), batch_size), desc="Embedding", unit="batch"
    ):
        batch = list(chunks[start : start + batch_size])
        texts = [item.text for item in batch]

        # 임베딩 생성
        vectors = embeddings_model.embed_documents(texts)

        # ChromaDB에 저장
        collection.upsert(
            ids=[item.chunk_id for item in batch],
            embeddings=vectors,
            metadatas=[item.metadata for item in batch],
            documents=texts,
        )

        # 결과 저장
        for item, vector in zip(batch, vectors):
            updated_chunks.append(
                ChunkRecord(
                    chunk_id=item.chunk_id,
                    doc_id=item.doc_id,
                    text=item.text,
                    metadata=item.metadata,
                    embedding=vector,
                )
            )

    return updated_chunks


def dump_chunks(path: Path, chunks: Sequence[ChunkRecord]) -> None:
    """청크 데이터를 JSON 파일로 저장"""
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding,
        }
        for chunk in chunks
    ]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_argument_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성"""
    parser = argparse.ArgumentParser(
        description="Chunk and embed legal documents into ChromaDB."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of PDFs for debugging (0 = all)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Character length for each chunk",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Overlap size between chunks",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Embedding batch size",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="elderly_legal",
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
    """메인 실행 함수"""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    # 경로 설정
    raw_dir = Path(settings.data_raw_dir)
    pdf_dir = raw_dir / "legal"
    processed_dir = _ensure_dir(Path("data/processed"))
    legal_texts_path = processed_dir / "legal_texts.jsonl"
    embedded_chunks_path = processed_dir / "legal_embedded_chunks.json"

    # ChromaDB 경로
    if args.db_dir:
        db_dir = Path(args.db_dir)
    else:
        db_dir = Path(settings.chroma_dir).parent / "chroma_legal"

    _ensure_dir(db_dir)

    print("=" * 70)
    print("📚 법률 문서 ChromaDB 로딩 파이프라인")
    print("=" * 70)
    print(f"PDF 디렉토리: {pdf_dir}")
    print(f"ChromaDB 경로: {db_dir}")
    print(f"컬렉션명: {args.collection}")
    print(f"청크 크기: {args.chunk_size} / 겹침: {args.chunk_overlap}")
    print("=" * 70 + "\n")

    # 1. PDF 로드
    print("[STEP 1] Loading PDFs...")
    legal_records = load_legal_pdfs(pdf_dir, limit=args.limit)

    if not legal_records:
        print("[ERROR] No legal documents loaded; aborting.")
        return 1

    print(f"[SUCCESS] Loaded {len(legal_records)} legal documents\n")

    # 2. 텍스트 저장
    print(f"[STEP 2] Writing normalized texts to {legal_texts_path}")
    dump_legal_texts(legal_texts_path, legal_records)
    print("[SUCCESS] Texts saved\n")

    # 3. 청크 분할
    print(f"[STEP 3] Chunking documents...")
    chunks = chunk_legal_docs(legal_records, args.chunk_size, args.chunk_overlap)
    print(f"[SUCCESS] Generated {len(chunks)} chunks\n")

    # 4. 임베딩 및 저장
    print(f"[STEP 4] Embedding and ingesting into ChromaDB...")
    embedded_chunks = embed_and_ingest(
        chunks,
        collection_name=args.collection,
        db_path=db_dir,
        batch_size=args.batch_size,
        reset_collection=args.reset,
    )
    print(f"[SUCCESS] Embedded and stored {len(embedded_chunks)} chunks\n")

    # 5. 임베딩 데이터 저장
    print(f"[STEP 5] Saving embedded chunks to {embedded_chunks_path}")
    dump_chunks(embedded_chunks_path, embedded_chunks)
    print("[SUCCESS] Embedded chunks saved\n")

    print("=" * 70)
    print("🎉 법률 문서 로딩 완료!")
    print("=" * 70)
    print(f"총 문서 수: {len(legal_records)}")
    print(f"총 청크 수: {len(chunks)}")
    print(f"ChromaDB 경로: {db_dir}")
    print(f"컬렉션명: {args.collection}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
