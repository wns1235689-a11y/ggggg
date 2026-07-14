"""
S7: §3 잠금 분석규칙 집계 (결정론)
==================================
§3 규칙을 응답에 문자 그대로 적용. 산출을 두 버킷으로 분리:
  A = 설계·운영·규칙로직 (인용가능)   — 순서효과·비단조·유효표본손실·규칙발동·채널플래그 '로직'
  B = 방향성 사전분포 (인용금지·참고) — B1/B2/C2/D1/A2/E1 수치 (🟡 방향참고 / 🔴 검증불가)
게이트B(H2)·§3 판정은 이 산출로 이동하지 않는다.
"""
from __future__ import annotations
import statistics
from collections import Counter
from . import config as C

A_SERIES = set(C.LOCKED_RULES["B2_series"]["A"])   # {매실청맛, 향신료부담없음}
_A_LABELS = {"매실청의 새콤한 맛", "향신료 부담 없음"}
_C_LABELS = {"5분 완조리", "외식 대비 가성비", "국산 새우·숙주 등 재료"}


def _cell(value, grade, cite, label):
    return {"value": value, "grade": grade, "cite": cite, "label": label}


def aggregate(responses: list[dict]) -> dict:
    full = responses
    n_total = len(full)
    # §3-1 1차대상, §3-2 B4 오답 제외, §3-3 대학생 별도
    primary = [r for r in full if r["_is_target"]]
    valid = [r for r in primary if r["_flag_b4_pass"]]
    students = [r for r in full if r["_is_student"]]
    n_valid = len(valid)

    # ── 산출물 A: 설계·운영·규칙로직 (인용가능) ─────────────────────────
    b4_fail = sum(not r["_flag_b4_pass"] for r in full)
    straight = sum(r["_flag_straightline"] for r in full)
    eff_loss = round((b4_fail + straight) / n_total, 3)
    e1_flip = round(sum(r["_flag_e1_swap_flip"] for r in full) / n_total, 3)
    d1_nonmono = round(sum(r["_flag_d1_nonmonotone"] for r in full) / n_total, 3)
    d1_downgrade = d1_nonmono > C.LOCKED_RULES["D1_nonmonotone_downgrade"]

    # §3-4 채널 호의편향 검출 — '플래그 발동 여부'만(로직), 크기는 🔴
    def _ch_b1(ch):
        xs = [r["B1"] for r in valid if r["F1_channel"] == ch]
        return statistics.mean(xs) if xs else None
    b1_blind, b1_relay = _ch_b1("직장인 커뮤니티"), _ch_b1("지인 소개")
    ch_flag = bool(b1_blind and b1_relay and (b1_relay - b1_blind) >= C.LOCKED_RULES["channel_bias_flag"]["B1_delta"])

    # §3-13 C1⑤(이런 맛 안 찾음) = 비수요층, C2 주분모 제외
    c1_nondemand = [r for r in valid if r["C1"] == "이런 맛 안 찾음"]

    bucket_A = {
        "N_총표본": _cell(n_total, "-", True, "합성·스트레스테스트"),
        "N_1차대상(§3-1)": _cell(len(primary), "-", True, "25-39∩구매≥1∩비학생"),
        "N_유효(§3-2 B4제외후)": _cell(n_valid, "-", True, "합성"),
        "N_대학생(§3-3 별도)": _cell(len(students), "-", True, "합산금지·별도"),
        "유효표본_손실률": _cell(eff_loss, "-", True, "합성·B4오답+직진, 실측 불성실률 아님"),
        "E1_순서역전율(§순서효과)": _cell(e1_flip, "-", True, "설계취약성; 승자 아님"),
        "D1_비단조율": _cell(d1_nonmono, "-", True, "합성"),
        "D1_§3-15_격하발동": _cell(d1_downgrade, "-", True, f">20% 규칙 발동={d1_downgrade}"),
        "채널편향_플래그발동(§3-4)": _cell(ch_flag, "-", True, "로직 발동 여부만; 편향 '크기'는 🔴 검증불가"),
        "C1⑤_비수요층(§3-13)": _cell(len(c1_nondemand), "-", True, "C2 주분모 제외·별도표기"),
        "B4_실패율": _cell(round(b4_fail / n_total, 3), "-", True, "합성·초과모집 버퍼 산정용"),
    }

    # ── 산출물 B: 방향성 사전분포 (인용금지·참고) ───────────────────────
    def _dist(key, src=valid):
        c = Counter(r[key] for r in src)
        return {k: round(v / max(len(src), 1), 3) for k, v in c.most_common()}

    b1s = [r["B1"] for r in valid]
    b1_mean = round(statistics.mean(b1s), 2) if b1s else None
    b1_sd = round(statistics.pstdev(b1s), 2) if len(b1s) > 1 else None
    top2 = round(sum(x >= 4 for x in b1s) / len(b1s), 3) if b1s else None

    # §3-11 B2 계열: 주지표=1순위 분포
    b2_first = Counter(r["B2_1순위"] for r in valid)
    a_first = sum(v for k, v in b2_first.items() if k in _A_LABELS)
    c_first = sum(v for k, v in b2_first.items() if k in _C_LABELS)

    # §3-12 A2 유병률
    a2 = [r["A2"] for r in valid]
    spice = round(sum(x[0] in "①②" for x in a2) / max(len(a2), 1), 3)
    access = round(sum(x[0] == "③" for x in a2) / max(len(a2), 1), 3)

    # C2 + 진술→행동 디스카운트(감사 #10: C2 인접만)
    c2 = _dist("C2")
    disc = C.ANCHOR_PRIORS["stated_to_behavior"]["top2_realization"]
    c2_pos = c2.get("꼭 산다", 0) + c2.get("가끔 산다", 0)
    behavior_ceiling = (round(c2_pos * disc[0], 3), round(c2_pos * disc[2], 3))

    # D1 수용곡선
    d1_curve = {p: round(sum(r[f"D1_{p}"] == "산다" for r in valid) / max(n_valid, 1), 3)
                for p in [5900, 6900, 7500, 8500]}

    bucket_B = {
        "B1_첫인상": _cell({"mean": b1_mean, "sd": b1_sd, "top2box": top2, "분포": _dist("B1")},
                        "🟡", False, "방향참고; 절대낙관은 게이트B C0>컨셉로 냉각"),
        "B2_계열방향(§3-11)": _cell({"A계열_1순위": a_first, "C계열_1순위": c_first,
                                 "1순위분포": {k: b2_first[k] for k in b2_first}},
                                "🔴", False, "H2 기제평행 → 방향참고조차 금지; 앵커 동어반복"),
        "B3_망설임": _cell(_dist("B3"), "🟡", False, "방향참고"),
        "C1_대안구조": _cell(_dist("C1"), "🟡", False, "방향참고; 게이트B 관습대안 우위"),
        "C2_전환의향": _cell({"분포": c2, "행동환산_구간": behavior_ceiling},
                        "🟡", False, "진술; 행동환산은 fake-door≠설문 라벨, 낙관상한"),
        "D1_수용곡선": _cell(d1_curve, "🟡", False, "가격 스윕변수; 정답 WTP 아님"),
        "A2_향기피유병률(§3-12)": _cell({"향기피": spice, "접근성": access},
                                  "🔴", False, "로컬지식 결손·검증불가; 밴드 20~48%"),
        "E1_헤드라인": _cell(_dist("E1"), "🔴", False,
                        "H2 평행·verbosity 교락 → 인용금지; 승패 판정 불가"),
    }

    return {
        "A_설계리스크_운영점검": bucket_A,
        "B_방향성_사전분포": bucket_B,
        "_invariant": C.LOCKED_RULES["invariant"],
        "_labels": ["합성", "비실측", "편의표본", "진술기준", "보정불가·방향성"],
    }
