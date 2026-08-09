#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오프라인 mock 저널 — LLM 없이 제네시스 체인 검증. 의도 결함 2종 주입:
① 비상기 거리 페르소나 1명의 Q1에 Genesis(비보조 누출) ② 'no' 상태 1명의 G_dist Y=6(에코 위반).
사용: HARNESS_RUNS=... python3 surveys/genesis_eu26/mock_journal.py <pool_id> [--run-id ...]"""
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
a = ap.parse_args()
pool_dir = os.path.join(RUNS_DIR, a.pool_id)
metas = json.load(open(f"{pool_dir}/pool_meta.json", encoding="utf-8"))
cfg = json.load(open(f"{pool_dir}/run_cfg.json", encoding="utf-8"))
run_id = a.run_id or f"wf_mockgenesis_{cfg['RUN_SEED']}"

Q1_POOLS = {
    "high": ["BMW, Mercedes, Porsche, Audi", "Mercedes, BMW, Bentley", "Audi, BMW, Tesla, Polestar",
             "Porsche, Ferrari, Lamborghini", "BMW, Mercedes, Lexus, Volvo"],
    "mid": ["BMW, Mercedes", "Mercedes, Audi", "BMW, Tesla", "Audi, Volvo", "BMW, Mercedes, Audi"],
    "low": ["BMW", "Mercedes", "", "BMW maybe", "Tesla"],
}
MAGMA_V = {"specific": ["the Magma team at Le Mans, Juncadella drives there", "GMR-001 hypercar, saw Spa"],
           "vague": ["saw them at Le Mans I think?", "some WEC thing right?", "racing at Le Mans"]}


def yn(rng, state, ys):
    if state == "knows":
        return int(rng.integers(8, 11))
    if state == "vague":
        return int(rng.integers(3, 8))
    return int(rng.binomial(10, ys))


def rows_for(m, rng):
    ci = m["latent"]["car_interest"]
    pool = Q1_POOLS["high" if ci > 0.6 else ("mid" if ci > 0.35 else "low")]
    q1 = [str(rng.choice(pool)) for _ in range(10)]
    if m["unaided_genesis"]:
        q1[0] = "BMW, Genesis, Mercedes"
    ys = m["yes_saying"]
    B = yn(rng, m["know"]["BMW"], 0.0)
    L = yn(rng, m["know"]["LEXUS"], ys)
    P = yn(rng, m["know"]["POLESTAR"], ys)
    G = yn(rng, m["know"]["GENESIS"], ys)
    magY = 0
    magv = []
    if m["pop"] == "gp_zandvoort" and G > 0:
        magY = int(rng.binomial(G, 0.5)) if m["magma"] else int(rng.binomial(G, 0.05))
        depth = m.get("magma_depth") or "vague"
        magv = [str(rng.choice(MAGMA_V[depth if depth in MAGMA_V else "vague"])) for _ in range(magY)]
    mag = [magY, (G - magY) if m["pop"] == "gp_zandvoort" else 0]
    return {"pid": m["pid"], "q1_lists": q1,
            "B_dist": [B, 10 - B], "L_dist": [L, 10 - L], "P_dist": [P, 10 - P], "G_dist": [G, 10 - G],
            "magma_dist": mag, "magma_verbatim": magv}


lines = []
leak_done = echo_done = False
for m in metas:
    rng = np.random.default_rng([cfg["RUN_SEED"], m["pid"], 99])
    r = rows_for(m, rng)
    if not leak_done and m["pop"] == "street_rtm" and not m["unaided_genesis"]:
        r["q1_lists"][0] = "BMW, Genesis, Audi"      # 의도 결함 ① 비보조 누출
        leak_done = True
    if not echo_done and m["know"]["GENESIS"] == "no":
        r["G_dist"] = [6, 4]                          # 의도 결함 ② 에코 위반
        if m["pop"] == "gp_zandvoort":
            r["magma_dist"] = [0, 6]
        echo_done = True
    lines.append(json.dumps({"type": "result", "result": r}, ensure_ascii=False))

dst = run_dir(run_id, create=True)
open(f"{dst}/journal.jsonl", "w", encoding="utf-8").write("\n".join(lines) + "\n")
for nm in ("prof.json", "pool_meta.json", "run_cfg.json"):
    shutil.copy2(f"{pool_dir}/{nm}", f"{dst}/{nm}")
json.dump({"run_id": run_id, "journal_file": "journal.jsonl", "mock": True,
           "params": {"survey_id": "genesis_eu26", "script": "surveys/genesis_eu26/wf_genesis.js",
                      "pool_id": a.pool_id, "effort": "mock", "dry_run": True,
                      "N": cfg["N"], "note": "MOCK — 파이프라인 검증 전용, 예측 인용 금지"}},
          open(f"{dst}/params.json", "w"), ensure_ascii=False, indent=1)
print(f"mock 저널 생성: {run_id} (N={len(metas)}, 의도결함: 비보조누출1·에코1)")
