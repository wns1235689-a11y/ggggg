#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3-sim 적합 판정 (SPEC_V3 §4 정정판 · §5 등급 · §8 보고 의무).

주판정 4개 — 각각 통합 부호 + 3풀 중 2풀 이상 동부호로 통과(§4):
  #1 ΔB1 음      : 협의 세그(A2a 실현 '매우') − 비기피의 B1 가중평균 차 < 0   [좁은 창발]
  #2 ΔC2 양      : C1 실현 '이런 맛 안 찾음' 제외 조건부 · **이진 구매율**(꼭+가끔 질량) 차 > 0
                   (§4-2 정정 83bfed3 — 순서점수는 보조 병기)                [전파 확인(부분 순환)]
  #3 ΔD1 양      : 총수용(buy 4점 평균/10, [0,1] 정규화) 차 > 0              [전파 확인(부분 순환)]
  #4 B3 비대칭   : '진짜 팟타이 아닐것' 질량이 세그 < 비기피                  [순수 창발]

등급(§5 · 무변경): 4/4 완전 적합 · 3/4+B3 부분 적합(구조 지지) · 3/4−B3 부분 적합(주변부만) · ≤2/4 부적합.
단일풀은 등급 판정이 아니라 §6 비용 게이트(방향 2개 이상 관측 시 진행).

