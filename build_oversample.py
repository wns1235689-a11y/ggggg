#!/usr/bin/env python3
"""
향기피 세그 오버샘플 — 층2("매실청은 좁고 깊다") 검정용.
지금까지 향기피 유병률을 자연치(~10%)로 두어 세그 n<10(검정 불가)였음.
이 표본은 spice_aversion을 상향 + access_barrier 하향으로 A2 향기피(①②)를
유효 타깃의 ≥40%가 되도록 쿼터. 향기피↔매실청 '정렬'은 심지 않음(라이브 창발).
※ 대표성 표본 아님 — A2 유병률은 '쿼터'라 해석 금지. 목적은 세그 검정력 확보뿐.
"""
import os, json, random
import numpy as np

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"

seed_entropy = int.from_bytes(os.urandom(8), "big")
meta_rng = random.Random(seed_entropy)
N = 58
RUN_SEED = meta_rng.randint(10_000_000, 99_999_999)

import sim.config as C
C.GLOBAL_SEED = RUN_SEED
# ── 오버샘플 오버라이드: 향기피↑·접근성↓ (A2 1순위 향신료가 접근성에 안 먹히게) ──
C.LATENT_SPECS = dict(C.LATENT_SPECS)
C.LATENT_SPECS["spice_aversion"] = (0.84, 0.20)   # 자연 0.34 → 강상향(향기피 쿼터 구동)
C.LATENT_SPECS["access_barrier"] = (0.26, 0.15)   # 자연 ↓ (접근성이 1순위 독식 방지)
# 매실청·message는 손대지 않음 → 세그의 나 선호는 창발이어야 함(순환 차단)
from sim import sampler

pool = sampler.build_pool(N)

A2_FULL = ["고수 등 향신료 향이 부담스러워서", "피시소스 등 낯선 소스·재료가 부담스러워서",
           "먹을 기회나 파는 곳이 마땅치 않아서", "가격이 부담스러워서",
           "동남아 음식 자체를 즐기지 않아서", "지금도 거리낌 없이 잘 먹는다"]
B2_FULL = ["5분 완조리(간편함)", "외식 대비 가성비", "국산 새우·숙주 등 재료",
           "매실청의 새콤한 맛", "향신료(고수 등) 부담 없음", "사고 싶은 이유 없음"]
B3_FULL = ["맛이 상상이 안 된다", "'진짜 팟타이 맛'이 아닐 것 같다", "냉동식품 품질을 믿기 어렵다",
           "가격이 걱정된다", "양(1인분 300g)이 부족할 것 같다", "팟타이 자체에 관심이 없다",
           "망설여지는 점 없다"]
E1_GA = "사 먹어도 결국 손이 가던 팟타이 — 5분 끝판왕 등장."
E1_NA = "타마린드 없이, 매실청으로 잡은 새콤함 — 부담 없는 진짜 팟타이."
E1_ITEMS = [("가", E1_GA), ("나", E1_NA), ("비슷", "두 문구가 비슷하다"), ("둘다", "둘 다 끌리지 않는다")]


def shuffled(items, pid, salt):
    r = np.random.default_rng([RUN_SEED, pid, salt]); idx = list(range(len(items))); r.shuffle(idx)
    return [items[i] for i in idx]


AGE_LBL = {"19-24": "만 19–24", "25-29": "만 25–29", "30-34": "만 30–34", "35-39": "만 35–39", "40+": "40세 이상"}
STAT_LBL = {"직장인": "직장인", "대학원생": "대학(원)생", "자영업·프리랜서": "자영업·프리랜서", "기타": "기타"}
RES_LBL = {"1인가구": "1인 가구(자취)", "2인가구": "2인 가구", "가족거주": "가족과 거주", "기숙사": "기숙사"}
S4_LBL = {"0회": "0회", "1-2회": "1–2회", "3-5회": "3–5회", "6+회": "6회 이상"}
S5_LBL = {"있다": "있다", "없다": "없다"}


def seg(p):
    return "타깃" if p.is_target else ("확장" if p.is_student_seg else "기타")


prof, meta = [], []
for p in pool:
    L = p.latent
    prof.append({
        "pid": p.pid, "seg": seg(p),
        "S1": AGE_LBL[p.S1_age], "S2": STAT_LBL[p.S2_status], "S3": RES_LBL[p.S3_residence],
        "S4": S4_LBL[p.S4_freq], "S5": S5_LBL[p.S5_travel],
        "향기피": round(L["spice_aversion"], 3), "매실청": round(L["plum_familiarity"], 3),
        "관여": round(L["involvement"], 3), "회의": round(L["skepticism"], 3),
        "가격민감": round(L["price_sensitivity"], 3), "접근성": round(L["access_barrier"], 3),
        "정통기대": round(L["authenticity_goal"], 3), "식사량": round(L["portion_expect"], 3),
        "카테고리빈도": round(L["category_frequency"], 3),
        "A2_order": shuffled(A2_FULL, p.pid, 2), "B2_order": shuffled(B2_FULL, p.pid, 3),
        "B3_order": shuffled(B3_FULL, p.pid, 4),
        "E1_order": [{"tag": t, "text": tx} for t, tx in shuffled(E1_ITEMS, p.pid, 6)],
    })
    meta.append(p.row())

json.dump(prof, open(f"{SP}/prof.json", "w"), ensure_ascii=False)
json.dump(meta, open(f"{SP}/pool_meta.json", "w"), ensure_ascii=False)
json.dump({"N": N, "RUN_SEED": RUN_SEED, "oversample": "spice"}, open(f"{SP}/run_cfg.json", "w"))

s = sampler.summarize(pool)
tgt = [p for p in pool if p.is_target]
# 향기피 성향(latent) 높음 비율 사전확인(A2 실제선택은 설문에서 결정)
hi = sum(1 for p in tgt if p.latent["spice_aversion"] > 0.66)
print(f"N={N} RUN_SEED={RUN_SEED}")
print(f"타깃(§3-1)={len(tgt)}  | 그중 향기피 잠재'높음'={hi}={hi/len(tgt)*100:.0f}% (A2 실제유병은 설문결정)")
print("거주:", s["S3_residence"], "| 빈도:", s["S4_freq"])
