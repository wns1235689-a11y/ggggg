#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""제네시스 설문 판정 — 사전등록 GH1~GH8 판독 (JSON stdout 플러그인).

순환 경계: 보조 인지 '수준'·두 모집단 '격차 크기'는 config 밴드의 입력 전파(사전등록 예측).
LLM 고유 기여(발견 후보) = 비보조 브랜드 구성(GH1 주변), 연령·EV 조건부 역전(GH5),
예스세잉 형상, 마그마 회상 내용의 깊이 분포.
"""
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

import config as C   # noqa: E402
import coding        # noqa: E402
from harness_paths import SP, JOURNAL_BASE  # noqa: E402

BRAND_KEY = {"BMW": "B_dist", "LEXUS": "L_dist", "POLESTAR": "P_dist", "GENESIS": "G_dist"}


def load_rows(run_id):
    rows = {}
    for line in open(os.path.join(JOURNAL_BASE, run_id, "journal.jsonl"), encoding="utf-8"):
        o = json.loads(line)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "q1_lists" in r:
            rows[r["pid"]] = r
    return rows


def run(run_id):
    cfg = json.load(open(f"{SP}/run_cfg.json", encoding="utf-8"))
    scen = cfg.get("scenario", "neutral")
    meta = {m["pid"]: m for m in json.load(open(f"{SP}/pool_meta.json", encoding="utf-8"))}
    rows = load_rows(run_id)
    N = len(rows)
    if N == 0:
        return {"run_id": run_id, "N": 0, "judgeable": False, "note": "결과 없음(진행 중)"}

    def pids(pop):
        return [p for p in rows if meta.get(p, {}).get("pop") == pop]

    def card_share(pop, brand):
        ps = pids(pop)
        tot = sum(sum(rows[p][BRAND_KEY[brand]]) for p in ps)
        y = sum(rows[p][BRAND_KEY[brand]][0] for p in ps)
        return round(y / tot, 3) if tot else None

    # GH1 거리 비보조 Genesis
    street_lines = [x for p in pids("street_rtm") for x in rows[p]["q1_lists"]]
    g_unaided = sum(1 for x in street_lines if "GENESIS" in coding.norm_brands(x))
    gh1_rate = round(g_unaided / max(len(street_lines), 1), 4)
    gh1 = {"id": "GH1", "unaided_genesis_rate_street": gh1_rate, "mentions": g_unaided,
           "band": (0.0, 0.02),
           "verdict": "밴드 내(지지)" if gh1_rate <= 0.02 else "밴드 초과(누출 의심 — verify 확인)"}

    # 비보조 브랜드 구성(LLM 기여) — 상위 랭킹
    q1_rank = Counter()
    for x in street_lines:
        for b in coding.norm_brands(x):
            q1_rank[b] += 1
    gh1["street_unaided_top"] = q1_rank.most_common(8)

    # GH2 거리 카드 서열
    sh = {b: card_share("street_rtm", b) for b in BRAND_KEY}
    order_ok = sh["BMW"] > sh["LEXUS"] > sh["POLESTAR"] > sh["GENESIS"] \
        if all(v is not None for v in sh.values()) else False
    gh2 = {"id": "GH2", "street_card_shares": sh, "band_genesis": (0.04, 0.18),
           "verdict": ("서열 재현 + Genesis 밴드 내" if order_ok and 0.04 <= (sh["GENESIS"] or 0) <= 0.18
                       else "서열 재현" if order_ok else "서열 불일치(입력·표집 확인)")}

    # GH3 GP vs 거리 격차(입력 전파)
    g_gp, g_st = card_share("gp_zandvoort", "GENESIS"), card_share("street_rtm", "GENESIS")
    ratio = round(g_gp / g_st, 2) if g_gp and g_st else None
    gh3 = {"id": "GH3", "genesis_gp": g_gp, "genesis_street": g_st, "ratio": ratio,
           "band": (2.0, 5.0),
           "note": "격차 크기=입력 전파(밴드 예측). 현장에서 방향·배수만 대조",
           "verdict": ("밴드 내(전파 확인)" if ratio and 2.0 <= ratio <= 5.0
                       else "밴드 밖(입력 확인)" if ratio else "표본 부족")}

    # GH4 마그마 조건부(GP)
    mag_y = sum(rows[p]["magma_dist"][0] for p in pids("gp_zandvoort"))
    gen_y_gp = sum(rows[p]["G_dist"][0] for p in pids("gp_zandvoort"))
    mag_rate = round(mag_y / gen_y_gp, 3) if gen_y_gp else None
    depth = Counter(coding.magma_depth(v) for p in pids("gp_zandvoort") for v in rows[p]["magma_verbatim"])
    gh4 = {"id": "GH4", "p_magma_given_genesis": mag_rate, "band": (0.25, 0.60),
           "depth_coded": dict(depth),
           "verdict": ("밴드 내(지지)" if mag_rate is not None and 0.25 <= mag_rate <= 0.60
                       else "밴드 밖" if mag_rate is not None else "표본 부족")}

    # GH5 Polestar·Lexus 조건부 역전(LLM 기여 — 연령·EV)
    def share_seg(brand, seg_pids):
        tot = sum(sum(rows[p][BRAND_KEY[brand]]) for p in seg_pids)
        return round(sum(rows[p][BRAND_KEY[brand]][0] for p in seg_pids) / tot, 3) if tot else None
    young = [p for p in rows if meta.get(p, {}).get("age") == "<30"]
    old = [p for p in rows if meta.get(p, {}).get("age") == "50+"]
    p_y, l_y = share_seg("POLESTAR", young), share_seg("LEXUS", young)
    p_o, l_o = share_seg("POLESTAR", old), share_seg("LEXUS", old)
    inv_young = (p_y is not None and l_y is not None and p_y >= l_y)
    lex_old = (p_o is not None and l_o is not None and l_o > p_o)
    gh5 = {"id": "GH5", "young": {"POLESTAR": p_y, "LEXUS": l_y}, "old": {"POLESTAR": p_o, "LEXUS": l_o},
           "verdict": ("역전 재현(<30 P≥L, 50+ L>P)" if inv_young and lex_old
                       else "부분 재현" if inv_young or lex_old else "미재현")}

    # GH6 예스세잉 상한 — 'no' 상태 페르소나의 Genesis Y율
    no_pids = [p for p in rows if meta.get(p, {}).get("know", {}).get("GENESIS") == "no"]
    no_tot = sum(sum(rows[p]["G_dist"]) for p in no_pids)
    no_y = sum(rows[p]["G_dist"][0] for p in no_pids)
    ys_rate = round(no_y / no_tot, 3) if no_tot else None
    gh6 = {"id": "GH6", "yes_saying_realized": ys_rate, "band": (0.02, 0.08),
           "note": "포일 없는 카드 — 현장 Genesis Y가 이 바닥 수준이면 예스세잉만으로 설명 가능",
           "verdict": ("밴드 내" if ys_rate is not None and 0.02 <= ys_rate <= 0.08
                       else "밴드 밖" if ys_rate is not None else "표본 부족")}

    # GH7·GH8 현장 규모 투영
    st_n, gp_n = C.FIELD_PLAN["street_n"][1], C.FIELD_PLAN["gp_n"][1]
    proj_st = round(st_n * (g_st or 0), 1)
    proj_gp = round(gp_n * (g_gp or 0), 1)
    gh7 = {"id": "GH7", "projected_genesis_y": {"street_n25": proj_st, "gp_n40": proj_gp},
           "verdict": f"격차는 방향·배수만 판독(거리 {proj_st}명 vs GP {proj_gp}명 — %p 비교 금지)"}
    gh8 = {"id": "GH8", "projected_magma_askable": proj_gp,
           "verdict": (f"마그마 발동 ≈{proj_gp}회 — 일화 수준" if proj_gp < 15 else "표본 확보 가능")}

    return {
        "run_id": run_id, "N": N, "scenario": scen, "seed": cfg.get("RUN_SEED"),
        "n_street": cfg.get("n_street"), "n_gp": cfg.get("n_gp"),
        "judgeable": True,
        "hypotheses": [gh1, gh2, gh3, gh4, gh5, gh6, gh7, gh8],
        "caveats": [
            "보조 인지 수준·GP/거리 격차 크기·마그마 조건부 수준은 config 밴드의 입력 전파 — 사전등록 예측이지 발견 아님.",
            "LLM 고유 기여(발견 후보) = 비보조 브랜드 구성(GH1 랭킹)·연령/EV 조건부 역전(GH5)·예스세잉 형상(GH6)·마그마 회상 내용.",
            "모든 수치는 합성·비실측 — 인용 불가. 현장(거리 20~30·GP 30~50) 대조가 완성이다.",
            f"시나리오={scen} — 3종 풀을 묶어야 밴드 완성.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
