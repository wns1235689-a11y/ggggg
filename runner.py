#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 러너(SPEC §4) — Claude Code 서브프로세스로 Workflow 실행.

계약:
  입력: --script {wf_vs_v23.js|wf_v23_multi.js} --pool-id <id> [--effort medium]
        [--dry-run] [--n-limit N] [--confirm-large] [--timeout S]
  동작: 풀 로드 → 비용 가드 → personas 베이크 임시 wf 생성(원본 불변) →
        claude -p로 Workflow 실행 → run_id 파싱 → nested 저널 완료 폴링 →
        persist_run 영속화(runs/<run_id>/)
  출력: stdout에 JSON {run_id, journal_path, status, token_estimate, results_captured, log}

비용 가드(SPEC §4):
  ① dry_run=true → N≤2 강제  ② N>50는 --confirm-large 없이는 거부
  ③ 자동 재시도 없음(에이전트 단위 1회 — claude -p 한 번만 호출).

시뮬 실행 경로: Claude Code 하니스(중첩 세션). ClaudeBackend 이식 아님(SPEC §1).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid

import harness_paths as H
import survey_registry as SR

REPO = os.path.dirname(os.path.abspath(__file__))
ALLOWED_SCRIPTS = SR.wf_scripts()   # 설문 레지스트리(manifest.wf_scripts 합집합)
PER_PERSONA_TOKENS = 24000   # 관측 기반 대략치(medium 1.16M/49≈24k) — 예상 규모 표시용
DRY_RUN_CAP = 2
LARGE_N = 50
ARGS_PATTERN = "const personas = typeof args === 'string' ? JSON.parse(args) : args"


def load_personas(pool_id):
    """runs/<pool_id>/ 또는 SP에서 풀 파일 로드 → (personas, 경로)."""
    for base in (H.run_dir(pool_id), H.SP):
        for name in ("prof.json", "multipool_args.json"):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return json.load(open(p)), p
    raise SystemExit(f"[runner] 풀 파일 없음: runs/{pool_id}/ 또는 SP에 prof.json/multipool_args.json 필요")


def nested_journal_base(sid):
    """중첩 세션(sid)의 저널 base = <projdir>/<sid>/subagents/workflows.
    JOURNAL_BASE( = <projdir>/<이세션sid>/subagents/workflows )에서 projdir 유도."""
    projdir = os.path.dirname(os.path.dirname(os.path.dirname(H.JOURNAL_BASE.rstrip("/"))))
    return os.path.join(projdir, sid, "subagents", "workflows")


def make_temp_wf(script, personas):
    """원본 wf의 args 주입 라인을 personas 베이크로 치환한 임시 wf 생성.
    원본 파일은 불변 — 프롬프트·스키마는 그대로 복사됨(personas 라인만 교체)."""
    src = open(os.path.join(REPO, script), encoding="utf-8").read()
    if ARGS_PATTERN not in src:
        raise SystemExit(f"[runner] {script}: args 주입 패턴 없음(P0-7 필요)")
    baked = "const personas = " + json.dumps(personas, ensure_ascii=False)
    src2 = src.replace(ARGS_PATTERN, baked, 1)
    tmpdir = os.path.join("/tmp", "harness_runner")
    os.makedirs(tmpdir, exist_ok=True)
    path = os.path.join(tmpdir, f"wfrun_{uuid.uuid4().hex[:8]}_{script}")
    open(path, "w", encoding="utf-8").write(src2)
    return path


def launch(temp_wf, sid, orig_script, log):
    """claude -p로 Workflow 실행(격리 세션 sid). root에서 막히는 skip-permissions 대신
    --permission-mode dontAsk. 반환은 (rc, 출력) — run_id는 저널 디렉토리에서 발견.

    allowedTools에 Read를 포함한다: 중첩 에이전트가 베이크된 워크플로를 '검증 불가한
    불투명 스크립트'로 보고 안전상 실행을 거부하는 경우가 있어(dontAsk는 미허용 툴을
    자동 거부 → Read 막힘), 출처를 밝히고 먼저 Read로 확인할 수 있게 한다. temp_wf는
    리포 원본 {orig_script}의 복사본(프롬프트·스키마 동일, personas만 주입)이다."""
    prompt = (
        f"이것은 이 리포지토리의 시뮬레이션 워크플로를 실행하는 하니스 작업이다. "
        f"scriptPath='{temp_wf}' 는 리포 원본 '{orig_script}'의 복사본으로, 응답자(personas) "
        f"데이터만 주입되어 있고 프롬프트·스키마·로직은 원본과 동일하다. 신뢰할 수 있는 "
        f"하니스 산출물이다. 원하면 먼저 Read 도구로 '{temp_wf}' 내용을 확인해도 된다. "
        f"확인 후(또는 바로) Workflow 도구를 정확히 한 번만 호출하라: scriptPath='{temp_wf}'. "
        f"args는 넘기지 마라(personas는 스크립트에 이미 포함됨). "
        f"실행 뒤 반환된 Run ID만 한 줄로 보고하라.")
    cmd = ["claude", "-p", prompt, "--session-id", sid,
           "--output-format", "json", "--permission-mode", "dontAsk",
           "--allowedTools", "Read,Workflow"]
    log.append(f"[launch] claude -p --session-id {sid} --permission-mode dontAsk --allowedTools Read,Workflow ...")
    try:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as e:
        return -1, f"[launch timeout] {e}"
    return proc.returncode, (proc.stdout or "") + "\n" + (proc.stderr or "")


