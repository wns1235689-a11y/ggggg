#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""제네시스 설문 판정 — 사전등록 GH1~GH8 판독 (JSON stdout 플러그인).

계층 경계(P2-07): 전파(GH2·GH3·GH4·GH6·GH7·GH8)=상태 밴드의 재확인 / LLM(GH5·비보조
비카드 브랜드 구성)=모델 기여 / 혼합(GH1). 밴드=knows '상태' 확률(P1-02) — 관측량(카드
Y율)은 파생 기대치로 병기·현장 대조. 예스세잉은 주입 에코(P2-01 — LLM 기여 아님).
시뮬 verdict 어휘: '전파 확인/자기일관/기제 이상/판정 유보'(P2-10).
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
import journal_io  # noqa: E402
from harness_paths import SP, JOURNAL_BASE  # noqa: E402

BRAND_KEY = {"BMW": "B_dist", "LEXUS": "L_dist", "POLESTAR": "P_dist", "GENESIS": "G_dist"}


def load_rows(run_id):
    rows, info = journal_io.load_rows(JOURNAL_BASE, run_id, "q1_lists")   # F8: gz·손상행 내성
    return rows, info


def _prereg(hid):
    """PREREG 단일 출처 조회(F12)."""
    for h in C.PREREG:
        if h["id"] == hid:
            return h
    return {}


def _obs_from_state(k, ys):
    """상태 확률 → 관측(카드 Y율) 파생: k×0.9 + vague폭×0.5 + ys×잔여 (P1-02)."""
    return round(k * 0.9 + C.VAGUE_MARGIN * 0.5 + ys * max(0.0, 1 - k - C.VAGUE_MARGIN), 3)


