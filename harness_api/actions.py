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


def _pool_touch(d):
    """풀 dir + 내부 파일의 최신 mtime. 디렉토리 mtime은 기존 파일을 덮어써도
    안 바뀌므로(동일 시드 재생성), 내부 파일까지 봐야 '방금 쓴' 풀을 고를 수 있다."""
    full = os.path.join(H.RUNS_DIR, d)
    t = os.path.getmtime(full)
    try:
        for f in os.listdir(full):
            t = max(t, os.path.getmtime(os.path.join(full, f)))
    except OSError:
        pass
    return t


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
    new = set(_pool_dirs()) - before
    if new:
        pool_id = max(new, key=_pool_touch)                 # 신규 dir 중 방금 쓴 것
    else:
        # 동일 시드 재생성(새 dir 없음) → 내부 파일 mtime 최신 = 방금 재생성한 풀
        allp = _pool_dirs()
        pool_id = max(allp, key=_pool_touch) if allp else None
    return {"pool_id": pool_id, "kind": kind, "seed": seed, "n": n,
            "summary": (p.stdout or "").strip().splitlines()}


# ── 러너 트리거(백그라운드 잡) ──
def _jobrec_path(job_id):
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def _pid_running(pid):
    """살아있고 '실행 중'이면 True. 좀비(Z)/종료(X)는 False.
    러너는 uvicorn이 Popen한 자식이라 종료 후 reap 전까지 좀비로 남는데,
    os.kill(zombie,0)은 성공을 반환하므로 /proc 상태로 좀비를 구분한다.
    가능하면 waitpid(WNOHANG)로 좀비를 수확(같은 프로세스의 자식일 때만 유효)."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            state = f.read().rsplit(")", 1)[1].split()[0]
        if state in ("Z", "X", "x"):
            try:
                os.waitpid(pid, os.WNOHANG)   # 좀비 수확(자식이면), 실패는 무시
            except OSError:
                pass
            return False
    except OSError:
        pass  # /proc 없음 → os.kill 성공만으로 살아있다고 간주
    return True


def _read_out_json(out_path):
    """러너가 종료 직전 stdout에 낸 종료 JSON(dict) — 없거나 미완이면 None."""
    try:
        txt = open(out_path, encoding="utf-8").read().strip()
    except OSError:
        return None
    if not txt:
        return None
    try:
        obj = json.loads(txt)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


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

    out_path = os.path.join(JOBS_DIR, rec["out"])
    result = _read_out_json(out_path)

    # ① 러너가 종료 JSON을 냈으면 그게 확정 신호(좀비 pid와 무관) —
    #    러너는 stdout에 종료 JSON을 정확히 1회 출력하고 종료한다.
    if result is not None and "status" in result:
        done = result.get("status") == "completed" and result.get("run_id")
        rec["status"] = "completed" if done else "failed"
        rec["result"] = result
        if not done:
            try:
                rec["stderr_tail"] = open(os.path.join(JOBS_DIR, rec["err"]), encoding="utf-8").read()[-800:]
            except OSError:
                pass
        json.dump(rec, open(recf, "w"), ensure_ascii=False)
        return rec

    # ② 종료 JSON 아직 없음 — 프로세스가 실제 실행 중이면 running
    if _pid_running(rec["pid"]):
        rec["status"] = "running"
        return rec

    # ③ 프로세스는 끝났는데 유효한 종료 JSON이 없음 → 실패(크래시)
    rec["status"] = "failed"
    try:
        rec["stderr_tail"] = open(os.path.join(JOBS_DIR, rec["err"]), encoding="utf-8").read()[-800:]
    except OSError:
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
