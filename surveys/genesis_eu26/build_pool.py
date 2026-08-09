#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""제네시스 설문 풀 생성 — 2모집단(로테르담 거리 + GP 팬존)을 한 풀에 담아 격차 판정 가능.

브랜드 인지 상태(knows/vague/no)를 스윕 밴드에서 상류 표집해 주입(입력 전파 규율).
사용: python3 surveys/genesis_eu26/build_pool.py [--n-street 25] [--n-gp 40] [--seed S]
                                                 [--scenario neutral]
산출: runs/pool_genesis_<seed>/ {prof.json, pool_meta.json, run_cfg.json} + SP 사본
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

import numpy as np

import config as C
from harness_paths import SP, run_dir

ap = argparse.ArgumentParser(description="제네시스 설문 표본 풀 생성(2모집단)")
ap.add_argument("--n-street", type=int, default=25, help="로테르담 거리 표본(현장 목표 20~30)")
ap.add_argument("--n-gp", type=int, default=40, help="GP 팬존 표본(현장 목표 30~50)")
ap.add_argument("--n", type=int, default=None, help="총 N 지정 시 6:10 비율로 분할(하니스 호환)")
ap.add_argument("--seed", type=int, default=None)
ap.add_argument("--scenario", default="neutral", choices=list(C.SCENARIOS))
a = ap.parse_args()

SEED = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), "big") % 90_000_000 + 10_000_000
SCEN = a.scenario
if a.n is not None:
    n_street = max(1, round(a.n * 25 / 65))
    n_gp = max(1, a.n - n_street)
else:
    n_street, n_gp = a.n_street, a.n_gp
N = n_street + n_gp

BRANDS = ["BMW", "LEXUS", "POLESTAR", "GENESIS"]
KNOW_LBL = {"knows": "안다(확실히 본 적 있음)", "vague": "어렴풋(본 것 같기도)", "no": "모른다"}


def lvl(x):
    return "높음" if x > 0.66 else ("낮음" if x < 0.40 else "보통")


def clip01(v):
    return float(np.clip(v, 0.0, 1.0))


def pick_w(rng, d):
    ks = list(d)
    w = np.array([d[k] for k in ks], float)
    return ks[int(rng.choice(len(ks), p=w / w.sum()))]


