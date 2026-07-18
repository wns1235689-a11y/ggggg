> **작업 기준 브랜치: `claude/runner-md-guide-89tnrn`**
> 기준 문서 4종(INVENTORY · SPEC · INSPECTION · RUNNER)과 구현 전체가 이 브랜치에 있다.
> `claude/simulation-survey-planning-d9rlih`는 이 브랜치의 **조상으로 동결**된 planning trunk다(직접 작업 금지).
>
> **임무 완료 조건**: 이후 새 세션이 새 브랜치를 따서 작업하는 경우, 작업을 마친 뒤 그 결과를 이 기준 브랜치(`claude/runner-md-guide-89tnrn`)로 **머지하는 것까지**가 임무 완료다. 새 브랜치만 푸시하고 종료하면 미완료로 간주한다.

---

# 게이트 C — 합성 시뮬레이션 설문 프로젝트

냉동 간편식 컨셉('매실청 팟타이') 수요검증 설문(게이트 C)을 **LLM 기반 합성 시뮬레이션**으로 돌려, 현실 설문에 최대한 가까운 결과를 얻기 위한 작업 공간.

## 문서
- **[`시뮬레이션_설계_브레인스토밍.md`](시뮬레이션_설계_브레인스토밍.md)** — 현재 단계 산출물. 시뮬레이션 파이프라인의 단계(S0~S9)·필요자료·보조프롬프트·검증전략 계획 초안.
- `docs/source/게이트C_설문설계_v1.4.md` — 원본 설문 설계서(사전등록·잠금).
- `docs/source/게이트C_파일럿프로토콜.md` — 파일럿 실행 프로토콜.

## 현재 상태
**파이프라인 S0→S9 완성·검증(v0.3).** 단일 산출물=50~100명 시뮬, 게이트B 실측을 입력 프라이어 앵커로 채택, E1 균등화 패러프레이즈, N5 스팟체크 유지.

- ✅ **S1–S3** 채널 조건부 결합분포 표집 → 잠재특성 → 스크리닝 (통계청·KREI 실측 grounding)
- ✅ **S4** unprimed 순차노출 상태기계 + SSR/VS 응답생성 (mock 검증 + ClaudeBackend 표준코드)
- ✅ **S6–S9** 행동노이즈 주입 · §3 잠금집계 · 이중용도 A/B 산출 · 정직성 린터

```
# 오프라인(mock) — 즉시 실행:
python3 run.py 100 mock
# 실 LLM(현실성) — 키 설정 후:
ANTHROPIC_API_KEY=... python3 run.py 100 claude
```
산출: `out/responses.csv`(Forms 동형) · `aggregate.json` · **`report_9_4.md`**(이중용도 A/B + 린터)

```
sim/config.py     실측 앵커·게이트B 입력앵커·§3 규칙·E1 패러프레이즈·출처
sim/sampler.py    S1–S3 결합분포 표집·잠재특성·스크리닝
sim/backends.py   MockBackend(오프라인) + ClaudeBackend(실 LLM VS)
sim/respondent.py S4 순차노출 상태기계(unprimed 봉인·E1 스왑·노이즈)
sim/aggregate.py  S7 §3 잠금집계(A/B 버킷 분리)
sim/report.py     S8 §9.4 5블록 이중용도 리포트
sim/linter.py     S9 정직성 린터(A/B 계약·🔴 등급·금지어)
run.py            오케스트레이터
```

## 핵심 원칙
시뮬레이션은 **'보정되지 않은 방향성 사전분포 + 설계리스크 탐지기'**이며, 파일럿 실측이 도착해야 '보정된 예측'으로 도약한다. **게이트 B와 §3 잠금 판정은 시뮬레이션으로 변경하지 않는다.**
