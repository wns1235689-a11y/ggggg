#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로봇 설문 리포트 — 사전등록 예측 문서 포맷 조립 (JSON stdout: {markdown, ...}).

새 통계를 계산하지 않는다 — verify/judge JSON을 렌더만 한다(게이트C 리포트 계층 규율).
⓪ 경고 헤더는 하드코딩·항상 포함·비활성화 옵션 없음.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

import config as C   # noqa: E402
import verify        # noqa: E402
import judge         # noqa: E402
from harness_paths import SP, RUNS_DIR  # noqa: E402

WARNING_HEADER = """## ⓪ 문서 지위 · 필수 경고 (먼저 읽을 것)

- **이 문서의 모든 수치는 LLM 합성·비실측(synthetic, non-empirical)이다.** 실제 유럽 행인 설문이 아니다.
- 용도는 **출발 전 봉인용 사전등록 예측 + 설계리스크 점검**뿐이다. 인용 불가 / 외부에 실측처럼 제시 금지.
- **Q1 수준·노출 경로 구성·국가 서열은 config 스윕 밴드의 '입력 전파'다** — 시뮬이 측정한 것이 아니다.
- 시뮬의 고유 기여(예측의 본체) = 무지 상태의 **오답 구성**(어느 회사로 착각하나) · DK 비율 ·
  프로브 반응 · Q3 형상. 이것도 LLM prior이지 측정이 아니다.
- 검증은 하나뿐이다: **현장 실측(n=60~150) 도착 후 이 문서와의 대조.** 예측이 틀리면 실패가 아니라 발견이다."""


def _fmt(v, dash="—"):
    return dash if v is None else v


def _prereg_table():
    L = ["## ① 사전등록 가설·밴드 (config v1.0 — 잠금 대상)", "",
         "| ID | 주장 | 밴드 | 근거 등급 |", "|---|---|---|---|"]
    for h in C.PREREG:
        band = f"{h['band'][0]}–{h['band'][1]}" if h.get("band") else "—"
        L.append(f"| {h['id']} | {h['claim']} | {band} | {h['basis']} |")
    return "\n".join(L)


def _diag_section(d):
    if not d.get("diagnosable"):
        return "## ③ 진단\n\n_" + d.get("note", "진단 불가") + "_"
    L = ["## ③ 진단 — 에코·누출·붕괴 (verify)", "",
         "| 체크 | 값 | 비고 |", "|---|---|---|",
         f"| 노출상태↔Q1 에코 위반 | {d['echo']['violation_rate_pct']}% | 임계 {d['thresholds']['echo_warn_pct']}% |",
         f"| **지식 누출**(무지식층 정답 발화) | {d['leak']['leak_rate_pct']}% | 임계 {d['thresholds']['leak_warn_pct']}% — 초과 시 런 격하 |",
         f"| 개수 정합 위반 | {d['count_consistency']['mismatches']}건 | q2·프로브 개수 |",
         f"| verbatim 다양성 | {_fmt(d['collapse']['verbatim_distinct_ratio'])} | 낮으면 동질성 |",
         f"| Q3 최빈패턴 점유 | {d['collapse']['q3_modal_pattern_share_pct']}% | 임계 {d['thresholds']['homogeneity_warn_pct']}% |",
         f"| UNCODED verbatim | {d['collapse']['uncoded_pct']}% | 코더 보강 지표 |"]
    warns = d.get("warnings") or []
    if warns:
        L.append("\n### ⚠ 경고")
        for w in warns:
            L.append(f"- **{w['code']}**: {w['message']} → {w['prescription']}")
    else:
        L.append("\n- 경고 없음(임계 내).")
    return "\n".join(L)


