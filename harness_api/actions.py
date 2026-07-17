# -*- coding: utf-8 -*-
"""액션 레이어(SPEC §5.1 실행 콘솔 백엔드).
- gen_pool: 풀 생성 스크립트(build_*)를 동기 실행(빠름) → runs/<pool_id>/
- start_run/get_job: 러너(runner.py)는 nested claude로 분 단위 → 백그라운드 잡 모델
  (HTTP 블로킹·타임아웃 회피). 상태는 runs/_jobs/ 파일.
비용 가드는 runner.py가 강제(dry_run≤2 / N>50 확인 / 재시도 없음)."""
import json
import os
import subprocess
import sys
import uuid

from . import REPO_ROOT
import harness_paths as H

BUILD = {"single": "build_fresh_pool.py", "multipool": "build_multipool.py", "sweep": "build_sweep.py"}
RUN_SCRIPTS = {"wf_vs_v23.js", "wf_v23_multi.js"}
POOL_PREFIXES = ("pool_", "multipool_", "sweep_")

JOBS_DIR = os.path.join(H.RUNS_DIR, "_jobs")
SP_SCOPE = os.path.join(H.RUNS_DIR, "_sp")   # 풀 생성 SP 사본 → 실 스크래치패드 대신 여기(격리)


# ── 풀 생성(동기) ──
def _pool_dirs():
    if not os.path.isdir(H.RUNS_DIR):
        return []
    return [d for d in os.listdir(H.RUNS_DIR) if d.startswith(POOL_PREFIXES)]


def gen_pool(kind, seed=None, n=None):
    if kind not in BUILD:
        raise ValueError(f"kind는 {list(BUILD)} 중 하나 (받음: {kind})")
    os.makedirs(SP_SCOPE, exist_ok=True)
    before = set(_pool_dirs())
    cmd = [sys.executable, os.path.join(REPO_ROOT, BUILD[kind])]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    if n is not None:
        cmd += ["--n", str(n)]
    env = dict(os.environ, HARNESS_RUNS=H.RUNS_DIR, HARNESS_SP=SP_SCOPE)
    p = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"풀 생성 실패(rc={p.returncode}): {(p.stderr or '')[-600:]}")
    new = sorted(set(_pool_dirs()) - before,
                 key=lambda d: os.path.getmtime(os.path.join(H.RUNS_DIR, d)))
    if new:
        pool_id = new[-1]
    else:
        # 동일 시드 재생성(새 dir 없음) → 최신 풀 dir로 폴백
        allp = sorted(_pool_dirs(), key=lambda d: os.path.getmtime(os.path.join(H.RUNS_DIR, d)))
        pool_id = allp[-1] if allp else None
    return {"pool_id": pool_id, "kind": kind, "seed": seed, "n": n,
            "summary": (p.stdout or "").strip().splitlines()}


# ── 러너 트리거(백그라운드 잡) ──
def _jobrec_path(job_id):
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_run(script, pool_id, effort="medium", dry_run=False, n_limit=None, confirm_large=False):
    if script not in RUN_SCRIPTS:
        raise ValueError(f"script는 {sorted(RUN_SCRIPTS)} 중 하나")
    os.makedirs(JOBS_DIR, exist_ok=True)
    job_id = uuid.uuid4().hex[:12]
    out_path = os.path.join(JOBS_DIR, f"{job_id}.out")
    err_path = os.path.join(JOBS_DIR, f"{job_id}.err")
    cmd = [sys.executable, os.path.join(REPO_ROOT, "runner.py"),
           "--script", script, "--pool-id", pool_id, "--effort", effort]
    if dry_run:
        cmd.append("--dry-run")
    if n_limit is not None:
        cmd += ["--n-limit", str(n_limit)]
    if confirm_large:
        cmd.append("--confirm-large")
    env = dict(os.environ, HARNESS_RUNS=H.RUNS_DIR)
    fo, fe = open(out_path, "w"), open(err_path, "w")
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=fo, stderr=fe, env=env)
    rec = {"job_id": job_id, "pid": proc.pid, "cmd": cmd[1:], "script": script,
           "pool_id": pool_id, "effort": effort, "dry_run": dry_run,
           "n_limit": n_limit, "confirm_large": confirm_large,
           "status": "running", "out": os.path.basename(out_path),
           "err": os.path.basename(err_path)}
    json.dump(rec, open(_jobrec_path(job_id), "w"), ensure_ascii=False)
    return rec


def get_job(job_id):
    recf = _jobrec_path(job_id)
    if not os.path.exists(recf):
        return None
    rec = json.load(open(recf))
    if rec.get("status") in ("completed", "failed"):
        return rec                                   # 종료 상태 확정본
    if _pid_alive(rec["pid"]):
        rec["status"] = "running"
        return rec
    # 프로세스 종료 — 러너 JSON 회수
    out_path = os.path.join(JOBS_DIR, rec["out"])
    result, parse_err = None, None
    try:
        txt = open(out_path, encoding="utf-8").read().strip()
        result = json.loads(txt) if txt else None
    except Exception as e:
        parse_err = str(e)
    rec["status"] = "completed" if result and result.get("run_id") else "failed"
    if result:
        rec["result"] = result
    if parse_err:
        rec["parse_error"] = parse_err
    if rec["status"] == "failed":
        try:
            rec["stderr_tail"] = open(os.path.join(JOBS_DIR, rec["err"]), encoding="utf-8").read()[-800:]
        except Exception:
            pass
    json.dump(rec, open(recf, "w"), ensure_ascii=False)
    return rec


def list_jobs():
    if not os.path.isdir(JOBS_DIR):
        return []
    out = []
    for f in os.listdir(JOBS_DIR):
        if f.endswith(".json"):
            out.append(get_job(f[:-5]))
    out.sort(key=lambda r: r.get("job_id", ""))
    return [r for r in out if r]
