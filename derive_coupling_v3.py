#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SPEC_V3 §2 결합 강도 도출 — 부록 A 산출 코드 (신규 파일 · LLM 호출 0회).

목적: 실측 파일럿(N=88)에서 2요인(경험평가·해결지향)과 향기피의 **결합 강도**를
      도출해, build_pool_v3.py의 선형 조건부 시프트 계수 β로 쓸 후보값을 산출한다.
      (기존 계보 관용구: sim/sampler.py:43 `lat[x] += 0.3*(spice_aversion-0.5)`)

원칙:
  - 필터는 대조보고서 §0 정본: 광고 시간컷(direct ≥ 2026-07-17 13:00) + B4="그렇다" → N=88.
  - 향기피 강도 척도는 v23_analyze.py의 a2_intensity 가중치 [0, 0.5, 1.0]를 그대로 계승.
  - 임의 선택 금지: 갈리는 지점은 모든 후보를 산출해 병기하고, 선택은 소유자 승인 사항으로 남긴다.
  - 감쇠(attenuation): 관측 결합은 '실현↔실현'인데 샘플러가 필요한 건 'latent↔latent'.
    기존 v2.3 런(R4 저널 + multipool_args)에서 corr(latent 향기피, 실현 A2a)를 측정해 보고.

사용: python3 derive_coupling_v3.py            (표준출력 리포트)
      python3 derive_coupling_v3.py --json OUT  (기계 판독용 JSON 병기)