표집·라벨·salt는 v23_analyze.py에서 그대로 계승(원본 무변경). 경로는 harness_paths.
사용: python3 v3_analyze.py <run_id> [--json OUT]
"""
import argparse
import json
import statistics
import sys
from collections import Counter

import numpy as np

from harness_paths import SP, JOURNAL_BASE as BASE

LABEL = ("보정 시뮬 · 가설 생성 전용 · 시장 증거 아님 · 인용 불가"
         "  (SPEC_V3 §0 — 하드코딩, 비활성화 불가)")

# ── v23_analyze.py 계승(동일 값·변경 금지) ──
A2c = ["아니다", "조금", "매우"]                                     # 출처 v23_analyze.py:20
B3O = ["맛 상상 안됨", "진짜 팟타이 아닐것", "냉동품질 불신", "가격 걱정",
       "양 부족", "팟타이 관심없음", "없음"]                          # 출처 v23_analyze.py:22
C1O = ["직접 만든다", "냉동·밀키트", "배달·외식", "안 먹음·참음", "이런 맛 안 찾음"]
C2O = ["꼭 산다", "가끔 산다", "기존 유지"]                          # 출처 v23_analyze.py:24
E1O = ["가(완성도)", "나(매실청)", "비슷", "둘 다 별로"]              # 출처 v23_analyze.py:25
SALT = {"A1": 40, "A2a": 41, "A2b": 42, "A2c": 43, "A2d": 44, "A2x": 45,
        "B1": 1, "B2": 46, "B3": 47, "C1": 2, "C2": 3, "E1": 60}      # 출처 v23_analyze.py:26-27
D1P = [5900, 6900, 7500, 8500]
B3_IDX_AUTH = 1        # '진짜 팟타이 아닐것'
C1_IDX_NOSEEK = 4      # '이런 맛 안 찾음'

TIER = {"B1": "좁은 창발", "C2": "전파 확인(부분 순환)",
        "D1": "전파 확인(부분 순환)", "B3": "순수 창발"}     # §4 창발 3계층(3df8d88)

# 널 도달 확률 — 참효과 0에서 규칙이 통과할 확률(부록 A A14 · null_rate_v3.py 수치적분).
# 표시 전용 상수: 판정 로직·임계에 관여하지 않는다. SPEC_V3 §5·§8 의무 공시라 끌 수 없다.
NULL_RATE = {"판정당": 0.4189, "완전 적합": 0.0308, "부분 적합(구조 지지)": 0.1281,
             "부분 적합(주변부만) — 2요인의 핵심 창발 미달": 0.0427, "부적합": 0.7984,
             "구조지지이상": 0.1589, "게이트": 0.6875}
V23_BASELINE = "v2.3 기준선(동일 판정기·기존 R4) = 1/4 부적합 · #4 B3 −0.000 (부록 A A12)"


def wmean(d, v):
    w = np.array([max(float(x), 0.0) for x in d])
    s = w.sum() or 1.0
    return float(np.dot(w, v) / s)


def mass(d, idx):
    w = np.array([max(float(x), 0.0) for x in d])
    s = w.sum() or 1.0
    return float(w[idx] / s)


def pick(d, k, pid, salt, seed):
    """결정론 실현 표집 — v23_analyze.pick과 동일 관용구."""
    w = np.array([max(float(x), 0.0) for x in d])
    w = w / (w.sum() or 1.0)
    return int(np.random.default_rng([seed, pid, salt]).choice(k, p=w))


def b1m(r):
    return wmean(r["B1_dist"], [1, 2, 3, 4, 5])


def c2_binary(r):
    """이진 구매율 = ('꼭 산다'+'가끔 산다') 질량 — §4-2 정정 판정 지표."""
    return mass(r["C2_dist"], 0) + mass(r["C2_dist"], 1)


def c2_ord(r):
    """순서점수(꼭1·가끔0.5·유지0) — 보조 병기(등급 무관)."""
    return wmean(r["C2_dist"], [1.0, 0.5, 0.0])


def d1a(r):
    return statistics.mean(r[f"buy_{v}"] for v in D1P) / 10.0


def b3_auth(r):
    return mass(r["B3_dist"], B3_IDX_AUTH)


def e1_na_ga(r):
    return mass(r["E1_dist"], 1) - mass(r["E1_dist"], 0)


def load_context(run_id):
    """단일/멀티 자동 판별. 반환 (mode, seed, meta{pid:row}, lat{pid:row})."""
    def rd(name):
        try:
            return json.load(open(f"{SP}/{name}", encoding="utf-8"))
        except Exception:
            return None
    mcfg = rd("multipool_cfg.json")
    if mcfg:
        meta = {m["pid"]: m for m in rd("multipool_meta.json") or []}
        lat = {a["pid"]: a for a in rd("multipool_args.json") or []}
        return "multi", mcfg["SAMPLE_SEED"], meta, lat, mcfg
    scfg = rd("run_cfg.json")
    if scfg:
        meta = {m["pid"]: m for m in rd("pool_meta.json") or []}
        lat = {a["pid"]: a for a in rd("prof.json") or []}
        return "single", scfg.get("RUN_SEED") or scfg.get("SAMPLE_SEED"), meta, lat, scfg
    raise SystemExit(f"[v3_analyze] 풀 설정 파일 없음: {SP}")


def load_rows(run_id):
    rows = {}
    for line in open(f"{BASE}/{run_id}/journal.jsonl", encoding="utf-8"):
        o = json.loads(line)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
            rows[r["pid"]] = r
    return rows


def judge_block(rows, base, seed):
    """한 풀(또는 통합)의 주판정 4개 + 보조 관찰."""
    seg = [p for p in base if pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"], seed) == 2]
    non = [p for p in base if p not in set(seg)]
    out = {"n": len(base), "n_seg": len(seg), "n_non": len(non), "judgments": {}, "aux": {}}
    if not seg or not non:
        out["error"] = "세그 한쪽이 빔 — 판정 불가"
        return out

    def delta(fn, S=seg, N=non):
        return statistics.mean(fn(rows[p]) for p in S) - statistics.mean(fn(rows[p]) for p in N)

    # #1 ΔB1 음
    out["judgments"]["B1"] = {"delta": round(delta(b1m), 3), "expect": "음", "tier": TIER["B1"]}
    # #2 ΔC2 양 — C1 실현 '이런 맛 안 찾음' 제외 조건부
    segc = [p for p in seg if pick(rows[p]["C1_dist"], 5, p, SALT["C1"], seed) != C1_IDX_NOSEEK]
    nonc = [p for p in non if pick(rows[p]["C1_dist"], 5, p, SALT["C1"], seed) != C1_IDX_NOSEEK]
    if segc and nonc:
        out["judgments"]["C2"] = {"delta": round(delta(c2_binary, segc, nonc), 3),
                                  "expect": "양", "tier": TIER["C2"],
                                  "n_seg_cond": len(segc), "n_non_cond": len(nonc),
                                  "metric": "이진 구매율(꼭+가끔 질량) — §4-2 정정"}
        out["aux"]["C2_순서점수_delta(병기)"] = round(delta(c2_ord, segc, nonc), 3)
    else:
        out["judgments"]["C2"] = {"delta": None, "expect": "양", "tier": TIER["C2"],
                                  "note": "조건부 표본 부족"}
    # #3 ΔD1 양
    out["judgments"]["D1"] = {"delta": round(delta(d1a), 3), "expect": "양", "tier": TIER["D1"]}
    # #4 B3 비대칭(세그 < 비기피 → delta 음)
    out["judgments"]["B3"] = {"delta": round(delta(b3_auth), 3), "expect": "음(세그<비기피)",
                              "tier": TIER["B3"],
                              "seg_pct": round(statistics.mean(b3_auth(rows[p]) for p in seg) * 100, 1),
                              "non_pct": round(statistics.mean(b3_auth(rows[p]) for p in non) * 100, 1)}
    # 보조 관찰
    grp = {0: [], 1: [], 2: []}
    for p in base:
        grp[pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"], seed)].append(p)
    dose = {A2c[k]: (round(statistics.mean(b1m(rows[p]) for p in g), 2) if g else None)
            for k, g in grp.items()}
    vals = [v for v in dose.values() if v is not None]
    out["aux"]["dose_B1"] = dose
    out["aux"]["dose_매우최저"] = (dose.get("매우") is not None and vals and dose["매우"] == min(vals))
    out["aux"]["E1_나-가_delta"] = round(delta(e1_na_ga), 3)
    out["aux"]["E1_세그_나질량%"] = round(statistics.mean(mass(rows[p]["E1_dist"], 1) for p in seg) * 100, 1)
    out["aux"]["E1_비기피_나질량%"] = round(statistics.mean(mass(rows[p]["E1_dist"], 1) for p in non) * 100, 1)
    return out


def passed(key, delta):
    if delta is None:
        return None
    return delta < 0 if key in ("B1", "B3") else delta > 0


def main():
    ap = argparse.ArgumentParser(description="v3-sim 적합 판정(SPEC_V3 §4·§5)")
    ap.add_argument("run_id")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    mode, seed, meta, lat, cfg = load_context(a.run_id)
    rows = load_rows(a.run_id)
    print("=" * 78)
    print(f"v3-sim 적합 판정  RUNID={a.run_id}  mode={mode}  N={len(rows)}  seed={seed}")
    print(f"⚠ {LABEL}")
    print("=" * 78)
    if not rows:
        print("결과 없음(진행 중).")
        return

    tgt = [p for p in rows if meta.get(p, {}).get("is_target")]
    pools = sorted({p // 1000 for p in rows}) if mode == "multi" else [0]
    res = {"run_id": a.run_id, "mode": mode, "seed": seed, "N": len(rows), "n_target": len(tgt),
           "label": LABEL, "coupling": (cfg or {}).get("coupling"), "per_pool": {}, "integrated": None}

    if mode == "multi":
        for k in pools:
            base = [p for p in tgt if p // 1000 == k]
            res["per_pool"][f"pool{k}"] = judge_block(rows, base, seed)
    res["integrated"] = judge_block(rows, tgt, seed)

    # ── 판정표 출력 (§8: 항목별 창발 등급 컬럼 필수) ──
    integ = res["integrated"]
    print(f"\n[통합] 타깃 n={integ['n']} (세그 {integ['n_seg']} / 비기피 {integ['n_non']})")
    print(f"\n{'판정':6s} {'지표':28s} {'통합Δ':>8s} {'기대':16s} {'풀부호':10s} {'통과':6s} 창발 등급")
    print("-" * 100)
    order = [("#1", "B1", "ΔB1(가중평균)"), ("#2", "C2", "ΔC2(이진 구매율·조건부)"),
             ("#3", "D1", "ΔD1(총수용 정규화)"), ("#4", "B3", "B3 '진짜 팟타이 아닐것' 질량")]
    n_pass = 0
    pass_map = {}
    for tag, key, nm in order:
        j = integ["judgments"].get(key, {})
        d = j.get("delta")
        ok_int = passed(key, d)
        signs = []
        if mode == "multi":
            for k in pools:
                pj = res["per_pool"][f"pool{k}"]["judgments"].get(key, {})
                pd_ = pj.get("delta")
                signs.append("—" if pd_ is None else ("−" if pd_ < 0 else "+"))
            want = "−" if key in ("B1", "B3") else "+"
            pool_ok = signs.count(want) >= 2
        else:
            pool_ok = None
        ok = bool(ok_int) and (pool_ok is not False if mode == "multi" else True) \
            if ok_int is not None else None
        if mode == "multi":
            ok = bool(ok_int) and bool(pool_ok)
        pass_map[key] = ok
        if ok:
            n_pass += 1
        print(f"{tag:6s} {nm:28s} {('—' if d is None else f'{d:+.3f}'):>8s} {j.get('expect',''):16s} "
              f"{''.join(signs) if signs else 'n/a':10s} {('통과' if ok else '미달' if ok is not None else '불가'):6s} {j.get('tier','')}")

    res["pass_map"] = pass_map
    res["n_pass"] = n_pass

    if mode == "multi":
        b3_ok = bool(pass_map.get("B3"))
        grade = ("완전 적합" if n_pass == 4 else
                 "부분 적합(구조 지지)" if n_pass == 3 and b3_ok else
                 "부분 적합(주변부만) — 2요인의 핵심 창발 미달" if n_pass == 3 else
                 "부적합")
        res["grade"] = grade
        res["variant_run_allowed"] = grade in ("완전 적합", "부분 적합(구조 지지)")
        res["null_rate"] = {"판정당": NULL_RATE["판정당"],
                            "이 등급": NULL_RATE.get(grade),
                            "구조지지이상": NULL_RATE["구조지지이상"]}
        res["v23_baseline"] = V23_BASELINE
        print(f"\n▶ 적합 등급(§5): **{grade}**  ({n_pass}/4, B3 {'포함' if b3_ok else '탈락'})")
        print(f"  └ 널 도달 확률(§8 의무 공시): 이 등급 {NULL_RATE.get(grade, float('nan'))*100:.1f}% · "
              f"판정당 {NULL_RATE['판정당']*100:.1f}% · 구조지지 이상 {NULL_RATE['구조지지이상']*100:.1f}%")
        print(f"  └ {V23_BASELINE} — 등급은 단독이 아니라 이 기준선과의 차이로 해석(§8)")
        print(f"▶ 카피 변형 런 진행 조건(부분 적합(구조 지지) 이상): "
              f"{'충족' if res['variant_run_allowed'] else '미충족 → 변형 런 미집행'}")
    else:
        obs = sum(1 for k in pass_map if pass_map[k])
        res["gate_directions_observed"] = obs
        res["gate_pass"] = obs >= 2
        res["null_rate"] = {"게이트(방향≥2/4)": NULL_RATE["게이트"]}
        print(f"\n▶ §6 비용 게이트(단일풀 — 등급 판정 아님): 방향 관측 {obs}/4 → "
              f"{'멀티풀 진행' if obs >= 2 else '조기중단 — 부적합(단일풀 조기중단) 보고'}")
        print(f"  └ 널 도달 확률(§8 의무 공시): 게이트 통과 {NULL_RATE['게이트']*100:.1f}% "
              f"(단일풀은 풀 부호 조건이 없어 판정당 50%) — 게이트는 증거가 아니라 비용 통제다")

    print("\n[보조 관찰 — 등급 무관·기록]")
    for k, v in integ["aux"].items():
        print(f"  {k}: {v}")

    print("\n[해석 규율] #2·#3은 결합의 보정 원천이 판정 대상 자신이라 '전파 확인(부분 순환)'이며,")
    print("  #1은 '좁은 창발'(경험평가→첫인상 1단계), #4만 '순수 창발'이다(§4 3계층).")
    print("  부적합 시 '구조 실패'와 '감쇠로 인한 검정력 부족'은 구분 불가 — 감쇠 병기, 재실행 사유 아님(§8).")

    if a.json:
        json.dump(res, open(a.json, "w"), ensure_ascii=False, indent=1)
        print(f"\n[JSON] {a.json}")


if __name__ == "__main__":
    main()
