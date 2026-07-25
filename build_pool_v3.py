#!/usr/bin/env python3
"""v3-sim 2요인 페르소나 풀 생성 (SPEC_V3 §2 · 부록 A A11 확정 파라미터).

기존 계보 무수정 원칙: sim/sampler.py·sim/config.py는 **건드리지 않는다**.
sampler.build_pool()로 v1.5 인구·9 latent를 그대로 얻은 뒤, 신규 2요인을
페르소나별 결정론 RNG로 **사후 부여**한다(선형 조건부 시프트).

  경험평가(과거경험부정) = clip( N(0.36, 0.35) + 0.56 × (향기피 − 0.5) )
  해결지향              = clip( N(0.50, 0.22) + 0.17 × (향기피 − 0.5) )

β는 파일럿 실측(N=88)에서 도출 — 부록 A A3/A11. 주변분포 근거도 A11 참조
(해결지향은 §3에서 C2·D1 수준이 이미 주입되므로 중립 특성 prior 사용).

출력(기존 파일 계약 유지 → runner.py·분석기 호환):
  --pools 1  → runs/v3pool_<seed>/{prof.json, pool_meta.json, run_cfg.json}
  --pools >1 → runs/v3multi_<sample_seed>/{multipool_args.json, multipool_meta.json,
                                            multipool_cfg.json}
사용: python3 build_pool_v3.py --seed S [--n 50] [--pools 1|3]
"""
import argparse
import json
import os
import random

import numpy as np

from harness_paths import SP, run_dir
import sim.config as C
from sim import sampler

# ── 부록 A A11 확정 파라미터 (변경 시 부록 A와 동기 필수) ──
BETA_EXP = 0.56                  # 향기피 → 경험평가 (A1 유래 · CI [0.334,0.778])
BETA_SOL = 0.17                  # 향기피 → 해결지향 (C2이진·D1 복합 · CI [0.059,0.285])
BASE_EXP = (0.36, 0.35)          # 경험평가 base (실측 A1 주변분포 분산분해)
BASE_SOL = (0.50, 0.22)          # 해결지향 base (중립 특성 prior — A11-1 근거)
SALT_EXP, SALT_SOL = 70, 71      # 신규 salt(기존 40~60·1~3·51 미충돌 — INVENTORY §4f)

AGE_LBL = {"19-24": "만 19–24", "25-29": "만 25–29", "30-34": "만 30–34",
           "35-39": "만 35–39", "40+": "40세 이상"}
STAT_LBL = {"직장인": "직장인", "대학원생": "대학(원)생",
            "자영업·프리랜서": "자영업·프리랜서", "기타": "기타"}
RES_LBL = {"1인가구": "1인 가구(자취)", "2인가구": "2인 가구",
           "가족거주": "가족과 거주", "기숙사": "기숙사"}
S4_LBL = {"0회": "0회", "1-2회": "1–2회", "3-5회": "3–5회", "6+회": "6회 이상"}
S5_LBL = {"있다": "있다", "없다": "없다"}


def lvl(x):
    """wf_vs_v3.js의 lvl()과 동일 임계 — 버킷 분포 진단용(출처 wf_vs_v23.js:29)."""
    return ("매우높음" if x > 0.75 else "높음" if x > 0.58 else
            "보통" if x > 0.42 else "낮음" if x > 0.25 else "매우낮음")


def add_v3_latents(pool, pool_seed):
    """신규 2요인을 페르소나별 결정론으로 부여(sim/* 무수정)."""
    for p in pool:
        sa = p.latent["spice_aversion"]
        re = np.random.default_rng([pool_seed, p.pid, SALT_EXP])
        rs = np.random.default_rng([pool_seed, p.pid, SALT_SOL])
        exp = float(re.normal(*BASE_EXP)) + BETA_EXP * (sa - 0.5)
        sol = float(rs.normal(*BASE_SOL)) + BETA_SOL * (sa - 0.5)
        p.latent["past_experience_negativity"] = float(np.clip(exp, 0.0, 1.0))
        p.latent["solution_orientation"] = float(np.clip(sol, 0.0, 1.0))
    return pool


def args_row(p, gid):
    L = p.latent
    return {
        "pid": gid,
        "S1": AGE_LBL[p.S1_age], "S2": STAT_LBL[p.S2_status], "S3": RES_LBL[p.S3_residence],
        "S4": S4_LBL[p.S4_freq], "S5": S5_LBL[p.S5_travel],
        "향기피": round(L["spice_aversion"], 3), "매실청": round(L["plum_familiarity"], 3),
        "관여": round(L["involvement"], 3), "회의": round(L["skepticism"], 3),
        "가격민감": round(L["price_sensitivity"], 3), "접근성": round(L["access_barrier"], 3),
        "정통기대": round(L["authenticity_goal"], 3), "식사량": round(L["portion_expect"], 3),
        "카테고리빈도": round(L["category_frequency"], 3),
        # ── v3 신규 2요인 ──
        "과거경험부정": round(L["past_experience_negativity"], 3),
        "해결지향": round(L["solution_orientation"], 3),
    }


