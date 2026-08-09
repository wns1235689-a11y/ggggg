#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사전등록 봉인 스크립트(P4-02) — 선행성 입증 장치.

주어진 run_id들의 config/wf 해시·git HEAD·판정 요약을 SEALED_<label>.json으로 박제한다.
봉인 절차(README 참조): ① 3시나리오(×3시드 권장) 풀·런 준비 ② check_bands 통과
③ 이 스크립트 실행 ④ git add SEALED_*.json && git commit && git tag prereg-seal-<label>.

사용: python3 surveys/seal_prereg.py <label> <run_id> [<run_id> ...]
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import survey_registry as SR     # noqa: E402
import harness_paths as H        # noqa: E402


def main():
    if len(sys.argv) < 3:
        raise SystemExit("사용: seal_prereg.py <label> <run_id> [...]")
    label, run_ids = sys.argv[1], sys.argv[2:]
    entries = []
    for rid in run_ids:
        d = os.path.join(H.RUNS_DIR, rid)
        cfg = json.load(open(os.path.join(d, "run_cfg.json"), encoding="utf-8"))
        sid, _ = SR.detect_run(d)
        entries.append({"run_id": rid, "survey_id": sid,
                        "scenario": cfg.get("scenario"), "seed": cfg.get("RUN_SEED"),
                        "N": cfg.get("N"), "config_sha256_16": cfg.get("config_sha256_16"),
                        "wf_sha256_16": cfg.get("wf_sha256_16"), "git_head": cfg.get("git_head")})
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except Exception:
        head = None
    seal = {"label": label, "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_head_at_seal": head, "runs": entries,
            "note": "봉인 = 이 파일이 커밋·태그된 시점의 리포트들. 이후 config 수정은 새 봉인으로만."}
    out = os.path.join(REPO, f"SEALED_{label}.json")
    json.dump(seal, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[seal] {out} ({len(entries)}개 런) — 다음: git add/commit + git tag prereg-seal-{label}")


if __name__ == "__main__":
    main()
