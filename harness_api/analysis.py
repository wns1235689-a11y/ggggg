# -*- coding: utf-8 -*-
"""분석/진단 스크립트를 서브프로세스로 실행하고 JSON stdout을 파싱하는 헬퍼.
스크립트는 runs/<run_id>/ 를 SP·저널 base로 보도록 환경변수를 주입한다.
텍스트 파싱 없음 — v23_verify 등은 JSON을 stdout으로 낸다."""
import gzip
import json
import os
import subprocess
import sys

from . import REPO_ROOT
import harness_paths as H


def run_env(run_id):
    return dict(os.environ,
                HARNESS_JOURNAL_BASE=H.RUNS_DIR,
                HARNESS_SP=os.path.join(H.RUNS_DIR, run_id))


def journal_format(run_id):
    """첫 result 라인으로 저널 포맷 판별: 'v2.3'(A2a_dist) / 'legacy'(A2_dist·E1_dist) / 'unknown'."""
    d = os.path.join(H.RUNS_DIR, run_id)
    for name in ("journal.jsonl", "journal.jsonl.gz"):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            continue
        opener = (lambda: gzip.open(p, "rt", encoding="utf-8")) if name.endswith(".gz") \
            else (lambda: open(p, encoding="utf-8"))
        try:
            with opener() as f:
                for line in f:
                    o = json.loads(line)
                    r = o.get("result")
                    if o.get("type") == "result" and isinstance(r, dict):
                        if "A2a_dist" in r:
                            return "v2.3"
                        if "A2_dist" in r or "E1_dist" in r:
                            return "legacy"
                        return "unknown"
        except Exception:
            return "unknown"
    return "no_journal"


def run_json_script(script, run_id, extra_args=None, timeout=180):
    """python3 <script> <run_id> [args...] → JSON(dict). 실패 시 RuntimeError."""
    cmd = [sys.executable, os.path.join(REPO_ROOT, script), run_id] + (extra_args or [])
    p = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                       env=run_env(run_id), timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{script} 실행 실패(rc={p.returncode}): {(p.stderr or '')[-800:]}")
    try:
        return json.loads(p.stdout)
    except Exception as e:
        raise RuntimeError(f"{script} JSON 파싱 실패: {e}; stdout 앞부분: {p.stdout[:500]}")
