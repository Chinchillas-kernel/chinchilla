#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B552474 – SenuriService 수집기 v6
- 목록(getJobList) + 상세(getJobInfo) 병합 저장(CSV/JSON)
- HTTPS 우선, HTTP 폴백, 재시도, 진행 로그, open-only 필터, 안전장치 등

실행 전 준비:
  1) .env에 SENURI_API_KEY=... (app.config.Settings가 로드)
  2) 프로젝트 루트에서 실행(또는 PYTHONPATH=. 설정)

빠른 테스트:
  python -u tools/senuri_b552474_fetch_v6.py --pages 1 --rows 20 --detail 10 --verbose

전건 수집(마감 제외 + 결과 0페이지 5회 연속시 중단):
  python -u tools/senuri_b552474_fetch_v6.py --all --open-only --stop-when-old 5 --detail -1 --verbose
"""
from __future__ import annotations

import os
import sys
import time
import re
import json
import argparse
from typing import Any, Dict, List, Optional, Tuple
from datetime import date

# 프로젝트 루트에서 app.config를 찾을 수 있도록 경로 보정(하위 폴더 실행 대비)
if "." not in sys.path:
    sys.path.insert(0, ".")

# --- 설정 로딩 (.env) ---
try:
    from app.config import (
        settings,
    )  # Settings()가 .env를 읽어 SENURI_API_KEY, data_raw_dir 제공
except Exception as _e:
    print(
        "[ERROR] app.config.settings import 실패. PYTHONPATH와 .env를 확인하세요.\n",
        _e,
        flush=True,
    )
    sys.exit(2)

# --- 외부 의존성 ---
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import xmltodict
    import pandas as pd
    from dateutil import parser as dateparser
except Exception as e:
    print(
        "[ERROR] 필요한 패키지 설치 필요:\n"
        "  pip install requests xmltodict pandas python-dateutil\n",
        e,
        flush=True,
    )
    sys.exit(1)

# --- 상수/디렉토리 ---
API_KEY: str = getattr(settings, "senuri_api_key", "") or os.getenv(
    "SENURI_API_KEY", ""
)
BASES = [
    "https://apis.data.go.kr/B552474/SenuriService",
    "http://apis.data.go.kr/B552474/SenuriService",
]
DATA_DIR: str = getattr(settings, "data_raw_dir", "data/raw")
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------- 공용 유틸 ----------------
def build_session(retries: int = 2, backoff: float = 0.4) -> requests.Session:
    s = requests.Session()
    r = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=backoff,
        status_forcelist=(502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=r))
    s.mount("https://", HTTPAdapter(max_retries=r))
    s.headers.update({"User-Agent": "senuri-agent/0.6 (+edu)"})
    return s


def yyyymmdd_to_iso(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = re.sub(r"[^0-9]", "", str(s))
    if len(s) == 8:
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    try:
        return dateparser.parse(str(s)).date().isoformat()
    except Exception:
        return None


def to_date(s: Optional[str]) -> Optional[date]:
    iso = yyyymmdd_to_iso(s)
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except Exception:
        return None


def request_xml(
    path: str,
    params: Dict[str, Any],
    session: requests.Session,
    connect_timeout: float,
    read_timeout: float,
    prefer_http: bool,
    verbose: bool,
) -> Dict[str, Any]:
    bases = BASES[::-1] if prefer_http else BASES
    last_err = None
    for base in bases:
        url = f"{base}/{path.lstrip('/')}"
        try:
            r = session.get(url, params=params, timeout=(connect_timeout, read_timeout))
            r.raise_for_status()
            return xmltodict.parse(r.text)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            if verbose:
                print(f"[WARN] {url} -> {last_err}", flush=True)
            time.sleep(0.25)
    raise RuntimeError(last_err or "request failed")


# ---------------- API Wrappers ----------------
def get_job_list(
    page_no: int,
    num_rows: int,
    session: requests.Session,
    connect_timeout: float,
    read_timeout: float,
    recrt_title: Optional[str],
    emplym_shp: Optional[str],
    work_plc_nm: Optional[str],
    prefer_http: bool,
    verbose: bool,
) -> Dict[str, Any]:
    params = {"serviceKey": API_KEY, "pageNo": page_no, "numOfRows": num_rows}
    if recrt_title:
        params["recrtTitle"] = recrt_title
    if emplym_shp:
        params["emplymShp"] = emplym_shp  # CM0101~CM0105
    if work_plc_nm:
        params["workPlcNm"] = work_plc_nm
    return request_xml(
        "getJobList",
        params,
        session,
        connect_timeout,
        read_timeout,
        prefer_http,
        verbose,
    )


def get_job_info(
    job_id: str,
    session: requests.Session,
    connect_timeout: float,
    read_timeout: float,
    prefer_http: bool,
    verbose: bool,
) -> Dict[str, Any]:
    params = {"serviceKey": API_KEY, "id": job_id}
    return request_xml(
        "getJobInfo",
        params,
        session,
        connect_timeout,
        read_timeout,
        prefer_http,
        verbose,
    )


# ---------------- 파서 ----------------
def parse_list(resp: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    body = (resp.get("response", {}) or {}).get("body", {})
    try:
        total = int(body.get("totalCount", 0))
    except Exception:
        total = 0
    items = (body.get("items", {}) or {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    rows: List[Dict[str, Any]] = []
    for it in items:
        rows.append(
            {
                "jobId": it.get("jobId"),
                "recrtTitle": it.get("recrtTitle"),
                "emplymShp": it.get("emplymShp"),
                "emplymShpNm": it.get("emplymShpNm"),
                "frDd": yyyymmdd_to_iso(it.get("frDd")),
                "toDd": yyyymmdd_to_iso(it.get("toDd")),
                "workPlc": it.get("workPlc"),
                "workPlcNm": it.get("workPlcNm"),
                "oranNm": it.get("oranNm"),
                "acptMthd": it.get("acptMthd"),
                "deadline": it.get("deadline"),
                "stmId": it.get("stmId"),  # A:100세누리 B:워크넷 C:일모아
            }
        )
    return total, rows


def parse_info(resp: Dict[str, Any]) -> Dict[str, Any]:
    body = (resp.get("response", {}) or {}).get("body", {})
    item = (body.get("items", {}) or {}).get("item", {})
    if not isinstance(item, dict):
        return {}
    # 날짜 필드 보정
    for k in ["frAcptDd", "toAcptDd", "createDy", "updDy"]:
        if k in item and item[k]:
            item[k] = yyyymmdd_to_iso(item[k])
    # 주요 키만 선별
    out = {
        "jobId": item.get("jobId"),
        "acptMthdCd": item.get("acptMthdCd"),
        "age": item.get("age"),
        "ageLim": item.get("ageLim"),
        "clltPrnnum": item.get("clltPrnnum"),
        "detCnts": item.get("detCnts"),
        "etcItm": item.get("etcItm"),
        "frAcptDd": item.get("frAcptDd"),
        "toAcptDd": item.get("toAcptDd"),
        "plDetAddr": item.get("plDetAddr"),
        "plbizNm": item.get("plbizNm"),
        "clerk": item.get("clerk"),
        "clerkContt": item.get("clerkContt"),
        "homepage": item.get("homepage"),
        "stmId_detail": item.get("stmId"),
        "lnkStmId": item.get("lnkStmId"),
        "organYn_detail": item.get("organYn"),
        "wantedAuthNo": item.get("wantedAuthNo"),
        "wantedTitle": item.get("wantedTitle"),
        "createDy": item.get("createDy"),
        "updDy": item.get("updDy"),
    }
    return out


# ---------------- 필터 ----------------
def filter_open(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    today = date.today()
    out: List[Dict[str, Any]] = []
    for r in rows:
        if str(r.get("deadline", "")).strip() == "마감":
            continue
        td = to_date(r.get("toDd"))
        if td and td < today:
            continue
        out.append(r)
    return out


# ---------------- 수집 본체 ----------------
def collect(args) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    if not API_KEY:
        raise SystemExit("SENURI_API_KEY not set.")

    sess = build_session(retries=args.retries, backoff=args.backoff)
    list_rows: List[Dict[str, Any]] = []
    total_seen: Optional[int] = None
    open_consec_zero = 0

    page = 1
    while True:
        print(f"[LIST] requesting page={page} rows={args.rows} ...", flush=True)
        try:
            resp = get_job_list(
                page_no=page,
                num_rows=args.rows,
                session=sess,
                connect_timeout=args.connect_timeout,
                read_timeout=args.read_timeout,
                recrt_title=args.title,
                emplym_shp=args.emplym,
                work_plc_nm=args.work,
                prefer_http=args.prefer_http,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"[WARN] getJobList p={page} failed: {e}", flush=True)
            if not args.all:
                break
            page += 1
            time.sleep(args.sleep)
            continue

        total, rows = parse_list(resp)
        if total_seen is None:
            total_seen = total
            if args.all and total_seen and total_seen > 200000:
                print(
                    f"[WARN] totalCount={total_seen} (매우 큼). --all 수집은 장시간 소요. "
                    f"--stop-when-old, --max-items 설정 권장.",
                    flush=True,
                )

        if not rows:
            print("[LIST] empty page -> stop.", flush=True)
            break

        if args.open_only:
            before = len(rows)
            rows = filter_open(rows)
            after = len(rows)
            print(
                f"[LIST] page={page} fetched={before}, open-only kept={after}",
                flush=True,
            )
            open_consec_zero = open_consec_zero + 1 if after == 0 else 0
            if args.stop_when_old > 0 and open_consec_zero >= args.stop_when_old:
                print(
                    f"[LIST] open-only 결과 없는 페이지 연속 {open_consec_zero}개 -> 조기중단",
                    flush=True,
                )
                break
        else:
            print(f"[LIST] page={page} fetched={len(rows)}", flush=True)

        list_rows.extend(rows)
        print(f"[LIST] cumulative collected(list)={len(list_rows)}", flush=True)

        if args.max_items > 0 and len(list_rows) >= args.max_items:
            print(f"[LIST] reached max-items={args.max_items} -> stop.", flush=True)
            break

        if not args.all and page >= args.pages:
            break

        page += 1
        if total_seen and len(list_rows) >= total_seen:
            break

        time.sleep(args.sleep)

    df_list = (
        pd.DataFrame(list_rows).drop_duplicates(subset=["jobId"])
        if list_rows
        else pd.DataFrame()
    )
    print(
        f"[LIST] total rows collected={len(df_list)} (open_only={args.open_only}) totalCount={total_seen}",
        flush=True,
    )

    # 상세 수집
    stats = {"detail_ok": 0, "detail_404": 0, "detail_error": 0}
    if args.detail == 0 or df_list.empty:
        return df_list, pd.DataFrame(), df_list, stats

    # detail_target: -1이면 전건, 양수면 head(n)
    if args.detail < 0:
        detail_df = df_list
    else:
        detail_df = df_list.head(args.detail)

    n_target = len(detail_df)
    details: List[Dict[str, Any]] = []

    print(f"[DETAIL] target={n_target} (requested={args.detail})", flush=True)

    for i, row in enumerate(detail_df.itertuples(index=False), start=1):
        job_id = getattr(row, "jobId", None)
        try:
            info = parse_info(
                get_job_info(
                    str(job_id),
                    sess,
                    args.connect_timeout,
                    args.read_timeout,
                    args.prefer_http,
                    args.verbose,
                )
            )
            if info:
                details.append(info)
                stats["detail_ok"] += 1
            else:
                details.append({"jobId": job_id, "_detail_status": "empty"})
                stats["detail_error"] += 1
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            details.append({"jobId": job_id, "_detail_status": f"http_{code}"})
            if code == 404:
                stats["detail_404"] += 1
            else:
                stats["detail_error"] += 1
        except Exception as e:
            details.append({"jobId": job_id, "_detail_status": f"err:{e}"})
            stats["detail_error"] += 1

        # 진행률 로그
        if (i % 50 == 0) or (i == n_target):
            print(
                f"[DETAIL] progress {i}/{n_target} ok={stats['detail_ok']} 404={stats['detail_404']} err={stats['detail_error']}",
                flush=True,
            )

        time.sleep(args.sleep)

    df_detail = pd.json_normalize(details)
    print(
        f"[DETAIL] done ok={stats['detail_ok']} 404={stats['detail_404']} error={stats['detail_error']}",
        flush=True,
    )

    # 병합
    df_merged = df_list.merge(
        df_detail, on="jobId", how="left", suffixes=("_list", "_detail")
    )
    print(f"[MERGE] merged rows={len(df_merged)}", flush=True)
    return df_list, df_detail, df_merged, stats


# ---------------- 엔트리 ----------------
def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser()
    # 목록 파라미터
    p.add_argument(
        "--pages", type=int, default=3, help="--all 미사용 시 가져올 총 페이지 수"
    )
    p.add_argument("--rows", type=int, default=50, help="페이지당 행 수")
    p.add_argument("--title", type=str, default=None, help="recrtTitle 검색어")
    p.add_argument(
        "--emplym", type=str, default=None, help="emplymShp 코드(CM0101~CM0105)"
    )
    p.add_argument("--work", type=str, default=None, help="workPlcNm(근무지역)")

    # 수집 모드/안전장치
    p.add_argument("--all", action="store_true", help="전체 페이지 순회")
    p.add_argument("--open-only", action="store_true", help="마감 제외(현재 모집 중만)")
    p.add_argument(
        "--stop-when-old",
        type=int,
        default=0,
        help="open-only 결과 0인 페이지가 연속 N회면 중단",
    )
    p.add_argument(
        "--max-items", type=int, default=5000, help="목록 수집 상한(0=무제한)"
    )

    # 상세 수집 개수
    p.add_argument(
        "--detail", type=int, default=150, help="양수=n건, 0=상세없음, -1=목록 전건"
    )

    # 네트워크/로깅
    p.add_argument("--sleep", type=float, default=0.3, help="요청 간 대기초")
    p.add_argument("--retries", type=int, default=2, help="요청 재시도 횟수")
    p.add_argument("--backoff", type=float, default=0.4, help="재시도 백오프 계수")
    p.add_argument("--connect-timeout", type=float, default=5.0)
    p.add_argument("--read-timeout", type=float, default=15.0)
    p.add_argument(
        "--prefer-http", action="store_true", help="HTTP를 우선 사용(장애 대응)"
    )
    p.add_argument("--verbose", action="store_true")

    args = p.parse_args(argv)

    if not API_KEY:
        print("⚠️ SENURI_API_KEY not set. .env를 확인하세요.", flush=True)
        return 2

    df_list, df_detail, df_merged, stats = collect(args)

    list_path_csv = f"{DATA_DIR}/senuri_job_list.csv"
    detail_path_csv = f"{DATA_DIR}/senuri_job_detail.csv"
    merged_path_csv = f"{DATA_DIR}/senuri_jobs_merged.csv"

    df_list.to_csv(list_path_csv, index=False, encoding="utf-8-sig")
    df_detail.to_csv(detail_path_csv, index=False, encoding="utf-8-sig")
    df_merged.to_csv(merged_path_csv, index=False, encoding="utf-8-sig")

    # JSON도 저장
    df_list.to_json(
        list_path_csv.replace(".csv", ".json"), orient="records", force_ascii=False
    )
    df_detail.to_json(
        detail_path_csv.replace(".csv", ".json"), orient="records", force_ascii=False
    )
    df_merged.to_json(
        merged_path_csv.replace(".csv", ".json"), orient="records", force_ascii=False
    )

    print("[SAVE]", list_path_csv, detail_path_csv, merged_path_csv, flush=True)
    print("[DETAIL STATS]", json.dumps(stats, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
