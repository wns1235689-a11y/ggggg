#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로봇 설문 풀 생성 — 도시×거주국×연령 + 노출·지식 상태의 상류 표집.

핵심 규율(config 참조): 노출·지식은 스윕 밴드에서 **여기서(파이썬)** 표집해 페르소나에
사실로 주입한다. LLM은 조건부 행동만 생성 → Q1 수준·채널믹스는 입력 전파로 문서화.

사용: python3 surveys/robot_wc26/build_pool.py [--n 110] [--seed S] [--scenario neutral]
산출: runs/pool_robot_<seed>/ {prof.json, pool_meta.json, run_cfg.json} + SP 사본
     (파일명은 persist_run._POOL_FILES와 동일 — 하니스 영속화 호환)
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)                      # harness_paths 임포트(스크립트 직접 실행 대비)

import numpy as np

import config as C                              # 같은 디렉토리(sys.path[0])
from harness_paths import SP, run_dir

ap = argparse.ArgumentParser(description="로봇 설문 표본 풀 생성")
ap.add_argument("--n", type=int, default=110, help="표본크기(현장 목표 100~150 중앙)")
ap.add_argument("--seed", type=int, default=None, help="RUN_SEED 재주입(미지정 시 os.urandom)")
ap.add_argument("--scenario", default="neutral", choices=list(C.SCENARIOS))
a = ap.parse_args()

SEED = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), "big") % 90_000_000 + 10_000_000
N, SCEN = a.n, a.scenario


def lvl(x):
    return "높음" if x > 0.66 else ("낮음" if x < 0.40 else "보통")


def clip01(v):
    return float(np.clip(v, 0.0, 1.0))


CITY_W = np.array([c[2] for c in C.CITIES], float)
CITY_W = CITY_W / CITY_W.sum()
TO_K = list(C.TOURIST_ORIGIN)
TO_W = np.array([C.TOURIST_ORIGIN[k] for k in TO_K], float)
TO_W = TO_W / TO_W.sum()

EXPO_LBL = {"tv_live": "TV 생중계", "clip_official": "SNS/유튜브 공식 클립(브랜딩 보임)",
            "clip_cropped": "SNS 짧은 클립(재업로드·브랜드 표기 잘림)",
            "news": "뉴스 기사/방송 뉴스", "wom": "지인에게 들음"}
KNOW_LBL = {
    "both": "Boston Dynamics가 만들었고, 그 회사가 Hyundai 소유라는 것까지 안다",
    "bd_only": "만든 회사가 Boston Dynamics라는 건 알지만 소유관계는 모른다(낡은 지식으로 다른 대기업을 떠올릴 수 있음)",
    "hyundai_only": "Hyundai가 이 로봇 행사와 연결된 회사라고 알고 있다(로봇 제작사 이름은 모름)",
    "desc_only": "회사 이름은 못 대지만 '유튜브의 그 유명한 로봇개/파쿠르 로봇 회사'라고 서술로는 안다",
    "none": "제조사 지식 없음(모름 — 단 실제 행인처럼 추측하는 사람은 있을 수 있음)",
}


