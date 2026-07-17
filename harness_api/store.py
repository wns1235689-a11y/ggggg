# -*- coding: utf-8 -*-
"""runs/ 파일 저장소 읽기 레이어.
runs/에는 두 종류가 섞인다:
  - 런(run):  wf_*            (persist_run이 저장 — 저널 + 풀 사본 + params)
  - 풀(pool): pool_* / multipool_* / sweep_*  (build_* 가 저장)
UI는 런 히스토리와 풀 선택 둘 다 필요하므로 접두어로 구분한다.
"""
import gzip
import json
import os

from . import REPO_ROOT  # noqa
import harness_paths as H

POOL_PREFIXES = ("pool_", "multipool_", "sweep_")


def _read_json(path):
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def _journal_info(rundir):
    for name in ("journal.jsonl", "journal.jsonl.gz"):
        p = os.path.join(rundir, name)
        if os.path.exists(p):
            return {"present": True, "gzipped": name.endswith(".gz"),
                    "file": name, "size_bytes": os.path.getsize(p)}
    return {"present": False}


def _count_results(rundir):
    for name, opener in (("journal.jsonl", open),
                         ("journal.jsonl.gz", lambda p, **k: gzip.open(p, "rt", encoding="utf-8"))):
        p = os.path.join(rundir, name)
        if not os.path.exists(p):
            continue
        n = 0
        try:
            f = opener(p, encoding="utf-8") if name.endswith(".jsonl") else opener(p)
            with f:
                for line in f:
                    try:
                        o = json.loads(line)
                        if o.get("type") == "result" and isinstance(o.get("result"), dict):
                            n += 1
                    except Exception:
                        pass
            return n
        except Exception:
            return None
    return None


def _pool_meta(rundir):
    """풀/설정 파일에서 kind·N·seed 유도."""
    single = _read_json(os.path.join(rundir, "run_cfg.json"))
    multi = _read_json(os.path.join(rundir, "multipool_cfg.json"))
    sweep = _read_json(os.path.join(rundir, "sweep_meta.json"))
    if multi:
        return {"kind": "multipool", "N": multi.get("N_PER"), "N_pools": multi.get("N_POOLS"),
                "seed": multi.get("SAMPLE_SEED"), "master_seed": multi.get("master_seed")}
    if single:
        return {"kind": "single", "N": single.get("N"), "seed": single.get("RUN_SEED")}
    if sweep:
        return {"kind": "sweep", "N": None, "seed": sweep.get("master_seed"),
                "names": sweep.get("names")}
    return {"kind": "unknown", "N": None, "seed": None}


def _is_pool(rid):
    return rid.startswith(POOL_PREFIXES)


def list_runs():
    """런(wf_*) 히스토리 — 콘솔 테이블용."""
    root = H.RUNS_DIR
    out = []
    if not os.path.isdir(root):
        return out
    for rid in os.listdir(root):
        d = os.path.join(root, rid)
        if not os.path.isdir(d) or rid.startswith("_") or _is_pool(rid) or not rid.startswith("wf_"):
            continue
        params = _read_json(os.path.join(d, "params.json"))
        pp = (params or {}).get("params", {}) or {}
        meta = _pool_meta(d)
        out.append({
            "run_id": rid,
            "kind": meta["kind"],
            "N": pp.get("N", meta.get("N")),
            "effort": pp.get("effort"),
            "seed": meta.get("seed"),
            "script": pp.get("script"),
            "pool_id": pp.get("pool_id"),
            "dry_run": pp.get("dry_run"),
            "journal": _journal_info(d),
            "created": os.path.getmtime(d),
        })
    out.sort(key=lambda r: r["created"], reverse=True)
    return out


def list_pools():
    """풀(pool_/multipool_/sweep_*) — 실행 콘솔 풀 선택용."""
    root = H.RUNS_DIR
    out = []
    if not os.path.isdir(root):
        return out
    for rid in os.listdir(root):
        d = os.path.join(root, rid)
        if not os.path.isdir(d) or not _is_pool(rid):
            continue
        meta = _pool_meta(d)
        out.append({"pool_id": rid, **meta, "created": os.path.getmtime(d)})
    out.sort(key=lambda r: r["created"], reverse=True)
    return out


def get_run(rid):
    d = os.path.join(H.RUNS_DIR, rid)
    if not os.path.isdir(d):
        return None
    params = _read_json(os.path.join(d, "params.json"))
    meta = _pool_meta(d)
    return {"run_id": rid, **meta, "params": params,
            "journal": _journal_info(d), "result_count": _count_results(d),
            "files": sorted(os.listdir(d)), "created": os.path.getmtime(d)}


def get_pool(pid):
    d = os.path.join(H.RUNS_DIR, pid)
    if not os.path.isdir(d) or not _is_pool(pid):
        return None
    meta = _pool_meta(d)
    return {"pool_id": pid, **meta, "files": sorted(os.listdir(d)),
            "created": os.path.getmtime(d)}
