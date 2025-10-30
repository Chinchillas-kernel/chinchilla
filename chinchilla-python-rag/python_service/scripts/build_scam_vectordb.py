#!/usr/bin/env python3
"""
사기 방어 벡터 DB 구축 스크립트
금융 사기 패턴, 지식 베이스, 통계 데이터를 ChromaDB에 임베딩
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import chromadb
import pandas as pd
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings
from tqdm import tqdm

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.config import settings
except Exception as exc:
    raise RuntimeError(
        "Failed to import app.config.settings. Ensure PYTHONPATH is set."
    ) from exc


@dataclass
class ScamRecord:
    """사기 패턴/지식 레코드"""

    doc_id: str
    text: str
    metadata: Dict[str, Any]


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
        # ChromaDB는 리스트를 지원하지 않으므로 문자열로 변환
        if isinstance(value, list):
            cleaned[key] = ", ".join(str(v) for v in value)
        else:
            cleaned[key] = value
    return cleaned


def load_scam_patterns(patterns_path: Path) -> List[ScamRecord]:
    """
    사기 패턴 JSON 로드
    data/scam_defense/scam_patterns.json
    """
    if not patterns_path.exists():
        print(f"[WARN] Scam patterns file not found: {patterns_path}")
        return []

    with open(patterns_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    financial_scams = data.get("financial_scams", [])
    keywords = data.get("keywords", {})
    legitimate_contacts = data.get("legitimate_contacts", {})

    records: List[ScamRecord] = []

    # 1) 사기 패턴 레코드
    for idx, scam in enumerate(financial_scams):
        scam_id = scam.get("id", f"pattern_{idx}")
        scam_type = scam.get("type", "알 수 없음")
        category = scam.get("category", "기타")
        danger_level = scam.get("danger_level", "중간")

        patterns = scam.get("patterns", [])
        sender_patterns = scam.get("sender_patterns", [])
        response_actions = scam.get("response_actions", [])
        prevention_tips = scam.get("prevention_tips", [])

        # 텍스트 구성
        lines = [
            f"사기 유형: {scam_type}",
            f"분류: {category}",
            f"위험도: {danger_level}",
            "",
            "의심 패턴:",
        ]
        lines.extend([f"- {p}" for p in patterns])
        lines.append("")
        lines.append("발신자 패턴:")
        lines.extend([f"- {s}" for s in sender_patterns])
        lines.append("")
        lines.append("대응 방법:")
        lines.extend([f"- {r}" for r in response_actions])
        lines.append("")
        lines.append("예방 팁:")
        lines.extend([f"- {t}" for t in prevention_tips])

        text = "\n".join(lines).strip()

        metadata = _normalize_metadata(
            {
                "doc_id": scam_id,
                "source_type": "scam_pattern",
                "scam_type": scam_type,
                "category": category,
                "danger_level": danger_level,
                "patterns": patterns,
                "sender_patterns": sender_patterns,
            }
        )

        records.append(ScamRecord(doc_id=scam_id, text=text, metadata=metadata))

    # 2) 키워드 레코드 (High Risk / Medium Risk)
    for risk_level, keyword_list in keywords.items():
        doc_id = f"keywords_{risk_level}"
        text = f"위험도: {risk_level}\n키워드: {', '.join(keyword_list)}"
        metadata = _normalize_metadata(
            {
                "doc_id": doc_id,
                "source_type": "keywords",
                "risk_level": risk_level,
            }
        )
        records.append(ScamRecord(doc_id=doc_id, text=text, metadata=metadata))

    # 3) 정식 연락처 레코드
    for org_name, phone in legitimate_contacts.items():
        doc_id = f"contact_{org_name}"
        text = f"기관명: {org_name}\n연락처: {phone}"
        metadata = _normalize_metadata(
            {
                "doc_id": doc_id,
                "source_type": "legitimate_contact",
                "organization": org_name,
                "phone": phone,
            }
        )
        records.append(ScamRecord(doc_id=doc_id, text=text, metadata=metadata))

    return records


def load_knowledge_base(kb_path: Path) -> List[ScamRecord]:
    """
    사기 지식 베이스 JSON 로드
    data/scam_defense/scam_knowledge_base.json
    """
    if not kb_path.exists():
        print(f"[WARN] Knowledge base file not found: {kb_path}")
        return []

    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    knowledge_base = data.get("scam_knowledge_base", [])
    records: List[ScamRecord] = []

    for item in knowledge_base:
        kb_id = item.get("id", "")
        title = item.get("title", "")
        category = item.get("category", "")
        content = item.get("content", "")
        danger_level = item.get("danger_level", "정보")
        scam_type = item.get("type", "")

        if not content:
            continue

        # 텍스트 구성
        lines = [
            f"제목: {title}",
            f"카테고리: {category}",
            f"위험도: {danger_level}",
            f"유형: {scam_type}",
            "",
            "내용:",
            content,
        ]

        text = "\n".join(lines).strip()

        metadata = _normalize_metadata(
            {
                "doc_id": kb_id,
                "source_type": "knowledge_base",
                "title": title,
                "category": category,
                "danger_level": danger_level,
                "scam_type": scam_type,
            }
        )

        records.append(ScamRecord(doc_id=kb_id, text=text, metadata=metadata))

    return records


def load_statistics_data(data_dir: Path) -> List[ScamRecord]:
    """
    통계 데이터 CSV 로드
    - 경찰청_보이스피싱 현황
    - 경찰청_사이버 금융범죄 현황
    - 과학기술정보통신부_통신빅데이터플랫폼_휴대전화 스팸트랩 문자 수집 내역
    - 한국인터넷진흥원_피싱사이트 URL
    """
    records: List[ScamRecord] = []

    # CSV 파일 목록
    csv_files = list(data_dir.glob("*.csv"))

    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(csv_path, encoding="cp949", dtype=str, keep_default_na=False)
            except Exception as e:
                print(f"[ERROR] Failed to read {csv_path.name}: {e}")
                continue

        # 각 행을 레코드로 변환
        for idx, row in df.iterrows():
            doc_id = f"{csv_path.stem}_{idx}"

            # 텍스트 구성
            fields = [f"{col}: {val}" for col, val in row.items() if val]
            text = "\n".join(fields).strip()

            if not text:
                continue

            metadata = _normalize_metadata(
                {
                    "doc_id": doc_id,
                    "source_type": "statistics",
                    "source_file": csv_path.name,
                    "record_index": idx,
                }
            )

            records.append(ScamRecord(doc_id=doc_id, text=text, metadata=metadata))

    return records


def chunk_records(
    records: Sequence[ScamRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> List[ScamRecord]:
    """레코드를 청크로 분할"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks: List[ScamRecord] = []
    for record in records:
        splits = splitter.split_text(record.text)
        if not splits:
            splits = [record.text]

        total_chunks = len(splits)
        for idx, chunk_text in enumerate(splits):
            chunk_id = f"{record.doc_id}#chunk{idx}"
            metadata = dict(record.metadata)
            metadata.update(
                {
                    "chunk_index": idx,
                    "chunk_total": total_chunks,
                }
            )
            metadata = _normalize_metadata(metadata)
            chunks.append(
                ScamRecord(doc_id=chunk_id, text=chunk_text, metadata=metadata)
            )

    return chunks