def sample_persona(pid):
    rng = np.random.default_rng([SEED, pid])
    ci = int(rng.choice(len(C.CITIES), p=CITY_W))
    city, ccountry, _, tshare = C.CITIES[ci]
    tourist = bool(rng.random() < tshare)
    res = TO_K[int(rng.choice(len(TO_K), p=TO_W))] if tourist else ccountry
    age = C.AGE_BANDS[int(rng.choice(3, p=C.AGE_MIX))]

    lat = {k: clip01(rng.normal(mu, sd)) for k, (mu, sd) in C.LATENT_SPECS.items()}
    lat["sns_short_video"] = clip01(lat["sns_short_video"] + C.SNS_AGE_BUMP[age])
    if res == "BE":
        lat["football_interest"] = clip01(lat["football_interest"] + C.FOOTBALL_BE_BUMP)

    # ── 노출 표집 [스윕 밴드 → 상태] ──
    base = C.band(C.Q1_BANDS.get(res, C.Q1_BANDS["OTHER_EU"]), SCEN)
    mult = C.AGE_EXPOSURE_MULT[age] * (0.70 + 0.60 * lat["football_interest"]) \
        * (0.88 + 0.24 * lat["sns_short_video"])
    p_exp = min(base * mult, C.EXPOSURE_P_CAP)
    exposed = bool(rng.random() < p_exp)
    conflated = False
    if not exposed and rng.random() < C.band(C.CONFLATED_FALSE_Y, SCEN):
        exposed, conflated = True, True          # Spot 순찰·로봇뉴스와 혼동한 희미한 Y
    strength = None
    channel = None
    if exposed:
        strength = "faint" if (conflated or rng.random() < C.FAINT_SHARE) else "clear"
        p_tv = C.band(C.CHANNEL_TV_LIVE, SCEN)
        w = dict(C.CHANNEL_BASE_W)
        w["news"] *= C.NEWS_W_MULT.get(res, 1.0)
        w["clip"] *= (0.80 + 0.50 * lat["sns_short_video"])
        tot = sum(w.values())
        probs = [p_tv] + [(1 - p_tv) * v / tot for v in (w["clip"], w["news"], w["wom"])]
        ch = ["tv_live", "clip", "news", "wom"][int(rng.choice(4, p=np.array(probs) / sum(probs)))]
        if ch == "clip":
            ch = "clip_official" if rng.random() < C.band(C.CLIP_OFFICIAL_SHARE, SCEN) else "clip_cropped"
        channel = ch

    # ── 지식 표집 [근사/스윕 밴드 → 상태] ──
    know = "none"
    if exposed and not conflated:
        tech_lv = "high" if lat["tech_news"] > 0.66 else ("low" if lat["tech_news"] < 0.40 else "mid")
        p_bd = min(C.band(C.P_BD_NAME, SCEN) * C.TECH_BD_MULT[tech_lv]
                   * C.CHANNEL_BD_MULT[channel], C.P_BD_CAP)
        p_hy = C.band(C.P_HYUNDAI_CH[channel], SCEN)
        if lat["football_interest"] > 0.5 and lat["sponsor_knowledge"] > 0.5:
            p_hy = min(p_hy + C.band(C.P_SPONSOR_INFER, SCEN), 0.5)
        bd = rng.random() < p_bd
        hy = rng.random() < p_hy
        if bd and hy:
            know = "both"
        elif bd:
            know = "bd_only"
        elif hy:
            know = "hyundai_only"
        elif rng.random() < C.band(C.P_DESC_ONLY, SCEN):
            know = "desc_only"
    elif conflated:
        # 혼동층 지식 [근사·감사3 §8]: EU Spot 기사 다수가 현대/BD 명시 → '우연 정답' 경로 포함
        kk = list(C.CONFLATED_KNOW_W)
        kw = np.array([C.CONFLATED_KNOW_W[k] for k in kk])
        know = kk[int(rng.choice(len(kk), p=kw / kw.sum()))]

    # Q3 성향(국가 앵커 + 연령 오프셋 + 개인 노이즈) — 성향 라벨만 프롬프트에 주입
    e, w_, m = C.Q3_CENTERS.get(res, C.Q3_CENTERS["_default"])
    de, dw = C.AGE_Q3_OFFSET[age]
    tri = np.clip([e + de + rng.normal(0, 0.06), w_ + dw + rng.normal(0, 0.06),
                   m + rng.normal(0, 0.06)], 0.02, None)
    tri = tri / tri.sum()
    senti = ["기대 쪽", "우려 쪽", "혼합(양가) 쪽"][int(np.argmax(tri))]

    meta_p_exposed = min(base * mult, C.EXPOSURE_P_CAP)   # 드리프트 체크용 기대확률(P2-08)
    prof = {
        "pid": pid, "도시": city, "도시국가": ccountry, "거주국": res,
        "관광객": tourist, "연령대": age,
        "축구관심": lvl(lat["football_interest"]), "숏폼SNS": lvl(lat["sns_short_video"]),
        "기술뉴스관심": lvl(lat["tech_news"]), "로봇정서성향": senti,
        "노출": ({"상태": "노출됨", "강도": ("선명" if strength == "clear" else "희미(스치듯·오래전)"),
                 "경로": EXPO_LBL[channel]} if exposed else {"상태": "비노출"}),
        "지식상태": KNOW_LBL[know],
        "혼동주의": conflated,
    }
    meta = {
        "pid": pid, "city": city, "city_country": ccountry, "res_country": res,
        "tourist": tourist, "age": age,
        "latent": {k: round(v, 3) for k, v in lat.items()},
        "q3_tri": [round(float(x), 3) for x in tri],
        "exposed": exposed, "strength": strength, "channel": channel,
        "conflated": conflated, "knowledge": know,
        "p_exposed": round(meta_p_exposed, 4),   # 기대확률(드리프트 z-체크·관측공간 파생용)
    }
    return prof, meta


profs, metas = [], []
for pid in range(N):
    p, m = sample_persona(pid)
    profs.append(p)
    metas.append(m)

pool_id = f"pool_robot_{SEED}"


def _sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def _git_head():
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_REPO,
                              capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


# 봉인 무결성(P4-02): 어떤 config·wf로 생성된 풀인지 해시로 박제
cfg = {"N": N, "RUN_SEED": SEED, "survey_id": "robot_wc26", "scenario": SCEN,
       "config_sha256_16": _sha(os.path.join(_HERE, "config.py")),
       "wf_sha256_16": _sha(os.path.join(_HERE, "wf_robot.js")),
       "git_head": _git_head()}
for d in (SP, run_dir(pool_id, create=True)):
    os.makedirs(d, exist_ok=True)
    json.dump(profs, open(f"{d}/prof.json", "w"), ensure_ascii=False)
    json.dump(metas, open(f"{d}/pool_meta.json", "w"), ensure_ascii=False)
    json.dump(cfg, open(f"{d}/run_cfg.json", "w"), ensure_ascii=False)

n_exp = sum(m["exposed"] for m in metas)
n_conf = sum(m["conflated"] for m in metas)
by_know = {}
for m in metas:
    by_know[m["knowledge"]] = by_know.get(m["knowledge"], 0) + 1
by_ctry = {}
for m in metas:
    by_ctry[m["res_country"]] = by_ctry.get(m["res_country"], 0) + 1
print(f"N={N}  RUN_SEED={SEED}  scenario={SCEN}  pool_id={pool_id}")
print(f"노출={n_exp}/{N} ({n_exp/N*100:.0f}%)  혼동오탐={n_conf}  [입력 전파 — 측정 아님]")
print(f"지식상태: {by_know}")
print(f"거주국: {dict(sorted(by_ctry.items(), key=lambda kv: -kv[1]))}")
ch = {}
for m in metas:
    if m["channel"]:
        ch[m["channel"]] = ch.get(m["channel"], 0) + 1
print(f"경로(노출자): {ch}")
