# -*- coding: utf-8 -*-
"""제네시스 유럽 인지 설문(로테르담 거리 + 잔드보르트 GP) 시뮬 — 설정 v1.0
==========================================================================
딱지: [실측]/[근사]/[스윕]/[운영] — 게이트C·robot_wc26 규율 동일.

설계 확정 사항(사용자 확인·현장 매뉴얼 v4):
  - DAY 1 로테르담 거리 서베이는 **GP 이전** 실행 → GP 주말 뉴스 오염 없음.
  - 로고 카드: BMW·Lexus·Polestar·Genesis 4종, **워드마크 포함** 표준 로고, 배열 2버전 로테이션.
  - 마그마(레이싱) 후속 질문은 **GP 팬존 전용**(로테르담에서 묻지 않음 — 사전등록 지표).
  - 그룹 규칙: 첫 응답자만 클린, 이후 grp 태그. BMW 모름 = 품질 의심 태그.

순환 차단 구조(robot_wc26 동일 — 판정단 P2-01·P1-02 반영판):
  - 브랜드 인지 상태는 **상류(파이썬)에서 스윕 밴드로 표집해 주입**. AIDED_BANDS는
    **'knows 상태' 확률**이며, 현장 관측량(카드 Y율)은 knows+vague발화+예스세잉의 합성 —
    judge가 관측공간 파생 기대치를 병기한다(카드Y ≈ k×0.9 + 0.10×0.5 + ys×잔여).
  - LLM 고유 기여 = 비보조 상기의 **브랜드 구성**(단, 카드 4브랜드는 프라이밍 하 생성이라
    판독 제외 — P2-06), 마그마 회상의 **내용**(verbatim), 연령·관심 조건부 형상.
  - 예스세잉은 **입력 전파(에코)**다 — 프롬프트에 바닥 %를 주입하므로(GH6는 에코 확인용).
    무주입 예스세잉 형상 측정은 v2 백로그(프롬프트 수치 제거 후 재측정).

출처: 조사 감사 1~4(2026-08-08/09). 이하 '감사N'.
"""

SCENARIOS = ("conservative", "neutral", "optimistic")
SCEN_IDX = {"conservative": 0, "neutral": 1, "optimistic": 2}

POPULATIONS = ("street_rtm", "gp_zandvoort")

# ─────────────────────────────────────────────────────────────────────────
# 0. 배경 팩트 [실측]
# ─────────────────────────────────────────────────────────────────────────
FACTS = {
    "genesis_nl": "출시 2026-03-20(PR·딜러 중심, 전국 TV/OOH 미확인[감사4]) · 등록누계 24대(7월까지) · 도로 위 50대",
    "nl_fleet": {"BMW": 472774, "LEXUS": 29348, "POLESTAR": 14814, "GENESIS": 50},  # [실측 2026-06/07]
    "uk_anchor": "Motorpoint 2026-01(자동차 보유자 n=2,000): Genesis 이름 53%·로고 27% — 이벤트 前 베이스라인",
    "be_polestar": "벨기에 2025 naamsbekendheid 49.6%(표본 미공개) — 인접국 참고만 [감사4]",
    "gmr_nl_media": "네덜란드어 F1 매체 Genesis/GMR 명시 ≥13건(GPblog 8·GPFans 2·RN365 1·Formule1.nl 2, "
                    "Verstappen→Juncadella 연결고리) — 노출 경로 실재, 도달·전환율 미공개 [감사4]",
    "gmr_results": "2026 WEC: 스파 8위(첫 포인트)·르망 데뷔 13위/#17 DNF·상파울루 13/15위. 다음 오스틴 9/6(여정 후)",
    "dutch_gp": "2026-08-21~23(최종회) · 공식 파트너 9개에 Genesis·Hyundai 없음[실측·감사4] · "
                "2025 입장 30.5만/4일·해외 ~30%[근사·2차] · 해외객 최대 집단 독일",
    "wec_follow_f1": 0.33,   # P(WEC 관심|F1 팬) [실측·자발표본 n=167,302]
}

