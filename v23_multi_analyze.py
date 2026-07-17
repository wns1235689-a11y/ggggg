# -*- coding: utf-8 -*-
"""다풀(3×100) 견고성 + 시드앙상블 판정.
   ⑴ 풀별/통합 연속상관(seed-free, 주지표): A2a향부담강도 ↔ B1·C2·D1·E1(나-가).
   ⑵ 시드앙상블: 세그교차 Δ(B1) 평균±sd (실현분류 노이즈 제거).
   ⑶ 강한 축(가격·관여) 풀-견고성 대조.
   방향 미주입 — 나오는 방향은 LLM prior. 통합 n으로 유의성까지 판정(N증대 질문 실증)."""
import json, sys, statistics
from collections import Counter
import numpy as np

from harness_paths import SP
cfg = json.load(open(f"{SP}/multipool_cfg.json"))
SSEED = cfg["SAMPLE_SEED"]
from harness_paths import JOURNAL_BASE as BASE
RUNID = sys.argv[1]
meta = {m["pid"]: m for m in json.load(open(f"{SP}/multipool_meta.json"))}
lat = {a["pid"]: a for a in json.load(open(f"{SP}/multipool_args.json"))}
K_ENS = 12
D1P = [5900, 6900, 7500, 8500]
SALT_A2a = 41


def load():
    rows = {}
    for l in open(f"{BASE}/{RUNID}/journal.jsonl", encoding="utf-8"):
        o = json.loads(l); r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
            rows[r["pid"]] = r
    return rows


def wmean(d, v):
    w = np.array([max(float(x), 0.0) for x in d]); s = w.sum() or 1.0
    return float(np.dot(w, v) / s)


def a2int(r): return wmean(r["A2a_dist"], [0, 0.5, 1.0])
def b1m(r):   return wmean(r["B1_dist"], [1, 2, 3, 4, 5])
def c2c(r):   return wmean(r["C2_dist"], [1.0, 0.5, 0.0])
def d1a(r):   return statistics.mean(r[f"buy_{v}"] for v in D1P) / 10.0
def e1ng(r):  return (r["E1_dist"][1] - r["E1_dist"][0]) / 10.0   # 나-가


def pearson(xs, ys):
    n = len(xs)
    if n < 4:
        return 0.0, 1.0
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** .5
    dy = (sum((y - my) ** 2 for y in ys)) ** .5
    r = num / (dx * dy) if dx * dy else 0.0
    r = max(min(r, 0.999), -0.999)
    t = r * ((n - 2) / (1 - r * r)) ** .5
    # 양측 p 근사(정규 근사, n 큼)
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / 2 ** .5)))
    return r, p


def ens_seg_delta(rows, base, cut):
    """시드앙상블: 실현 A2a로 세그분류(seed별), Δ b1_mean 평균±sd."""
    deltas = []
    for e in range(K_ENS):
        av, nv = [], []
        for p in base:
            d = rows[p]["A2a_dist"]
            w = np.array([max(float(x), 0.0) for x in d]); w = w / (w.sum() or 1)
            k = int(np.random.default_rng([SSEED, p, SALT_A2a, e]).choice(3, p=w))
            (av if k >= cut else nv).append(p)
        if av and nv:
            deltas.append(statistics.mean(b1m(rows[q]) for q in av) - statistics.mean(b1m(rows[q]) for q in nv))
    if not deltas:
        return None
    return statistics.mean(deltas), (statistics.pstdev(deltas) if len(deltas) > 1 else 0.0), len(deltas)


def block(name, rows, base):
    ai = [a2int(rows[p]) for p in base]
    print(f"\n【{name}】 타깃 n={len(base)}")
    for lbl, fn in [("B1첫인상", b1m), ("C2전환", c2c), ("D1수용", d1a), ("E1(나-가)", e1ng)]:
        r, p = pearson(ai, [fn(rows[q]) for q in base])
        sig = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
        print(f"   향부담강도 ↔ {lbl:<8}: r={r:+.2f}  p={p:.3f} {sig}")
    ens = ens_seg_delta(rows, base, cut=2)
    if ens:
        print(f"   [시드앙상블 협의컷] 세그교차 ΔB1 = {ens[0]:+.2f} ± {ens[1]:.2f} (seed {ens[2]}회)")
    # 강한 축 견고성
    price = [lat[p]["가격민감"] for p in base]; invo = [lat[p]["관여"] for p in base]
    rp, pp = pearson(price, [d1a(rows[q]) for q in base])
    ri, pi = pearson(invo, [wmean(rows[q]["E1_dist"], [0, 0, 0, 1]) for q in base])  # E1 둘다별로 질량
    print(f"   [강한축] 가격민감↔D1수용 r={rp:+.2f}(p={pp:.3f})   관여↔E1둘다별로 r={ri:+.2f}(p={pi:.3f})")


def main():
    rows = load()
    pools = sorted({p // 1000 for p in rows})
    print(f"════ 다풀 견고성 판정  RUNID={RUNID}  N={len(rows)}  풀={pools}  SAMPLE_SEED={SSEED} ════")
    if not rows:
        print("결과 없음(진행 중).")
        return
    all_t = []
    for k in pools:
        base = [p for p in rows if p // 1000 == k and meta[p]["is_target"]]
        block(f"풀{k}", rows, base)
        all_t += base
    block("통합(3풀)", rows, all_t)

    # 풀-일관성 요약(부호)
    print("\n── 풀-일관성 요약: 향부담강도↔반응 부호 ──")
    for lbl, fn in [("B1", b1m), ("C2", c2c), ("D1", d1a), ("E1(나-가)", e1ng)]:
        signs = []
        for k in pools:
            base = [p for p in rows if p // 1000 == k and meta[p]["is_target"]]
            r, _ = pearson([a2int(rows[p]) for p in base], [fn(rows[p]) for p in base])
            signs.append(f"{r:+.2f}")
        print(f"   {lbl:<9}: 풀0..2 = {signs}  → {'부호일관' if len({s[0] for s in signs})==1 else '부호혼조'}")
    print("\n[해석] 통합 n으로 유의성 확정 = N증대 효과의 실증. 부호일관 = 풀-견고.")
    print("       방향은 LLM prior(진실 아님) — 실측만이 최종.")


if __name__ == "__main__":
    main()
