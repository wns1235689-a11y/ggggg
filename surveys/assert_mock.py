#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mock 결함 검출 단언(P2-11) — 'verify가 주입 결함 pid를 실제로 잡는가'를 비영 종료로 보증.

배경: 결함 1건은 경고 임계 미만이라 warnings가 비어도 정상 — 검출은 cases 목록으로
확인해야 한다. 이 단언이 없으면 진단 로직 퇴행(P4-01류)이 체인을 조용히 통과한다.

사용: python3 surveys/assert_mock.py <run_id>   (HARNESS_RUNS 환경변수 기준)
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import survey_registry as SR                     # noqa: E402
import harness_paths as H                        # noqa: E402


def main():
    run_id = sys.argv[1]
    run_dir = os.path.join(H.RUNS_DIR, run_id)
    params = json.load(open(os.path.join(run_dir, "params.json"), encoding="utf-8"))
    defects = params.get("defects") or {}
    sid, man = SR.detect_run(run_dir)
    if not sid or not man.get("verify"):
        raise SystemExit(f"[assert_mock] 설문 판별 실패: {run_id}")
    env = dict(os.environ, HARNESS_JOURNAL_BASE=H.RUNS_DIR, HARNESS_SP=run_dir)
    p = subprocess.run([sys.executable, os.path.join(REPO, man["verify"]), run_id],
                       capture_output=True, text=True, env=env, cwd=REPO, timeout=180)
    if p.returncode != 0:
        raise SystemExit(f"[assert_mock] verify 실행 실패: {p.stderr[-400:]}")
    d = json.loads(p.stdout)

    leak_found = {c["pid"] for c in d.get("leak", {}).get("cases", [])}
    echo_found = {c["pid"] for c in d.get("echo", {}).get("cases", [])}
    miss_leak = set(defects.get("leak_pids", [])) - leak_found
    miss_echo = set(defects.get("echo_pids", [])) - echo_found
    if miss_leak or miss_echo:
        print(f"[assert_mock] FAIL {run_id} ({sid}) — 미검출: leak {sorted(miss_leak)}, echo {sorted(miss_echo)}")
        sys.exit(1)
    print(f"[assert_mock] OK {run_id} ({sid}) — 주입 결함 전수 검출 "
          f"(leak {len(defects.get('leak_pids', []))}건, echo {len(defects.get('echo_pids', []))}건)")


if __name__ == "__main__":
    main()
