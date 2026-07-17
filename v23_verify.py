# -*- coding: utf-8 -*-
"""v2.3 붕괴/동질성 진단 — 진단 계층 신규 파일(엔진 무수정).

배경: vs_verify.py는 wf_vs_all(v1.x) 저널 전용(A2_dist 6지·B2 6지)이라 v2.3 저널
(A2a~A2d·B2 5지)에는 KeyError로 비호환. 이 파일은 v2.3 스키마로 동일 취지의 진단
지표(믿음질량·realized 사용률·최빈패턴 점유=동질성·붕괴 체크)를 계산하고 **JSON을 stdout**
으로 출력한다(진단 API가 이 JSON을 파싱 — 취약한 텍스트 파싱 금지).

표집 salt·상수·표집 함수(SALT/SEED/pick/wmean/옵션라벨)는 **v23_analyze.py의 값을 그대로**
사용한다(INVENTORY §4f "파일 간 salt 일치 = 재현 정합", 임의 변경 금지). 아래 각 지점에 출처 표기.
진단 임계(동질성 warn 등)는 진단 계층 휴리스틱이며 엔진 판정 임계가 아니다.

사용: python3 v23_verify.py <run_id>   (경로는 harness_paths 환경변수 오버라이드)
"""
import json
import sys
from collections import Counter

import numpy as np

from harness_paths import SP
cfg = json.load(open(f"{SP}/run_cfg.json"))
SEED = cfg["RUN_SEED"]                       # 출처: v23_analyze.py:15 (동일)
from harness_paths import JOURNAL_BASE as BASE
RUNID = sys.argv[1]

# ── 옵션 라벨/표집 상수: v23_analyze.py에서 그대로 복사(동일 값) ──
A2SCALE = ["아니다", "조금", "매우"]                                   # v23_analyze.py:20 (A2c)
B2O = ["5분 완조리", "외식 대비 가성비", "국산 새우·숙주", "매실청 새콤함", "이유 없음"]  # v23_analyze.py:21
B3O = ["맛 상상 안됨", "진짜 팟타이 아닐것", "냉동품질 불신", "가격 걱정", "양 부족", "팟타이 관심없음", "없음"]  # v23_analyze.py:22
C2O = ["꼭 산다", "가끔 산다", "기존 유지"]                            # v23_analyze.py:23
E1O = ["가(완성도)", "나(매실청)", "비슷", "둘 다 별로"]               # v23_analyze.py:24
# 표시 전용 라벨(표집에 무관, wf_vs_v23.js 프롬프트 기준) — salt는 아래 SALT가 권위
A1O = ["좋아한다", "보통이다", "별로였다", "먹어본 적 없다"]
A2xO = ["예", "아니오"]
B1O = ["1점", "2점", "3점", "4점", "5점"]
C1O = ["직접 만든다", "냉동·밀키트", "배달·외식", "안 먹음·참음", "이런 맛 안 찾음"]

# 출처: v23_analyze.py:25-26 (동일 값 — 재현 정합, 임의변경 금지)
SALT = {"A1": 40, "A2a": 41, "A2b": 42, "A2c": 43, "A2d": 44, "A2x": 45,
        "B1": 1, "B2": 46, "B3": 47, "C1": 2, "C2": 3, "E1": 60}
D1P = [5900, 6900, 7500, 8500]                # 출처: v23_analyze.py:27

# (field, dist키, salt, 라벨) — dist키가 field와 다른 경우(A2a 등) 분리
ITEMS = [
    ("A1", "A1_dist", SALT["A1"], A1O),
    ("A2a", "A2a_dist", SALT["A2a"], A2SCALE),
    ("A2b", "A2b_dist", SALT["A2b"], A2SCALE),
    ("A2c", "A2c_dist", SALT["A2c"], A2SCALE),
    ("A2d", "A2d_dist", SALT["A2d"], A2SCALE),
    ("A2x", "A2x_dist", SALT["A2x"], A2xO),
    ("B1", "B1_dist", SALT["B1"], B1O),
    ("B2", "B2_dist", SALT["B2"], B2O),
    ("B3", "B3_dist", SALT["B3"], B3O),
    ("C1", "C1_dist", SALT["C1"], C1O),
    ("C2", "C2_dist", SALT["C2"], C2O),
    ("E1", "E1_dist", SALT["E1"], E1O),
]

# 진단 계층 휴리스틱 임계(엔진 판정 임계 아님)
HOMOGENEITY_WARN = 55.0
HOMOGENEITY_HIGH = 70.0

PRESCRIPTION_HOMOGENEITY = ("effort 상향(low→medium/high) 또는 프롬프트 특성-조건화 강화"
                            "(게이트C 설계 §2c 탈동질화 처방)")
PRESCRIPTION_COLLAPSE = ("VS 분포화가 문항 내 보기를 살리는지 점검 — 중립/부정 보기가 realized에서 "
                         "0이면 강제단발선택 붕괴 재발 신호(게이트C §2b)")