# ─────────────────────────────────────────────────────────────────────────
# 1. 모집단 구성 [운영/근사]
# ─────────────────────────────────────────────────────────────────────────
AGE_BANDS = ["<30", "30-50", "50+"]
AGE_MIX = {
    "street_rtm": [0.32, 0.44, 0.24],          # 광장 행인 [운영]
    "gp_zandvoort": [0.35, 0.45, 0.20],        # F1 팬 젊은 편(2025 설문 avg 37.4·U35 42%) [근사]
}
# 거주국 — street: 로테르담(관광 20%) / GP: 2025 해외 ~30%·독일 최대 [감사4 §6]
RES_MIX = {
    "street_rtm": {"NL": 0.80, "DE": 0.04, "BE": 0.03, "UK": 0.02, "OTHER": 0.11},
    "gp_zandvoort": {"NL": 0.72, "DE": 0.13, "BE": 0.04, "UK": 0.03, "OTHER": 0.08},
}
GP_CONTEXTS = {"entry_queue": 0.4, "exit_queue": 0.6}   # 퇴장줄 최대 수확 구간 [매뉴얼]

LATENT_SPECS = {
    "car_interest":   {"street_rtm": (0.42, 0.24), "gp_zandvoort": (0.68, 0.18)},
    "ev_interest":    {"street_rtm": (0.45, 0.24), "gp_zandvoort": (0.50, 0.24)},
    "wec_follow":     {"street_rtm": (0.15, 0.15), "gp_zandvoort": (0.33, 0.22)},  # GP 평균=0.33 앵커 [실측]
    "nl_f1_media":    {"street_rtm": (0.20, 0.18), "gp_zandvoort": (0.55, 0.22)},  # GPblog류 소비 [근사]
    "premium_affinity": {"street_rtm": (0.42, 0.24), "gp_zandvoort": (0.52, 0.22)},
}

# ─────────────────────────────────────────────────────────────────────────
# 2. 보조 인지(로고 카드·워드마크 포함) 밴드 (low, mid, high) — 사전등록 예측 본체
#    카드가 워드마크 포함 → 순수 로고가 아니라 '이름 인지'에 가까움 [매뉴얼·감사2 논의]
# ─────────────────────────────────────────────────────────────────────────
AIDED_BANDS = {
    "street_rtm": {
        "BMW":      (0.95, 0.97, 0.99),   # 품질 앵커(모르면 현장서 품질의심 태그) [운영]
        "LEXUS":    (0.55, 0.68, 0.80),   # 도로 2.9만대·2023 TV 집행 이력 [스윕·근사방향]
        "POLESTAR": (0.30, 0.45, 0.60),   # 도로 1.5만대·BE 49.6% 인접 [스윕·근사방향]
        "GENESIS":  (0.04, 0.10, 0.18),   # 도로 50대·PR-only·4.5개월 — UK 53%는 이식 불가 [스윕]
    },
    "gp_zandvoort": {
        "BMW":      (0.97, 0.98, 0.995),
        "LEXUS":    (0.62, 0.74, 0.84),
        "POLESTAR": (0.40, 0.55, 0.70),
        "GENESIS":  (0.15, 0.27, 0.40),   # F1/WEC 기사 경로 ≥13건 실재 → 냉출발 아님 [감사4·스윕]
    },
}
# 예스세잉(포일 없는 카드의 오인정 바닥): 무지식층이 '본 것 같다'고 Y — Genesis Y의 해석 상한 문제
YES_SAYING_BASE = (0.02, 0.04, 0.08)     # [근사 — 보조인지 인플레이션 일반론; 카드에 가짜 브랜드 없음]
VAGUE_MARGIN = 0.10                       # knows 미달 시 '어렴풋' 상태 폭 [운영]

# 브랜드별 성향 보정 [근사방향] — 개인 간 '기울기'만 만들고 모집단 평균은 밴드에 고정
POLESTAR_EV_MULT = (0.80, 0.50)   # ×(0.80+0.50×ev_interest) — EV 관심층·젊은층 상향
AGE_MULT = {"POLESTAR": {"<30": 1.15, "30-50": 1.0, "50+": 0.85},
            "LEXUS":    {"<30": 0.90, "30-50": 1.0, "50+": 1.15}}
GENESIS_CAR_MULT = (0.60, 0.80)   # ×(0.60+0.80×car_interest)
GENESIS_WEC_MULT = 1.6            # GP: WEC 팔로워 상향(인지 경로=레이싱 뉴스) [감사4]
GENESIS_F1MEDIA_MULT = (0.70, 0.60)  # ×(0.70+0.60×nl_f1_media)
# 승수 정규화(P2-04): 손계산 상수 대신 build_pool이 모집단 스펙에서 **수치로 산출**해 나눈다
# (고정 서브시드 MC — 결정론). LEXUS 포함 전 승수 브랜드 일괄. '선언 밴드=기대 knows율' 불변식.
# 마그마 조건승수(1.5/0.7)도 동일 정규화(E[factor]≈0.877 — P2-03).

