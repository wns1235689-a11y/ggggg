"""
S4: 순차노출 응답자 상태기계
============================
정보 게이팅을 강제한다:
  [태깅 S1-5] → [사전태도 A: 컨셉/가격 없음] → [컨셉 B: 가격 없음]
             → [행동 C: 가격 없음] → [가격 D: 첫 노출] → [메시지 E]
★ A1·A2는 컨셉/가격이 ledger에 없는 상태에서 생성(unprimed 봉인, assertion으로 검증).
E1은 가/나 순서 양방향 스왑 — 선택 축이 뒤집히면 '비슷'(감사 G2).
백엔드(mock/claude)가 문항별 응답을 만들고, 여기서 노출순서·품질노이즈·§3-9를 처리.
"""
from __future__ import annotations
import numpy as np
from . import config as C

# 문항 옵션(원 라벨)
OPT = {
    "A1": ["먹어봤고 좋아한다", "먹어봤고 보통이다", "먹어봤지만 별로였다", "먹어본 적 없다"],
    "A1_key": ["좋아함", "보통", "별로", "무경험"],
    "A2": ["①향신료향 부담", "②낯선 소스·재료", "③접근성 부족", "④가격 부담",
           "⑤단순 비선호", "⑥지금도 잘 먹음"],
    "B3": ["맛 상상 안 됨", "진짜 팟타이 아닐 것", "냉동품질 불신", "가격 걱정",
           "양(300g) 부족", "팟타이 관심 없음", "망설임 없음"],
    "B4": ["매우 그렇다", "그렇다", "아니다", "모르겠다"],
    "C1": ["직접 만든다", "냉동/밀키트", "배달·외식", "안 먹거나 참는다", "이런 맛 안 찾음"],
    "C2": ["꼭 산다", "가끔 산다", "기존 방식 유지"],
    "C2_key": ["꼭산다", "가끔산다", "기존유지"],
    "E1": ["가(T1·완성도)", "나(T2·매실청)", "비슷", "둘 다 안 끌림"],
    "B2_rows": ["5분 완조리", "외식 대비 가성비", "국산 새우·숙주 등 재료",
                "매실청의 새콤한 맛", "향신료 부담 없음", "사고 싶은 이유 없음"],
}
CHANNEL_F1 = {"blind": "직장인 커뮤니티", "relay": "지인 소개", "student": "대학생 커뮤니티"}
D1_PRICES = [5900, 6900, 7500, 8500]
B4_CORRECT = "그렇다"  # 지시: '그렇다(②)'


def _b4_fails(persona) -> bool:
    rng = np.random.default_rng([C.GLOBAL_SEED, persona.pid, 4])
    a = C.ANCHOR_PRIORS["B4_fail_rate"]
    rate = a["base"][1] + (a["student_add"] if persona.is_student_seg else 0)
    # 부주의(attentiveness 낮음)와 상관
    rate *= (1.15 - 0.5 * persona.latent["attentiveness"])
    return bool(rng.random() < np.clip(rate, 0.02, 0.35))


def _e1_with_swap(backend, persona, ledger) -> tuple[str, bool]:
    """가/나 순서 양방향 실행 → 축 뒤집히면 '비슷'. returns (choice, swap_flip)."""
    order1 = OPT["E1"]                                   # [가, 나, 비슷, 둘다]
    order2 = [OPT["E1"][1], OPT["E1"][0], OPT["E1"][2], OPT["E1"][3]]  # [나, 가, ...]
    c1 = backend.choose(persona, "E1", order1, ledger)
    c2 = backend.choose(persona, "E1", order2, ledger)
    axis = lambda c: "T2" if c.startswith("나") else ("T1" if c.startswith("가") else c)
    if axis(c1) != axis(c2):                            # 순서로 뒤집힘 → 취약 → 비슷
        return "비슷", True
    return c1, False