def run(run_id):
    cfg = json.load(open(f"{SP}/run_cfg.json", encoding="utf-8"))
    scen = cfg.get("scenario", "neutral")
    meta = {m["pid"]: m for m in json.load(open(f"{SP}/pool_meta.json", encoding="utf-8"))}
    rows, jinfo = load_rows(run_id)
    N = len(rows)
    if N == 0 and jinfo["missing"]:
        return {"run_id": run_id, "N": 0, "judgeable": False,
                "note": "저널 파일 부재 — run_id·경로 확인(진행 중 아님)"}
    if N == 0:
        return {"run_id": run_id, "N": 0, "judgeable": False, "note": "결과 없음(진행 중)"}

    ys = C.band(C.YES_SAYING_BASE, scen)

    def pids(pop):
        return [p for p in rows if meta.get(p, {}).get("pop") == pop]

    def card_share(pop, brand):
        ps = pids(pop)
        tot = sum(sum(rows[p][BRAND_KEY[brand]]) for p in ps)
        y = sum(rows[p][BRAND_KEY[brand]][0] for p in ps)
        return round(y / tot, 3) if tot else None

    def knows_share(pop, brand):
        ms = [m for m in meta.values() if m["pop"] == pop]
        return round(sum(1 for m in ms if m["know"][brand] == "knows") / len(ms), 3) if ms else None

    # GH1 거리 비보조 Genesis
    gh1p = _prereg("GH1")
    street_lines = [x for p in pids("street_rtm") for x in rows[p]["q1_lists"]]
    g_unaided = sum(1 for x in street_lines if "GENESIS" in coding.norm_brands(x))
    gh1_rate = round(g_unaided / max(len(street_lines), 1), 4)
    gh1 = {"id": "GH1", "unaided_genesis_rate_street": gh1_rate, "mentions": g_unaided,
           "band": gh1p.get("band"),
           "verdict": "자기일관(밴드 내)" if gh1_rate <= gh1p["band"][1] else "기제 이상(밴드 초과 — verify 누출 확인)"}

    # 비보조 브랜드 구성 — 카드 4브랜드는 프라이밍 하 생성이라 '*' 마킹·판독 제외(P2-06)
    CARD_BRANDS = set(BRAND_KEY)
    q1_rank = Counter()
    for x in street_lines:
        for b in coding.norm_brands(x):
            q1_rank[b] += 1
    gh1["street_unaided_top"] = [(f"{b}*" if b in CARD_BRANDS else b, c)
                                 for b, c in q1_rank.most_common(8)]
    gh1["note"] = "'*'=카드 브랜드(프롬프트 프라이밍 하 생성 — 비보조 순위 판독 금지, P2-06)"

    # GH2 거리 카드 서열 — 상태(knows) 밴드 판정 + 관측(카드 Y) 파생 병기
    gh2p = _prereg("GH2")
    sh = {b: card_share("street_rtm", b) for b in BRAND_KEY}
    ks = {b: knows_share("street_rtm", b) for b in BRAND_KEY}
    order_ok = all(v is not None for v in sh.values()) and \
        sh["BMW"] > sh["LEXUS"] > sh["POLESTAR"] > sh["GENESIS"]
    g_state = ks.get("GENESIS")
    band = gh2p["band"]
    gh2 = {"id": "GH2", "street_card_shares_observed": sh, "street_knows_states": ks,
           "band_genesis_state": band,
           "derived_obs_band_genesis": (_obs_from_state(band[0], ys), _obs_from_state(band[1], ys)),
           "verdict": (("전파 확인(서열 재현)" if order_ok else "판정 유보(서열 미확인 — 표집·드리프트 확인)")
                       + (f" · Genesis 상태 {'밴드 내' if g_state is not None and band[0] <= g_state <= band[1] else '밴드 밖(드리프트 확인)'}"
                          if g_state is not None else ""))}

    # GH3 GP vs 거리 격차 — 상태(knows) 비 판정 + 관측 카드 비 병기 (F7·P1-09 게이트)
    gh3p = _prereg("GH3")
    g_gp, g_st = card_share("gp_zandvoort", "GENESIS"), card_share("street_rtm", "GENESIS")
    k_gp, k_st = knows_share("gp_zandvoort", "GENESIS"), knows_share("street_rtm", "GENESIS")
    state_ratio = round(k_gp / k_st, 2) if (k_gp is not None and k_st) else None
    card_ratio = round(g_gp / g_st, 2) if (g_gp is not None and g_st) else None
    band3 = gh3p["band"]
    if k_gp is None or k_st is None:
        verdict3 = "판정 유보(모집단 행 부재)"
    elif k_st == 0.0:
        verdict3 = "거리 knows 0 — 배수 미정의(격차 방향은 자기일관)" if (k_gp or 0) > 0 else "양쪽 0 — 판정 유보"
    else:
        verdict3 = ("전파 확인(상태비 밴드 내)" if band3[0] <= state_ratio <= band3[1]
                    else "기제 이상(상태비 밴드 밖 — 입력·드리프트 확인)")
    gh3 = {"id": "GH3", "knows_gp": k_gp, "knows_street": k_st, "state_ratio": state_ratio,
           "card_gp_observed": g_gp, "card_street_observed": g_st, "card_ratio_observed": card_ratio,
           "band_state": band3, "min_street_y_field": gh3p.get("min_street_y"),
           "note": "밴드는 상태비(전파). 현장 대조는 관측 카드비 — 거리 Y<3이면 Fisher 방향판정으로 대체",
           "verdict": verdict3}

    # GH4 마그마 조건부(GP) — min_denom 게이트 + echo 깊이 분리(P1-08)
    gh4p = _prereg("GH4")
    mag_y = sum(rows[p]["magma_dist"][0] for p in pids("gp_zandvoort"))
    gen_y_gp = sum(rows[p]["G_dist"][0] for p in pids("gp_zandvoort"))
    mag_rate = round(mag_y / gen_y_gp, 3) if gen_y_gp else None
    depth = Counter(coding.magma_depth(v) for p in pids("gp_zandvoort") for v in rows[p]["magma_verbatim"])
    band4 = gh4p["band"]
    gh4 = {"id": "GH4", "p_magma_given_genesis": mag_rate, "band": band4,
           "denom_gen_y": gen_y_gp, "min_denom": gh4p.get("min_denom"),
           "depth_coded": dict(depth),
           "note": "현장 마그마 Y는 유도형 질문의 상한 해석(P1-08). depth 'echo'=질문 어휘 반복만",
           "verdict": ("판정 유보(분모<최소 — 일화 기술 전용)" if gen_y_gp < gh4p.get("min_denom", 0)
                       else "전파 확인(밴드 내)" if mag_rate is not None and band4[0] <= mag_rate <= band4[1]
                       else "기제 이상(밴드 밖 — 정규화·표집 확인)" if mag_rate is not None else "판정 유보")}

    # GH5 모집단 내(within-pop) <30×EV관심 세그먼트의 P/L 역전(LLM 기여 — P2-08 교란 제거)
    def share_seg(brand, seg_pids):
        tot = sum(sum(rows[p][BRAND_KEY[brand]]) for p in seg_pids)
        return round(sum(rows[p][BRAND_KEY[brand]][0] for p in seg_pids) / tot, 3) if tot else None
    gh5_pops = {}
    for pop in ("street_rtm", "gp_zandvoort"):
        young_ev = [p for p in pids(pop) if meta[p]["age"] == "<30" and meta[p]["latent"]["ev_interest"] > 0.5]
        allp = pids(pop)
        seg = {"young_ev": {"POLESTAR": share_seg("POLESTAR", young_ev), "LEXUS": share_seg("LEXUS", young_ev),
                            "n": len(young_ev)},
               "overall": {"POLESTAR": share_seg("POLESTAR", allp), "LEXUS": share_seg("LEXUS", allp)}}
        yv = seg["young_ev"]
        ov = seg["overall"]
        if yv["n"] < 3 or yv["POLESTAR"] is None or ov["POLESTAR"] is None:
            seg["pattern"] = "판정 유보(세그 n<3)"
        elif yv["POLESTAR"] > yv["LEXUS"] and ov["LEXUS"] > ov["POLESTAR"]:
            seg["pattern"] = "역전 재현"
        elif yv["POLESTAR"] == yv["LEXUS"]:
            seg["pattern"] = "판정 유보(동률)"
        else:
            seg["pattern"] = "미재현"
        gh5_pops[pop] = seg
    pat = [s["pattern"] for s in gh5_pops.values()]
    gh5 = {"id": "GH5", "by_pop": gh5_pops,
           "verdict": ("자기일관(역전 재현)" if "역전 재현" in pat and "미재현" not in pat
                       else "기제 이상(미재현)" if "미재현" in pat else "판정 유보")}

    # GH6 예스세잉 — 주입 에코 확인(P2-01: LLM 기여 아님)
    gh6p = _prereg("GH6")
    no_pids = [p for p in rows if meta.get(p, {}).get("know", {}).get("GENESIS") == "no"]
    no_tot = sum(sum(rows[p]["G_dist"]) for p in no_pids)
    no_y = sum(rows[p]["G_dist"][0] for p in no_pids)
    ys_rate = round(no_y / no_tot, 3) if no_tot else None
    band6 = gh6p["band"]
    gh6 = {"id": "GH6", "yes_saying_realized": ys_rate, "injected": ys, "band": band6,
           "note": "바닥 %는 프롬프트 주입값 — 전파 확인(에코)이지 LLM 기여 아님. 현장 Genesis Y가 "
                   "이 바닥 수준이면 예스세잉만으로 설명 가능(상한 해석)",
           "verdict": ("전파 확인(에코 정합)" if ys_rate is not None and band6[0] <= ys_rate <= band6[1]
                       else "기제 이상(에코 이탈)" if ys_rate is not None else "판정 유보")}

    # GH7·GH8 현장 규모 투영(관측 카드율 기준 — grp는 카드 분모 포함이라 미차감)
    gh8p = _prereg("GH8")
    st_n, gp_n = C.FIELD_PLAN["street_n"][1], C.FIELD_PLAN["gp_n"][1]
    proj_st = round(st_n * (g_st or 0), 1)
    proj_gp = round(gp_n * (g_gp or 0), 1)
    gh7 = {"id": "GH7", "projected_genesis_y": {"street_n25": proj_st, "gp_n40": proj_gp},
           "note": "카드 분모는 grp 포함(매뉴얼: 로고 인지는 각자 유효)",
           "verdict": f"전파 확인 — 격차는 방향·배수만 판독(거리 {proj_st}명 vs GP {proj_gp}명, %p 비교 금지)"}
    ok_min = gh8p.get("askable_ok_min", 17)
    gh8 = {"id": "GH8", "projected_magma_askable": proj_gp,
           "verdict": (f"전파 확인(경고) — 마그마 발동 ≈{proj_gp}회: 일화 수준" if proj_gp < ok_min
                       else f"마그마 표본 확보 가능(≥{ok_min})")}

    return {
        "run_id": run_id, "N": N, "scenario": scen, "seed": cfg.get("RUN_SEED"),
        "n_street": cfg.get("n_street"), "n_gp": cfg.get("n_gp"),
        "judgeable": True,
        "hypotheses": [gh1, gh2, gh3, gh4, gh5, gh6, gh7, gh8],
        "observed_space": {
            "formula": "카드Y ≈ knows×0.9 + vague폭(0.10)×0.5 + 예스세잉×잔여",
            "yes_saying_injected": ys,
            "note": "밴드=상태 확률(사전등록), 현장 관측량 대조는 파생 기대치(derived_obs_band) 기준",
        },
        "caveats": [
            "계층(P2-07): 전파(GH2·3·4·6·7·8)=상태 밴드 재확인 / LLM(GH5·비카드 비보조 구성) / 혼합(GH1).",
            "예스세잉은 프롬프트 주입 에코(P2-01) — LLM 기여 목록에서 제외. 무주입 측정은 v2 백로그.",
            "비보조 랭킹의 카드 4브랜드('*')는 프라이밍 하 생성 — 판독 금지(P2-06).",
            "모든 수치는 합성·비실측 — 인용 불가. 현장(거리 20~30·GP 30~50) 대조가 완성이다.",
            f"시나리오={scen} — 3시나리오×3시드 풀 세트로 봉인(P2-08). 거리 조사일이 8/23 이후면 "
            "pre_gp_fallback 적용(P4-03).",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