def diagnose(rows, label):
    """LLM 없이 주입 검증: 결합 상관·버킷 분포. 부록 A A5-2의 감쇠 예상과 대조용."""
    sa = np.array([r["향기피"] for r in rows])
    ex = np.array([r["과거경험부정"] for r in rows])
    so = np.array([r["해결지향"] for r in rows])
    print(f"\n[{label} 주입 검증 n={len(rows)}]")
    print(f"  향기피 μ={sa.mean():.3f} σ={sa.std(ddof=1):.3f}")
    for nm, v, b in (("과거경험부정", ex, BETA_EXP), ("해결지향", so, BETA_SOL)):
        r = float(np.corrcoef(sa, v)[0, 1])
        print(f"  {nm}: μ={v.mean():.3f} σ={v.std(ddof=1):.3f}  corr(향기피)={r:+.3f} "
              f"(β={b} 주입 → 이론 r≈{b*sa.std(ddof=1)/v.std(ddof=1):+.3f})")
        from collections import Counter
        c = Counter(lvl(x) for x in v)
        print(f"     lvl 버킷: {dict(c)}")
    # 향기피 상·하 3분위 간 신규 요인 격차(= 시뮬 내 세그 격차의 상한 근사)
    q1, q3 = np.quantile(sa, [1 / 3, 2 / 3])
    hi, lo = sa >= q3, sa <= q1
    print(f"  향기피 상3분위−하3분위 격차: 과거경험부정 {ex[hi].mean()-ex[lo].mean():+.3f} · "
          f"해결지향 {so[hi].mean()-so[lo].mean():+.3f}")


def main():
    ap = argparse.ArgumentParser(description="v3-sim 2요인 풀 생성")
    ap.add_argument("--seed", type=int, default=None, help="마스터 시드(미지정 시 os.urandom)")
    ap.add_argument("--n", type=int, default=50, help="풀당 표본크기(기본 50)")
    ap.add_argument("--pools", type=int, default=1, help="풀 수(1=단일, 3=멀티풀)")
    a = ap.parse_args()

    master = a.seed
    if master is not None:
        mr = random.Random(master)
        pool_seeds = [mr.randint(10_000_000, 99_999_999) for _ in range(a.pools)]
        sample_seed = mr.randint(10_000_000, 99_999_999)
    else:
        pool_seeds = [int.from_bytes(os.urandom(4), "big") % 90_000_000 + 10_000_000
                      for _ in range(a.pools)]
        sample_seed = int.from_bytes(os.urandom(4), "big") % 90_000_000 + 10_000_000

    all_args, all_meta, cfg_pools = [], [], []
    for k, seed in enumerate(pool_seeds):
        save = C.GLOBAL_SEED
        C.GLOBAL_SEED = seed
        try:
            pool = sampler.build_pool(a.n)
        finally:
            C.GLOBAL_SEED = save              # 전역상태 복원(P0-5 관용구)
        add_v3_latents(pool, seed)
        s = sampler.summarize(pool)
        cfg_pools.append({"pool": k, "seed": seed, "N": a.n,
                          "target": s["n_target(§3-1)"], "target_rate": s["target_rate"]})
        print(f"[풀{k}] seed={seed} N={a.n} 타깃={s['n_target(§3-1)']}({s['target_rate']*100:.0f}%)")
        for p in pool:
            gid = k * 1000 + p.pid if a.pools > 1 else p.pid
            all_args.append(args_row(p, gid))
            row = p.row()
            row["pid"] = gid
            if a.pools > 1:
                row["pool"] = k
            all_meta.append(row)

    cfg = {"engine": "v3-sim", "pools": cfg_pools, "N_PER": a.n, "N_POOLS": a.pools,
           "master_seed": master, "SAMPLE_SEED": sample_seed,
           "coupling": {"BETA_EXP": BETA_EXP, "BETA_SOL": BETA_SOL,
                        "BASE_EXP": BASE_EXP, "BASE_SOL": BASE_SOL,
                        "SALT_EXP": SALT_EXP, "SALT_SOL": SALT_SOL,
                        "source": "SPEC_V3_부록A.md A11 (파일럿 N=88 도출)"}}

    if a.pools > 1:
        pool_id = f"v3multi_{sample_seed}"
        files = {"multipool_args.json": all_args, "multipool_meta.json": all_meta,
                 "multipool_cfg.json": cfg}
    else:
        pool_id = f"v3pool_{pool_seeds[0]}"
        cfg["N"] = a.n
        cfg["RUN_SEED"] = pool_seeds[0]
        files = {"prof.json": all_args, "pool_meta.json": all_meta, "run_cfg.json": cfg}

    for d in (SP, run_dir(pool_id, create=True)):
        os.makedirs(d, exist_ok=True)
        for fn, obj in files.items():
            json.dump(obj, open(f"{d}/{fn}", "w"), ensure_ascii=False)

    diagnose(all_args, "전체")
    print(f"\n총 {len(all_args)}명 ({a.pools}풀×{a.n}) → runs/{pool_id}/  "
          f"[{' · '.join(files)}]")
    print(f"결합: β_exp={BETA_EXP} β_sol={BETA_SOL} (부록 A A11) · SAMPLE_SEED={sample_seed}")


if __name__ == "__main__":
    main()