def respond(persona, backend) -> dict:
    ledger = {"S1_age": persona.S1_age, "S2_status": persona.S2_status,
              "S3_residence": persona.S3_residence, "S4_freq": persona.S4_freq,
              "S5_travel": persona.S5_travel}
    flags = {"b4_pass": True, "straightline": False, "d1_nonmonotone": False,
             "e1_swap_flip": False, "unprimed_ok": True}

    # ── Stage A: 사전태도 (unprimed — 컨셉/가격 미노출) ────────────────
    assert "concept" not in ledger and "price" not in ledger, "unprimed 위반"
    a1 = backend.choose(persona, "A1", OPT["A1"], ledger)
    ledger["A1"] = OPT["A1_key"][OPT["A1"].index(a1)]
    a2 = backend.choose(persona, "A2", OPT["A2"], ledger)
    ledger["A2"] = a2
    flags["unprimed_ok"] = ("concept" not in ledger and "price" not in ledger)

    # ── Stage B: 컨셉 노출 (가격 없음) ────────────────────────────────
    ledger["concept"] = True
    b1 = backend.rate_likert(persona, "B1", ledger); ledger["B1"] = b1
    b2_1, b2_2 = backend.choose_grid_rank(persona, OPT["B2_rows"], ledger)
    b3 = backend.choose(persona, "B3", OPT["B3"], ledger)
    # B4 주의력: 정답 '그렇다', 단 부주의 확률로 실패
    if _b4_fails(persona):
        rngb = np.random.default_rng([C.GLOBAL_SEED, persona.pid, 44])
        b4 = rngb.choice([o for o in OPT["B4"] if o != B4_CORRECT])
        flags["b4_pass"] = False
    else:
        b4 = B4_CORRECT

    # ── Stage C: 행동·전환 (가격 없음) ────────────────────────────────
    c1 = backend.choose(persona, "C1", OPT["C1"], ledger); ledger["C1"] = c1
    c2 = backend.choose(persona, "C2", OPT["C2"], ledger); ledger["C2"] = c2

    # ── Stage D: 가격 첫 노출 (Gabor-Granger) ─────────────────────────
    ledger["price"] = True
    d1 = {}
    for pr in D1_PRICES:
        d1[pr] = "산다" if backend.accept_price(persona, pr, ledger) else "안 산다"
    # §3-15 비단조: 역치근처 소수에 '안산다→산다' 상승꺾임을 명시 주입(검출 가능하게)
    rngd = np.random.default_rng([C.GLOBAL_SEED, persona.pid, 15])
    p_inject = C.ANCHOR_PRIORS["D1_nonmonotone_rate"][1] * (1.1 - 0.4 * persona.latent["attentiveness"])
    if rngd.random() < p_inject:
        j = int(rngd.integers(0, 3))                    # (j, j+1) 쌍에 상승꺾임 생성
        d1[D1_PRICES[j]] = "안 산다"
        d1[D1_PRICES[j + 1]] = "산다"
    seq = [d1[p] == "산다" for p in D1_PRICES]
    flags["d1_nonmonotone"] = any(seq[i] < seq[i + 1] for i in range(len(seq) - 1))  # 안산다→산다 = 상승 꺾임

    # ── Stage E: 메시지 선호 (E1 스왑) + E2 ───────────────────────────
    e1, flip = _e1_with_swap(backend, persona, ledger)
    flags["e1_swap_flip"] = flip
    e2 = backend.freetext(persona, "E2", ledger)

    # 직진응답(straightline) 플래그: 낮은 attentiveness
    rngs = np.random.default_rng([C.GLOBAL_SEED, persona.pid, 7])
    if rngs.random() < C.ANCHOR_PRIORS["straightline_rate"][1] * (1.5 - persona.latent["attentiveness"]):
        flags["straightline"] = True

    return {
        # Forms 동형 컬럼(원 라벨)
        "respondent_id": persona.pid, "F1_channel": CHANNEL_F1[persona.channel],
        "S1": persona.S1_age, "S2": persona.S2_status, "S3": persona.S3_residence,
        "S4": persona.S4_freq, "S5": persona.S5_travel,
        "A1": a1, "A2": a2, "B1": b1, "B2_1순위": b2_1, "B2_2순위": b2_2 or "",
        "B3": b3, "B4": b4, "C1": c1, "C2": c2,
        "D1_5900": d1[5900], "D1_6900": d1[6900], "D1_7500": d1[7500], "D1_8500": d1[8500],
        "E1": e1, "E2": e2, "F2": "",
        # 메타 사이드카(분석 전 비노출)
        "_is_target": persona.is_target, "_is_student": persona.is_student_seg,
        "_screenout": persona.screenout_reason,
        **{f"_flag_{k}": v for k, v in flags.items()},
        "_backend": backend.name,
    }


def run_survey(pool, backend) -> list[dict]:
    return [respond(p, backend) for p in pool]
