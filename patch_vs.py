#!/usr/bin/env python3
"""VS 분포에서 B1/C1/C2를 표집해 기존 라이브 응답에 패치(모드붕괴 수정)."""
import json, sys
import numpy as np
from sim import config as C
C1_OPT = ["직접 만든다", "냉동/밀키트", "배달·외식", "안 먹거나 참는다", "이런 맛 안 찾음"]
C2_OPT = ["꼭 산다", "가끔 산다", "기존 방식 유지"]

def sample(dist, options, pid, itemid):
    w = np.array([max(float(x), 0.0) for x in dist])
    if w.sum() <= 0:
        w = np.ones(len(options))
    rng = np.random.default_rng([C.GLOBAL_SEED, pid, itemid])
    return options[int(rng.choice(len(options), p=w / w.sum()))]

def main(resp_path, dist_path, out_path):
    resp = json.load(open(resp_path))
    dists = {d["pid"]: d for d in json.load(open(dist_path))}
    for r in resp:
        d = dists.get(r["pid"])
        if not d:
            continue
        r["B1"] = int(sample(d["B1_dist"], [1, 2, 3, 4, 5], r["pid"], 1))
        r["C1"] = sample(d["C1_dist"], C1_OPT, r["pid"], 2)
        r["C2"] = sample(d["C2_dist"], C2_OPT, r["pid"], 3)
    json.dump(resp, open(out_path, "w"), ensure_ascii=False)
    print(f"패치 완료: {out_path} ({len(resp)}명, B1/C1/C2를 VS 분포에서 표집)")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
