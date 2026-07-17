# -*- coding: utf-8 -*-
"""리포트 조립 계층(SPEC §5.4 리포트 내보내기).

게이트C_시뮬결과_정리.md 포맷으로 **한 런**의 진단(v23_verify)+판정(v23_judge/
v23_multi_judge) JSON을 채워 Markdown을 생성한다. 이 계층은 **새 통계를 계산하지
않는다** — 판정·진단 스크립트가 낸 값을 렌더만 한다(엔진/판정 무변경).

⓪ 경고 헤더는 모듈 상수로 하드코딩되어 **항상** 선두에 들어간다. 비활성화 인자
자체를 두지 않는다(SPEC §5.4: "비활성화 옵션 자체를 만들지 않음"). 헤더 문구는
게이트C_시뮬결과_정리.md ⓪ 절에서 그대로 복사.
"""
from . import store, analysis

# ── ⓪ 경고 헤더 (하드코딩·항상 포함·끌 수 없음) — 게이트C_시뮬결과_정리.md ⓪ 절 동일 복사 ──
WARNING_HEADER = """## ⓪ 문서 지위 · 필수 경고 (먼저 읽을 것)

- **이 문서의 모든 수치는 LLM 합성·비실측(synthetic, non-empirical)이다.** 실제 한국 소비자 설문이 아니다.
- **여기서 나온 "방향"은 LLM의 보정된 믿음(prior)이지 측정치가 아니다.** 유병률·수용률·효과크기의 **절대값은 신뢰 불가**.
- **인용 불가 / 외부에 실측처럼 제시 금지.** 내부 계획 점검용 directional prior로만 사용.
- 특히 **유병률(향 기피 비율) 수준은 시뮬로 판정 불가**(모델 latent에 앵커됨) → 그건 **실측(파일럿)의 몫**.
- 시뮬이 잘하는 것 = "무엇이 무엇과 같은/반대 방향으로 움직이는가"(부호·상대). 못하는 것 = "실제로 몇 %인가"(수준)."""


def _fmt(v, dash="—"):
    return dash if v is None else v


def _exec_log(meta):
    """③ 실행 로그(재현 정보) — 런 params/메타에서 채움."""
    pp = ((meta.get("params") or {}).get("params") or {})
    rows = [
        ("run_id", meta.get("run_id")),
        ("종류", meta.get("kind")),
        ("N(표본)", _fmt(pp.get("N", meta.get("N")))),
        ("effort", _fmt(pp.get("effort"))),
        ("시드", _fmt(meta.get("seed"))),
        ("스크립트", _fmt(pp.get("script"))),
        ("풀", _fmt(pp.get("pool_id"))),
        ("dry_run", _fmt(pp.get("dry_run"))),
        ("결과 수", _fmt(meta.get("result_count"))),
    ]
    body = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return "## ③ 실행 로그 (재현 정보)\n\n| 항목 | 값 |\n|---|---|\n" + body


def _diag_section(diag):
    """진단(붕괴·동질성) — v23_verify JSON 렌더. 새 판정 없음(값은 v23_verify가 낸 것)."""
    if not diag or not diag.get("diagnosable"):
        note = (diag or {}).get("note", "진단 대상 아님(v2.3 저널만 진단).")
        return "## ④ 진단 — 붕괴/동질성\n\n_" + note + "_"
    cc = diag.get("collapse_checks", {})
    th = diag.get("thresholds", {})
    lines = ["## ④ 진단 — 붕괴/동질성 (v23_verify)", ""]

    # 붕괴 3종 + 유병률 요약 체크
    lines.append("### 붕괴/동질성 체크")
    homog = cc.get("cross_persona_homogeneity") or {}
    e1n = cc.get("within_item_E1_neutral") or {}
    ou = cc.get("option_usage") or {}
    a2p = cc.get("A2_prevalence_info") or {}
    lines.append("\n| 체크 | 값 | 상태 |\n|---|---|---|")
    lines.append(f"| 페르소나 간 동질성(최빈패턴 점유 최악) | {homog.get('worst_field')} "
                 f"{_fmt(homog.get('modal_share_pct'))}% | {homog.get('status')} |")
    lines.append(f"| 문항 내 붕괴(E1 중립 realized) | {e1n.get('비슷+둘다_realized')} | {e1n.get('status')} |")
    lines.append(f"| 보기 사용률(최소) | {ou.get('worst_field')} {_fmt(ou.get('min_used_ratio'))} | — |")
    lines.append(f"| A2 향부담 광의 믿음질량(참고·수준 신뢰X) | {_fmt(a2p.get('향부담_광의_믿음질량_pct'))}% | 참고 |")
    warn = th.get("homogeneity_modal_share_warn_pct")
    high = th.get("homogeneity_modal_share_high_pct")
    lines.append(f"\n> 휴리스틱 임계(진단계층·엔진 아님): 최빈패턴 점유 경고≥{_fmt(warn)}% / 높음≥{_fmt(high)}%.")

    # 보기별 믿음질량 vs realized + 최빈패턴 점유율(문항 내부)
    items = diag.get("items") or {}
    if items:
        lines.append("\n### 문항별 — 보기 사용·최빈패턴 점유율(문항 내부 붕괴)")
        lines.append("\n| 문항 | 보기사용 | 서로다른패턴 | 최빈패턴 점유% |\n|---|---|---|---|")
        for key, it in items.items():
            lines.append(f"| {it.get('name', key)} | {it.get('options_used')}/{it.get('options_total')} | "
                         f"{_fmt(it.get('distinct_patterns'))} | {_fmt(it.get('modal_pattern_share_pct'))} |")

    warns = diag.get("warnings") or []
    if warns:
        lines.append("\n### ⚠ 경고 배지")
        for w in warns:
            lines.append(f"- {w}")
        lines.append("\n> 처방(게이트C §2c): effort 상향(low→medium) · 특성 등급 5단계 · 특성-조건화 프롬프트 강화.")
    else:
        lines.append("\n- 경고 없음(임계 내).")
    return "\n".join(lines)


