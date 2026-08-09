#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""제네시스 설문 리포트 — 사전등록 예측 문서 조립 (JSON stdout: {markdown, ...}).
새 통계 없음 — verify/judge JSON 렌더만. ⓪ 경고 헤더 하드코딩·항상 포함."""
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

- **이 문서의 모든 수치는 LLM 합성·비실측이다.** 실제 유럽 행인·GP 관중 설문이 아니다.
- 용도는 **출발 전 봉인용 사전등록 예측 + 설계리스크 점검**뿐. 인용 불가 / 실측처럼 제시 금지.
- **보조 인지 수준·GP↔거리 격차 크기·마그마 조건부 수준은 config 스윕 밴드의 '입력 전파'다.**
- 시뮬 고유 기여 = 비보조 브랜드 구성 · 연령/EV 조건부 역전 · 예스세잉 형상 · 마그마 회상 내용.
  이것도 LLM prior이지 측정이 아니다.
- 가설편(인간 예측)과 **독립** 생성됨 — 3자 대조(인간 예측 vs 시뮬 예측 vs 실측)가 설계 의도다.
- 예측이 틀리면 실패가 아니라 발견이다."""


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
    L = ["## ③ 진단 — 에코·누출·정합·붕괴 (verify)", "",
         "| 체크 | 값 | 비고 |", "|---|---|---|",
         f"| 인지상태↔카드 에코 위반 | {d['echo']['violation_rate_pct']}% | 임계 {d['thresholds']['echo_warn_pct']}% |",
         f"| **비보조 누출**(비상기층 Q1 Genesis) | {d['leak']['leak_rate_pct']}% | 임계 {d['thresholds']['leak_warn_pct']}% — 초과 시 격하 |",
         f"| 개수 정합(마그마) | {d['count_consistency']['mismatches']}건 | |",
         f"| Q1 목록 다양성 | {_fmt(d['collapse']['q1_distinct_ratio'])} | 최빈 점유 {d['collapse']['q1_modal_share_pct']}% |"]
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
    L = [f"## ④ 판정 — 사전등록 GH 판독 (judge · 시나리오={j.get('scenario')} · 거리 {j.get('n_street')}+GP {j.get('n_gp')})", ""]
    L.append("| ID | 결과 | 판정 |\n|---|---|---|")
    for h in j["hypotheses"]:
        hid = h["id"]
        if hid == "GH1":
            res = f"비보조 Genesis {h['unaided_genesis_rate_street']} ({h['mentions']}건) · 상위: " + \
                  ", ".join(f"{b}:{c}" for b, c in h["street_unaided_top"][:5]) + " (*=카드 브랜드·판독 제외)"
        elif hid == "GH2":
            res = (f"관측 {json.dumps(h['street_card_shares_observed'], ensure_ascii=False)} · "
                   f"상태 Genesis {_fmt(h['street_knows_states'].get('GENESIS'))} "
                   f"[파생관측밴드 {h['derived_obs_band_genesis']}]")
        elif hid == "GH3":
            res = (f"상태비 {_fmt(h['state_ratio'])} (knows GP {_fmt(h['knows_gp'])} vs 거리 {_fmt(h['knows_street'])}) · "
                   f"관측 카드비 {_fmt(h['card_ratio_observed'])}")
        elif hid == "GH4":
            res = (f"P(마그마|GenY)={_fmt(h['p_magma_given_genesis'])} (분모 {h['denom_gen_y']}) · "
                   f"깊이 {h['depth_coded']}")
        elif hid == "GH5":
            res = " / ".join(f"{p}: young_ev {s['young_ev']['POLESTAR']}vs{s['young_ev']['LEXUS']}"
                             f"(n={s['young_ev']['n']}) → {s['pattern']}"
                             for p, s in h["by_pop"].items())
        elif hid == "GH6":
            res = f"예스세잉 실현 {_fmt(h['yes_saying_realized'])} (주입 {h['injected']})"
        elif hid == "GH7":
            res = json.dumps(h["projected_genesis_y"])
        elif hid == "GH8":
            res = f"마그마 발동 투영 {h['projected_magma_askable']}회"
        else:
            res = "—"
        L.append(f"| {hid} | {res} | {h['verdict']} |")
    L.append("\n### 한계(덮지 않음)")
    for c in j.get("caveats", []):
        L.append(f"- {c}")
    return "\n".join(L)


def _field_protocol():
    return """## ⑤ 현장 대조 절차 (실측 도착 후)

1. 시트를 브랜드 정규화(coding.norm_brands 규칙)로 판정 → GH1~GH8 표와 1:1 대조.
2. **BMW 품질 앵커**: BMW=N 응답은 현장 규칙대로 품질의심 태그 — 헤드라인 분모에서 별도 표기.
3. **grp 규칙(매뉴얼 원문 그대로)**: Q1 비보조는 grp 행 제외(앞사람 답 오염), **카드 4종 Y/N은
   grp 행도 유효**("로고 인지는 각자 유효" — DAY1 ①-1). 문항별로 분모가 달라짐에 유의.
4. Genesis 카드 Y는 **상한 해석**(GH6): 실측 Y율이 예스세잉 바닥(2~8%)과 겹치면 "인지 존재" 주장 금지.
5. GP↔거리 격차는 **방향·배수만**(GH7) — n이 작아 %p 차이 해석 금지. 로고카드 2버전 순서효과는
   버전별 분리 집계 후 합산.
6. 마그마 답변의 원문을 깊이 코딩(specific/vague)해 GH4의 깊이 분포와 대조 — '막연 Y' 지배가 예측.
7. 어긋난 밴드는 실패가 아니라 발견 — config 밴드·근거 등급과 함께 그대로 기록."""


def run(run_id):
    d = verify.run(run_id)
    j = judge.run(run_id)
    cfg = {}
    try:
        cfg = json.load(open(f"{SP}/run_cfg.json", encoding="utf-8"))
    except Exception:
        pass
    params = {}
    try:
        params = json.load(open(os.path.join(RUNS_DIR, run_id, "params.json"), encoding="utf-8"))
    except Exception:
        pass
    pp = (params.get("params") or {})
    exec_rows = [("run_id", run_id), ("설문", "genesis_eu26 (로테르담 거리 + 잔드보르트 GP)"),
                 ("N", f"{cfg.get('N')} (거리 {cfg.get('n_street')} + GP {cfg.get('n_gp')})"),
                 ("시나리오", _fmt(cfg.get("scenario"))), ("시드", _fmt(cfg.get("RUN_SEED"))),
                 ("effort", _fmt(pp.get("effort"))), ("dry_run", _fmt(pp.get("dry_run"))),
                 ("결과 수", d.get("N"))]
    exec_md = "## ② 실행 로그 (재현 정보)\n\n| 항목 | 값 |\n|---|---|\n" + \
        "\n".join(f"| {k} | {v} |" for k, v in exec_rows)
    md = "\n\n".join([
        f"# 제네시스 유럽 인지 설문 — LLM 합성 시뮬 사전등록 리포트 · 런 `{run_id}`",
        WARNING_HEADER, _prereg_table(), exec_md, _diag_section(d), _judge_section(j),
        _field_protocol(),
        "---\n_생성: Research Harness 리포트 계층(조립 전용·새 통계 없음). 수치 출처 = verify(진단)·judge(판정)._",
    ])
    return {"run_id": run_id, "survey_id": "genesis_eu26", "warning_included": True,
            "markdown": md, "diagnosis": d, "judgment": j}


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
