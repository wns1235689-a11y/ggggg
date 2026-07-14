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
        base = a["mean"][0] - 0.15   # recenter down(3.45): 유리한 표적 + 다변량 상방 상쇄
        # 관여도·매실청친숙도·호의(+), 회의도·향기피(-)
        score = (base
                 + 0.85 * (L["involvement"] - 0.5)
                 + 0.6 * (L["plum_familiarity"] - 0.5)
                 + 0.45 * (L["quality_trust"] - 0.5)      # KREI 품질만족 → 첫인상↑
                 + 0.3 * (L["novelty_seeking"] - 0.5)     # 신메뉴 탐색 → 첫인상↑
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
            # 워크북: 접근성(access_barrier)은 독립 잠재환경 변수 — 라이브 데모서 지배적
            w = np.array([1.1 * L["spice_aversion"],                 # ① 향
                          0.9 * L["sauce_barrier"],                   # ② 낯선소스
                          1.0 * L["access_barrier"],                  # ③ 접근성
                          0.7 * L["price_sensitivity"],               # ④ 가격
                          0.5 * (1 - L["category_frequency"]),        # ⑤ 단순비선호
                          0.6 * L["category_frequency"] * (1 - L["spice_aversion"])]) + 0.1  # ⑥ 잘먹음
        elif item == "B3":
            # [맛상상 진짜팟타이 냉동품질 가격 양 관심없음 없음]
            # Low Rating 테마 방향: VALUE_NEG(가격) 최상위, AUTH_NEG(진짜팟타이), FRESHNESS(냉동품질), PORTION(양)
            w = np.array([0.45 + 0.5 * L["sauce_barrier"],       # 맛 상상 안됨 (낯선 소스→상상 어려움)
                          0.55 + 0.6 * L["authenticity_goal"],   # 진짜팟타이 아님 (정통성 기대↑)
                          0.75 * (1 - L["quality_trust"]),        # 냉동품질 불신 (FRESHNESS)
                          0.9 * L["price_sensitivity"],           # 가격 걱정 (VALUE_NEG 최상위)
                          0.3 + 0.7 * L["portion_expect"],        # 양 부족 (식사량 기대↑, B012)
                          0.6 * (1 - L["involvement"]),           # 관심없음
                          0.65 * (1 - L["skepticism"])]) + 0.1    # 없음
        elif item == "C1":
            # [직접만듦 냉동밀키트 배달외식 안먹음 이런맛안찾음]
            solo = ledger.get("S3_residence") in ("1인가구", "기숙사")
            ab = L["access_barrier"]                            # 접근 장벽↑ → HMR 전환·안먹음
            w = np.array([0.5 * (1 - ab),                       # 직접만듦
                          (1.2 if solo else 0.7) + 0.5 * ab,    # 냉동밀키트 (접근장벽→HMR)
                          0.9,                                   # 배달외식
                          0.4 * ab,                              # 안먹음
                          0.8 * (1 - L["involvement"])]) + 0.1   # 이런맛안찾음
        elif item == "C2":
            # [꼭산다 가끔산다 기존유지] — trial_propensity·category_frequency(B015)·social_desirability
            b1 = ledger.get("B1", 3)
            w = np.array([
                _mid(C.ANCHOR_PRIORS["C2"]["꼭산다"]) * (b1 / 3.0)
                    * (0.5 + 0.9 * L["trial_propensity"]) * (0.8 + 0.4 * L["social_desirability"]),
                _mid(C.ANCHOR_PRIORS["C2"]["가끔산다"]) * (0.8 + 0.5 * (1 - L["category_frequency"])),  # 저빈도→가끔만
                0.45 + 0.3 * L["skepticism"] + 0.3 * (1 - L["quality_trust"])])
        elif item == "E1":
            # 게이트B 방향프라이어 P(T2)≈0.53. mock은 위치편향 없음 → 제시순서 무시하고
            # '정체성' 기준 canonical 표집(스왑해도 동일 축 → 정상적으로 flip 안 함).
            # 위치·verbosity 편향은 실 LLM(ClaudeBackend)에서만 발현. 감사 G2 스왑은 그때 작동.
            # message_orientation(I027, 높을수록 T2)로 persona별 변조하되 gate-B center 유지
            gp = C.GATE_B_INPUT_PRIORS["E1_P_T2"]["center"]
            mo = L["message_orientation"]
            canon = ["가(T1·완성도)", "나(T2·매실청)", "비슷", "둘 다 안 끌림"]
            wmap = {"가": (1 - gp) * (1.0 + 0.7 * (1 - mo)),      # T1: 편의 지향(mo 낮음)
                    "나": gp * (1.0 + 0.7 * mo) + 0.2 * L["plum_familiarity"],  # T2: 향완화 지향
                    "비슷": 0.16 + 0.20 * L["midpoint_bias"],
                    "둘": 0.15 * L["skepticism"]}
            w = np.array([wmap["가"], wmap["나"], wmap["비슷"], wmap["둘"]])
            w = w / w.sum()
            return canon[int(rng.choice(4, p=w))]
        w = np.clip(w, 1e-6, None); w = w / w.sum()
        return options[int(rng.choice(len(options), p=w))]

    def choose_grid_rank(self, persona, rows, ledger):
        # B2: [5분완조리 외식대비가성비 국산재료 매실청새콤 향신료부담없음 이유없음]
        # KREI 실측 앵커(구입이유): 가성비 0.32·간편 0.32·맛 0.17 → C계열 stated 우세.
        # A계열은 제품특정(매실청·향기피 성향)으로만 상승. gate-B A축 인위 부스트 제거(E1 관할).
        L = persona.latent
        rng = _rng(persona, "B2")
        w = np.array([
            0.95 + 0.4 * L["involvement"],          # 5분완조리 (C·간편, KREI 0.32)
            1.00 + 0.5 * L["price_sensitivity"],    # 가성비 (C·비용, KREI 최상위 0.32)
            0.55 + 0.3 * L["quality_trust"],        # 국산재료 (C·품질/맛, KREI 0.17)
            0.45 + 0.6 * L["plum_familiarity"],     # 매실청새콤 (A·제품특정)
            0.35 + 0.8 * L["spice_aversion"],       # 향신료부담없음 (A·제품특정)
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
        lv = lambda x: '높음' if x > 0.6 else ('보통' if x > 0.4 else '낮음')
        return (
            "너는 설문 응답을 '평가'하는 조수가 아니라, 실제 한국 소비자 1명이다. "
            "제품을 옹호하지 말고 회의적으로 반응하라. 맛 상상의 어려움·진짜 팟타이 논쟁·"
            "냉동 품질·가격·양 같은 마찰을 눈감지 마라.\n"
            f"[너의 프로필] 연령 {persona.S1_age}, {persona.S2_status}, {persona.S3_residence}, "
            f"최근1개월 간편식 {persona.S4_freq}, 동남아여행 {persona.S5_travel}. "
            f"향신료 부담 {lv(L['spice_aversion'])}, 매실청 친숙도 {lv(L['plum_familiarity'])}, "
            f"회의도 {lv(L['skepticism'])}, 접근성 장벽(파는 곳/기회 부족) {lv(L['access_barrier'])}, "
            f"정통성 기대 {lv(L['authenticity_goal'])}, 식사량 기대 {lv(L['portion_expect'])}, "
            f"이 카테고리 평소 섭취빈도 {lv(L['category_frequency'])}.\n"
            "[현실 힌트] 1인가구면 고수·대파 같은 고명을 따로 사두지 않는다. "
            "표기 1~2인분이 성인 한 끼로는 적게 느껴질 수 있다. "
            "이 음식을 평소 자주 먹지 않으면 맛이 괜찮아도 '가끔만' 재구매한다. "
            "좋아하지만 안 사거나, 만족해도 가끔만 사는 현실적 불일치도 자연스럽다.\n"
            "이 성향을 응답에 자연스럽게 반영하되 과장하지 마라."
        )

    def _exposure(self, ledger: dict) -> str:
        """순차노출 게이팅: 컨셉/가격은 ledger 플래그가 켜졌을 때만 프롬프트에 노출."""
        parts = []
        if ledger.get("concept"):
            parts.append("[지금 본 컨셉] " + CONCEPT_CARD)
        if ledger.get("price"):
            parts.append("[가격이 공개됨] 5,900 / 6,900 / 7,500 / 8,500원")
        return "\n".join(parts)

    def _vs(self, persona, user: str, options: list[str], rng_seed=None) -> dict:
        """Verbalized Sampling: 모델이 응답분포를 언어화 → 표집. returns {choice, why, dist}."""
        self._require()
        schema = ('아래 JSON만 출력: {"dist": {"<옵션>": <확률>, ...}, "choice": "<선택 옵션>", '
                  '"why": "<한 문장 이유(그 사람 말투)>"} · dist 확률 합=1 · choice는 dist에서 표집한 값.')
        msg = self._client.messages.create(
            model=self.model, max_tokens=500, system=user["system"],
            messages=[{"role": "user",
                       "content": f"{user['body']}\n\n선택지: {options}\n{schema}"}],
        )
        txt = msg.content[0].text
        try:
            data = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            ch = data.get("choice")
            return {"choice": ch if ch in options else options[0],
                    "why": data.get("why", ""), "dist": data.get("dist", {})}
        except Exception:
            return {"choice": options[0], "why": "", "dist": {}}

    def _ask(self, persona, question: str, options: list[str], ledger: dict) -> dict:
        body = (self._exposure(ledger) + "\n\n" + question).strip()
        return self._vs(persona, {"system": self._system(persona), "body": body}, options)

    def rate_likert(self, persona, item, ledger):
        q = ("이 제품의 첫인상을 1~5점으로. (1=전혀 안 끌린다 ... 5=매우 끌린다) "
             "회의적 실제 소비자로서, 마찰도 감안해 표집하라.")
        r = self._ask(persona, q, ["1", "2", "3", "4", "5"], ledger)
        try:
            return int(r["choice"])
        except Exception:
            return 3

    def choose(self, persona, item, options, ledger):
        Q = {
            "A1": "팟타이를 먹어본 경험은? (아직 아무 제품도 보지 않은 상태에서 답하라)",
            "A2": "동남아 음식을 지금보다 자주 먹지 않는 '가장 큰' 이유 하나는? (아직 제품 미노출)",
            "B3": "이 제품 구매를 가장 망설이게 하는 것 하나는?",
            "C1": "이런 팟타이가 먹고 싶을 때 지금 당신은 주로?",
            "C2": "이 냉동 완제품이 나온다면 기존 방식 '대신' 시도해 보겠는가?",
            "E1": "다음 두 소개 문구 중 이 제품을 더 사고 싶게 만드는 쪽은?\n"
                  f"(가) {C.E1_HEADLINES['가']['paraphrase']}\n(나) {C.E1_HEADLINES['나']['paraphrase']}",
        }.get(item, "다음 중 하나를 고르라.")
        return self._ask(persona, Q, options, ledger)["choice"]

    def choose_grid_rank(self, persona, rows, ledger):
        q = ("이 제품을 사고 싶게 만드는 이유의 1순위와 2순위를 하나씩 고르라. "
             "'사고 싶은 이유 없음'을 1순위로 고르면 2순위는 비운다.")
        r1 = self._ask(persona, q + " (1순위)", rows, ledger)
        first = r1["choice"]
        if first == "사고 싶은 이유 없음":
            return first, None
        rest = [x for x in rows if x != first]
        r2 = self._ask(persona, q + f" (1순위='{first}'; 2순위, 없으면 '없음')",
                       rest + ["없음"], ledger)
        second = r2["choice"]
        return first, (None if second == "없음" else second)

    def accept_price(self, persona, price, ledger):
        q = (f"이 제품이 {price:,}원이라면 사겠는가? "
             "사람은 보통 한 임계 이하 가격만 산다(단조). 회의적으로 판단하라.")
        return self._ask(persona, q, ["산다", "안 산다"], ledger)["choice"] == "산다"

    def freetext(self, persona, item, ledger):
        if item == "E2":
            r = self._ask(persona, "방금 고른 문구가 더 끌린 이유를 한 단어~한 문장으로(선택).",
                          ["작성", "공란"], ledger)
            return r.get("why", "") if r["choice"] == "작성" else ""
        return ""


# 컨셉카드(동결 사실만) — 순차노출에서 2단계(컨셉) 진입 시에만 프롬프트에 노출
CONCEPT_CARD = (
    "태국 볶음쌀국수 '팟타이'를 한국 재료로 재해석한 냉동 간편식. 새콤한 맛을 내는 "
    "타마린드 대신 매실청을 써서 고수·피시소스 같은 향 부담을 덜었습니다. 냉동 쌀면 + "
    "매실청 소스 + 국산 새우·숙주·부추, 1인분(300g), 5분 완조리."
)


def get_backend(name: str = "mock") -> Backend:
    return {"mock": MockBackend, "claude": ClaudeBackend}[name]()
