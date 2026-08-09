#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로봇 설문 판정 — 사전등록 가설 H1~H9 판독 (JSON stdout 플러그인).

계층 경계 3분류(판정단 P2-07 반영):
  전파  = 상류 주입의 재확인(H5 채널믹스·H6 국가서열·H7 투영·H9 혼동) — 발견 아님
  LLM   = 순수 모델 기여(H2 오답 구성·H8 Q3 형상)
  혼합  = 지식상태 빈도가 골격을 만들고 LLM이 그 위에서 행동(H1 DK·H3 비·H4 프로브)
          → judge가 pool_meta 기반 '구조 골격값'을 병기해 실현치-골격 분해를 보고.
시뮬 verdict 어휘: '전파 확인/자기일관/기제 이상/판정 유보'만 사용(P2-10).
'지지/반증'은 현장 대조 계층 전용. H4는 현장 전용 판정(field_only).
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


def load_rows(run_id):
    rows, info = journal_io.load_rows(JOURNAL_BASE, run_id, "q2_verbatim")   # F8: gz·손상행 내성
    return rows, info


def _prereg(hid):
    """PREREG 단일 출처 조회(F12 — judge 하드코딩 금지)."""
    for h in C.PREREG:
        if h["id"] == hid:
            return h
    return {}


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

    # ── 코딩 집계(가상 응답자 단위 = verbatim 1개) ──
    q2 = Counter()
    q2_by_channel = {}
    for pid, r in rows.items():
        ch = (meta.get(pid) or {}).get("channel") or "none"
        for v in r["q2_verbatim"]:
            c = coding.code_q2(v)
            q2[c] += 1
            q2_by_channel.setdefault(ch, Counter())[c] += 1
    n_y = sum(q2.values())
    total_sim_people = sum(sum(r["Q1_dist"]) for r in rows.values())   # F1: 합 하드코딩 제거

    def share(codes):
        return round(sum(q2.get(c, 0) for c in codes) / n_y, 3) if n_y else None

    # ── 구조 골격값(P2-07): 지식상태 빈도 — '혼합' 계층 가설의 주입 골격 ──
    kn = Counter(m["knowledge"] for m in meta.values())
    skel = {
        "none_share": round(kn.get("none", 0) / max(len(meta), 1), 3),
        "H3_skeleton_ratio": (round((kn.get("both", 0) + kn.get("bd_only", 0))
                                    / (kn.get("both", 0) + kn.get("hyundai_only", 0)), 2)
                              if (kn.get("both", 0) + kn.get("hyundai_only", 0)) else None),
        "H4_skeleton": (round(kn.get("both", 0) / (kn.get("both", 0) + kn.get("bd_only", 0)), 3)
                        if (kn.get("both", 0) + kn.get("bd_only", 0)) else None),
        "note": "골격=지식상태 빈도(주입). 실현치-골격 차이가 LLM 행동 기여분",
    }

    # 프로브 코딩 + §6 A3 승격(P1-04 양방향): A2∧probeA=HYUNDAI→A3, A1∧probeB=BOSTON→A3
    pa, pb = Counter(), Counter()
    for r in rows.values():
        for v in r["probeA_verbatim"]:
            pa[coding.code_probe_a(v)] += 1
        for v in r["probeB_verbatim"]:
            pb[coding.code_probe_b(v)] += 1
    promo_a = min(pa.get("HYUNDAI", 0), q2.get("A2", 0))
    promo_b = min(pb.get("BOSTON", 0), q2.get("A1", 0))

    # H1 DK 지배 — 이중 정의(P1-05)
    h1p = _prereg("H1")
    dk_strict = share(["DK"])
    dk_desc = share(["DK", "DESC"])
    def _band_verdict(v, band):
        if v is None:
            return "판정 유보(표본 없음)"
        return "자기일관(밴드 내)" if band[0] <= v <= band[1] else \
            ("기제 이상(밴드 위)" if v > band[1] else "기제 이상(밴드 아래)")
    h1 = {"id": "H1", "dk_plus_desc": dk_desc, "dk_strict": dk_strict,
          "band_dk_plus_desc": h1p.get("band"), "band_dk_strict": h1p.get("band_strict"),
          "skeleton_none_share": skel["none_share"],
          "verdict": f"DK+DESC {_band_verdict(dk_desc, h1p['band'])} / strict {_band_verdict(dk_strict, h1p['band_strict'])}",
          "note": "현장 대조는 같은 정의끼리만(§6 밤코딩=strict, 부록 재코딩=DK+DESC)"}

    # H2 특정 기업 오답 1위 (LLM 계층)
    wrongs = {k: v for k, v in q2.items() if k.startswith("W-")}
    wrong_rank = sorted(wrongs.items(), key=lambda kv: -kv[1])
    h2 = {"id": "H2", "wrong_ranking": wrong_rank[:6],
          "top_wrong": wrong_rank[0][0] if wrong_rank else None,
          "verdict": ("자기일관(Tesla 1위)" if wrong_rank and wrong_rank[0][0] == "W-TESLA"
                      else "기제 이상(Tesla 1위 아님)" if wrong_rank else "판정 유보(오답 표본 없음)")}

    # H3 BD명명 vs 현대명명 비 — §6 정의(승격 반영: A3'=A3+promoA+promoB)
    h3p = _prereg("H3")
    a3_adj = q2.get("A3", 0) + promo_a + promo_b
    bd_n = (q2.get("A2", 0) - promo_a) + a3_adj
    hy_n = (q2.get("A1", 0) - promo_b) + a3_adj
    ratio = round(bd_n / hy_n, 2) if hy_n else None
    h3 = {"id": "H3", "bd_named": bd_n, "hyundai_named": hy_n, "ratio": ratio,
          "band": h3p.get("band"), "promoted": {"A2→A3": promo_a, "A1→A3": promo_b},
          "skeleton_ratio": skel["H3_skeleton_ratio"],
          "verdict": ("판정 유보(분모<최소)" if hy_n < h3p.get("min_denom", 0)
                      else "현대 명명 0(비 미정의·방향 자기일관)" if hy_n == 0 and bd_n > 0
                      else _band_verdict(ratio, h3p["band"]) if ratio is not None else "판정 유보")}

    # H4 프로브A — 현장 전용 판정(field_only): 시뮬은 골격·부분공개 행동만 보고
    h4p = _prereg("H4")
    pa_n = sum(pa.values())
    pa_hy = round(pa.get("HYUNDAI", 0) / pa_n, 3) if pa_n else None
    h4 = {"id": "H4", "probeA_n": pa_n, "coded": dict(pa), "hyundai_share_sim": pa_hy,
          "field_band": h4p.get("band"), "min_denom": h4p.get("min_denom"),
          "skeleton_both_given_bd": skel["H4_skeleton"],
          "stale_present": (pa.get("GOOGLE_STALE", 0) + pa.get("SOFTBANK_STALE", 0)) > 0,
          "verdict": "현장 전용 판정(시뮬은 골격+부분공개 행동 보고만 — P2-02)",
          "note": "시뮬 프로브A 정답은 both층의 Q2 부분공개 행동에 의존 — 밴드 판정은 현장 데이터로만"}

    # H5 채널믹스(입력 전파) + 채널별 귀속 조건부(LLM 기여)
    ch_mix = Counter((m.get("channel") or "none") for m in meta.values() if m.get("exposed"))
    ch_attr = {ch: {"n": sum(cnt.values()),
                    "hyundai_pct": round(100 * sum(cnt.get(c, 0) for c in ("A1", "A3")) / max(sum(cnt.values()), 1), 1),
                    "bd_pct": round(100 * sum(cnt.get(c, 0) for c in ("A2", "A3")) / max(sum(cnt.values()), 1), 1)}
               for ch, cnt in q2_by_channel.items() if ch != "none"}
    l_share = round(ch_mix.get("tv_live", 0) / max(sum(ch_mix.values()), 1), 3)
    h5 = {"id": "H5", "channel_mix_injected": dict(ch_mix), "tv_live_share": l_share,
          "attribution_by_channel": ch_attr,
          "note": ("채널믹스=입력 전파(측정 아님). 매핑 규칙(P1-07): 현장 'L 1회 이상 주장률' vs "
                   "시뮬 tv_live 단일 배정률. W는 자발 발화만 — 현장 ≈0 예상. "
                   "L-주장률 > 시뮬 상단이면 '기억 재구성' 해석(사전등록 규칙)"),
          "verdict": "전파 확인(S+N≫L)" if l_share < 0.15 else "기제 이상(L 과대 — 입력 확인 요)"}

    # H6 국가 Q1 서열(입력 전파 확인)
    ctry_y = {}
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m:
            continue
        ctry_y.setdefault(m["res_country"], []).append(r["Q1_dist"][0] / max(sum(r["Q1_dist"]), 1))
    ctry_rate = {k: round(sum(v) / len(v), 3) for k, v in ctry_y.items() if len(v) >= 3}
    ord_ok = all(k in ctry_rate for k in ("BE", "DE", "NL")) and \
        ctry_rate.get("BE", 0) > ctry_rate.get("DE", 0) > ctry_rate.get("NL", 0)
    h6 = {"id": "H6", "q1_by_country": dict(sorted(ctry_rate.items(), key=lambda kv: -kv[1])),
          "verdict": ("전파 확인(BE>DE>NL)" if ord_ok else "판정 유보(표본·노이즈로 서열 미확인)"),
          "note": "입력 밴드 전파 — 시뮬 발견 아님. 현장은 국가별 조사일 3일+ 차이 시 감쇠 교락 주석(P4-05)"}

    # H7 현장 규모 투영: n=150에서 분기A(=Q2 BD단독 발화자) 발동수 — grp 제외 유효 n(P1-06)
    y_rate = n_y / total_sim_people
    bd_only_rate_among_y = ((q2.get("A2", 0)) / n_y) if n_y else 0
    grp_mid = C.FIELD_PLAN["grp_share_expected"][1]
    eff_n = C.FIELD_PLAN["n_target"] * (1 - grp_mid)
    proj_a = round(eff_n * y_rate * bd_only_rate_among_y, 1)
    h7 = {"id": "H7", "sim_y_rate": round(y_rate, 3), "bd_only_rate_among_y": round(bd_only_rate_among_y, 3),
          "effective_n": round(eff_n), "projected_branchA": proj_a,
          "verdict": (f"전파 확인(경고) — 분기A ≈{proj_a}회(<{C.FIELD_PLAN['branchA_warn_min']}): 일화 수준"
                      if proj_a < C.FIELD_PLAN["branchA_warn_min"] else "분기A 표본 확보 가능(>15)")}

    # H8 Q3 연령 경사(LLM 조건부 형상)
    def q3_share(pids, idx):
        arr = [rows[p]["Q3_dist"] for p in pids if p in rows]
        tot = sum(sum(d) for d in arr)
        return round(sum(d[idx] for d in arr) / tot, 3) if tot else None
    young = [p for p, m in meta.items() if m["age"] == "<30"]
    old = [p for p, m in meta.items() if m["age"] == "50+"]
    e_y, e_o = q3_share(young, 0), q3_share(old, 0)
    w_y, w_o = q3_share(young, 1), q3_share(old, 1)
    grad_ok = (e_y is not None and e_o is not None and e_y > e_o) and \
              (w_y is not None and w_o is not None and w_o > w_y)
    h8 = {"id": "H8", "excited": {"<30": e_y, "50+": e_o}, "worried": {"<30": w_y, "50+": w_o},
          "verdict": "자기일관(경사 재현)" if grad_ok else "기제 이상(경사 미재현)",
          "note": "현장 경사는 연령 눈추정 오분류로 감쇠 예상 — 방향만 대조(P1-12)"}

    # H9 혼동(Spot/로봇개) 기여 — 입력 전파 확인 + 코딩 마커
    confl_pids = {p for p, m in meta.items() if m.get("conflated")}
    confl_y = sum(rows[p]["Q1_dist"][0] for p in confl_pids if p in rows)
    confl_codes = Counter()
    for p in confl_pids:
        if p in rows:
            for v in rows[p]["q2_verbatim"]:
                confl_codes[coding.code_q2(v)] += 1
    h9 = {"id": "H9", "conflated_personas": len(confl_pids),
          "conflated_y_people": confl_y,
          "conflated_y_share_of_all_y": round(confl_y / n_y, 3) if n_y else None,
          "conflated_coded": dict(confl_codes),
          "note": "혼동층 존재는 입력 전파(존재 자체는 실측 — EU Spot 기사). 현장 식별 마커 = 'dog' 계열 verbatim",
          "verdict": ("혼동층이 A1(우연 정답)에 기여함 — 현장 코딩 시 dog-마커 분리 필요"
                      if confl_codes.get("A1", 0) > 0 else "혼동층 정답 기여 없음(이번 표집)")}

    # 관측공간 파생 기대치(P1-02): 상태 밴드 × 발화 합성 — 현장 대조용 표
    p_exp_list = [m.get("p_exposed") for m in meta.values() if m.get("p_exposed") is not None]
    obs_space = {
        "factor": 0.76, "formula": "E[Q1Y]=p_노출×(0.6×0.9+0.4×0.55)",
        "pool_expected_q1y": round(sum(p_exp_list) / len(p_exp_list) * 0.76, 3) if p_exp_list else None,
        "realized_q1y": round(n_y / total_sim_people, 3) if total_sim_people else None,
        "note": "밴드=상태 확률(사전등록), 현장 관측량 대조는 이 파생 기대치 기준",
    }

    # 국가별 Q3 vs 앵커 — 성향 라벨은 준상수(혼합 ~90%+)라 앵커 '수준'은 사실상 미전파(P2-12):
    q3_ctry = {}
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m:
            continue
        q3_ctry.setdefault(m["res_country"], []).append(r["Q3_dist"])
    q3_vs_anchor = {}
    for k, arr in q3_ctry.items():
        if len(arr) < 5 or k not in C.Q3_CENTERS:
            continue
        tot = sum(sum(d) for d in arr)
        simv = [round(sum(d[i] for d in arr) / tot, 3) for i in range(3)]
        q3_vs_anchor[k] = {"sim_EWM": simv, "anchor_EWM": list(C.Q3_CENTERS[k]),
                           "delta_pp": [round(100 * (simv[i] - C.Q3_CENTERS[k][i]), 1) for i in range(3)]}

    return {
        "run_id": run_id, "N": N, "scenario": scen, "seed": cfg.get("RUN_SEED"),
        "judgeable": True,
        "q2_coded_total": dict(q2), "n_y_people": n_y, "total_sim_people": total_sim_people,
        "hypotheses": [h1, h2, h3, h4, h5, h6, h7, h8, h9],
        "structural_skeleton": skel,
        "observed_space": obs_space,
        "q3_vs_anchor": q3_vs_anchor,
        "caveats": [
            "계층 3분류(P2-07): 전파(H5·H6·H7·H9)=주입 재확인 / LLM(H2·H8)=모델 기여 / "
            "혼합(H1·H3·H4)=골격(structural_skeleton) 위의 LLM 행동 — 실현치-골격 분해로 읽을 것.",
            "H4는 현장 전용 판정 — 시뮬 프로브A는 both층 부분공개 행동에 의존(P2-02).",
            "성향 라벨은 준상수(혼합 지배) — Q3 앵커 '수준'은 미전파, q3_vs_anchor는 사실상 무순환 대조(P2-12).",
            "모든 수치는 합성·비실측 — 인용 불가. 현장 n=60~150(grp 제외 유효 n) 대조가 완성이다.",
            f"시나리오={scen} — 3시나리오×3시드 풀 세트로 봉인(P2-08).",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
