"""
S4 응답생성 백엔드 (pluggable)
==============================
- Backend        : 추상 인터페이스
- MockBackend    : LLM 불요. 잠재특성+앵커에서 규칙적으로 응답 생성 → 오프라인 완전 실행.
                   (현실적 자유서술은 아니나 앵커·상관·노이즈 형태를 재현, 파이프라인 검증용)
- ClaudeBackend  : 실 LLM. 순차노출 프롬프트 + Verbalized Sampling으로 현실적 응답 생성.
                   ANTHROPIC_API_KEY 필요. 없으면 import는 되되 호출 시 안내.

핵심(v0.3): 게이트B 입력 프라이어는 '방향만' 주입, 출력은 인용금지. 크기 앵커 금지.
"""
from __future__ import annotations
import os, json, zlib
import numpy as np
from . import config as C


# ─── 척도 앵커문장(SSR용, ClaudeBackend에서 임베딩 매핑; Mock은 미사용) ───────────
SSR_ANCHORS = {
    "B1": {1: "전혀 안 끌린다. 사고 싶지 않다.",
           2: "별로 끌리지 않는다.",
           3: "그저 그렇다. 잘 모르겠다.",
           4: "꽤 괜찮다. 관심이 간다.",
           5: "매우 끌린다. 꼭 먹어보고 싶다."},
    "C2": {"꼭산다": "기존 방식 대신 꼭 사서 시도하겠다.",
           "가끔산다": "상황 보고 가끔은 시도해보겠다.",
           "기존유지": "아니오, 지금 방식을 유지하겠다."},
}


class Backend:
    """응답 1건을 생성하는 인터페이스. 상태기계가 문항별로 호출한다."""
    name = "base"

    def rate_likert(self, persona, item: str, ledger: dict) -> int:
        raise NotImplementedError

    def choose(self, persona, item: str, options: list[str], ledger: dict) -> str:
        raise NotImplementedError

    def choose_grid_rank(self, persona, rows: list[str], ledger: dict) -> tuple[str, str | None]:
        raise NotImplementedError

    def accept_price(self, persona, price: int, ledger: dict) -> bool:
        raise NotImplementedError

    def freetext(self, persona, item: str, ledger: dict) -> str:
        return ""  # 선택 문항 기본 공란


# ─────────────────────────────────────────────────────────────────────────
# MockBackend — 잠재특성 + 앵커에서 규칙 생성 (오프라인)
# ─────────────────────────────────────────────────────────────────────────
def _rng(persona, item):
    # 페르소나×문항 결정론 시드. zlib.crc32(안정 해시) — Python hash()는 프로세스별 랜덤이라 금지.
    return np.random.default_rng([C.GLOBAL_SEED, persona.pid, zlib.crc32(item.encode())])


def _mid(triple):  # (low,mid,high) → mid
    return triple[1]