# ─────────────────────────────────────────────────────────────────────────
# 3. 비보조 상기(Q1)·마그마(GP 전용)
# ─────────────────────────────────────────────────────────────────────────
UNAIDED_GENESIS = {"street_rtm": (0.000, 0.005, 0.02),   # 사실상 0 — 언급되면 그 자체가 뉴스 [스윕]
                   "gp_zandvoort": (0.01, 0.03, 0.07)}
# P(마그마 들어봄 | Genesis 카드 Y, GP) — NL의 Genesis 인지 경로 자체가 레이싱 뉴스라 조건부 높음
# (구조 예측: UK처럼 쇼룸·광고가 아니라 F1/WEC 기사가 지배 경로) [감사4 §3 — 스윕]
MAGMA_GIVEN_GENESIS_GP = (0.25, 0.42, 0.60)
MAGMA_DEPTH = {"specific_if_wec": 0.65,   # WEC 팔로워면 구체 회상(르망·드라이버·GMR-001) [운영]
               "vague_else": 0.75}        # 비팔로워 마그마 Y는 대개 막연("르망 나왔죠?")

# ─────────────────────────────────────────────────────────────────────────
# 4. 코딩 — Q1 브랜드 정규화·마그마 깊이
# ─────────────────────────────────────────────────────────────────────────
BRAND_ALIASES = {
    "BMW": ["bmw"], "MERCEDES": ["mercedes", "merc", "benz", "amg"], "AUDI": ["audi"],
    "PORSCHE": ["porsche"], "TESLA": ["tesla"], "VOLVO": ["volvo"], "LEXUS": ["lexus"],
    "POLESTAR": ["polestar"], "GENESIS": ["genesis"], "JAGUAR": ["jaguar", "jag"],
    "LANDROVER": ["land rover", "range rover"], "BENTLEY": ["bentley"],
    "FERRARI": ["ferrari"], "LAMBORGHINI": ["lamborghini", "lambo"], "MASERATI": ["maserati"],
    "ROLLSROYCE": ["rolls", "rolls-royce", "rolls royce"], "ASTON": ["aston", "aston martin"],
    "CADILLAC": ["cadillac"], "LUCID": ["lucid"], "NIO": ["nio"], "BYD": ["byd"],
    "ALFAROMEO": ["alfa"], "MINI": ["mini"], "CUPRA": ["cupra"], "DS": ["ds"],
}
MAGMA_SPECIFIC_KEYS = ["magma", "gmr", "juncadella", "lotterer", "hypercar", "ickx",
                       "spa", "imola", "austin", "chadwick", "gmr-001"]
# P1-08: 질문이 직접 제시한 어휘("in racing — Le Mans, or the WEC")만 반복한 답은
# 지식이 아니라 반향(echo) — 별도 코드로 분리해 GH4 깊이 분포 오염 차단
MAGMA_ECHO_KEYS = ["le mans", "lemans", "wec", "racing"]
MAGMA_VAGUE_KEYS = ["endurance", "race", "races", "race team", "24 h", "24h",
                    "motorsport", "championship"]

