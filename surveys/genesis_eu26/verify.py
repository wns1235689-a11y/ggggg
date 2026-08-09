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
import journal_io  # noqa: E402
from harness_paths import SP, JOURNAL_BASE  # noqa: E402

LEAK_WARN_PCT = 5.0     # 비상기층의 Q1 Genesis 발화율
ECHO_WARN_PCT = 15.0
BMW_FLOOR = 8           # BMW 카드 Y 최소(품질 앵커 — 미달 페르소나는 이상)

BRAND_KEY = {"BMW": "B_dist", "LEXUS": "L_dist", "POLESTAR": "P_dist", "GENESIS": "G_dist"}


def load_rows(run_id):
    rows, info = journal_io.load_rows(JOURNAL_BASE, run_id, "q1_lists")   # F8: gz·손상행 내성
    return rows, info


def run(run_id):
    meta = {m["pid"]: m for m in json.load(open(f"{SP}/pool_meta.json", encoding="utf-8"))}
    rows, jinfo = load_rows(run_id)
    N = len(rows)
    if N == 0 and jinfo["missing"]:
        return {"run_id": run_id, "N": 0, "diagnosable": False,
                "note": "저널 파일 부재 — run_id·경로 확인(진행 중 아님)"}
    if N == 0:
        return {"run_id": run_id, "N": 0, "diagnosable": False, "note": "결과 없음(진행 중)"}

    echo_viol, leak_cases, cnt_mismatch, bmw_low = [], [], [], []
    street_magma_autozero = 0
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
        # ③ 개수 정합: 합=10(F1)·magma 합=G Y수(GP), 거리면 [0,0]; verbatim 수=magma Y
        bad_sums = [k for k in ("B_dist", "L_dist", "P_dist", "G_dist") if sum(r[k]) != 10]
        if bad_sums:
            cnt_mismatch.append({"pid": pid, "why": f"합≠10: {bad_sums}"})
        gy = r["G_dist"][0]
        ms = sum(r["magma_dist"])
        if m["pop"] == "gp_zandvoort":
            if abs(ms - gy) > 1:
                cnt_mismatch.append({"pid": pid, "why": f"magma 합 {ms} vs G_Y {gy}"})
            if abs(len(r["magma_verbatim"]) - r["magma_dist"][0]) > 1:
                cnt_mismatch.append({"pid": pid, "why": f"verbatim {len(r['magma_verbatim'])} vs magmaY {r['magma_dist'][0]}"})
        elif ms != 0:
            street_magma_autozero += 1   # 거리=질문 미실시 — 구조적 0으로 정규화(게이트 아님, 정보만)
        # ④ BMW 품질 앵커 — F10: knows 주입자만 판정(vague/no 주입은 정당한 저 Y)
        if m["know"]["BMW"] == "knows" and r["B_dist"][0] < BMW_FLOOR:
            bmw_low.append({"pid": pid, "B_Y": r["B_dist"][0]})

    echo_rate = round(100 * len(echo_viol) / (N * 4), 1)
    leak_rate = round(100 * len(leak_cases) / max(n_nonrecall_lists, 1), 2)

    # ⑤ vague 상태 검사 + 실현 vague-Y율 노출(P2-05 — 관측공간 역산의 실측 계수)
    vague_viol, vague_y_shares = [], []
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m:
            continue
        for b, key in BRAND_KEY.items():
            if m["know"][b] == "vague":
                y = r[key][0]
                vague_y_shares.append(y / max(sum(r[key]), 1))
                if not (1 <= y <= 8):
                    vague_viol.append({"pid": pid, "brand": b, "why": f"vague인데 Y={y}∉[1,8]"})
    vague_y_mean = round(sum(vague_y_shares) / len(vague_y_shares), 3) if vague_y_shares else None

    # ⑥ 마그마 상태 에코·깊이 누출(P2-05)
    magma_echo, magma_depth_leak = [], []
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m or m["pop"] != "gp_zandvoort":
            continue
        if not m["magma"] and r["magma_dist"][0] > 0:
            magma_echo.append({"pid": pid, "why": f"마그마 상태 False인데 Y={r['magma_dist'][0]}"})
        if m.get("magma_depth") == "vague":
            for v in r["magma_verbatim"]:
                if coding.magma_depth(v) == "specific":
                    magma_depth_leak.append({"pid": pid, "verbatim": v,
                                             "why": "막연 상태인데 구체 회상(GMR·드라이버 등) — 지식 누출"})
    leak_cases.extend(magma_depth_leak)

    # ⑦ 풀 드리프트 z-체크(P2-08): 실현 knows율 vs 기대 p̄ — |z|>2면 재표집 권고
    drift = []
    for pop in ("street_rtm", "gp_zandvoort"):
        ms = [m for m in meta.values() if m["pop"] == pop and m.get("p_know")]
        if not ms:
            continue
        for b in BRAND_KEY:
            sum_p = sum(m["p_know"][b] for m in ms)
            var = sum(m["p_know"][b] * (1 - m["p_know"][b]) for m in ms)
            realized = sum(1 for m in ms if m["know"][b] == "knows")
            z = (realized - sum_p) / (var ** 0.5) if var > 0 else 0.0
            if abs(z) > 2.0:
                drift.append({"pop": pop, "brand": b, "realized": realized,
                              "expected": round(sum_p, 1), "z": round(z, 2)})

    # ⑧ 붕괴/동질성: Q1 목록 다양성·최빈 목록 점유
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
    if len(vague_viol) > max(1, len(vague_y_shares) * 0.2):
        warnings.append({"code": "vague_violation", "value": len(vague_viol),
                         "message": f"vague 상태 Y∉[1,8] {len(vague_viol)}건 — 어렴풋 상태 미준수",
                         "prescription": "프롬프트의 vague 상태 서술 강화"})
    if magma_echo:
        warnings.append({"code": "magma_echo", "value": len(magma_echo),
                         "message": f"마그마 상태 False인데 Y>0 {len(magma_echo)}건 — 상태 에코 위반",
                         "prescription": "마그마 상태 문구 강화(유도형 묵종은 현장 상한 해석으로만)"})
    if drift:
        warnings.append({"code": "pool_drift", "value": len(drift),
                         "message": f"주입 드리프트 |z|>2 {len(drift)}셀: {drift[:4]} — 표집 노이즈가 밴드 압도",
                         "prescription": "다른 시드로 재표집 또는 3시드 풀 세트로 봉인(P2-08)"})

    return {
        "run_id": run_id, "N": N, "diagnosable": True, "journal_skipped_lines": jinfo["skipped"],
        "echo": {"violation_rate_pct": echo_rate, "cases": echo_viol[:10]},
        "leak": {"nonrecall_q1_lines": n_nonrecall_lists, "leak_rate_pct": leak_rate,
                 "cases": leak_cases[:10],
                 "note": "비상기 페르소나의 Q1 Genesis 발화 = LLM 지식 누출(비보조 ≈0 규율 훼손)"},
        "count_consistency": {"mismatches": len(cnt_mismatch), "cases": cnt_mismatch[:10],
                              "street_magma_autozero": street_magma_autozero},
        "vague": {"violations": len(vague_viol), "cases": vague_viol[:10],
                  "realized_y_share_mean": vague_y_mean,
                  "note": "관측공간 역산의 E[Y|vague] 실측치(가정 0.5 검증용)"},
        "magma_state": {"echo_violations": len(magma_echo), "cases": magma_echo[:10],
                        "depth_leaks": len(magma_depth_leak)},
        "pool_drift": {"cells_over_2z": drift,
                       "note": "실현 knows율 vs 기대 p̄ — 봉인은 3시드 세트 권장(P2-08)"},
        "collapse": {"q1_distinct_ratio": distinct_ratio, "q1_modal_share_pct": modal_share,
                     "q1_empty_lists": q1_len_zero},
        "thresholds": {"leak_warn_pct": LEAK_WARN_PCT, "echo_warn_pct": ECHO_WARN_PCT,
                       "bmw_floor": BMW_FLOOR, "_note": "진단 계층 휴리스틱(판정 임계 아님)"},
        "warnings": warnings,
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
