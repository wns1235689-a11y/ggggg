"""
S1–S3: 결합 인구통계 표집 → 잠재특성 부여 → 스크리닝
====================================================
결합분포 = 채널 조건부 Bayes-net 인수분해 (독립표집 금지).
  channel → age → status | age → residence | age,status → S4 | residence,age → S5 | age
각 페르소나는 결정론 시드(hash(GLOBAL_SEED, pid))로 재현.
LLM 불요 — 순수 numpy. 오프라인 완전 실행 가능.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field, asdict
from . import config as C


def _rng(pid: int) -> np.random.Generator:
    # 페르소나별 결정론 시드 — bit-identical 재현
    return np.random.default_rng([C.GLOBAL_SEED, pid])


def _choice(rng, options, probs):
    p = np.asarray(probs, float)
    p = p / p.sum()
    return options[int(rng.choice(len(options), p=p))]


def _sample_latents(rng, channel: str, s4_freq: str) -> dict:
    lat = {}
    for name, (mu, sd) in C.LATENT_SPECS.items():
        v = float(rng.normal(mu, sd))
        lat[name] = float(np.clip(v, 0.0, 1.0))
    # 향기피 ↔ 매실청 친숙도 음(-) 완충 상관 (사전조사 권장):
    # 매실청 친숙도 높을수록 향 부담을 덜 느낌 → spice_aversion 하향
    lat["spice_aversion"] = float(np.clip(
        lat["spice_aversion"] - 0.20 * (lat["plum_familiarity"] - 0.5), 0.0, 1.0))
    # S4 관여도 재보정: 고빈도 → involvement +
    bump = {"0회": -0.15, "1-2회": 0.0, "3-5회": 0.10, "6+회": 0.20}[s4_freq]
    lat["involvement"] = float(np.clip(lat["involvement"] + bump, 0.0, 1.0))
    # 채널 호의 오프셋(리커트 가산 상수 + 개인노이즈)
    off = C.CHANNEL_FAVOR_OFFSET[channel]
    lat["channel_favor_offset"] = float(off + rng.normal(0, 0.1))
    return lat


@dataclass
class Persona:
    pid: int
    channel: str
    S1_age: str
    S2_status: str
    S3_residence: str
    S4_freq: str
    S5_travel: str
    is_target: bool          # §3-1 1차대상 = 25-39 AND 구매≥1회
    is_student_seg: bool     # §3-3 대학생 세그먼트(별도, 합산금지)
    screenout_reason: str    # "" 이면 유효
    latent: dict = field(default_factory=dict)

    def row(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if k != "latent"}
        return d


def sample_persona(pid: int) -> Persona:
    rng = _rng(pid)
    channel = _choice(rng, list(C.CHANNEL_MIX), list(C.CHANNEL_MIX.values()))
    age = _choice(rng, C.S1_AGE, C.CPT_AGE[channel])
    status = _choice(rng, C.S2_STATUS, C.cpt_status(age, channel))
    residence = _choice(rng, C.S3_RESIDENCE, C.cpt_residence(age, status, channel))
    freq = _choice(rng, C.S4_FREQ, C.cpt_freq(residence, age))
    travel = _choice(rng, C.S5_TRAVEL, C.cpt_travel(age))

    # §3-3 대학생 세그먼트 = S2 대학원생 또는 S1 19-24 (설계서 §3-3)
    is_student_seg = (status == "대학원생") or (age == "19-24") or (channel == "student")
    # §3-1 1차대상 = 25-39 AND 최근1개월 구매 ≥1회
    age_ok = age in ("25-29", "30-34", "35-39")
    freq_ok = freq in ("1-2회", "3-5회", "6+회")
    is_target = age_ok and freq_ok and not is_student_seg

    # 스크린아웃 사유(모집수 계산엔 포함, 집계 제외)
    reasons = []
    if age == "40+":
        reasons.append("40+")
    if age == "19-24":
        reasons.append("19-24")
    if freq == "0회":
        reasons.append("구매0회")
    screenout = ";".join(reasons)

    p = Persona(pid, channel, age, status, residence, freq, travel,
                is_target, is_student_seg, screenout)
    p.latent = _sample_latents(rng, channel, freq)
    return p


def build_pool(n: int = C.DEFAULT_N) -> list[Persona]:
    return [sample_persona(pid) for pid in range(n)]


# ─── 요약 통계 (검증용) ───────────────────────────────────────────────
def summarize(pool: list[Persona]) -> dict:
    n = len(pool)
    def dist(key):
        from collections import Counter
        c = Counter(getattr(p, key) for p in pool)
        return {k: round(v / n, 3) for k, v in sorted(c.items())}
    n_target = sum(p.is_target for p in pool)
    n_student = sum(p.is_student_seg for p in pool)
    n_screenout = sum(bool(p.screenout_reason) for p in pool)
    return {
        "N": n,
        "channel": dist("channel"),
        "S1_age": dist("S1_age"),
        "S2_status": dist("S2_status"),
        "S3_residence": dist("S3_residence"),
        "S4_freq": dist("S4_freq"),
        "S5_travel": dist("S5_travel"),
        "n_target(§3-1)": n_target,
        "target_rate": round(n_target / n, 3),
        "n_student_seg(§3-3)": n_student,
        "n_screenout": n_screenout,
    }