# ─────────────────────────────────────────────────────────────────────────
# 5. 사전등록 가설(G-H) — judge 판독 대상
# ─────────────────────────────────────────────────────────────────────────
# [밴드 의미론 — P1-02] AIDED_BANDS = 'knows 상태' 확률. judge가 관측공간 기대치를 파생·병기.
# [판정 어휘 — P2-10] 시뮬 verdict: '전파 확인/자기일관/기제 이상/판정 유보'. 지지/반증=현장 전용.
PREREG = [
    {"id": "GH1", "claim": "로테르담 비보조에서 Genesis 언급 ≈ 0 (0~2%) — 언급 1건도 특기사항. "
                           "비보조 랭킹에서 카드 4브랜드는 프라이밍 하 생성이라 판독 제외(P2-06)",
     "band": (0.00, 0.02), "layer": "혼합", "basis": "[스윕] 도로 50대·PR-only·4.5개월"},
    {"id": "GH2", "claim": "거리 카드 서열 BMW ≫ Lexus > Polestar ≫ Genesis (Genesis knows 4~18%)",
     "band": (0.04, 0.18), "layer": "전파",
     "basis": "[스윕·근사방향] 차량수 서열(감사4: 비율≠인지율, 방향만). 관측량 대조는 파생 기대치로"},
    {"id": "GH3", "claim": "GP 팬존 Genesis 인지 ≥ 거리의 2배 (모터스포츠 경로 도달의 헤드라인 판정) — "
                           "거리 Y<3이면 배수 미판정, Fisher 방향판정으로 대체(P1-09)",
     "band": (2.0, 5.0), "min_street_y": 3, "layer": "전파",
     "basis": "[입력전파+감사4] NL 미디어 경로 ≥13건 실재 — 격차 크기는 스윕"},
    {"id": "GH4", "claim": "GP의 P(마그마 들어봄|Genesis Y) 25~60% — 현장 Y는 유도형 질문의 상한 해석"
                           "(GH6 동형·P1-08). 질문 어휘만 반복한 답은 echo로 분리 코딩",
     "band": (0.25, 0.60), "min_denom": 8, "layer": "전파",
     "basis": "[스윕] WEC|F1=33%[실측] × 기사→기억 전환율[스윕]"},
    {"id": "GH5", "claim": "모집단 내(within-pop) <30×EV관심층에서 Polestar가 Lexus 역전(전체는 Lexus 우위) — "
                           "동률은 미판정, 현장은 눈추정 감쇠로 방향만(P2-08·P1-12)",
     "band": None, "layer": "LLM", "basis": "[근사방향] EV 시장·차령 구조 — LLM 조건부 형상"},
    {"id": "GH6", "claim": "Genesis 카드 Y는 상한 해석 — 포일 없는 카드의 예스세잉 바닥(2~8%)과 미분리",
     "band": (0.02, 0.08), "layer": "전파",
     "basis": "[근사·에코 확인] 바닥 %는 프롬프트 주입값 — GH6는 전파 확인이지 LLM 기여 아님(P2-01)"},
    {"id": "GH7", "claim": "표본 투영: 거리 n=25에서 Genesis Y 1~4명 / GP n=40에서 6~16명 — 격차는 방향만. "
                           "카드 분모는 grp 포함(매뉴얼: 로고 인지는 각자 유효)",
     "band": None, "layer": "전파", "basis": "소표본 — %p 비교 금지, 서열·배수만"},
    {"id": "GH8", "claim": "마그마 발동 수 = GP Genesis Y 인원(≈6~16) — 마그마 데이터는 일화 수준",
     "band": None, "askable_ok_min": 17, "layer": "전파",
     "basis": "분기 소표본 경고(robot H7과 동형) — 임계는 claim 상단과 정합(P2-10)"},
]

FIELD_PLAN = {"street_n": (20, 25, 30), "gp_n": (30, 40, 50),
              # P1-06 정정: 매뉴얼 원문은 'grp 행도 로고 인지는 각자 유효' — 문항별 규칙으로 사전등록
              "grp_rule": "Q1 비보조만 grp 행 제외(오염), 카드 4종 Y/N은 grp 행도 유효(매뉴얼 ①-1 그대로)",
              "grp_share_expected": (0.10, 0.18, 0.25),   # [운영] 2~3인 그룹 접근 비중
              # P1-10: 완주자 기준 예측(오프닝이 'car brands' 주제 공개 → 관심 선택편향 상향 내재)
              "population_note": "완주자 기준 예측(주제 관심 선택편향 내재·상향 방향)",
              # P4-03: '로테르담=GP 이전'은 사용자 확인된 '전제'(매뉴얼 원문은 '날짜 유동') — 위반 폴백:
              "pre_gp_fallback": "거리 조사일이 8/23 이후면 street 데이터를 post-GP 태그로 강등 — "
                                 "GH1~GH3 방향만 판독, 밴드 판정 중지. report에 조사일 기입",
              # P4-04: 8/23 당일 운영 규칙(발화 대본 불변 — 운영 양식만)
              "gp_day_rules": ["팬존에 Genesis/현대 활성화 목격 시: 사진+시각 기록, 이후 응답에 primed 태그 — "
                               "GH3·GH4는 primed 제외/포함 2값 보고",
                               "시트 13열 권장(+grp, +카드vA/vB) — grp 문항별 분모·카드 순서효과 절차의 실행 조건"],
              "note": "로테르담=GP 이전 실행(사용자 확인 전제 — 위반 시 pre_gp_fallback)."}


def band(t, scenario):
    return t[SCEN_IDX[scenario]]
