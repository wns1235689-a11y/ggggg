#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SPEC_V3 §5 등급의 '널 도달 확률' 산출 — 참효과 0에서 판정·등급이 통과할 확률.

왜 필요한가
-----------
§4 통과 규칙은 "통합 부호 + 3풀 중 2풀 이상 동부호"다. 두 조건은 독립이 아니라
**같은 3개 풀 관측치로 계산되므로 강하게 상관**한다. 따라서 널(참효과 0)에서의
통과율은 0.5×0.5=0.25가 아니고 그보다 크다. §5 등급 표기 옆에 이 수치를 병기하는
의무 공시(SPEC_V3 §8)의 근거 산출이 본 스크립트다.

널 모형(명시적 가정 — 이 가정이 결과를 만든다)
--------------------------------------------
  H0: 풀별 판정통계량 Δ_k (k=1,2,3)가 평균 0의 **연속 대칭** 분포에서 iid.
      → 표준정규를 대표값으로 사용. 부호 규칙만 쓰므로 스케일에는 불변이고,
        통합 조건이 크기에 의존하므로 '동일 분산·동일 풀크기'가 실질 가정이다.
  통합 = 풀 3개의 등가중 합(멀티풀 3×100, 타깃 수가 풀별로 비슷 → 등가중 근사).
  판정 4개는 서로 독립(널이므로 공통 신호가 없다는 가정).
  동점(Δ=0) 없음 — 실제로는 이산 질량 때문에 정확히 0이 나올 수 있고
  (v2.3 기준선 #4가 −0.000), 동점은 통과율을 **낮추는** 방향이라 본 수치는 상한 근사다.

산출: (1) 판정당 통과율 p  (2) 등급별 도달 확률  (3) 대조용 순진 가정 0.25
사용: python3 null_rate_v3.py [--mc 20000000]
"""
import argparse
import math
from itertools import product

import numpy as np
from scipy import stats


def p_pass_exact() -> float:
    """P(ΣΔ>0 AND #{Δ_k>0}≥2), Δ~iid N(0,1).

    분해: 3개 모두 양(확률 1/8) → 합>0 항상 참.
          정확히 2개 양(확률 3/8) → 합>0 조건부확률 q를 수치적분.
    q = P(X1+X2-X3'>0 | X1,X2>0, X3'>0)  (X3'=-X3, 모두 절반정규)
      = P(H1+H2 > H3),  H_i ~ HalfNormal(1) iid
    """
    # H1+H2의 밀도와 H3의 분포함수를 곱해 이중적분
    from scipy import integrate

    def inner(h1):
        # ∫ φ_H(h2) · P(H3 < h1+h2) dh2
        g = lambda h2: 2 * stats.norm.pdf(h2) * (2 * stats.norm.cdf(h1 + h2) - 1)  # noqa: E731
        return integrate.quad(g, 0, 40)[0]

    q = integrate.quad(lambda h1: 2 * stats.norm.pdf(h1) * inner(h1), 0, 40)[0]
    return 1 / 8 + 3 / 8 * q, q


def p_pass_mc(n: int, seed: int = 20260725) -> float:
    """동일 확률의 몬테카를로 재확인(독립 경로)."""
    rng = np.random.default_rng(seed)
    hit = 0
    chunk = 2_000_000
    done = 0
    while done < n:
        m = min(chunk, n - done)
        x = rng.standard_normal((m, 3))
        ok = (x.sum(axis=1) > 0) & ((x > 0).sum(axis=1) >= 2)
        hit += int(ok.sum())
        done += m
    return hit / n


def grades(p: float) -> dict:
    """판정 4개 독립·통과확률 p일 때 §5 등급 도달 확률."""
    # 판정 식별: 0=#1 B1, 1=#2 C2, 2=#3 D1, 3=#4 B3
    out = {"완전 적합(4/4)": 0.0, "부분 적합(구조 지지)(3/4·B3 포함)": 0.0,
           "부분 적합(주변부만)(3/4·B3 탈락)": 0.0, "부적합(≤2/4)": 0.0}
    for combo in product([0, 1], repeat=4):
        pr = math.prod(p if c else (1 - p) for c in combo)
        n_pass, b3 = sum(combo), combo[3]
        if n_pass == 4:
            out["완전 적합(4/4)"] += pr
        elif n_pass == 3 and b3:
            out["부분 적합(구조 지지)(3/4·B3 포함)"] += pr
        elif n_pass == 3:
            out["부분 적합(주변부만)(3/4·B3 탈락)"] += pr
        else:
            out["부적합(≤2/4)"] += pr
    out["변형런 권한(구조 지지 이상)"] = (out["완전 적합(4/4)"]
                                    + out["부분 적합(구조 지지)(3/4·B3 포함)"])
    out["3/4 이상(B3 무관)"] = out["완전 적합(4/4)"] + out["부분 적합(구조 지지)(3/4·B3 포함)"] \
        + out["부분 적합(주변부만)(3/4·B3 탈락)"]
    return out


def main():
    ap = argparse.ArgumentParser(description="SPEC_V3 §5 널 도달 확률")
    ap.add_argument("--mc", type=int, default=20_000_000, help="몬테카를로 표본수(교차확인)")
    a = ap.parse_args()

    p, q = p_pass_exact()
    pm = p_pass_mc(a.mc)
    print("=" * 74)
    print("SPEC_V3 §5 널 도달 확률 (참효과 0 · §8 의무 공시 근거)")
    print("=" * 74)
    print(f"P(합>0 | 정확히 2풀 양) = q = {q:.6f}")
    print(f"판정당 통과율  p(수치적분) = {p:.6f}  ({p*100:.1f}%)")
    print(f"판정당 통과율  p(MC n={a.mc:,}) = {pm:.6f}  ({pm*100:.1f}%)")
    print(f"대조 — 두 조건 독립 가정 시(오류) = 0.250000  (25.0%)")
    print("\n[등급 도달 확률 — 판정 4개 독립·p 적용]")
    g = grades(p)
    for k in ["완전 적합(4/4)", "부분 적합(구조 지지)(3/4·B3 포함)",
              "부분 적합(주변부만)(3/4·B3 탈락)", "부적합(≤2/4)",
              "변형런 권한(구조 지지 이상)", "3/4 이상(B3 무관)"]:
        print(f"  {k:38s} {g[k]:.5f}  ({g[k]*100:.1f}%)")
    print("\n[단일풀 §6 비용 게이트 — 등급 아님]")
    print("  단일풀은 풀 부호 조건이 없어 판정당 통과율 = 0.5.")
    for k in (2, 3, 4):
        pr = sum(math.comb(4, i) * 0.5 ** 4 for i in range(k, 5))
        print(f"  P(방향 관측 ≥{k}/4) = {pr:.4f}  ({pr*100:.1f}%)")
    print("\n주의: 위 수치는 '통계적 유의성'이 아니라 **규칙의 널 도달 확률**이다.")
    print("      동점(Δ=0)·풀크기 불균형·판정 간 상관은 반영하지 않았다(상한 근사).")


if __name__ == "__main__":
    main()