def sample_persona(pid, pop):
    rng = np.random.default_rng([SEED, pid])
    age = C.AGE_BANDS[int(rng.choice(3, p=C.AGE_MIX[pop]))]
    res = pick_w(rng, C.RES_MIX[pop])
    context = pick_w(rng, C.GP_CONTEXTS) if pop == "gp_zandvoort" else "street"
    lat = {k: clip01(rng.normal(*spec[pop])) for k, spec in C.LATENT_SPECS.items()}

    # ── 브랜드별 인지 상태 주입 [스윕 밴드 → knows/vague/no] ──
    know = {}
    for b in BRANDS:
        p = C.band(C.AIDED_BANDS[pop][b], SCEN)
        if b == "POLESTAR":
            p *= (C.POLESTAR_EV_MULT[0] + C.POLESTAR_EV_MULT[1] * lat["ev_interest"])
            p *= C.AGE_MULT["POLESTAR"][age]
            p /= C.MULT_NORM["POLESTAR"][pop]      # 평균 보존(선언 밴드=기대 주입률)
        elif b == "LEXUS":
            p *= C.AGE_MULT["LEXUS"][age]
        elif b == "GENESIS":
            p *= (C.GENESIS_CAR_MULT[0] + C.GENESIS_CAR_MULT[1] * lat["car_interest"])
            if pop == "gp_zandvoort":
                if lat["wec_follow"] > 0.5:
                    p *= C.GENESIS_WEC_MULT
                p *= (C.GENESIS_F1MEDIA_MULT[0] + C.GENESIS_F1MEDIA_MULT[1] * lat["nl_f1_media"])
            p /= C.MULT_NORM["GENESIS"][pop]       # 평균 보존
        p = min(p, 0.995)
        u = rng.random()
        know[b] = "knows" if u < p else ("vague" if u < p + C.VAGUE_MARGIN else "no")

    # 비보조 Genesis 언급(희귀) — 상기하면 카드 인지는 당연히 knows
    unaided_genesis = bool(rng.random() < C.band(C.UNAIDED_GENESIS[pop], SCEN))
    if unaided_genesis:
        know["GENESIS"] = "knows"

    # 마그마(GP 전용·Genesis 인지자 조건부)
    magma, magma_depth = False, None
    if pop == "gp_zandvoort" and know["GENESIS"] in ("knows", "vague"):
        pm = C.band(C.MAGMA_GIVEN_GENESIS_GP, SCEN) * (1.5 if lat["wec_follow"] > 0.5 else 0.7)
        magma = bool(rng.random() < min(pm, 0.9))
        if magma:
            spec_p = C.MAGMA_DEPTH["specific_if_wec"] if lat["wec_follow"] > 0.5 \
                else 1 - C.MAGMA_DEPTH["vague_else"]
            magma_depth = "specific" if rng.random() < spec_p else "vague"

    yes_saying = C.band(C.YES_SAYING_BASE, SCEN)

    prof = {
        "pid": pid, "모집단": ("로테르담 거리(GP 이전)" if pop == "street_rtm" else "잔드보르트 GP(최종회)"),
        "접촉맥락": {"street": "역앞 광장·보행자 거리", "entry_queue": "입장 줄",
                   "exit_queue": "퇴장 줄(레이스 직후·들뜬 상태)"}[context],
        "거주국": res, "연령대": age,
        "자동차관심": lvl(lat["car_interest"]), "EV관심": lvl(lat["ev_interest"]),
        "모터스포츠/WEC": lvl(lat["wec_follow"]), "F1미디어소비": lvl(lat["nl_f1_media"]),
        "프리미엄지향": lvl(lat["premium_affinity"]),
        "브랜드인지(사실)": {b: KNOW_LBL[know[b]] for b in BRANDS},
        "비보조Genesis상기": unaided_genesis,
        "마그마인지(사실)": ({"안다": True, "깊이": magma_depth} if magma else {"안다": False}),
        "예스세잉바닥": yes_saying,
    }
    meta = {
        "pid": pid, "pop": pop, "context": context, "res_country": res, "age": age,
        "latent": {k: round(v, 3) for k, v in lat.items()},
        "know": know, "unaided_genesis": unaided_genesis,
        "magma": magma, "magma_depth": magma_depth, "yes_saying": yes_saying,
    }
    return prof, meta


profs, metas = [], []
pid = 0
for pop, n_pop in (("street_rtm", n_street), ("gp_zandvoort", n_gp)):
    for _ in range(n_pop):
        p, m = sample_persona(pid, pop)
        profs.append(p)
        metas.append(m)
        pid += 1

pool_id = f"pool_genesis_{SEED}"
cfg = {"N": N, "RUN_SEED": SEED, "survey_id": "genesis_eu26", "scenario": SCEN,
       "n_street": n_street, "n_gp": n_gp}
for d in (SP, run_dir(pool_id, create=True)):
    os.makedirs(d, exist_ok=True)
    json.dump(profs, open(f"{d}/prof.json", "w"), ensure_ascii=False)
    json.dump(metas, open(f"{d}/pool_meta.json", "w"), ensure_ascii=False)
    json.dump(cfg, open(f"{d}/run_cfg.json", "w"), ensure_ascii=False)


def kshare(pop, b):
    ms = [m for m in metas if m["pop"] == pop]
    return sum(1 for m in ms if m["know"][b] == "knows") / max(len(ms), 1)


print(f"N={N} (거리 {n_street} + GP {n_gp})  RUN_SEED={SEED}  scenario={SCEN}  pool_id={pool_id}")
for pop in C.POPULATIONS:
    print(f"  {pop}: " + "  ".join(f"{b} {kshare(pop, b)*100:.0f}%" for b in BRANDS) + "  [입력 전파 — 측정 아님]")
n_mag = sum(1 for m in metas if m["magma"])
n_gen_gp = sum(1 for m in metas if m["pop"] == "gp_zandvoort" and m["know"]["GENESIS"] != "no")
print(f"  GP Genesis 인지(knows+vague)={n_gen_gp}  마그마 인지={n_mag}  비보조상기={sum(m['unaided_genesis'] for m in metas)}")
