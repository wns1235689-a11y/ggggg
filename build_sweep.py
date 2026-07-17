#!/usr/bin/env python3
"""
사전분포 스윕 — 심리 latent를 4개 상반된 인구로 광폭 변주(v1.5 인구프레임 유지).
각 인구가 자기에게 불리한 방향까지 재현하면 robust, 뒤집히면 fragile로 판별하기 위한 표본 생성.
"""
import os, json, random, argparse
import numpy as np

from harness_paths import SP, run_dir
N_PER = 30

import sim.config as C
from sim import sampler

BASE = dict(C.LATENT_SPECS)  # 원본 사전분포 보존

# (mean, sd) 오버라이드 — 심리 성향만. 인구(거주/빈도) 프레임은 v1.5 그대로.
SWEEPS = {
    0: ("매실청군", {
        "spice_aversion": (0.65, 0.20), "plum_familiarity": (0.72, 0.20),
        "message_orientation": (0.68, 0.20), "sauce_barrier": (0.60, 0.20)}),
    1: ("간편완성도군", {
        "involvement": (0.72, 0.20), "category_frequency": (0.72, 0.20),
        "plum_familiarity": (0.35, 0.20), "spice_aversion": (0.30, 0.20),
        "message_orientation": (0.30, 0.20)}),
    2: ("저접근장벽군", {"access_barrier": (0.25, 0.18)}),
    3: ("평탄무정보군", {
        "spice_aversion": (0.5, 0.30), "plum_familiarity": (0.5, 0.30),
        "access_barrier": (0.5, 0.30), "involvement": (0.5, 0.30),
        "message_orientation": (0.5, 0.30), "category_frequency": (0.5, 0.30),
        "quality_trust": (0.5, 0.30)}),
}

AGE_LBL = {"19-24": "만 19–24", "25-29": "만 25–29", "30-34": "만 30–34",
           "35-39": "만 35–39", "40+": "40세 이상"}
STAT_LBL = {"직장인": "직장인", "대학원생": "대학(원)생", "자영업·프리랜서": "자영업·프리랜서", "기타": "기타"}
RES_LBL = {"1인가구": "1인 가구(자취)", "2인가구": "2인 가구", "가족거주": "가족과 거주", "기숙사": "기숙사"}
S4_LBL = {"0회": "0회", "1-2회": "1–2회", "3-5회": "3–5회", "6+회": "6회 이상"}
S5_LBL = {"있다": "있다", "없다": "없다"}


def seg(p):
    if p.is_target: return "타깃"
    if p.is_student_seg: return "확장"
    return "기타"


_ap = argparse.ArgumentParser(description="게이트C 사전분포 스윕 생성")
_ap.add_argument("--seed", type=int, default=None, help="마스터 시드 재주입(cfg별 시드 결정론 파생; 미지정 시 os.urandom)")
_ap.add_argument("--n", type=int, default=None, help="인구당 표본크기 N_PER(미지정 시 30)")
_args = _ap.parse_args()
if _args.n is not None:
    N_PER = _args.n
master = _args.seed if _args.seed is not None else int.from_bytes(os.urandom(8), "big")
mrng = random.Random(master)
seeds = {cfg: mrng.randint(10_000_000, 99_999_999) for cfg in SWEEPS}

combined, meta = [], {}
for cfg, (name, ovr) in SWEEPS.items():
    C.LATENT_SPECS = dict(BASE)
    C.LATENT_SPECS.update(ovr)
    C.GLOBAL_SEED = seeds[cfg]
    pool = sampler.build_pool(N_PER)
    for p in pool:
        L = p.latent
        pid = cfg * 100 + p.pid
        meta[pid] = cfg
        combined.append({
            "pid": pid, "seg": seg(p),
            "S1": AGE_LBL[p.S1_age], "S2": STAT_LBL[p.S2_status], "S3": RES_LBL[p.S3_residence],
            "S4": S4_LBL[p.S4_freq], "S5": S5_LBL[p.S5_travel],
            "향기피": round(L["spice_aversion"], 3), "매실청": round(L["plum_familiarity"], 3),
            "관여": round(L["involvement"], 3), "회의": round(L["skepticism"], 3),
            "가격민감": round(L["price_sensitivity"], 3), "접근성": round(L["access_barrier"], 3),
            "정통기대": round(L["authenticity_goal"], 3), "식사량": round(L["portion_expect"], 3),
            "카테고리빈도": round(L["category_frequency"], 3),
        })

C.LATENT_SPECS = BASE  # 복원
# 런 디렉토리 격리(P0-4): runs/<pool_id>/ 스코프 저장 + SP 사본(하위 호환)
_pool_id = f"sweep_{master}"
_meta_out = {"meta": meta, "seeds": seeds, "names": {c: n for c, (n, _) in SWEEPS.items()},
             "master_seed": master}
for _d in (SP, run_dir(_pool_id, create=True)):
    os.makedirs(_d, exist_ok=True)
    json.dump(combined, open(f"{_d}/sweep_prof.json", "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(_meta_out, open(f"{_d}/sweep_meta.json", "w"), ensure_ascii=False)

from collections import Counter
print(f"총 {len(combined)}명 ({len(SWEEPS)}인구 × {N_PER})  master_seed={master}")
for cfg, (name, _) in SWEEPS.items():
    sub = [p for p in combined if meta[p["pid"]] == cfg]
    def lvl(x): return "높음" if x > 0.66 else ("보통" if x > 0.4 else "낮음")
    mp = np.mean([p["매실청"] for p in sub]); ms = np.mean([p["향기피"] for p in sub])
    ma = np.mean([p["접근성"] for p in sub]); mi = np.mean([p["관여"] for p in sub])
    tgt = sum(1 for p in sub if p["seg"] == "타깃")
    print(f"  cfg{cfg} {name}: 타깃{tgt}/{len(sub)} | 매실청{mp:.2f}·향기피{ms:.2f}·접근성{ma:.2f}·관여{mi:.2f}")
