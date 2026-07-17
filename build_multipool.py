#!/usr/bin/env python3
"""다른 풀 3종(각 N=100) 생성 — 매실청 깊이 반증의 풀-견고성 검정용.
   풀별 상이 시드로 latent 독립. pid를 풀별 오프셋(pool*1000+local)해 전역 유일화.
   출력: multipool_args.json(300, 워크플로), multipool_meta.json, multipool_cfg.json."""
import os, json, random, argparse
import numpy as np

from harness_paths import SP
N_PER = 100
N_POOLS = 3

import sim.config as C
from sim import sampler

# 풀별 시드(엔트로피 기반, 기록으로 재현). 실현표집용 전역시드 1개 별도.
_ap = argparse.ArgumentParser(description="게이트C 다풀 표본 생성")
_ap.add_argument("--seed", type=int, default=None, help="마스터 시드 재주입(풀시드·SAMPLE_SEED 결정론 파생; 미지정 시 os.urandom)")
_ap.add_argument("--n", type=int, default=None, help="풀당 표본크기 N_PER(미지정 시 100)")
_args = _ap.parse_args()
if _args.n is not None:
    N_PER = _args.n
MASTER_SEED = _args.seed
if MASTER_SEED is not None:
    _mrng = random.Random(MASTER_SEED)
    pool_seeds = [_mrng.randint(10_000_000, 99_999_999) for _ in range(N_POOLS)]
    SAMPLE_SEED = _mrng.randint(10_000_000, 99_999_999)
else:
    pool_seeds = [int.from_bytes(os.urandom(4), "big") % 90_000_000 + 10_000_000 for _ in range(N_POOLS)]
    SAMPLE_SEED = int.from_bytes(os.urandom(4), "big") % 90_000_000 + 10_000_000

AGE_LBL = {"19-24": "만 19–24", "25-29": "만 25–29", "30-34": "만 30–34",
           "35-39": "만 35–39", "40+": "40세 이상"}
STAT_LBL = {"직장인": "직장인", "대학원생": "대학(원)생", "자영업·프리랜서": "자영업·프리랜서", "기타": "기타"}
RES_LBL = {"1인가구": "1인 가구(자취)", "2인가구": "2인 가구", "가족거주": "가족과 거주", "기숙사": "기숙사"}
S4_LBL = {"0회": "0회", "1-2회": "1–2회", "3-5회": "3–5회", "6+회": "6회 이상"}
S5_LBL = {"있다": "있다", "없다": "없다"}

args, meta, cfg_pools = [], [], []
for k, seed in enumerate(pool_seeds):
    C.GLOBAL_SEED = seed
    pool = sampler.build_pool(N_PER)
    s = sampler.summarize(pool)
    cfg_pools.append({"pool": k, "seed": seed, "N": N_PER,
                      "target": s["n_target(§3-1)"], "target_rate": s["target_rate"]})
    print(f"[풀{k}] seed={seed} N={N_PER} 타깃={s['n_target(§3-1)']}({s['target_rate']*100:.0f}%) "
          f"거주1인={s['S3_residence'].get('1인가구',0)}")
    for p in pool:
        gid = k * 1000 + p.pid           # 전역 유일 pid
        L = p.latent
        args.append({
            "pid": gid,
            "S1": AGE_LBL[p.S1_age], "S2": STAT_LBL[p.S2_status], "S3": RES_LBL[p.S3_residence],
            "S4": S4_LBL[p.S4_freq], "S5": S5_LBL[p.S5_travel],
            "향기피": round(L["spice_aversion"], 3), "매실청": round(L["plum_familiarity"], 3),
            "관여": round(L["involvement"], 3), "회의": round(L["skepticism"], 3),
            "가격민감": round(L["price_sensitivity"], 3), "접근성": round(L["access_barrier"], 3),
            "정통기대": round(L["authenticity_goal"], 3), "식사량": round(L["portion_expect"], 3),
            "카테고리빈도": round(L["category_frequency"], 3),
        })
        row = p.row()
        row["pid"] = gid
        row["pool"] = k
        meta.append(row)

json.dump(args, open(f"{SP}/multipool_args.json", "w"), ensure_ascii=False)
json.dump(meta, open(f"{SP}/multipool_meta.json", "w"), ensure_ascii=False)
json.dump({"pools": cfg_pools, "SAMPLE_SEED": SAMPLE_SEED, "N_PER": N_PER, "N_POOLS": N_POOLS,
           "master_seed": MASTER_SEED},
          open(f"{SP}/multipool_cfg.json", "w"))
print(f"\n총 {len(args)}명 ({N_POOLS}풀×{N_PER}), SAMPLE_SEED={SAMPLE_SEED}")
print(f"풀 시드: {pool_seeds}")
