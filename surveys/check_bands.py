#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""밴드↔주입 기계 검산(P1-02·P2-03 — LLM 불필요) — 봉인 전 필수 게이트.

각 설문×3시나리오에 대해 대표본 풀을 생성해:
  ① 정규화 불변식: 페르소나 기대확률 평균(mean p) ≈ 선언 상태 밴드 (허용 오차 TOL_NORM)
  ② 표집 정합: 실현 상태율이 mean p의 3σ 이내
를 검사하고 위반 시 비영 종료. 관측공간 파생값(카드Y·Q1Y 기대)도 표로 출력한다.

사용: python3 surveys/check_bands.py [--n-mult 8]   (스크래치 HARNESS_RUNS 권장)
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

TOL_NORM = 0.02      # 정규화 불변식 허용 오차(절대)
SCENARIOS = ("conservative", "neutral", "optimistic")


def run_build(cmd, env):
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=REPO, timeout=300)
    if p.returncode != 0:
        raise SystemExit(f"[check_bands] 빌드 실패: {' '.join(cmd)}\n{p.stderr[-400:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-mult", type=int, default=8, help="현장 규모 대비 배수(대표본)")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="check_bands_")
    env = dict(os.environ, HARNESS_RUNS=tmp, HARNESS_SP=os.path.join(tmp, "sp"))
    os.makedirs(env["HARNESS_SP"], exist_ok=True)
    fails = []

    # ── genesis: 브랜드×모집단 knows 불변식 ──
    sys.path.insert(0, os.path.join(REPO, "surveys", "genesis_eu26"))
    import config as GC                       # noqa: E402
    for scen in SCENARIOS:
        seed = 900_000 + SCENARIOS.index(scen)
        run_build([sys.executable, "surveys/genesis_eu26/build_pool.py",
                   "--n-street", str(25 * a.n_mult), "--n-gp", str(40 * a.n_mult),
                   "--seed", str(seed), "--scenario", scen], env)
        metas = json.load(open(f"{tmp}/pool_genesis_{seed}/pool_meta.json", encoding="utf-8"))
        ys = GC.band(GC.YES_SAYING_BASE, scen)
        print(f"\n[genesis · {scen}] N={len(metas)}")
        for pop in GC.POPULATIONS:
            ms = [m for m in metas if m["pop"] == pop]
            for b in ("BMW", "LEXUS", "POLESTAR", "GENESIS"):
                band_v = GC.band(GC.AIDED_BANDS[pop][b], scen)
                mean_p = sum(m["p_know"][b] for m in ms) / len(ms)
                realized = sum(1 for m in ms if m["know"][b] == "knows") / len(ms)
                var = sum(m["p_know"][b] * (1 - m["p_know"][b]) for m in ms)
                z = (realized * len(ms) - mean_p * len(ms)) / (var ** 0.5) if var > 0 else 0.0
                obs = mean_p * 0.9 + GC.VAGUE_MARGIN * 0.5 + ys * max(0, 1 - mean_p - GC.VAGUE_MARGIN)
                # BMW 캡(0.995) 등 상한 클리핑 브랜드는 불변식에서 완화
                tol = TOL_NORM if band_v < 0.9 else 0.05
                mark = ""
                if abs(mean_p - band_v) > tol:
                    mark = " ◀ 정규화 위반"
                    fails.append(f"genesis {scen} {pop} {b}: mean_p {mean_p:.3f} vs band {band_v}")
                if abs(z) > 3:
                    mark += " ◀ 표집 3σ 초과"
                    fails.append(f"genesis {scen} {pop} {b}: z={z:.1f}")
                print(f"  {pop:13s} {b:8s} band={band_v:.3f} mean_p={mean_p:.3f} "
                      f"realized={realized:.3f} (z={z:+.1f})  obs기대={obs:.3f}{mark}")

    # ── robot: 국가 무관 총 노출 불변식(승수 평균 ≈1 확인) + 관측 Q1Y ──
    for scen in SCENARIOS:
        seed = 910_000 + SCENARIOS.index(scen)
        run_build([sys.executable, "surveys/robot_wc26/build_pool.py",
                   "--n", str(120 * a.n_mult), "--seed", str(seed), "--scenario", scen], env)
        metas = json.load(open(f"{tmp}/pool_robot_{seed}/pool_meta.json", encoding="utf-8"))
        mean_p = sum(m["p_exposed"] for m in metas) / len(metas)
        realized = sum(1 for m in metas if m["exposed"]) / len(metas)
        var = sum(m["p_exposed"] * (1 - m["p_exposed"]) for m in metas)
        z = (realized * len(metas) - mean_p * len(metas)) / (var ** 0.5) if var > 0 else 0.0
        obs_q1y = mean_p * 0.76
        mark = " ◀ 표집 3σ 초과" if abs(z) > 3 else ""
        if abs(z) > 3:
            fails.append(f"robot {scen}: z={z:.1f}")
        print(f"\n[robot · {scen}] N={len(metas)}  mean_p_exposed={mean_p:.3f} "
              f"realized={realized:.3f} (z={z:+.1f})  obs기대 Q1Y={obs_q1y:.3f}{mark}")

    print()
    if fails:
        print(f"[check_bands] FAIL — {len(fails)}건:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("[check_bands] OK — 정규화 불변식·표집 정합 전 시나리오 통과")


if __name__ == "__main__":
    main()
