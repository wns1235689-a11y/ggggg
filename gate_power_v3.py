#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""단일풀 게이트의 검정력 진단 — 순열검정 (서술적 · 판정 아님 · LLM 0회).

§6-2 비용 게이트는 등급 판정이 아니다. 그런데 단일풀(n=50)에서 협의 세그는
**실현 표집 결과 6명**뿐이라, 관측된 Δ 4개가 우연 변동과 구분되는지 자체가
불확실하다. 이 스크립트는 그 불확실성을 수치화한다 — **판정을 다시 하지 않고**,
게이트 결과를 어느 정도 신뢰할 수 있는지 소유자가 판단할 재료만 제공한다.

방법: 세그/비기피 라벨을 타깃 안에서 무작위 재배치(B회)해 각 판정통계량의
귀무분포를 만들고, 관측 Δ의 양측 위치를 본다. 표집·salt·지표 정의는
v3_analyze.py에서 그대로 import — 정의 불일치 여지 없음.

사용: HARNESS_SP=$PWD/runs/<run> HARNESS_JOURNAL_BASE=$PWD/runs \
      python3 gate_power_v3.py <run_id> [--B 20000]
"""
import argparse
import statistics

import numpy as np

import v3_analyze as V


def main():
    ap = argparse.ArgumentParser(description="단일풀 게이트 검정력 진단(순열검정)")
    ap.add_argument("run_id")
    ap.add_argument("--B", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20260725)
    a = ap.parse_args()

    mode, seed, meta, lat, cfg = V.load_context(a.run_id)
    rows = V.load_rows(a.run_id)
    tgt = [p for p in rows if meta.get(p, {}).get("is_target")]
    seg = [p for p in tgt if V.pick(rows[p]["A2a_dist"], 3, p, V.SALT["A2a"], seed) == 2]
    non = [p for p in tgt if p not in set(seg)]
    noseek = {p for p in tgt
              if V.pick(rows[p]["C1_dist"], 5, p, V.SALT["C1"], seed) == V.C1_IDX_NOSEEK}

    STATS = [("#1 ΔB1", V.b1m, "음", False), ("#2 ΔC2(이진·조건부)", V.c2_binary, "양", True),
             ("#3 ΔD1(총수용)", V.d1a, "양", False),
             ("#4 B3 정통우려 질량", V.b3_auth, "음", False)]
    print("=" * 78)
    print(f"단일풀 게이트 검정력 진단  run={a.run_id}  타깃 {len(tgt)} "
          f"(세그 {len(seg)} / 비기피 {len(non)})  B={a.B}")
    print(f"⚠ {V.LABEL}")
    print("서술적 진단 — 판정 아님. §6-2 게이트 결과를 대체하거나 수정하지 않는다.")
    print("=" * 78)
    rng = np.random.default_rng(a.seed)
    pool = np.array(tgt)
    k = len(seg)
    print(f"\n{'판정':22s} {'관측Δ':>8s} {'기대':4s} {'귀무 2.5%':>9s} {'97.5%':>8s} "
          f"{'양측 p':>7s} 부호 우연 확률")
    print("-" * 78)
    for name, fn, want, cond in STATS:
        def delta(S, N):
            S2 = [p for p in S if not cond or p not in noseek]
            N2 = [p for p in N if not cond or p not in noseek]
            if not S2 or not N2:
                return None
            return (statistics.mean(fn(rows[p]) for p in S2)
                    - statistics.mean(fn(rows[p]) for p in N2))
        obs = delta(seg, non)
        null = []
        for _ in range(a.B):
            idx = rng.permutation(len(pool))
            S = list(pool[idx[:k]])
            N = list(pool[idx[k:]])
            d = delta(S, N)
            if d is not None:
                null.append(d)
        null = np.array(null)
        lo, hi = np.quantile(null, [0.025, 0.975])
        p2 = float((np.abs(null) >= abs(obs)).mean())
        # 기대 부호가 우연히 나올 확률
        psign = float((null < 0).mean() if want == "음" else (null > 0).mean())
        print(f"{name:22s} {obs:+8.3f} {want:4s} {lo:+9.3f} {hi:+8.3f} {p2:7.3f} {psign*100:5.1f}%")
    print("\n[읽는 법] 귀무 구간이 관측Δ를 넉넉히 포함하면 그 판정은 이 표본 크기에서")
    print("  방향을 식별할 힘이 없다는 뜻이다. 세그 실현 인원이 작을수록 구간이 넓어진다.")
    print("  이 표는 게이트 통과·미달을 바꾸지 않는다(§5 사후 조정 금지).")


if __name__ == "__main__":
    main()
