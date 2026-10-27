#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""해외 패널 설문 v1.1 §8 '리허설 엔진 lite' — 미국 성인 페르소나 풀 생성 (LLM 불요).

실측 앵커가 없으므로 **사전분포만**(문서 §8: 태국 음식 빈도·고수 기피·집에서 요리·가격 민감·한식 친숙).
모든 수치는 [규범근사] — 미국 패널(Prolific) 모집단의 직접 실측치가 아니다. 엔진 수치는 PT 어디에도 쓰지 않는다.

사용:
  python3 build_us_pool.py [--seed S] [--n N]      (기본 N=50, 시드는 os.urandom → 기록으로 재현)
산출(runs/uspool_<seed>/ + SP 사본):
  prof.json      워크플로 args용 페르소나(영문 라벨 + 5축 0~1 실수 + 인구통계)
  pool_meta.json 진단용 메타(원 latent·범주)
  run_cfg.json   {"N", "RUN_SEED", "pool_kind": "us_lite"}
"""
import os, json, random, argparse
import numpy as np

from harness_paths import SP, run_dir

ap = argparse.ArgumentParser(description="US lite 리허설 페르소나 풀 생성")
ap.add_argument("--seed", type=int, default=None, help="RUN_SEED 재주입(미지정 시 os.urandom)")
ap.add_argument("--n", type=int, default=50, help="표본크기(기본 50, 문서 §8: 50~100)")
args = ap.parse_args()
_entropy = int.from_bytes(os.urandom(8), "big")
RUN_SEED = args.seed if args.seed is not None else random.Random(_entropy).randint(10_000_000, 99_999_999)
N = args.n

# ─────────────────────────────────────────────────────────────────────────
# 사전분포 [규범근사] — Prolific 미국 패널은 일반 인구보다 젊고 도시·교외 비중이 높다.
# ─────────────────────────────────────────────────────────────────────────
US_PRIORS = {
    "age":        (["18-24", "25-34", "35-44", "45-54", "55+"], [0.18, 0.30, 0.22, 0.14, 0.16]),
    "gender":     (["woman", "man", "non-binary"], [0.50, 0.47, 0.03]),
    "region":     (["Northeast", "Midwest", "South", "West"], [0.18, 0.20, 0.37, 0.25]),
    "urbanicity": (["urban", "suburban", "rural"], [0.35, 0.47, 0.18]),
    "household":  (["1", "2", "3 or more"], [0.24, 0.34, 0.42]),   # Q9 축. 센서스 1인 28%보다 소폭 낮게(패널 연령)
    # 축① 태국·동남아 음식 빈도 — Q1 척도 그대로. 미국 일반 성인 기준 [규범근사]
    "thai_freq":  (["Never", "A few times a year", "About once a month", "A few times a month", "Once a week or more"],
                   [0.18, 0.37, 0.22, 0.15, 0.08]),
    # 축②~⑤ 연속 latent (평균, SD) → [0,1] clip
    "latent": {
        "cilantro_aversion":  (0.30, 0.25),  # 고수·강한 허브 기피. 유전적 비누맛 ~10~20% + 선호 기피 → 상단 꼬리
        "home_cooking":       (0.50, 0.22),  # 집에서 직접 요리하는 성향
        "price_sensitivity":  (0.55, 0.22),  # 가격 민감도
        "kfood_familiarity":  (0.42, 0.25),  # 한식·K-브랜드(Bibigo 등) 친숙도
    },
    "_label": "[규범근사] 실측 앵커 없음. 사전분포 폭을 넓게 두어 유형 다양성 확보. 수준 인용 금지.",
}
FREQ = US_PRIORS["thai_freq"][0]


def _rng(pid):
    return np.random.default_rng([RUN_SEED, pid])


def _choice(rng, options, probs):
    p = np.asarray(probs, float); p = p / p.sum()
    return options[int(rng.choice(len(options), p=p))]


def _clip(v):
    return float(np.clip(v, 0.0, 1.0))


def sample(pid):
    rng = _rng(pid)
    age = _choice(rng, *US_PRIORS["age"])
    gender = _choice(rng, *US_PRIORS["gender"])
    region = _choice(rng, *US_PRIORS["region"])
    urb = _choice(rng, *US_PRIORS["urbanicity"])
    hh = _choice(rng, *US_PRIORS["household"])

    # 축① 빈도: 도시·젊음 → 상향, 농촌·고령 → 하향 (방향만, 소폭)
    fp = np.array(US_PRIORS["thai_freq"][1], float)
    tilt = (0.25 if urb == "urban" else -0.25 if urb == "rural" else 0.0) + \
           (0.15 if age in ("18-24", "25-34") else -0.15 if age == "55+" else 0.0)
    fp = fp * np.exp(tilt * np.arange(5) / 2.0)
    thai_freq = _choice(rng, FREQ, fp)

    lat = {k: _clip(rng.normal(mu, sd)) for k, (mu, sd) in US_PRIORS["latent"].items()}
    # 약한 조건부 상관(방향만): 가족가구·고령 → 집요리↑, 농촌·18-24 → 가격민감↑, 도시·젊음·연안 → 한식친숙↑
    if hh == "3 or more": lat["home_cooking"] = _clip(lat["home_cooking"] + 0.05)
    if age in ("35-44", "45-54", "55+"): lat["home_cooking"] = _clip(lat["home_cooking"] + 0.05)
    if urb == "rural" or age == "18-24": lat["price_sensitivity"] = _clip(lat["price_sensitivity"] + 0.06)
    if urb == "urban": lat["kfood_familiarity"] = _clip(lat["kfood_familiarity"] + 0.08)
    if region in ("West", "Northeast"): lat["kfood_familiarity"] = _clip(lat["kfood_familiarity"] + 0.05)
    if age in ("18-24", "25-34"): lat["kfood_familiarity"] = _clip(lat["kfood_familiarity"] + 0.05)
    # 태국 음식 고빈도 ↔ 고수 기피 음(-) 완충 (빈도가 높은 사람은 기피가 낮은 쪽으로)
    fi = FREQ.index(thai_freq)
    lat["cilantro_aversion"] = _clip(lat["cilantro_aversion"] - 0.06 * (fi - 2))

    return {
        "pid": pid, "age": age, "gender": gender, "region": region, "urbanicity": urb,
        "household": hh, "thai_freq": thai_freq, **{k: round(v, 3) for k, v in lat.items()},
    }


pool = [sample(pid) for pid in range(N)]

pool_id = f"uspool_{RUN_SEED}"
cfg = {"N": N, "RUN_SEED": RUN_SEED, "pool_kind": "us_lite", "priors": US_PRIORS}
for d in (SP, run_dir(pool_id, create=True)):
    os.makedirs(d, exist_ok=True)
    json.dump(pool, open(f"{d}/prof.json", "w"), ensure_ascii=False)
    json.dump(pool, open(f"{d}/pool_meta.json", "w"), ensure_ascii=False)
    json.dump(cfg, open(f"{d}/run_cfg.json", "w"), ensure_ascii=False)

from collections import Counter
def dist(k):
    c = Counter(p[k] for p in pool); return {a: round(b / N, 2) for a, b in sorted(c.items())}
print(f"pool_id={pool_id}  N={N}  RUN_SEED={RUN_SEED}")
for k in ("age", "household", "urbanicity", "thai_freq"):
    print(f"  {k}: {dist(k)}")
for k in US_PRIORS["latent"]:
    v = np.array([p[k] for p in pool])
    print(f"  {k}: mean={v.mean():.2f} sd={v.std():.2f}  >0.75: {(v > 0.75).mean():.2f}  <0.25: {(v < 0.25).mean():.2f}")