"""
import argparse
import json
import os
import statistics
import sys

import numpy as np
import pandas as pd

XLSX = "data/actual/게이트C_파일럿_응답.xlsx"
CUT = pd.Timestamp("2026-07-17 13:00:00")      # 광고 태깅 사고 복구 컷(소유자 확인)
A2_W = [0.0, 0.5, 1.0]                         # 출처 v23_analyze.py a2_intensity 가중치
A2_LV = ["아니다", "조금", "매우"]


# ── 0. 정본 표본 ──────────────────────────────────────────────────────────
def load_valid():
    df = pd.read_excel(XLSX, sheet_name="응답")
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    universe = (df["src"] != "direct") | (df["ts"] >= CUT)      # 완주 91
    V = df[universe & (df["B4"] == "그렇다")].copy()             # 유효 88
    V["a2int"] = V["A2a"].map(dict(zip(A2_LV, A2_W)))          # 향기피 강도 [0,.5,1]
    V["seg"] = V["A2a"] == "매우"                               # 협의 세그(설계서 v2.5 §4-3)
    return V


# ── 1. 요인 프록시 ────────────────────────────────────────────────────────
# 경험평가(과거 카테고리 경험의 부정성) ← A1. '안먹어봄'(무경험) 코딩은 해석이 갈려 3변형 + 이진.
A1_VARIANTS = {
    "무경험0.50": {"좋아한다": 0.0, "보통이다": 0.5, "별로였다": 1.0, "안먹어봄": 0.50},
    "무경험0.75": {"좋아한다": 0.0, "보통이다": 0.5, "별로였다": 1.0, "안먹어봄": 0.75},
    "무경험1.00": {"좋아한다": 0.0, "보통이다": 0.5, "별로였다": 1.0, "안먹어봄": 1.00},
    "이진(별로∪무경험)": {"좋아한다": 0.0, "보통이다": 0.0, "별로였다": 1.0, "안먹어봄": 1.0},
}
C2_W = {"꼭산다": 1.0, "가끔산다": 0.5, "기존유지": 0.0}          # 출처 v23_analyze c2_conv
D1_COLS = ["D1_5900", "D1_6900", "D1_7500", "D1_8500"]


def proxies(V):
    """요인별 프록시 시리즈 dict. 판정대상(C2·D1) 계열과 비판정 계열을 라벨로 구분."""
    P = {}
    for name, m in A1_VARIANTS.items():
        P[(f"경험평가/A1[{name}]", "비판정")] = V["A1"].map(m)

    # 해결지향 — (ㄱ) 판정대상 유래(SPEC §2가 지목한 근거: C2 +11%p·D1 +14%p)
    c2 = V["C2"].map(C2_W)                                      # SKIP은 NaN → 조건부 표본
    P[("해결지향/C2전환(SKIP제외)", "판정대상")] = c2
    d1 = V[D1_COLS].apply(lambda r: (r == "산다").sum(), axis=1) / 4.0
    P[("해결지향/D1총수용", "판정대상")] = d1
    both = pd.concat([c2, d1], axis=1).mean(axis=1, skipna=False)
    P[("해결지향/C2·D1평균", "판정대상")] = both

    # 해결지향 — (ㄴ) 비판정 대안(서로소 보존용 후보)
    P[("해결지향대안/A2c접근성장벽", "비판정")] = V["A2c"].map(dict(zip(A2_LV, A2_W)))
    P[("해결지향대안/A2x(아니오=1)", "비판정")] = (V["A2x"] == "아니오").astype(float)
    P[("해결지향대안/C1탐색중(안찾음=0)", "비판정")] = (V["C1"] != "안찾음").astype(float)
    P[("해결지향대안/B2매실청1순위", "비판정")] = (V["B2_1"] == "매실청새콤").astype(float)
    return P


# ── 2. 결합 강도 추정 2방식 ───────────────────────────────────────────────
def estimate(V, y):
    """향기피(a2int) → 프록시 y 의 결합 강도. 두 추정치를 병기.
       β_shift = (세그 평균 − 비기피 평균) / (세그 a2int 평균 − 비기피 a2int 평균)
       β_ols   = cov(a2int, y)/var(a2int)  (연속 회귀 기울기)"""
    m = y.notna()
    x, yy, seg = V.loc[m, "a2int"], y[m], V.loc[m, "seg"]
    out = {"n": int(m.sum()), "n_seg": int(seg.sum()), "n_non": int((~seg).sum()),
           "mean_seg": None, "mean_non": None, "delta": None,
           "beta_shift": None, "beta_ols": None, "r_pearson": None, "r_spearman": None,
           "sd_y": float(yy.std(ddof=1)) if m.sum() > 1 else None}
    if seg.sum() == 0 or (~seg).sum() == 0:
        return out
    ms, mn = float(yy[seg].mean()), float(yy[~seg].mean())
    dx = float(x[seg].mean() - x[~seg].mean())
    out.update(mean_seg=round(ms, 4), mean_non=round(mn, 4), delta=round(ms - mn, 4))
    if abs(dx) > 1e-9:
        out["beta_shift"] = round((ms - mn) / dx, 4)
    if float(x.std(ddof=0)) > 1e-9 and float(yy.std(ddof=0)) > 1e-9:
        out["beta_ols"] = round(float(np.cov(x, yy, ddof=0)[0, 1] / np.var(x)), 4)
        out["r_pearson"] = round(float(np.corrcoef(x, yy)[0, 1]), 3)
        out["r_spearman"] = round(float(pd.Series(x).corr(pd.Series(yy), method="spearman")), 3)
    out["dx_a2int"] = round(dx, 4)
    return out


# ── 3. 근거 행렬(교차표) ──────────────────────────────────────────────────
def matrices(V):
    M = {}
    for col in ["A1", "C2", "C1", "B3", "E1", "A2c", "A2x"]:
        ct = pd.crosstab(V["A2a"], V[col])
        ct = ct.reindex(A2_LV)
        M[f"A2a × {col}"] = ct
    d1 = pd.DataFrame({c: V.groupby("A2a")[c].apply(lambda s: (s == "산다").mean() * 100)
                       for c in D1_COLS}).reindex(A2_LV).round(1)
    M["A2a × D1 수용률%"] = d1
    return M


# ── 4. 감쇠 계수: latent 향기피 ↔ 실현 A2a (기존 v2.3 R4 런에서 측정) ──────
def attenuation(run_id="wf_6ff10eda-c1f"):
    """LLM 호출 없음 — 커밋된 R4 저널 + multipool_args(latent 원값) 재분석.
       ρ_belief = corr(latent 향기피, 믿음질량 a2int) / ρ_real = corr(latent, 실현 pick 강도)"""
    base = os.environ.get("HARNESS_RUNS", os.path.join(os.getcwd(), "runs"))
    d = os.path.join(base, run_id)
    jp, ap, cp = (os.path.join(d, f) for f in
                  ("journal.jsonl", "multipool_args.json", "multipool_cfg.json"))
    if not all(map(os.path.exists, (jp, ap, cp))):
        return {"available": False, "note": f"R4 산출물 없음: {d}"}
    lat = {a["pid"]: a["향기피"] for a in json.load(open(ap, encoding="utf-8"))}
    sseed = json.load(open(cp))["SAMPLE_SEED"]
    SALT_A2a = 41                                   # 출처 v23_multi_analyze.py:20
    rows = {}
    for line in open(jp, encoding="utf-8"):
        o = json.loads(line)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
            rows[r["pid"]] = r
    xs, yb, yr = [], [], []
    for pid, r in rows.items():
        if pid not in lat:
            continue
        w = np.array([max(float(v), 0.0) for v in r["A2a_dist"]])
        s = w.sum() or 1.0
        p = w / s
        xs.append(lat[pid])
        yb.append(float(np.dot(p, A2_W)))                                    # 믿음질량 강도
        k = int(np.random.default_rng([sseed, pid, SALT_A2a]).choice(3, p=p))  # 실현 pick
        yr.append(A2_W[k])
    if len(xs) < 4:
        return {"available": False, "note": "표본 부족"}
    return {"available": True, "n": len(xs), "run_id": run_id,
            "rho_belief": round(float(np.corrcoef(xs, yb)[0, 1]), 3),
            "rho_realized": round(float(np.corrcoef(xs, yr)[0, 1]), 3),
            "sd_latent": round(float(np.std(xs, ddof=1)), 3),
            "sd_belief": round(float(np.std(yb, ddof=1)), 3),
            "sd_realized": round(float(np.std(yr, ddof=1)), 3)}


# ── 5. 요인 간 구조(직교성) + 참고 매핑 ───────────────────────────────────
def _corr(a, b, method="pearson"):
    m = a.notna() & b.notna()
    if m.sum() < 4:
        return None
    return round(float(a[m].corr(b[m], method=method)), 3)


def _partial(a, b, c):
    """c를 통제한 a·b의 편상관(선형 잔차 상관)."""
    m = a.notna() & b.notna() & c.notna()
    if m.sum() < 5:
        return None
    A, B, C = a[m].to_numpy(float), b[m].to_numpy(float), c[m].to_numpy(float)
    ra = A - np.polyval(np.polyfit(C, A, 1), C)
    rb = B - np.polyval(np.polyfit(C, B, 1), C)
    return round(float(np.corrcoef(ra, rb)[0, 1]), 3)


def factor_structure(V):
    """두 요인 프록시의 상호 상관 — 샘플러가 요인 간 상관까지 주입해야 하는지 판단 근거."""
    exp = V["A1"].map(A1_VARIANTS["무경험0.75"])                      # 경험평가 대표 프록시
    c2 = V["C2"].map(C2_W)
    d1 = V[D1_COLS].apply(lambda r: (r == "산다").sum(), axis=1) / 4.0
    sol = pd.concat([c2, d1], axis=1).mean(axis=1, skipna=False)     # 해결지향 대표 프록시
    out = {
        "corr(경험평가, 해결지향[C2·D1])": _corr(exp, sol),
        "partial corr | a2int 통제": _partial(exp, sol, V["a2int"]),
        "corr(경험평가, C2전환)": _corr(exp, c2),
        "corr(경험평가, D1총수용)": _corr(exp, d1),
        "corr(a2int, 경험평가)": _corr(V["a2int"], exp),
        "corr(a2int, 해결지향)": _corr(V["a2int"], sol),
    }
    # 참고(주입 아님): 프록시 → 판정 결과 매핑의 실측 강도. LLM이 창발로 재현해야 하는 대상.
    ref = {
        "corr(경험평가, B1)": _corr(exp, V["B1"].astype(float)),
        "corr(a2int, B1)": _corr(V["a2int"], V["B1"].astype(float)),
        "corr(해결지향, B1)": _corr(sol, V["B1"].astype(float)),
        "corr(경험평가, B3=맛상상안됨)": _corr(exp, (V["B3"] == "맛상상안됨").astype(float)),
        "corr(경험평가, B3=정통맛의심)": _corr(exp, (V["B3"] == "정통맛의심").astype(float)),
        "corr(a2int, B3=정통맛의심)": _corr(V["a2int"], (V["B3"] == "정통맛의심").astype(float)),
        "corr(정통기대프록시 없음 — B3정통 자체가 결과)": None,
    }
    # C2 지표 이중성: 순서점수(§4-2 정의) vs 이진 구매율(파일럿 헤드라인)
    Vc = V[V["C2"] != "SKIP"]
    seg = Vc["A2a"] == "매우"
    binary = Vc["C2"].isin(["꼭산다", "가끔산다"]).astype(float)
    ordinal = Vc["C2"].map(C2_W)
    c2dual = {
        "n(SKIP제외)": int(len(Vc)),
        "순서점수 Δ(§4-2 정의)": round(float(ordinal[seg].mean() - ordinal[~seg].mean()), 4),
        "이진 구매율 Δ%p(파일럿 헤드라인)": round(float(binary[seg].mean() - binary[~seg].mean()) * 100, 1),
        "세그 이진 구매율%": round(float(binary[seg].mean()) * 100, 1),
        "비기피 이진 구매율%": round(float(binary[~seg].mean()) * 100, 1),
        "세그 꼭산다 비율%": round(float((Vc.loc[seg, "C2"] == "꼭산다").mean()) * 100, 1),
        "비기피 꼭산다 비율%": round(float((Vc.loc[~seg, "C2"] == "꼭산다").mean()) * 100, 1),
    }
    return out, ref, c2dual


def main():
    ap = argparse.ArgumentParser(description="SPEC_V3 부록A 결합 강도 도출")
    ap.add_argument("--json", default=None, help="결과 JSON 저장 경로")
    a = ap.parse_args()

    V = load_valid()
    print("=" * 78)
    print("SPEC_V3 부록 A — 결합 강도 도출 (LLM 0회)")
    print("=" * 78)
    print(f"[정본 표본] N={len(V)} "
          f"(comm {int((V.src=='comm').sum())}/verify {int((V.src=='verify').sum())}/direct {int((V.src=='direct').sum())})"
          f"  협의 세그 n={int(V.seg.sum())} ({V.seg.mean()*100:.1f}%)  비기피 n={int((~V.seg).sum())}")
    print(f"[향기피 척도] a2int = A2a→{dict(zip(A2_LV, A2_W))}  "
          f"평균 {V.a2int.mean():.3f} · sd {V.a2int.std(ddof=1):.3f}")
    print(f"  세그 a2int 평균 {V.loc[V.seg,'a2int'].mean():.3f} / 비기피 {V.loc[~V.seg,'a2int'].mean():.3f} "
          f"→ Δx={V.loc[V.seg,'a2int'].mean()-V.loc[~V.seg,'a2int'].mean():.3f}")

    P = proxies(V)
    res = {}
    print("\n" + "-" * 78)
    print(f"{'프록시':38s} {'지위':6s} {'n':>4s} {'세그':>7s} {'비기피':>7s} {'Δ':>7s} "
          f"{'β_shift':>8s} {'β_ols':>7s} {'r_p':>6s} {'r_s':>6s}")
    print("-" * 78)
    for (name, status), y in P.items():
        e = estimate(V, y)
        res[name] = dict(e, status=status)
        f = lambda v, w=7, p=3: (f"{v:{w}.{p}f}" if isinstance(v, (int, float)) else f"{'—':>{w}}")
        print(f"{name:38s} {status:6s} {e['n']:4d} {f(e['mean_seg'])} {f(e['mean_non'])} {f(e['delta'])} "
              f"{f(e['beta_shift'],8)} {f(e['beta_ols'])} {f(e['r_pearson'],6,2)} {f(e['r_spearman'],6,2)}")

    print("\n[프록시 주변분포 — 신규 latent의 μ·σ 후보]")
    for (name, status), y in P.items():
        yy = y.dropna()
        print(f"  {name:38s} μ={yy.mean():.3f}  σ={yy.std(ddof=1):.3f}  n={len(yy)}")

    print("\n[감쇠 계수 — latent 향기피 ↔ 실현 A2a (v2.3 R4 런 재분석)]")
    att = attenuation()
    print("  " + json.dumps(att, ensure_ascii=False))

    fs, ref, c2dual = factor_structure(V)
    print("\n[요인 간 구조 — 요인 상관 주입 필요성 판단]")
    for k, v in fs.items():
        print(f"  {k:34s} {v}")
    print("\n[참고 · 주입 아님 — LLM이 창발로 재현해야 하는 프록시→결과 매핑의 실측 강도]")
    for k, v in ref.items():
        if v is not None:
            print(f"  {k:34s} {v}")
    print("\n[C2 지표 이중성 — §4-2 정의(순서점수) vs 파일럿 헤드라인(이진 구매율)]")
    for k, v in c2dual.items():
        print(f"  {k:30s} {v}")

    print("\n[근거 행렬]")
    M = matrices(V)
    for k, ct in M.items():
        print(f"\n### {k}")
        print(ct.to_string())

    if a.json:
        json.dump({"N": len(V), "n_seg": int(V.seg.sum()), "couplings": res,
                   "attenuation": att,
                   "marginals": {n: {"mu": round(float(y.dropna().mean()), 4),
                                     "sd": round(float(y.dropna().std(ddof=1)), 4)}
                                 for (n, _s), y in P.items()}},
                  open(a.json, "w"), ensure_ascii=False, indent=1)
        print(f"\n[JSON] {a.json}")


if __name__ == "__main__":
    main()
