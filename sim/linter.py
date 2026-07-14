"""
S9: 정직성 린터 (필요조건, 충분조건 아님)
=========================================
집계 산출물을 스캔해 이중용도 A/B 계약 위반을 차단한다.
감사 #9(린터 우회 halo): 린터 통과 = 기계적 하한일 뿐 누출 부재 증명 아님.
"""
from __future__ import annotations

# H2와 구조 평행(승자·기제류) → 방향참고조차 🔴 (v0.3 부록 D.6)
_MUST_BE_RED = {"B2_계열방향(§3-11)", "E1_헤드라인", "A2_향기피유병률(§3-12)"}
_FORBIDDEN_WORDS = ("검증됨", "보정된", "예측된", "정확", "실측 확인")


def lint(agg: dict) -> dict:
    violations = []
    A, B = agg["A_설계리스크_운영점검"], agg["B_방향성_사전분포"]

    # 1) B버킷 전 셀 인용금지(cite=False)
    for k, c in B.items():
        if c.get("cite", False):
            violations.append(f"[B-인용] '{k}'가 인용가능으로 표기됨(B는 참고전용)")
        if not c.get("label"):
            violations.append(f"[라벨] '{k}' 라벨 없음")

    # 2) A버킷: 태도·유병률·승패 수치 금지(설계·운영·규칙로직만)
    for k in A:
        if any(t in k for t in ("첫인상", "유병률", "헤드라인", "계열")):
            violations.append(f"[A-오염] 태도/방향 수치 '{k}'가 A버킷에 있음")
        if not A[k].get("label"):
            violations.append(f"[라벨] A '{k}' 라벨 없음")

    # 3) 구조평행 항목은 반드시 🔴
    for k in _MUST_BE_RED:
        if k in B and B[k].get("grade") != "🔴":
            violations.append(f"[등급] '{k}'는 H2 평행 → 🔴이어야 함(현재 {B[k].get('grade')})")

    # 4) calibration 비활성: 금지어(검증됨/보정/예측) 등장 차단
    import json
    blob = json.dumps(agg, ensure_ascii=False)
    for w in _FORBIDDEN_WORDS:
        if w in blob:
            violations.append(f"[과대주장] 금지어 '{w}' 등장(ground truth 부재)")

    # 5) 불변 선언 존재
    if "게이트B" not in agg.get("_invariant", ""):
        violations.append("[불변] 게이트B/§3 판정 불변 선언 누락")

    return {"pass": len(violations) == 0, "violations": violations,
            "note": "린터는 기계적 하한 — 통과가 누출 부재를 증명하지 않는다(결론부 사람검수 병행)."}
