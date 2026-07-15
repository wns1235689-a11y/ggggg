# -*- coding: utf-8 -*-
"""E1 강제 양자택일 붕괴 수정 — VS 4지 분포(가/나/비슷/둘다)에서 표집해 rows_final E1 재패치."""
import json, sys
import numpy as np

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
cfg = json.load(open(f"{SP}/run_cfg.json"))
SEED = cfg["RUN_SEED"]
BASE = "/root/.claude/projects/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/subagents/workflows"

# journal → e1dist (pid→[가,나,비슷,둘다])
dist = {}
for line in open(f"{BASE}/{sys.argv[1]}/journal.jsonl", encoding="utf-8"):
    o = json.loads(line)
    if o.get("type") == "result" and isinstance(o.get("result"), dict) and "E1_dist" in o.get("result", {}):
        dist[o["result"]["pid"]] = o["result"]["E1_dist"]

E1_OPT = ["가(T1·완성도)", "나(T2·매실청)", "비슷", "둘 다 안 끌림"]


def sample_e1(d, pid):
    w = np.array([max(float(x), 0.0) for x in d], float)
    if w.sum() <= 0:
        w = np.ones(4)
    rng = np.random.default_rng([SEED, pid, 60])
    return E1_OPT[int(rng.choice(4, p=w / w.sum()))]


rows = json.load(open(f"{SP}/rows_final.json"))
from collections import Counter
before = Counter(r["E1"] for r in rows)
patched = 0
for r in rows:
    d = dist.get(r["respondent_id"])
    if d:
        r["E1"] = sample_e1(d, r["respondent_id"])
        patched += 1
json.dump(rows, open(f"{SP}/rows_final.json", "w"), ensure_ascii=False)
after = Counter(r["E1"] for r in rows)
print(f"E1 재패치 {patched}/{len(rows)}")
print("이전:", dict(before))
print("이후:", dict(after))
