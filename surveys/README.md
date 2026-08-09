# surveys/ — 다설문 매니페스트 (하니스 설문 독립화)

하니스(러너·잡·저장소·플러그인 계약·UI 배관)는 설문 무관이다. 설문마다 다른 것 —
풀 생성·wf 프롬프트/스키마·진단·판정·리포트 — 은 `surveys/<survey_id>/`에 두고
`manifest.json`으로 선언한다. 라우팅은 `survey_registry.py`가 담당한다.

## 매니페스트 계약

```json
{
  "survey_id": "디렉토리명과 일치",
  "label": "UI 표시명",
  "journal_marker": "저널 result 행에서 이 설문을 식별하는 필드",
  "builds": {"<kind>": "풀 생성 스크립트 경로"},
  "wf_scripts": ["러너 허용 워크플로 경로"],
  "verify": "진단 플러그인 | null",
  "judge": "판정 플러그인 | {\"single\":…, \"multipool\":…} | null",
  "report": "리포트 플러그인 | \"legacy\" | null",
  "curve": "\"legacy_d1\"(게이트C 전용) | null"
}
```

플러그인 계약(기존과 동일): `python3 <script> <run_id>` + harness_paths 환경변수
(`HARNESS_SP`=runs/<run_id>, `HARNESS_JOURNAL_BASE`=runs/) → **JSON stdout**.
리포트 플러그인은 `{"markdown": …}` 포함. 풀 산출 파일명은 persist_run과 호환되게
`prof.json`/`pool_meta.json`/`run_cfg.json`(+ run_cfg에 `survey_id` 기입).

## 등록된 설문

| survey_id | 내용 | 비고 |
|---|---|---|
| `gatec_v23` | 게이트C v2.3 매실청 팟타이 (레거시 계보) | 기존 루트 스크립트를 가리키기만 — 엔진 동결(SPEC §2·§6) 무수정 |
| `robot_wc26` | 월드컵 하프타임 로봇 인지 — 유럽 거리 설문 | 2026-08 여정 사전등록 예측용 |
| `genesis_eu26` | 제네시스 유럽 인지 — 로테르담 거리(GP前)+GP 팬존 | 2모집단 한 풀(격차 판정), 마그마=GP 전용 |

## robot_wc26 설계 요점 (순환 차단 구조)

- **노출·지식 상태는 상류(build_pool.py) 주입**: config의 [스윕] 밴드에서 표집해
  페르소나 사실로 박음 → Q1 수준·채널믹스·국가서열은 "입력 전파"로 문서화(측정 아님).
- **LLM 고유 기여 = 조건부 행동**: 무지 상태의 오답 구성(verbatim), DK 비율, 프로브
  반응, Q3 형상. 정답(BD/현대)·오답 후보(Tesla 등)는 프롬프트에 나열하지 않는다.
- **Q2는 verbatim 생성 → coding.py가 §6 코드 판정**(A1/A2/A3/G/W-x/DK + DESC 부록
  코드) — 카테고리를 스키마에 두면 후보 주입이 되므로 자유 문자열로 받는다.
- **verify의 고유 진단 = 지식 누출**: 무지식층 verbatim에서 정답이 새면(LLM은 정답을
  안다) 런 격하. mock_journal.py가 의도 결함(누출·에코 위반)을 주입해 검출을 검증.
- config의 모든 수치는 [실측]/[근사]/[스윕]/[운영] 딱지 + 조사 감사 기록 2건
  (2026-08-08/09)을 출처로 명기.

## 새 설문 추가 절차

1. `surveys/<id>/` 생성: config.py → build_pool.py → wf_*.js(**러너의 args 주입 라인
   `const personas = typeof args === 'string' ? JSON.parse(args) : args` 필수 포함**)
   → verify.py → judge.py → report.py → manifest.json.
2. 오프라인 검증: 풀 시드 재현(bit-identical) → mock 저널 → verify/judge/report 체인
   → **`surveys/assert_mock.py <mock_run_id>`로 주입 결함 검출 단언(비영 종료)**.
3. **`surveys/check_bands.py`** — 밴드↔주입 정규화 불변식·표집 정합 기계 검산(LLM 불필요).
4. dry_run(N≤2) 실 LLM 스모크 → 본 실행. 비용 가드(runner)는 설문 무관 공통.
   **genesis처럼 다모집단 설문은 풀이 모집단 교차 배치라 dry-run 2명이 두 모집단을 커버**
   — 본 실행 전 GP(마그마 분기) 포함 dry-run 1회 필수.

## 사전등록 봉인 절차 (P4-02 — 선행성 입증)

봉인 = "시뮬 예측이 현장보다 먼저 존재했다"의 git 증명. 절차:

1. 시나리오 3종(conservative/neutral/optimistic) × 시드 3개 풀 생성 → 실 LLM 런
   (단일 시드는 표집 노이즈가 밴드 폭을 압도할 수 있음 — verify의 pool_drift 경고 참조).
2. `check_bands.py` 통과 확인(밴드·주입 정합) + 각 런 verify 경고(누출·에코) 확인.
3. `python3 surveys/seal_prereg.py <label> <run_id...>` → `SEALED_<label>.json` 생성
   (run_cfg의 config/wf 해시·git HEAD가 함께 박제됨).
4. `git add -A && git commit && git tag prereg-seal-<label>` — **태그 이후 config 수정은
   새 봉인으로만**. 현장 대조는 태그 시점의 리포트 3부(시나리오별)와만 한다.
