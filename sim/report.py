"""
S8: 이중용도 §9.4 리포트 조립 (5블록)
=====================================
블록1 사전등록 · 블록2 산출물A(인용가능) · 블록3 산출물B(인용금지)
블록4 재현성·보정상태 · 블록5 정직성·불변 선언
블록2·3은 물리 분리 렌더, 상호 링크만.
"""
from __future__ import annotations
import json
from . import config as C, linter as _linter


def _fmt(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)


def build_report(agg: dict, n: int, backend_name: str) -> str:
    lint = _linter.lint(agg)
    A, B = agg["A_설계리스크_운영점검"], agg["B_방향성_사전분포"]
    L = []
    L.append("# 게이트 C 합성 시뮬레이션 — 문서 E §9.4 기록\n")
    L.append(f"> 라벨: **{' · '.join(agg['_labels'])}** · backend={backend_name} · "
             f"N={n} · seed={C.GLOBAL_SEED}\n")

    # 블록1
    L.append("## [블록1] 사전등록\n")
    L.append("- **목적**: 설계리스크·기대분포·운영계획 탐지. 실측 대체 아님.")
    L.append("- **화이트리스트(A 인용가능)**: 순서효과·비단조 발동·유효표본 손실·§3 규칙 발동·채널 플래그 로직·B1 평균 대략 방향")
    L.append("- **블랙리스트(B 인용금지)**: 분산·세그먼트차·채널편향 크기·A2 유병률·E1 승패·B2 기제방향·저빈도 표적셀 정밀치\n")

    # 블록2 (A)
    L.append("## [블록2] 산출물 A — 설계리스크·운영점검 (✅ 인용가능)\n")
    L.append("| 항목 | 값 | 라벨 |\n|---|---|---|")
    for k, c in A.items():
        L.append(f"| {k} | {_fmt(c['value'])} | {c['label']} |")
    L.append("")

    # 블록3 (B) — 물리 분리, 인용금지 배너
    L.append("## [블록3] 산출물 B — 방향성 사전분포 (🚫 인용금지·참고전용·보정불가)\n")
    L.append("> ⚠️ 이 블록의 어떤 수치도 결론·게이트B·§3에 인용 불가. 🔴는 방향조차 인용 불가.\n")
    L.append("| 항목 | 등급 | 값 | 라벨 |\n|---|---|---|---|")
    for k, c in B.items():
        L.append(f"| {k} | {c['grade']} | {_fmt(c['value'])} | {c['label']} |")
    L.append("")

    # 블록4
    L.append("## [블록4] 재현성 · 보정상태\n")
    L.append(f"- run: seed={C.GLOBAL_SEED}, backend={backend_name}, N={n} (bit-identical 재현)")
    L.append(f"- **calibration_hook: 비활성** — 진술층 직접 실측 부재. "
             f"N5 스팟체크({'유지' if C.PILOT_SPOTCHECK['enabled'] else '생략'})는 gross-error 외부점검 only.")
    L.append("- 게이트B 원자료: 물리 봉인(방향 유도만, 수치 미주입)\n")

    # 블록5
    L.append("## [블록5] 정직성 · 불변 선언\n")
    L.append(f"- **정직성 린터: {'✅ 통과(위반 0건)' if lint['pass'] else '❌ 위반 ' + str(len(lint['violations']))}**")
    if not lint["pass"]:
        for v in lint["violations"]:
            L.append(f"    - {v}")
    L.append(f"    - {lint['note']}")
    L.append(f"- **불변**: {agg['_invariant']}")
    return "\n".join(L), lint