def _grade(label):
    return {"prior": "sim-내 견고(prior)", "ref": "참고", "unreliable": "신뢰불가(수준)"}.get(label, label)


def _judge_single(j):
    L = ["## ⑤ 판정 — v2.3 단일풀 (v23_judge)", ""]
    base = j.get("base", {})
    L.append(f"- 1차대상 n={_fmt(base.get('target'))} · 전체 n={_fmt(base.get('total'))}")
    if j.get("discipline"):
        L.append(f"- 원칙: {j['discipline']}")
    # 연속상관(주지표·방향)
    cc = j.get("continuous_corr", {})
    if cc:
        L.append(f"\n### 향부담강도 ↔ 반응 연속상관 [{_grade('prior')}] · {cc.get('note','')}")
        L.append("\n| 지표 | r |\n|---|---|")
        for k in ("B1", "C2", "D1"):
            if k in cc:
                L.append(f"| {k} | {cc[k]:+.2f} |")
    # 세그교차
    seg = j.get("segment_cross") or []
    if seg:
        L.append("\n### 매실청 깊이 세그 교차")
        L.append("\n| 컷 | hi n | lo n | ΔB1 | ΔC2 | ΔD1(pp) | 판정 |\n|---|---|---|---|---|---|---|")
        for s in seg:
            if "B1" in s:
                L.append(f"| {s['cut']} | {s['hi_n']} | {s['lo_n']} | {s['B1']['delta']:+.2f} | "
                         f"{s['C2']['delta']:+.2f} | {s['D1']['delta_pp']:+d} | {s['verdict']} |")
            else:
                L.append(f"| {s['cut']} | {s.get('hi_n')} | {s.get('lo_n')} | — | — | — | {s['verdict']} |")
        if base.get("target") is not None and base["target"] < 15:
            L.append(f"\n> ⚠ 소표본(n={base['target']}<15) — 세그 분할 불안정. 연속상관을 우선.")
    # dose-response
    dr = j.get("dose_response")
    if dr:
        L.append(f"\n### dose-response · B1 단조 = **{dr.get('b1_monotone')}**")
        L.append("\n| 수준 | n | B1 | C2 | D1% |\n|---|---|---|---|---|")
        for g in dr.get("groups", []):
            L.append(f"| {g.get('level')} | {g.get('n')} | {_fmt(g.get('B1'))} | "
                     f"{_fmt(g.get('C2'))} | {_fmt(g.get('D1_pct'))} |")
    # 보조 판정
    lc, sb = j.get("low_commitment"), j.get("statement_vs_behavior")
    if lc:
        L.append(f"\n- **저커밋(B3)**: 양·맛={lc.get('yang_mat')} vs 가격={lc.get('price')} → {lc.get('verdict')}")
    if sb:
        L.append(f"- **진술≠행동(E1)**: 나={sb.get('na')} 가={sb.get('ga')} 뭉갬={sb.get('mush')} → {sb.get('verdict')}")
    ax = j.get("a2x_validity")
    if ax:
        L.append(f"- **A2x 앵커 타당성**: 예 강도={ax.get('intensity_yes')} vs 아니오={ax.get('intensity_no')} → {ax.get('verdict')}")
    # 유병률(참고)
    prev = j.get("prevalence", {})
    if prev:
        L.append(f"\n### 유병률 [{_grade('unreliable')}] — {prev.get('note','')}")
        for label, d in (prev.get("data") or {}).items():
            L.append(f"- {label}(n={d['n']}): 협의 {d['narrow_pct']}% · 광의 {d['wide_pct']}% · 질량 {d['mass_wide_pct']}%")
    return "\n".join(L)


