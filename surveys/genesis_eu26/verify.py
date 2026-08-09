#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""제네시스 설문 진단 — 에코·비보조 누출·카드 정합·붕괴 (JSON stdout 플러그인)."""
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

import coding  # noqa: E402
from harness_paths import SP, JOURNAL_BASE  # noqa: E402

LEAK_WARN_PCT = 5.0     # 비상기층의 Q1 Genesis 발화율
ECHO_WARN_PCT = 15.0
BMW_FLOOR = 8           # BMW 카드 Y 최소(품질 앵커 — 미달 페르소나는 이상)

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
    meta = {m["pid"]: m for m in json.load(open(f"{SP}/pool_meta.json", encoding="utf-8"))}
    rows = load_rows(run_id)
    N = len(rows)
    if N == 0:
        return {"run_id": run_id, "N": 0, "diagnosable": False, "note": "결과 없음(진행 중)"}

    echo_viol, leak_cases, cnt_mismatch, bmw_low = [], [], [], []
    n_nonrecall_lists = 0
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m:
            continue
        # ① 에코: 주입 인지상태 ↔ 카드 Y수 (knows≥7, no≤2+예스세잉 여유, vague는 광폭)
        for b, key in BRAND_KEY.items():
            y = r[key][0]
            st = m["know"][b]
            if st == "knows" and y < 7:
                echo_viol.append({"pid": pid, "brand": b, "why": f"knows인데 Y={y}<7"})
            elif st == "no" and y > 3:
                echo_viol.append({"pid": pid, "brand": b, "why": f"no인데 Y={y}>3(예스세잉 초과)"})
        # ② 비보조 누출: 상기 플래그 없는 페르소나의 Q1에 Genesis
        if not m["unaided_genesis"]:
            for line in r["q1_lists"]:
                n_nonrecall_lists += 1
                if "GENESIS" in coding.norm_brands(line):
                    leak_cases.append({"pid": pid, "line": line})
        else:
            n_nonrecall_lists += 0
        # ③ 개수 정합: magma 합=G Y수(GP), 거리면 [0,0]; verbatim 수=magma Y
        gy = r["G_dist"][0]
        ms = sum(r["magma_dist"])
        if m["pop"] == "gp_zandvoort":
            if abs(ms - gy) > 1:
                cnt_mismatch.append({"pid": pid, "why": f"magma 합 {ms} vs G_Y {gy}"})
            if abs(len(r["magma_verbatim"]) - r["magma_dist"][0]) > 1:
                cnt_mismatch.append({"pid": pid, "why": f"verbatim {len(r['magma_verbatim'])} vs magmaY {r['magma_dist'][0]}"})
        elif ms != 0:
            cnt_mismatch.append({"pid": pid, "why": f"거리인데 magma_dist 합 {ms}≠0"})
        # ④ BMW 품질 앵커
        if r["B_dist"][0] < BMW_FLOOR:
            bmw_low.append({"pid": pid, "B_Y": r["B_dist"][0]})

    echo_rate = round(100 * len(echo_viol) / (N * 4), 1)
    leak_rate = round(100 * len(leak_cases) / max(n_nonrecall_lists, 1), 2)

    # ⑤ 붕괴/동질성: Q1 목록 다양성·최빈 목록 점유
    all_lists = [",".join(coding.norm_brands(x)) for r in rows.values() for x in r["q1_lists"]]
    distinct_ratio = round(len(set(all_lists)) / max(len(all_lists), 1), 3)
    modal_share = round(100 * Counter(all_lists).most_common(1)[0][1] / max(len(all_lists), 1), 1)
    q1_len_zero = sum(1 for x in all_lists if not x)

    warnings = []
    if leak_rate > LEAK_WARN_PCT:
        warnings.append({"code": "unaided_leak", "value": leak_rate,
                         "message": f"비상기층 Q1 Genesis 발화 {leak_rate}% — 비보조 상기 오염(LLM 지식 누출)",
                         "prescription": "프롬프트 규율 문구 강화 또는 런 격하"})
    if echo_rate > ECHO_WARN_PCT:
        warnings.append({"code": "echo_violation", "value": echo_rate,
                         "message": f"인지상태↔카드 에코 위반 {echo_rate}%",
                         "prescription": "인지 상태 서술 강화"})
    if modal_share >= 30.0:
        warnings.append({"code": "q1_homogeneity", "value": modal_share,
                         "message": f"Q1 최빈 목록 점유 {modal_share}% — 비보조 구성 동질화",
                         "prescription": "effort 상향·유형 조건화 강화"})
    if bmw_low:
        warnings.append({"code": "bmw_anchor", "value": len(bmw_low),
                         "message": f"BMW 카드 Y<{BMW_FLOOR} 페르소나 {len(bmw_low)}명 — 품질 앵커 이상",
                         "prescription": "해당 페르소나 응답 검토(현장 규칙: BMW 모름=품질의심)"})

    return {
        "run_id": run_id, "N": N, "diagnosable": True,
        "echo": {"violation_rate_pct": echo_rate, "cases": echo_viol[:10]},
        "leak": {"nonrecall_q1_lines": n_nonrecall_lists, "leak_rate_pct": leak_rate,
                 "cases": leak_cases[:10],
                 "note": "비상기 페르소나의 Q1 Genesis 발화 = LLM 지식 누출(비보조 ≈0 규율 훼손)"},
        "count_consistency": {"mismatches": len(cnt_mismatch), "cases": cnt_mismatch[:10]},
        "collapse": {"q1_distinct_ratio": distinct_ratio, "q1_modal_share_pct": modal_share,
                     "q1_empty_lists": q1_len_zero},
        "thresholds": {"leak_warn_pct": LEAK_WARN_PCT, "echo_warn_pct": ECHO_WARN_PCT,
                       "bmw_floor": BMW_FLOOR, "_note": "진단 계층 휴리스틱(판정 임계 아님)"},
        "warnings": warnings,
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
