#!/usr/bin/env python3
"""
게이트C 신규 표본 생성 — 프로토콜/설문설계 재독 후 '더 정교하게'.
 - N = 50~100 무작위, 신규 RUN_SEED(재현 가능하게 기록)
 - 셔플(ⓢ) 모델링: A2·B2행·B3·E1 옵션을 페르소나별 결정론 순서로 섞어 args에 embed
 - prof.json(워크플로 args) + pool_meta.json(ingest용, 시드 독립) + run_cfg.json 저장
"""
import os, json, random
import numpy as np

from harness_paths import SP

# ── 신규 시드/표본크기(엔트로피 기반, 이후 기록으로 재현) ──
import argparse
_ap = argparse.ArgumentParser(description="게이트C 표본 풀 생성")
_ap.add_argument("--seed", type=int, default=None, help="RUN_SEED 재주입(미지정 시 os.urandom)")
_ap.add_argument("--n", type=int, default=None, help="표본크기 N 지정(미지정 시 44~53 무작위)")
_args = _ap.parse_args()
seed_entropy = int.from_bytes(os.urandom(8), "big")
meta_rng = random.Random(seed_entropy)
N = _args.n if _args.n is not None else meta_rng.randint(44, 53)
RUN_SEED = _args.seed if _args.seed is not None else meta_rng.randint(10_000_000, 99_999_999)

import sim.config as C
C.GLOBAL_SEED = RUN_SEED          # 신규 표본 — 전체 파이프라인이 이 시드로 일관 재현
from sim import sampler

pool = sampler.build_pool(N)

# ── 원 라벨(설문설계 §2 정확 문자열) ──
A2_FULL = ["고수 등 향신료 향이 부담스러워서", "피시소스 등 낯선 소스·재료가 부담스러워서",
           "먹을 기회나 파는 곳이 마땅치 않아서", "가격이 부담스러워서",
           "동남아 음식 자체를 즐기지 않아서", "지금도 거리낌 없이 잘 먹는다"]
B2_FULL = ["5분 완조리(간편함)", "외식 대비 가성비", "국산 새우·숙주 등 재료",
           "매실청의 새콤한 맛", "향신료(고수 등) 부담 없음", "사고 싶은 이유 없음"]
B3_FULL = ["맛이 상상이 안 된다", "'진짜 팟타이 맛'이 아닐 것 같다", "냉동식품 품질을 믿기 어렵다",
           "가격이 걱정된다", "양(1인분 300g)이 부족할 것 같다", "팟타이 자체에 관심이 없다",
           "망설여지는 점 없다"]
# E1: (가)=T1 완성도, (나)=T2 매실청 — 동결 원문. ③④는 자기완결(전체 셔플 대상)
E1_GA = "사 먹어도 결국 손이 가던 팟타이 — 5분 끝판왕 등장."         # T1
E1_NA = "타마린드 없이, 매실청으로 잡은 새콤함 — 부담 없는 진짜 팟타이."  # T2
E1_ITEMS = [("가", E1_GA), ("나", E1_NA), ("비슷", "두 문구가 비슷하다"), ("둘다", "둘 다 끌리지 않는다")]


def shuffled(items, pid, salt):
    """페르소나·문항별 결정론 셔플 순서(재현 가능)."""
    r = np.random.default_rng([RUN_SEED, pid, salt])
    idx = list(range(len(items)))
    r.shuffle(idx)
    return [items[i] for i in idx]


AGE_LBL = {"19-24": "만 19–24", "25-29": "만 25–29", "30-34": "만 30–34",
           "35-39": "만 35–39", "40+": "40세 이상"}
STAT_LBL = {"직장인": "직장인", "대학원생": "대학(원)생", "자영업·프리랜서": "자영업·프리랜서", "기타": "기타"}
RES_LBL = {"1인가구": "1인 가구(자취)", "2인가구": "2인 가구", "가족거주": "가족과 거주", "기숙사": "기숙사"}
S4_LBL = {"0회": "0회", "1-2회": "1–2회", "3-5회": "3–5회", "6+회": "6회 이상"}
S5_LBL = {"있다": "있다", "없다": "없다"}


def seg(p):
    if p.is_target: return "타깃"
    if p.is_student_seg: return "확장"        # v1.5 확장세그(기숙사·저빈도)
    return "기타"


prof, meta = [], []
for p in pool:
    L = p.latent
    # 셔플 순서(문항별 salt 고정)
    a2_order = shuffled(A2_FULL, p.pid, 2)
    b2_order = shuffled(B2_FULL, p.pid, 3)
    b3_order = shuffled(B3_FULL, p.pid, 4)
    e1_order = shuffled(E1_ITEMS, p.pid, 6)
    prof.append({
        "pid": p.pid, "seg": seg(p),
        "S1": AGE_LBL[p.S1_age], "S2": STAT_LBL[p.S2_status], "S3": RES_LBL[p.S3_residence],
        "S4": S4_LBL[p.S4_freq], "S5": S5_LBL[p.S5_travel],
        "향기피": round(L["spice_aversion"], 3), "매실청": round(L["plum_familiarity"], 3),
        "관여": round(L["involvement"], 3), "회의": round(L["skepticism"], 3),
        "가격민감": round(L["price_sensitivity"], 3), "접근성": round(L["access_barrier"], 3),
        "정통기대": round(L["authenticity_goal"], 3), "식사량": round(L["portion_expect"], 3),
        "카테고리빈도": round(L["category_frequency"], 3),
        # 셔플된 표시 순서(원문 문자열) — 워크플로가 이 순서로 제시
        "A2_order": a2_order, "B2_order": b2_order, "B3_order": b3_order,
        "E1_order": [{"tag": t, "text": tx} for t, tx in e1_order],
    })
    meta.append(p.row())  # pid, channel, S1_age..., is_target, is_student_seg, screenout_reason

json.dump(prof, open(f"{SP}/prof.json", "w"), ensure_ascii=False)
json.dump(meta, open(f"{SP}/pool_meta.json", "w"), ensure_ascii=False)
json.dump({"N": N, "RUN_SEED": RUN_SEED}, open(f"{SP}/run_cfg.json", "w"))

s = sampler.summarize(pool)
print(f"N={N}  RUN_SEED={RUN_SEED}")
print(f"타깃(§3-1)={s['n_target(§3-1)']}  학생세그={s['n_student_seg(§3-3)']}  스크린아웃={s['n_screenout']}")
print("연령:", s["S1_age"])
print("거주:", s["S3_residence"])
print("채널:", s["channel"])
print("간편식빈도:", s["S4_freq"])