def _judge_multi(j):
    L = ["## ⑤ 판정 — v2.3 다풀 견고성 (v23_multi_judge)", ""]
    L.append(f"- N={_fmt(j.get('N'))} · 풀={_fmt(j.get('pools'))} · SAMPLE_SEED={_fmt(j.get('sample_seed'))}")
    integ = j.get("integrated", {})
    cc = integ.get("continuous_corr", {})
    if cc:
        L.append(f"\n### 통합 향부담강도 ↔ 반응 연속상관 [{_grade('prior')}]")
        L.append("\n| 지표 | r | p | 유의 |\n|---|---|---|---|")
        for k, v in cc.items():
            L.append(f"| {k} | {v['r']:+.2f} | {v['p']:.3f} | {v['sig']} |")
    ens = integ.get("seed_ensemble")
    if ens:
        L.append(f"\n- **시드앙상블 세그교차 ΔB1** = {ens['delta_b1_mean']:+.2f} ± {ens['sd']:.2f} (seed {ens['seeds']}회)")
    sc = j.get("sign_consistency", {})
    if sc:
        L.append("\n### 풀-부호 일관성")
        L.append("\n| 지표 | 풀별 r | 부호일관 |\n|---|---|---|")
        for k, v in sc.items():
            L.append(f"| {k} | {v['per_pool_r']} | {v['consistent']} |")
    for note in j.get("interpretation") or []:
        L.append(f"\n> {note}")
    return "\n".join(L)


def _caveats(j):
    cv = (j or {}).get("caveats") or []
    if not cv:
        return ""
    return "## ⑪ 한계 (덮지 않음)\n\n" + "\n".join(f"- {c}" for c in cv)


def build_markdown(meta, fmt, diag, judg):
    kind = meta.get("kind")
    parts = [
        f"# 게이트 C — LLM 합성 시뮬 결과 리포트 · 런 `{meta.get('run_id')}`",
        f"> **종류**: {kind} · **저널 포맷**: {fmt} · **자동 생성**(runs/ 데이터 채움)",
        "",
        WARNING_HEADER,          # ⓪ — 항상, 하드코딩, 끌 수 없음
        "",
        _exec_log(meta),
        "",
        _diag_section(diag),
        "",
    ]
    if not judg or not judg.get("judgeable"):
        note = (judg or {}).get("note", "판정 대상 아님(v2.3 저널만 판정).")
        parts.append("## ⑤ 판정\n\n_" + note + "_")
    elif kind == "multipool":
        parts.append(_judge_multi(judg))
    else:
        parts.append(_judge_single(judg))
    cav = _caveats(judg)
    if cav:
        parts += ["", cav]
    parts += ["", "---",
              "_생성: Research Harness 리포트 계층(조립 전용·새 통계 없음). "
              "수치 출처 = v23_verify(진단)·v23_judge/v23_multi_judge(판정)._"]
    return "\n".join(parts)


def report(run_id):
    """런 하나의 진단+판정을 게이트C MD 포맷으로 조립해 반환.
    반환: {run_id, kind, format, warning_included(True 고정), markdown, diagnosis, judgment}."""
    meta = store.get_run(run_id)
    if meta is None:
        return None
    fmt = analysis.journal_format(run_id)
    diag = judg = None
    if fmt == "v2.3":
        try:
            diag = analysis.run_json_script("v23_verify.py", run_id)
            diag["diagnosable"] = True
        except RuntimeError as e:
            diag = {"diagnosable": False, "note": f"진단 실패: {e}"}
        script = "v23_multi_judge.py" if meta.get("kind") == "multipool" else "v23_judge.py"
        try:
            judg = analysis.run_json_script(script, run_id)
            judg["judgeable"] = True
        except RuntimeError as e:
            judg = {"judgeable": False, "note": f"판정 실패: {e}"}
    else:
        diag = {"diagnosable": False, "note": f"저널 포맷 {fmt} — v2.3만 진단."}
        judg = {"judgeable": False, "note": f"저널 포맷 {fmt} — v2.3만 판정."}
    md = build_markdown(meta, fmt, diag, judg)
    return {"run_id": run_id, "kind": meta.get("kind"), "format": fmt,
            "warning_included": True, "markdown": md,
            "diagnosis": diag, "judgment": judg}