def load():
    rows = {}
    for l in open(f"{BASE}/{RUNID}/journal.jsonl", encoding="utf-8"):
        o = json.loads(l)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
            rows[r["pid"]] = r
    return rows


def pick(dist, n, pid, salt):                 # 출처: v23_analyze.py:39-44 (동일)
    w = np.array([max(float(x), 0.0) for x in dist])
    if w.sum() <= 0:
        w = np.ones(n)
    rng = np.random.default_rng([SEED, pid, salt])
    return int(rng.choice(n, p=w / w.sum()))


def belief_mass_pct(rows, key, n):
    acc = np.zeros(n)
    for r in rows.values():
        d = np.array([max(float(x), 0.0) for x in r[key]], float)
        if d.sum() > 0:
            acc += d / d.sum()                # 페르소나당 동일가중(vs_verify.mass와 동일 취지)
    tot = acc.sum() or 1.0
    return [round(100 * x / tot, 1) for x in acc]


def diagnose():
    rows = load()
    N = len(rows)
    out_items = {}
    homog = []   # (field, modal_share)
    for name, key, salt, labels in ITEMS:
        n = len(labels)
        mass = belief_mass_pct(rows, key, n)
        realized = Counter()
        for pid, r in rows.items():
            realized[labels[pick(r[key], n, pid, salt)]] += 1
        patterns = Counter(tuple(r[key]) for r in rows.values())
        modal_share = round(100 * patterns.most_common(1)[0][1] / N, 1) if N else 0.0
        used = sum(1 for lab in labels if realized.get(lab, 0) > 0)
        homog.append((name, modal_share))
        out_items[key] = {
            "name": name, "options": labels,
            "belief_mass_pct": mass,
            "realized_counts": {lab: realized.get(lab, 0) for lab in labels},
            "options_used": used, "options_total": n,
            "distinct_patterns": len(patterns), "modal_pattern_share_pct": modal_share,
        }

    # ── 붕괴 3종 체크 ──
    warnings = []

    # (1) 페르소나간 동질성 — 최빈패턴 점유 최악값
    worst_field, worst_share = max(homog, key=lambda t: t[1]) if homog else (None, 0.0)
    if worst_share >= HOMOGENEITY_HIGH:
        h_status = "high"
    elif worst_share >= HOMOGENEITY_WARN:
        h_status = "warn"
    else:
        h_status = "ok"
    if h_status != "ok":
        warnings.append({"code": "homogeneity", "field": worst_field,
                         "message": f"{worst_field} 최빈패턴 점유 {worst_share}% — 페르소나간 동질성 높음",
                         "prescription": PRESCRIPTION_HOMOGENEITY})

    # (2) 문항내 붕괴 — E1 중립/부정(비슷+둘다) 생존 + 보기 사용률
    e1 = out_items["E1_dist"]["realized_counts"]
    e1_neutral = e1.get("비슷", 0) + e1.get("둘 다 별로", 0)
    e1_status = "ok" if e1_neutral > 0 else "warn"
    if e1_status != "ok":
        warnings.append({"code": "within_item_collapse", "field": "E1_dist",
                         "message": "E1 '비슷+둘 다 별로' realized=0 — 강제단발선택 붕괴 신호",
                         "prescription": PRESCRIPTION_COLLAPSE})
    min_used = min((it["options_used"] / it["options_total"] for it in out_items.values()), default=1.0)
    worst_use = min(out_items.items(), key=lambda kv: kv[1]["options_used"] / kv[1]["options_total"])[0] if out_items else None

    # (3) A2 향부담 유병률(참고 — latent앵커라 '수준'은 신뢰X)
    a2a = out_items["A2a_dist"]["belief_mass_pct"]   # [아니다, 조금, 매우]
    prevalence_wide = round(a2a[1] + a2a[2], 1)

    return {
        "run_id": RUNID, "N": N, "seed": SEED,
        "thresholds": {"homogeneity_modal_share_warn_pct": HOMOGENEITY_WARN,
                       "homogeneity_modal_share_high_pct": HOMOGENEITY_HIGH,
                       "_note": "진단 계층 휴리스틱(엔진 판정 임계 아님)"},
        "items": out_items,
        "collapse_checks": {
            "cross_persona_homogeneity": {"worst_field": worst_field,
                                          "modal_share_pct": worst_share, "status": h_status},
            "within_item_E1_neutral": {"비슷+둘다_realized": e1_neutral, "status": e1_status},
            "option_usage": {"min_used_ratio": round(min_used, 3), "worst_field": worst_use},
            "A2_prevalence_info": {"향부담_광의_믿음질량_pct": prevalence_wide,
                                   "note": "수준은 latent앵커 — 참고만(실측 몫)"},
        },
        "warnings": warnings,
        "salt_source": "v23_analyze.py:25-26 (동일 값), SEED=run_cfg.RUN_SEED",
    }


if __name__ == "__main__":
    print(json.dumps(diagnose(), ensure_ascii=False))