def _judge_section(j):
    if not j.get("judgeable"):
        return "## ④ 판정\n\n_" + j.get("note", "판정 불가") + "_"
    L = [f"## ④ 판정 — 사전등록 가설 판독 (judge · 시나리오={j.get('scenario')})", ""]
    L.append(f"- 가상 응답자 {j['total_sim_people']}명 중 Q1=Y {j['n_y_people']}명 · Q2 코딩 합계: "
             + ", ".join(f"{k} {v}" for k, v in sorted(j["q2_coded_total"].items(), key=lambda kv: -kv[1])))
    L.append("\n| ID | 결과 | 판정 |\n|---|---|---|")
    for h in j["hypotheses"]:
        hid = h["id"]
        if hid == "H1":
            res = f"DK {h['value']}"
        elif hid == "H2":
            res = "오답랭킹 " + ", ".join(f"{k}:{v}" for k, v in h["wrong_ranking"][:3]) if h["wrong_ranking"] else "오답 없음"
        elif hid == "H3":
            res = f"BD {h['bd_named']} vs 현대 {h['hyundai_named']} (비 {_fmt(h['ratio'])})"
        elif hid == "H4":
            res = f"프로브A n={h['probeA_n']}, 현대 {_fmt(h['hyundai_share'])}, 낡은답 {h['stale_present']}"
        elif hid == "H5":
            res = f"tv_live 점유 {h['tv_live_share']} (주입)"
        elif hid == "H6":
            res = json.dumps(h["q1_by_country"], ensure_ascii=False)
        elif hid == "H7":
            res = f"n=150 투영 분기A ≈{h['projected_branchA_at_n150']}회"
        elif hid == "H8":
            res = f"E: <30 {h['excited']['<30']} vs 50+ {h['excited']['50+']} / W: {h['worried']['<30']} vs {h['worried']['50+']}"
        elif hid == "H9":
            res = (f"혼동층 {h['conflated_personas']}명, Y기여 {h['conflated_y_people']}명"
                   f"({h['conflated_y_share_of_all_y']}), 코딩 {h['conflated_coded']}")
        else:
            res = "—"
        L.append(f"| {hid} | {res} | {h['verdict']} |")
    if j.get("q3_vs_anchor"):
        L.append("\n### Q3 국가별 vs 앵커 (참고 — 성향 주입으로 부분 순환)")
        L.append("\n| 국가 | sim E/W/M | 앵커 E/W/M | Δpp |\n|---|---|---|---|")
        for k, v in j["q3_vs_anchor"].items():
            L.append(f"| {k} | {v['sim_EWM']} | {v['anchor_EWM']} | {v['delta_pp']} |")
    L.append("\n### 한계(덮지 않음)")
    for c in j.get("caveats", []):
        L.append(f"- {c}")
    return "\n".join(L)


def _field_protocol():
    return """## ⑤ 현장 대조 절차 (실측 도착 후)

1. 현장 시트를 §6 코딩(+DESC 부록 코드)으로 판정 → 이 문서의 H1~H8 표와 1:1 대조.
2. **L-주장률**이 시뮬 tv_live 상단을 크게 넘으면: 사전등록 규칙에 따라 '기억 재구성(클립→생중계 오귀속)' 후보로 해석.
3. 분기A 실발동 수를 H7 투영과 대조 — 15회 미만이면 프로브 결과는 일화로만 기술.
4. 국가별 Q1은 표본이 작으므로(도시당 ≤15) BE/DE/NL 서열 방향만 대조, %p 차이는 해석 금지.
5. **혼동 분리(H9)**: verbatim에 'dog/robot dog/순찰' 계열 발화가 있으면 Spot·Unitree 혼동 후보로
   태그 — Atlas 공연 인지와 합산하지 말 것(EU 로봇개 보도 실재·멕시코 Unitree는 현대와 무관).
6. 어긋난 밴드는 실패가 아니라 발견 — config 밴드·근거 등급과 함께 그대로 기록."""


def run(run_id):
    d = verify.run(run_id)
    j = judge.run(run_id)
    params = {}
    try:
        params = json.load(open(os.path.join(RUNS_DIR, run_id, "params.json"), encoding="utf-8"))
    except Exception:
        pass
    cfg = {}
    try:
        cfg = json.load(open(f"{SP}/run_cfg.json", encoding="utf-8"))
    except Exception:
        pass
    pp = (params.get("params") or {})
    exec_rows = [("run_id", run_id), ("설문", "robot_wc26 (월드컵 하프타임 로봇 인지)"),
                 ("N(페르소나)", _fmt(cfg.get("N"))), ("시나리오", _fmt(cfg.get("scenario"))),
                 ("시드", _fmt(cfg.get("RUN_SEED"))), ("effort", _fmt(pp.get("effort"))),
                 ("dry_run", _fmt(pp.get("dry_run"))), ("결과 수", d.get("N"))]
    exec_md = "## ② 실행 로그 (재현 정보)\n\n| 항목 | 값 |\n|---|---|\n" + \
        "\n".join(f"| {k} | {v} |" for k, v in exec_rows)
    md = "\n\n".join([
        f"# 로봇 미니 설문 — LLM 합성 시뮬 사전등록 리포트 · 런 `{run_id}`",
        WARNING_HEADER, _prereg_table(), exec_md, _diag_section(d), _judge_section(j),
        _field_protocol(),
        "---\n_생성: Research Harness 리포트 계층(조립 전용·새 통계 없음). 수치 출처 = verify(진단)·judge(판정)._",
    ])
    return {"run_id": run_id, "survey_id": "robot_wc26", "warning_included": True,
            "markdown": md, "diagnosis": d, "judgment": j}


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
