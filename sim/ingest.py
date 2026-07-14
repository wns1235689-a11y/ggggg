"""
실 LLM(에이전트) 응답 → 파이프라인 응답 포맷 매핑 + 노이즈 주입
================================================================
워크플로가 생성한 검증 응답(에이전트, per-persona)을 respondent 출력 스키마로 옮기고,
코딩 파이프라인과 동일한 노이즈 모델(B4 실패·직진)을 시드 일관되게 주입한다.
D1 비단조는 에이전트 실제 응답에서 계산(주입 없음 — 실 행동 그대로).
E1 스왑은 라이브 데모에서 미수행 → flip=False(코드형 ClaudeBackend에서만 스왑 작동).
"""
from __future__ import annotations
import numpy as np
from . import sampler, respondent, config as C

D1P = [5900, 6900, 7500, 8500]


def _pool_index(n: int = 100):
    return {p.pid: p for p in sampler.build_pool(n)}


def ingest_live(agent_responses: list[dict], n: int = 100) -> list[dict]:
    idx = _pool_index(n)
    out = []
    for a in agent_responses:
        p = idx[a["pid"]]
        # B4: 에이전트는 지시대로 '그렇다' 통과 → 현실적 부주의 실패를 attn 모델로 주입(내용 독립)
        b4_pass = not respondent._b4_fails(p)
        b4_ans = a["B4"] if b4_pass else ("아니다" if a["B4"] == "그렇다" else a["B4"])
        rngs = np.random.default_rng([C.GLOBAL_SEED, p.pid, 7])
        straight = bool(rngs.random() < C.ANCHOR_PRIORS["straightline_rate"][1] * (1.5 - p.latent["attentiveness"]))
        seq = [a[f"D1_{pr}"] == "산다" for pr in D1P]
        nonmono = any(seq[i] < seq[i + 1] for i in range(3))
        out.append({
            "respondent_id": p.pid, "F1_channel": respondent.CHANNEL_F1[p.channel],
            "S1": p.S1_age, "S2": p.S2_status, "S3": p.S3_residence, "S4": p.S4_freq, "S5": p.S5_travel,
            "A1": a["A1"], "A2": a["A2"], "B1": int(a["B1"]),
            "B2_1순위": a["B2_1"], "B2_2순위": "" if a["B2_2"] == "없음" else a["B2_2"],
            "B3": a["B3"], "B4": b4_ans, "C1": a["C1"], "C2": a["C2"],
            "D1_5900": a["D1_5900"], "D1_6900": a["D1_6900"], "D1_7500": a["D1_7500"], "D1_8500": a["D1_8500"],
            "E1": a["E1"], "E2": a.get("E2", ""), "F2": "",
            "_is_target": p.is_target, "_is_student": p.is_student_seg, "_screenout": p.screenout_reason,
            "_flag_b4_pass": b4_pass, "_flag_straightline": straight,
            "_flag_d1_nonmonotone": nonmono, "_flag_e1_swap_flip": False, "_flag_unprimed_ok": True,
            "_backend": "claude-live", "_B1_why": a.get("B1_why", ""), "_B2_why": a.get("B2_why", ""),
        })
    return out