def embed_and_ingest(
    chunks: Sequence[ScamRecord],
    collection_name: str,
    db_path: Path,
    batch_size: int,
    reset_collection: bool,
) -> None:
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

    # 배치 단위로 임베딩 및 저장
    for start in tqdm(range(0, len(chunks), batch_size), desc="Embedding", unit="batch"):
        batch = list(chunks[start : start + batch_size])
        texts = [item.text for item in batch]
        vectors = embeddings_model.embed_documents(texts)

        collection.upsert(
            ids=[item.doc_id for item in batch],
            embeddings=vectors,
            metadatas=[item.metadata for item in batch],
            documents=texts,
        )

    print(f"[INFO] Total documents in collection: {collection.count()}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build Scam Defense vector DB from JSON and CSV data."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/scam_defense",
        help="Scam defense data directory",
    )
    parser.add_argument(
        "--db-dir",
        type=str,
        default="data/chroma_scam_defense",
        help="ChromaDB persistence directory",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="scam_defense",
        help="ChromaDB collection name",
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
        default=100,
        help="Overlap size between chunks",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing collection before ingesting",
    )
    parser.add_argument(
        "--skip-stats",
        action="store_true",
        help="Skip loading statistics CSV files",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.exists():
        raise SystemExit(f"Data directory not found: {data_dir}")

    db_dir = Path(args.db_dir).resolve()
    _ensure_dir(db_dir)

    # 1) 사기 패턴 로드
    print(f"[INFO] Loading scam patterns from {data_dir}/scam_patterns.json ...")
    patterns_path = data_dir / "scam_patterns.json"
    pattern_records = load_scam_patterns(patterns_path)
    print(f"[INFO] Loaded {len(pattern_records)} pattern records")

    # 2) 지식 베이스 로드
    print(f"[INFO] Loading knowledge base from {data_dir}/scam_knowledge_base.json ...")
    kb_path = data_dir / "scam_knowledge_base.json"
    kb_records = load_knowledge_base(kb_path)
    print(f"[INFO] Loaded {len(kb_records)} knowledge base records")

    # 3) 통계 데이터 로드 (옵션)
    stats_records = []
    if not args.skip_stats:
        print(f"[INFO] Loading statistics CSV files from {data_dir} ...")
        stats_records = load_statistics_data(data_dir)
        print(f"[INFO] Loaded {len(stats_records)} statistics records")

    # 전체 레코드 병합
    all_records = pattern_records + kb_records + stats_records
    if not all_records:
        print("[WARN] No records loaded; aborting.")
        return 1

    print(f"[INFO] Total records: {len(all_records)}")

    # 4) 청킹
    print(
        f"[INFO] Chunking with chunk_size={args.chunk_size}, overlap={args.chunk_overlap}"
    )
    chunks = chunk_records(all_records, args.chunk_size, args.chunk_overlap)
    print(f"[INFO] Generated {len(chunks)} chunks")

    # 5) 임베딩 및 저장
    print(
        f"[INFO] Embedding and ingesting into ChromaDB at {db_dir} (collection={args.collection})"
    )
    embed_and_ingest(
        chunks,
        collection_name=args.collection,
        db_path=db_dir,
        batch_size=args.batch_size,
        reset_collection=args.reset,
    )

    print("[INFO] Scam Defense vector DB build completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
