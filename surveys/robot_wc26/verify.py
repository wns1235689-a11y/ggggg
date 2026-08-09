#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로봇 설문 진단 — 에코 정합·지식 누출·붕괴 체크 (JSON stdout 플러그인).

게이트C v23_verify와 동일 계약: python3 <script> <run_id> + harness_paths 환경변수.
이 설문 고유 진단 = **지식 누출**: '모름/서술만' 상태 페르소나의 verbatim에서 정답
(BD/현대)이 새어나오면 시뮬 타당성 훼손 → 격하 경고. (LLM은 정답을 알므로 이 체크가 필수)
"""
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

import coding  # noqa: E402  (같은 디렉토리)
from harness_paths import SP, JOURNAL_BASE  # noqa: E402

# 진단 계층 휴리스틱 임계(판정 임계 아님)
LEAK_WARN_PCT = 5.0          # 무지식층 정답 발화율
ECHO_WARN_PCT = 15.0         # 노출상태↔Q1 에코 위반율
HOMOG_WARN_PCT = 55.0        # Q3 최빈패턴 점유


def load_rows(run_id):
    rows = {}
    for line in open(os.path.join(JOURNAL_BASE, run_id, "journal.jsonl"), encoding="utf-8"):
        o = json.loads(line)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "q2_verbatim" in r:
            rows[r["pid"]] = r
    return rows


def run(run_id):
    meta = {m["pid"]: m for m in json.load(open(f"{SP}/pool_meta.json", encoding="utf-8"))}
    rows = load_rows(run_id)
    N = len(rows)
    if N == 0:
        return {"run_id": run_id, "N": 0, "diagnosable": False, "note": "결과 없음(진행 중)"}

    # ── ① 에코 정합: 주입한 노출 상태 ↔ Q1_dist ──
    echo_viol = []
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m:
            continue
        y = r["Q1_dist"][0]
        if m["exposed"] and m["strength"] == "clear" and y < 7:
            echo_viol.append({"pid": pid, "why": f"선명 노출인데 Y={y}<7"})
        elif m["exposed"] and m["strength"] == "faint" and not (2 <= y <= 9):
            echo_viol.append({"pid": pid, "why": f"희미 노출인데 Y={y}∉[2,9]"})
        elif not m["exposed"] and y > 2:
            echo_viol.append({"pid": pid, "why": f"비노출인데 Y={y}>2"})
    echo_rate = round(100 * len(echo_viol) / N, 1)

    # ── ② 지식 누출: 무지식층 verbatim의 정답 발화 ──
    leak_cases = []
    n_uninformed_verbatim = 0
    for pid, r in rows.items():
        m = meta.get(pid)
        if not m or m["knowledge"] not in ("none", "desc_only"):
            continue
        for v in r["q2_verbatim"]:
            n_uninformed_verbatim += 1
            c = coding.code_q2(v)
            if c in ("A1", "A2", "A3"):
                leak_cases.append({"pid": pid, "verbatim": v, "code": c})
    leak_rate = round(100 * len(leak_cases) / n_uninformed_verbatim, 1) if n_uninformed_verbatim else 0.0

    # ── ③ 개수 정합: len(q2_verbatim)=Q1 Y수, 프로브 수=명명자 수 ──
    cnt_mismatch = []
    for pid, r in rows.items():
        y = r["Q1_dist"][0]
        if len(r["q2_verbatim"]) != y:
            cnt_mismatch.append({"pid": pid, "why": f"q2 {len(r['q2_verbatim'])}개 ≠ Y {y}"})
        codes = [coding.code_q2(v) for v in r["q2_verbatim"]]
        n_bd = sum(1 for c in codes if c in ("A2", "A3"))
        n_hy = sum(1 for c in codes if c in ("A1", "A3"))
        if abs(len(r["probeA_verbatim"]) - n_bd) > 1:
            cnt_mismatch.append({"pid": pid, "why": f"probeA {len(r['probeA_verbatim'])} vs BD명명 {n_bd}"})
        if abs(len(r["probeB_verbatim"]) - n_hy) > 1:
            cnt_mismatch.append({"pid": pid, "why": f"probeB {len(r['probeB_verbatim'])} vs 현대명명 {n_hy}"})

    # ── ④ 붕괴/동질성: verbatim 다양성·Q3 최빈패턴·UNCODED ──
    all_v = [v.strip().lower() for r in rows.values() for v in r["q2_verbatim"]]
    distinct_ratio = round(len(set(all_v)) / len(all_v), 3) if all_v else None
    q3_patterns = Counter(tuple(r["Q3_dist"]) for r in rows.values())
    q3_modal = round(100 * q3_patterns.most_common(1)[0][1] / N, 1)
    codes_all = Counter(coding.code_q2(v) for r in rows.values() for v in r["q2_verbatim"])
    uncoded = codes_all.get("UNCODED", 0)
    uncoded_pct = round(100 * uncoded / max(sum(codes_all.values()), 1), 1)

    warnings = []
    if leak_rate > LEAK_WARN_PCT:
        warnings.append({"code": "knowledge_leak", "value_pct": leak_rate,
                         "message": f"무지식층 정답 발화 {leak_rate}% (> {LEAK_WARN_PCT}%) — 시뮬 타당성 훼손",
                         "prescription": "프롬프트의 지식상태 사실 규정 강화 또는 해당 런 격하(판정 인용 금지)"})
    if echo_rate > ECHO_WARN_PCT:
        warnings.append({"code": "echo_violation", "value_pct": echo_rate,
                         "message": f"노출상태↔Q1 에코 위반 {echo_rate}% (> {ECHO_WARN_PCT}%)",
                         "prescription": "노출 상태 문구가 프롬프트에서 약함 — 상태 서술 강화"})
    if q3_modal >= HOMOG_WARN_PCT:
        warnings.append({"code": "homogeneity", "value_pct": q3_modal,
                         "message": f"Q3 최빈패턴 점유 {q3_modal}% — 페르소나간 동질성 높음",
                         "prescription": "effort 상향 또는 특성-조건화 강화(게이트C §2c 처방 준용)"})
    if uncoded_pct > 10.0:
        warnings.append({"code": "uncoded_verbatim", "value_pct": uncoded_pct,
                         "message": f"UNCODED verbatim {uncoded_pct}% — 코더 사전 보강 필요",
                         "prescription": "coding.py 키워드 확장(수동 검토 목록 확인)"})

    return {
        "run_id": run_id, "N": N, "diagnosable": True,
        "echo": {"violation_rate_pct": echo_rate, "cases": echo_viol[:10]},
        "leak": {"uninformed_verbatims": n_uninformed_verbatim, "leak_rate_pct": leak_rate,
                 "cases": leak_cases[:10],
                 "note": "무지식(none/desc_only) 페르소나의 A1/A2/A3 발화 — LLM 정답지식 누출 검출"},
        "count_consistency": {"mismatches": len(cnt_mismatch), "cases": cnt_mismatch[:10]},
        "collapse": {"verbatim_distinct_ratio": distinct_ratio,
                     "q3_modal_pattern_share_pct": q3_modal,
                     "q2_code_preview": dict(codes_all), "uncoded_pct": uncoded_pct},
        "thresholds": {"leak_warn_pct": LEAK_WARN_PCT, "echo_warn_pct": ECHO_WARN_PCT,
                       "homogeneity_warn_pct": HOMOG_WARN_PCT,
                       "_note": "진단 계층 휴리스틱(판정 임계 아님)"},
        "warnings": warnings,
    }


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