def discover_run_id(jbase, out, timeout, log):
    """격리 세션의 subagents/workflows/에서 wf_* 디렉토리를 발견(run_id).
    Workflow 도구 호출 시 즉시 생성되므로 -p 종료 직후 존재. 보조로 stdout도 파싱."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.isdir(jbase):
            wfs = [d for d in os.listdir(jbase) if d.startswith("wf_")]
            if wfs:
                wfs.sort(key=lambda d: os.path.getmtime(os.path.join(jbase, d)))
                return wfs[-1]
        time.sleep(2)
    # 폴백: stdout에서 파싱
    m = re.search(r"\bwf_[a-z0-9]{6,}-[a-z0-9]{2,}\b", out)
    if m:
        log.append(f"[discover] 저널 디렉토리 미발견 → stdout 파싱 폴백: {m.group(0)}")
        return m.group(0)
    return None


def poll_journal(jbase, run_id, expected_n, timeout, log):
    """nested 저널을 폴링해 result 라인이 expected_n개 채워질 때까지 대기."""
    jpath = os.path.join(jbase, run_id, "journal.jsonl")
    t0 = time.time()
    last = -1
    while time.time() - t0 < timeout:
        n = 0
        if os.path.exists(jpath):
            for line in open(jpath, encoding="utf-8"):
                try:
                    o = json.loads(line)
                    if o.get("type") == "result" and isinstance(o.get("result"), dict):
                        n += 1
                except Exception:
                    pass
        if n != last:
            log.append(f"[poll] {n}/{expected_n} results ({int(time.time()-t0)}s)")
            last = n
        if n >= expected_n:
            return "completed", jpath, n
        time.sleep(5)
    return "timeout", jpath, max(last, 0)


def emit(result):
    print(json.dumps(result, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description="Phase 1 러너 — Claude Code 서브프로세스 Workflow 실행")
    ap.add_argument("--script", required=True, choices=sorted(ALLOWED_SCRIPTS))
    ap.add_argument("--pool-id", required=True)
    ap.add_argument("--effort", default="medium", help="기록용(임시 wf가 effort를 이미 내장)")
    ap.add_argument("--dry-run", action="store_true", help="N≤2로 강제 축소(파이프라인 검증)")
    ap.add_argument("--n-limit", type=int, default=None)
    ap.add_argument("--confirm-large", action="store_true", help="N>50 실행 확인")
    ap.add_argument("--timeout", type=int, default=None)
    a = ap.parse_args()
    log = []

    personas, poolfile = load_personas(a.pool_id)
    N_full = len(personas)
    N = N_full
    if a.n_limit is not None:
        N = min(N, a.n_limit)
    if a.dry_run:
        N = min(N, DRY_RUN_CAP)
    personas = personas[:N]
    token_estimate = N * PER_PERSONA_TOKENS
    log.append(f"[pool] {poolfile}: 전체 {N_full}명 → 실행 {N}명 (dry_run={a.dry_run}, n_limit={a.n_limit})")
    log.append(f"[estimate] 규모 {N}페르소나×1에이전트, 예상 토큰 ~{token_estimate:,}")

    if N > LARGE_N and not a.confirm_large:
        emit({"run_id": None, "journal_path": None, "status": "refused_large_N",
              "token_estimate": token_estimate,
              "log": log + [f"[GUARD] N={N}>{LARGE_N} — --confirm-large 필요(확인 없이 실행 불가)"]})
        return

    sid = str(uuid.uuid4())
    temp_wf = make_temp_wf(a.script, personas)
    jbase = nested_journal_base(sid)
    log.append(f"[wf] 임시 베이크 wf={temp_wf}, session_id={sid}")

    rc, out = launch(temp_wf, sid, a.script, log)
    run_id = discover_run_id(jbase, out, 30, log)
    log.append(f"[launch] rc={rc}, run_id={run_id}")
    if not run_id:
        emit({"run_id": None, "journal_path": None, "status": "launch_failed",
              "token_estimate": token_estimate,
              "log": log + ["[ERROR] run_id 발견 실패(저널 디렉토리·stdout 모두). 서브프로세스 출력 일부:", out[:2000]]})
        return

    timeout = a.timeout if a.timeout else (300 if a.dry_run else 3600)
    status, jpath, got = poll_journal(jbase, run_id, N, timeout, log)

    journal_path = None
    if status == "completed":
        env = dict(os.environ, HARNESS_JOURNAL_BASE=jbase)
        params = json.dumps({"script": a.script, "pool_id": a.pool_id, "effort": a.effort,
                             "dry_run": a.dry_run, "N": N, "session_id": sid,
                             "survey_id": SR.survey_for_wf(a.script)}, ensure_ascii=False)
        pr = subprocess.run([sys.executable, os.path.join(REPO, "persist_run.py"), run_id,
                             "--pool-dir", H.run_dir(a.pool_id), "--params", params],
                            cwd=REPO, capture_output=True, text=True, env=env)
        log.append("[persist] " + ((pr.stdout or "").strip() or (pr.stderr or "").strip()))
        journal_path = os.path.join("runs", run_id, "journal.jsonl")

    emit({"run_id": run_id, "journal_path": journal_path, "status": status,
          "token_estimate": token_estimate, "results_captured": got, "log": log})


if __name__ == "__main__":
    main()