class MockBackend(Backend):
    name = "mock"

    def rate_likert(self, persona, item, ledger):
        L = persona.latent
        a = C.ANCHOR_PRIORS["B1"]
        base = _mid(a["mean"])
        # 관여도·매실청친숙도·호의(+), 회의도·향기피(-)
        score = (base
                 + 1.0 * (L["involvement"] - 0.5)
                 + 0.7 * (L["plum_familiarity"] - 0.5)
                 - 0.9 * (L["skepticism"] - 0.5)
                 - 0.7 * (L["spice_aversion"] - 0.5)
                 + L["channel_favor_offset"])
        # 한국 응답스타일: 중간편중은 약하게만(분산붕괴 방지 — 규범 SD 0.7~0.9 목표)
        score = 3.0 + (score - 3.0) * (1.0 - 0.15 * L["midpoint_bias"])
        rng = _rng(persona, item)
        score += rng.normal(0, _mid(a["sd"]) * 0.95)    # 분산 확보(붕괴 방어)
        val = int(np.clip(round(score), 1, 5))
        # 극단 회피는 약하게만(1점은 희소하되 0은 아님)
        if val == 5 and rng.random() < L["extremity_low"] * 0.25:
            val = 4
        if val == 1 and rng.random() < L["extremity_low"] * 0.35:
            val = 2
        return val

    def choose(self, persona, item, options, ledger):
        L = persona.latent
        rng = _rng(persona, item)
        w = np.ones(len(options))
        if item == "A1":
            w = np.array([_mid(C.ANCHOR_PRIORS["A1"][k]) for k in
                          ["좋아함", "보통", "별로", "무경험"]])
            if ledger.get("S5_travel") == "있다":
                w[0] *= 1.4; w[3] *= 0.6           # 여행경험 → 경험·선호↑
        elif item == "A2":
            # [①향신료향 ②낯선소스 ③접근성 ④가격 ⑤단순비선호 ⑥잘먹음]
            sa, price, inv = L["spice_aversion"], L["price_sensitivity"], L["involvement"]
            w = np.array([1.2 * sa, 0.8 * sa, 0.6 * (1 - inv), 0.7 * price,
                          0.5 * (1 - sa), 0.5 * inv]) + 0.1
        elif item == "B3":
            # [맛상상 진짜팟타이 냉동품질 가격 양 관심없음 없음]
            w = np.array([0.8, 0.7 * (1 - L["plum_familiarity"]), 0.7 * L["skepticism"],
                          0.9 * L["price_sensitivity"], 0.5, 0.6 * (1 - L["involvement"]),
                          0.7 * (1 - L["skepticism"])]) + 0.1
        elif item == "C1":
            # [직접만듦 냉동밀키트 배달외식 안먹음 이런맛안찾음]
            solo = ledger.get("S3_residence") in ("1인가구", "기숙사")
            w = np.array([0.5, 1.2 if solo else 0.7, 0.9, 0.4,
                          0.8 * (1 - L["involvement"])]) + 0.1
        elif item == "C2":
            # [꼭산다 가끔산다 기존유지] — 게이트B: 관습대안 우위 → 기존유지 질량↑
            b1 = ledger.get("B1", 3)
            w = np.array([_mid(C.ANCHOR_PRIORS["C2"]["꼭산다"]) * (b1 / 3.0),
                          _mid(C.ANCHOR_PRIORS["C2"]["가끔산다"]),
                          0.45 + 0.3 * L["skepticism"]])
        elif item == "E1":
            # 게이트B 방향프라이어 P(T2)≈0.53. mock은 위치편향 없음 → 제시순서 무시하고
            # '정체성' 기준 canonical 표집(스왑해도 동일 축 → 정상적으로 flip 안 함).
            # 위치·verbosity 편향은 실 LLM(ClaudeBackend)에서만 발현. 감사 G2 스왑은 그때 작동.
            gp = C.GATE_B_INPUT_PRIORS["E1_P_T2"]["center"]
            canon = ["가(T1·완성도)", "나(T2·매실청)", "비슷", "둘 다 안 끌림"]
            wmap = {"가": (1 - gp) + 0.4 * L["involvement"],
                    "나": gp + 0.5 * L["spice_aversion"] + 0.3 * L["plum_familiarity"],
                    "비슷": 0.16 + 0.20 * L["midpoint_bias"],
                    "둘": 0.15 * L["skepticism"]}
            w = np.array([wmap["가"], wmap["나"], wmap["비슷"], wmap["둘"]])
            w = w / w.sum()
            return canon[int(rng.choice(4, p=w))]
        w = np.clip(w, 1e-6, None); w = w / w.sum()
        return options[int(rng.choice(len(options), p=w))]

    def choose_grid_rank(self, persona, rows, ledger):
        # B2: [5분완조리 외식대비가성비 국산재료 매실청새콤 향신료부담없음 이유없음]
        L = persona.latent
        rng = _rng(persona, "B2")
        A_boost_maesil = 0.6 * L["plum_familiarity"]
        A_boost_spice = 0.8 * L["spice_aversion"]
        w = np.array([
            0.8 * L["involvement"],                 # 5분완조리 (C) — primacy 억제(계수 낮게)
            0.7 * L["price_sensitivity"],           # 가성비 (C)
            0.6,                                    # 국산재료 (C)
            0.7 + A_boost_maesil,                   # 매실청새콤 (A) — 게이트B A≥C 방향
            0.6 + A_boost_spice,                    # 향신료부담없음 (A)
            0.25 * (1 - L["involvement"]),          # 이유없음
        ]) + 0.05
        w = w / w.sum()
        i1 = int(rng.choice(len(rows), p=w))
        first = rows[i1]
        if first == "사고 싶은 이유 없음":
            return first, None                      # §3-9: 이유없음 1순위 → 2순위 무효
        w2 = w.copy(); w2[i1] = 0
        if rng.random() < 0.15 * (1 - L["involvement"]):   # 만족화 일부 2순위 공란
            return first, None
        w2 = w2 / w2.sum()
        second = rows[int(rng.choice(len(rows), p=w2))]
        return first, second

    def accept_price(self, persona, price, ledger):
        # WTP 임계 모델: 페르소나별 고정 rank(가격 무관) → 임계 이하 가격만 수용 → 단조.
        # 집계 수용률 ≈ 앵커곡선(rank 균등 시). 비단조는 respondent에서 소수만 주입.
        L = persona.latent
        rng = np.random.default_rng([C.GLOBAL_SEED, persona.pid, 1])  # persona-level(가격 무관)
        rank = rng.random()
        rank = float(np.clip(rank + 0.30 * (L["price_sensitivity"] - 0.5)
                             - 0.10 * (ledger.get("B1", 3) - 3) / 2, 0.0, 1.0))
        return rank < _mid(C.ANCHOR_PRIORS["D1_accept"][price])

    def freetext(self, persona, item, ledger):
        return ""  # Mock은 자유서술 생략 (ClaudeBackend가 담당)


