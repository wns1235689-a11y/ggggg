#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""저널 영속화(SPEC P0-3).

시뮬 종료 직후 워크플로 저널(journal.jsonl) + 해당 런의 풀 파일(prof/meta/cfg) +
실행 파라미터를 runs/<run_id>/ 로 복사한다. 20MB 초과 저널은 gzip.

사용:
  python3 persist_run.py <run_id> [--pool-from-sp | --pool-dir <dir>] [--params '<json>']
                         [--gzip-threshold-mb 20]

경로는 harness_paths(환경변수 오버라이드) 사용:
  저널 원본 = HARNESS_JOURNAL_BASE/<run_id>/journal.jsonl
  대상      = HARNESS_RUNS/<run_id>/
"""
import argparse
import json
import os
import shutil
import gzip

import harness_paths as H

# 복사 대상 풀/설정 파일(존재하는 것만 복사).
_POOL_FILES = [
    "run_cfg.json", "pool_meta.json", "prof.json",
    "multipool_cfg.json", "multipool_meta.json", "multipool_args.json",
    "sweep_meta.json", "sweep_prof.json",
]


def main():
    ap = argparse.ArgumentParser(description="워크플로 저널·풀 파일을 runs/<run_id>/로 영속화")
    ap.add_argument("run_id", help="워크플로 런ID (예: wf_9971e46b-6d1)")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--pool-from-sp", action="store_true", help="풀 파일을 HARNESS_SP에서 복사")
    src.add_argument("--pool-dir", default=None, help="풀 파일을 이 디렉토리에서 복사")
    ap.add_argument("--params", default=None, help="실행 파라미터 JSON 문자열(있으면 params.json에 기록)")
    ap.add_argument("--gzip-threshold-mb", type=float, default=20.0, help="저널 gzip 임계(MB)")
    a = ap.parse_args()

    dst = H.run_dir(a.run_id, create=True)
    src_journal = H.journal_path(a.run_id)
    if not os.path.exists(src_journal):
        raise SystemExit(f"[persist_run] 저널 없음: {src_journal}")

    # 저널 복사(20MB 초과 시 gzip)
    size_mb = os.path.getsize(src_journal) / 1e6
    if size_mb > a.gzip_threshold_mb:
        jdest_name = "journal.jsonl.gz"
        with open(src_journal, "rb") as fi, gzip.open(os.path.join(dst, jdest_name), "wb") as fo:
            shutil.copyfileobj(fi, fo)
    else:
        jdest_name = "journal.jsonl"
        shutil.copy2(src_journal, os.path.join(dst, jdest_name))

    # 풀/설정 파일 복사
    pool_src = a.pool_dir if a.pool_dir else (H.SP if a.pool_from_sp else None)
    copied = []
    if pool_src:
        for nm in _POOL_FILES:
            p = os.path.join(pool_src, nm)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(dst, nm))
                copied.append(nm)

    # 실행 파라미터 기록
    manifest = {
        "run_id": a.run_id,
        "journal_file": jdest_name,
        "journal_mb": round(size_mb, 3),
        "gzipped": jdest_name.endswith(".gz"),
        "pool_source": pool_src,
        "pool_files": copied,
    }
    if a.params:
        try:
            manifest["params"] = json.loads(a.params)
        except Exception:
            manifest["params_raw"] = a.params
    json.dump(manifest, open(os.path.join(dst, "params.json"), "w"),
              ensure_ascii=False, indent=1)

    print(f"[persist_run] {a.run_id} → {dst}")
    print(f"  저널: {jdest_name} ({size_mb:.2f}MB{', gzip' if manifest['gzipped'] else ''})")
    print(f"  풀 파일: {copied or '없음'}")


if __name__ == "__main__":
    main()
