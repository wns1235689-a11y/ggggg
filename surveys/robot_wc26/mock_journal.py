#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오프라인 mock 저널 — LLM 없이 verify→judge→report 체인 검증용.

규칙 기반으로 페르소나 상태에 정합하는 저널을 생성한다. 의도적 결함 2종을 주입해
진단이 잡아내는지 확인한다: ① 무지식층 1명의 정답 발화(누출) ② 비노출 1명의 Y=5(에코 위반).
이 산출물은 파이프라인 검증 전용 — 예측·판정 인용 금지(mock 딱지).

사용: HARNESS_RUNS=... python3 surveys/robot_wc26/mock_journal.py <pool_id> [--run-id wf_mockrobot1]
"""
import argparse
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

import numpy as np

from harness_paths import RUNS_DIR, run_dir

ap = argparse.ArgumentParser()
ap.add_argument("pool_id")
ap.add_argument("--run-id", default=None)
ap.add_argument("--defect-rate", type=float, default=0.0,
                help="무지식층 verbatim에 추가 누출을 이 확률로 주입(임계 초과 픽스처용 — P2-11)")
a = ap.parse_args()
pool_dir = os.path.join(RUNS_DIR, a.pool_id)
metas = json.load(open(f"{pool_dir}/pool_meta.json", encoding="utf-8"))
cfg = json.load(open(f"{pool_dir}/run_cfg.json", encoding="utf-8"))
run_id = a.run_id or f"wf_mockrobot_{cfg['RUN_SEED']}"

GUESS_POOL = ["Tesla? Elon's one?", "google I think", "no idea, sorry", "Samsung maybe?",
              "not sure at all", "some American company?", "no clue", "is it Tesla",
              "that robot dog company, the viral one", "honestly no idea"]
DESC_POOL = ["the robot dog company", "the one with the parkour videos", "that famous robot company from YouTube"]
DK_POOL = ["no idea", "don't know", "not sure", "no clue, sorry"]


def rows_for(m, rng):
    know, exposed, strength = m["knowledge"], m["exposed"], m["strength"]
    if not exposed:
        y = 0
    elif strength == "clear":
        y = int(rng.integers(8, 11))
    else:
        y = int(rng.integers(3, 8))
    q2, pa, pb = [], [], []
    for _ in range(y):
        u = rng.random()
        if know == "both":
            # 분기C 정합(P1-01): 양사 동시 발화 60% → 프로브 없음 / 부분공개 40% → A2 발화+probeA 정답
            if u < 0.6:
                q2.append("Boston Dynamics — it's Hyundai's now, right?")   # A3, 프로브 미첨부
            else:
                q2.append("Boston Dynamics")                                # 부분공개(A2) → probeA서 정답
                pa.append("Hyundai owns them now")
        elif know == "bd_only":
            if u < 0.7:
                q2.append("Boston Dynamics")
                pa.append(str(rng.choice(["no idea", "Google's, no?", "SoftBank I thought"])))
            else:
                q2.append(str(rng.choice(DESC_POOL)))
        elif know == "hyundai_only":
            if u < 0.6:
                q2.append("Hyundai I think? the sponsor")
                pb.append(str(rng.choice(["no idea", "don't know the name"])))
            else:
                q2.append(str(rng.choice(DK_POOL)))
        elif know == "desc_only":
            q2.append(str(rng.choice(DESC_POOL if u < 0.6 else GUESS_POOL)))
        else:
            q2.append(str(rng.choice(GUESS_POOL if u < 0.5 else DK_POOL)))
    tri = np.array(m["q3_tri"])
    q3 = np.random.default_rng([cfg["RUN_SEED"], m["pid"], 7]).multinomial(10, tri / tri.sum())
    return {"pid": m["pid"], "Q1_dist": [y, 10 - y], "q2_verbatim": q2,
            "probeA_verbatim": pa, "probeB_verbatim": pb, "Q3_dist": [int(x) for x in q3]}


lines = []
leak_pids, echo_pids = [], []
leak_done = echo_done = False
for m in metas:
    rng = np.random.default_rng([cfg["RUN_SEED"], m["pid"], 99])
    r = rows_for(m, rng)
    # 의도 결함 ①: 무지식층 첫 1명에 정답 발화 주입(누출 검출 확인)
    if not leak_done and m["knowledge"] == "none" and r["q2_verbatim"]:
        r["q2_verbatim"][0] = "Boston Dynamics obviously"
        leak_pids.append(m["pid"])
        leak_done = True
    # --defect-rate: 무지식층에 추가 누출 주입(임계 초과 픽스처 — P2-11)
    elif a.defect_rate > 0 and m["knowledge"] in ("none", "desc_only") and r["q2_verbatim"] \
            and rng.random() < a.defect_rate:
        r["q2_verbatim"][0] = "Tesla? or maybe Hyundai actually"   # raw-text 스캔 검증(P4-01형)
        leak_pids.append(m["pid"])
    # 의도 결함 ②: 비노출 첫 1명에 Y=5(에코 위반 검출 확인)
    if not echo_done and not m["exposed"]:
        r["Q1_dist"] = [5, 5]
        r["q2_verbatim"] = [str(x) for x in np.random.default_rng(1).choice(DK_POOL, 5)]
        echo_pids.append(m["pid"])
        echo_done = True
    lines.append(json.dumps({"type": "result", "result": r}, ensure_ascii=False))

dst = run_dir(run_id, create=True)
open(f"{dst}/journal.jsonl", "w", encoding="utf-8").write("\n".join(lines) + "\n")
for nm in ("prof.json", "pool_meta.json", "run_cfg.json"):
    shutil.copy2(f"{pool_dir}/{nm}", f"{dst}/{nm}")
json.dump({"run_id": run_id, "journal_file": "journal.jsonl", "mock": True,
           "defects": {"leak_pids": leak_pids, "echo_pids": echo_pids},   # 단언 스크립트용(P2-11)
           "params": {"survey_id": "robot_wc26", "script": "surveys/robot_wc26/wf_robot.js",
                      "pool_id": a.pool_id, "effort": "mock", "dry_run": True,
                      "N": cfg["N"], "note": "MOCK — 파이프라인 검증 전용, 예측 인용 금지"}},
          open(f"{dst}/params.json", "w"), ensure_ascii=False, indent=1)
print(f"mock 저널 생성: {run_id} (N={len(metas)}, 의도결함: 누출{len(leak_pids)}·에코{len(echo_pids)})")