# ─────────────────────────────────────────────────────────────────────────
# ClaudeBackend — 실 LLM (Verbalized Sampling). ANTHROPIC_API_KEY 필요.
# ─────────────────────────────────────────────────────────────────────────
class ClaudeBackend(Backend):
    name = "claude"
    MODEL = "claude-opus-4-8"

    def __init__(self, model: str | None = None):
        self.model = model or self.MODEL
        try:
            import anthropic  # noqa
            self._client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수
        except Exception as e:
            self._client = None
            self._err = e

    def _require(self):
        if self._client is None:
            raise RuntimeError(
                "ClaudeBackend 사용 불가: anthropic SDK/ANTHROPIC_API_KEY 필요. "
                "`pip install anthropic` 후 환경변수 설정. (원인: %r)" % self._err)

    def _system(self, persona) -> str:
        # 회의적 실제 소비자 역할고정 + 잠재특성 주입 (게이트B 수치는 절대 미노출)
        L = persona.latent
        return (
            "너는 설문 응답을 '평가'하는 조수가 아니라, 실제 한국 소비자 1명이다. "
            "제품을 옹호하지 말고 회의적으로 반응하라. 맛 상상의 어려움·진짜 팟타이 논쟁·"
            "냉동 품질·가격 같은 마찰을 눈감지 마라.\n"
            f"[너의 프로필] 연령 {persona.S1_age}, {persona.S2_status}, {persona.S3_residence}, "
            f"최근1개월 간편식 {persona.S4_freq}, 동남아여행 {persona.S5_travel}. "
            f"향신료 부담 성향 {'높음' if L['spice_aversion']>0.55 else '보통' if L['spice_aversion']>0.35 else '낮음'}, "
            f"매실청 친숙도 {'높음' if L['plum_familiarity']>0.6 else '보통'}, "
            f"회의도 {'높음' if L['skepticism']>0.6 else '보통'}. "
            "이 성향을 응답에 자연스럽게 반영하되 과장하지 마라."
        )

    def _vs_call(self, system: str, user: str, options: list[str]) -> str:
        """Verbalized Sampling: 모델이 응답분포를 언어화 → 표집. (실 API 호출)"""
        self._require()
        schema = ("다음 JSON만 출력: {\"dist\": {옵션:확률...}, \"choice\": 선택옵션, "
                  "\"why\": \"한 문장\"}. 확률 합=1.")
        msg = self._client.messages.create(
            model=self.model, max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": f"{user}\n\n옵션: {options}\n{schema}"}],
        )
        txt = msg.content[0].text
        try:
            data = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            return data.get("choice", options[0])
        except Exception:
            return options[0]

    # 실 구현은 _vs_call을 각 문항 프롬프트로 감싼다(순차노출 ledger를 user에 반영).
    # SSR 경로(자유서술→임베딩 유사도)는 임베딩 모델 확보 시 rate_likert에 추가.
    def rate_likert(self, persona, item, ledger):
        raise NotImplementedError("ClaudeBackend.rate_likert — 실 API 배선 지점(다음 증분)")


def get_backend(name: str = "mock") -> Backend:
    return {"mock": MockBackend, "claude": ClaudeBackend}[name]()
