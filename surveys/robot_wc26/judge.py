#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로봇 설문 판정 — 사전등록 가설 H1~H8 판독 (JSON stdout 플러그인).

순환 경계(항상 명시): Q1 수준·채널믹스·국가서열(H5·H6)은 config 밴드의 **입력 전파**로
'사전등록 예측'이지 시뮬의 발견이 아니다. LLM 고유 기여(발견 후보) = 오답 구성(H2),
DK 비율(H1), BD:현대 비(H3), 프로브 반응(H4), Q3 형상(H8).
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


def load_rows(run_id):
    rows = {}
    for line in open(os.path.join(JOURNAL_BASE, run_id, "journal.jsonl"), encoding="utf-8"):
        o = json.loads(line)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "q2_verbatim" in r:
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
    total_sim_people = 10 * N

    def share(codes):
        return round(sum(q2.get(c, 0) for c in codes) / n_y, 3) if n_y else None

    # H1 DK 지배
    dk = share(["DK"])
    h1 = {"id": "H1", "value": dk, "band": (0.40, 0.60),
          "verdict": ("밴드 내(지지)" if dk is not None and 0.40 <= dk <= 0.60
                      else "밴드 위(무지 과대)" if dk is not None and dk > 0.60 else "밴드 아래(지식 과대)")}

    # H2 특정 기업 오답 1위
    wrongs = {k: v for k, v in q2.items() if k.startswith("W-")}
    wrong_rank = sorted(wrongs.items(), key=lambda kv: -kv[1])
    h2 = {"id": "H2", "wrong_ranking": wrong_rank[:6],
          "top_wrong": wrong_rank[0][0] if wrong_rank else None,
          "verdict": ("지지(Tesla 1위)" if wrong_rank and wrong_rank[0][0] == "W-TESLA"
                      else "반증" if wrong_rank else "오답 표본 없음")}

    # H3 BD명명 vs 현대명명 비
    bd_n = sum(q2.get(c, 0) for c in ("A2", "A3"))
    hy_n = sum(q2.get(c, 0) for c in ("A1", "A3"))
    ratio = round(bd_n / hy_n, 2) if hy_n else None
    h3 = {"id": "H3", "bd_named": bd_n, "hyundai_named": hy_n, "ratio": ratio, "band": (1.5, 6.0),
          "verdict": ("밴드 내(지지)" if ratio is not None and 1.5 <= ratio <= 6.0
                      else "현대 명명 0(비 미정의·방향은 지지)" if hy_n == 0 and bd_n > 0
                      else "밴드 밖" if ratio is not None else "표본 부족")}

    # H4 프로브A: BD 명명자의 소유주 지식
    pa = Counter()
    for r in rows.values():
        for v in r["probeA_verbatim"]:
            pa[coding.code_probe_a(v)] += 1
    pa_n = sum(pa.values())
    pa_hy = round(pa.get("HYUNDAI", 0) / pa_n, 3) if pa_n else None
    h4 = {"id": "H4", "probeA_n": pa_n, "coded": dict(pa), "hyundai_share": pa_hy,
          "band": (0.15, 0.30),
          "stale_present": (pa.get("GOOGLE_STALE", 0) + pa.get("SOFTBANK_STALE", 0)) > 0,
          "verdict": ("밴드 내(지지)" if pa_hy is not None and 0.15 <= pa_hy <= 0.30
                      else "표본 부족(H7 참조)" if pa_n < 8 else "밴드 밖")}

    # H5 채널믹스(입력 전파) + 채널별 귀속 조건부(LLM 기여)
    ch_mix = Counter((m.get("channel") or "none") for m in meta.values() if m.get("exposed"))
    ch_attr = {ch: {"n": sum(cnt.values()),
                    "hyundai_pct": round(100 * sum(cnt.get(c, 0) for c in ("A1", "A3")) / max(sum(cnt.values()), 1), 1),
                    "bd_pct": round(100 * sum(cnt.get(c, 0) for c in ("A2", "A3")) / max(sum(cnt.values()), 1), 1)}
               for ch, cnt in q2_by_channel.items() if ch != "none"}
    l_share = round(ch_mix.get("tv_live", 0) / max(sum(ch_mix.values()), 1), 3)
    h5 = {"id": "H5", "channel_mix_injected": dict(ch_mix), "tv_live_share": l_share,
          "attribution_by_channel": ch_attr,
          "note": "채널믹스=입력 전파(측정 아님). 현장 L-주장률이 이 상단을 크게 넘으면 '기억 재구성' 해석(사전등록 규칙)",
          "verdict": "S+N≫L 구조 확인(입력 전파)" if l_share < 0.15 else "L 과대(입력 확인 요)"}

    # H6 국가 Q1 서열(입력 전파 확인)
    ctry_y = {}
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m:
            continue
        ctry_y.setdefault(m["res_country"], []).append(r["Q1_dist"][0] / 10)
    ctry_rate = {k: round(sum(v) / len(v), 3) for k, v in ctry_y.items() if len(v) >= 3}
    ord_ok = all(k in ctry_rate for k in ("BE", "DE", "NL")) and \
        ctry_rate.get("BE", 0) > ctry_rate.get("DE", 0) > ctry_rate.get("NL", 0)
    h6 = {"id": "H6", "q1_by_country": dict(sorted(ctry_rate.items(), key=lambda kv: -kv[1])),
          "verdict": ("BE>DE>NL 전파 확인" if ord_ok else "서열 미확인(표본·노이즈)"),
          "note": "입력 밴드 전파 — 시뮬 발견 아님"}

    # H7 현장 규모 투영: n=150에서 분기A 발동수
    y_rate = n_y / total_sim_people
    bd_rate_among_y = (bd_n / n_y) if n_y else 0
    proj_a = round(C.FIELD_PLAN["n_target"] * y_rate * bd_rate_among_y, 1)
    h7 = {"id": "H7", "sim_y_rate": round(y_rate, 3), "bd_rate_among_y": round(bd_rate_among_y, 3),
          "projected_branchA_at_n150": proj_a,
          "verdict": (f"경고 지지 — 분기A ≈{proj_a}회(<{C.FIELD_PLAN['branchA_warn_min']}): 일화 수준"
                      if proj_a < C.FIELD_PLAN["branchA_warn_min"] else "분기A 표본 확보 가능")}

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
          "verdict": "경사 재현(지지)" if grad_ok else "경사 미재현"}

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

    # 국가별 Q3 vs 앵커(참고 — 부분 순환: 성향 주입됨)
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
        "q3_vs_anchor": q3_vs_anchor,
        "caveats": [
            "Q1 수준·채널믹스·국가서열은 config 스윕 밴드의 입력 전파 — 사전등록 예측이지 발견 아님.",
            "LLM 고유 기여(발견 후보) = 오답 구성(H2)·DK 비율(H1)·BD:현대 비(H3)·프로브 반응(H4)·Q3 형상(H8).",
            "모든 수치는 합성·비실측 — 인용 불가. 현장 n=60~150 도착 후 대조가 이 문서의 완성이다.",
            f"시나리오={scen} — 다른 시나리오 풀과 함께 봐야 밴드가 완성됨.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
