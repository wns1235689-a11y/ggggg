# LEGACY.md — 동결 파일 목록 (역사적 아티팩트)

> **지위**: 아래 파일들은 **v2.3 이전 버전 계보의 역사적 아티팩트**다. Research Harness UI(SPEC.md)의 현행 계보에 포함되지 않는다.
> **규칙**: 읽기만 가능. **수정·삭제·이동 금지.** 지우지 않고 보존한다(설계 근거·재현 이력의 일부).
> **기준**: SPEC.md §2 「계보 경계」의 레거시 동결 목록. 현행 계보(수정 허용 대상)는 SPEC §2를 참조.

## 동결 파일

### 구형 워크플로 (wf_*.js)
- `wf_precise_survey.js` — 순차노출 단일선택 설문(mode collapse 확인되어 VS 계열로 대체됨)
- `wf_vs_dist.js` — B1/C1/C2 부분 VS 분포
- `wf_vs_d1.js` — 가격 수용인원 분포
- `wf_vs_cat.js` — A1/A2/B2/B3/E1 부분 VS 분포
- `wf_e1_dist.js` — E1 4지 분포(양자택일 붕괴 보정)
- `wf_vs_all.js` — VS 전면화(전 문항 분포, v1.x 문항 세트 — v2.3 이전)
- `wf_fidelity.js` — 충실도 메타평가(N=74 세대 기준 고정)

### 구형 경로 후처리
- `extract_raw.py` — 저널 → survey_raw/dist_raw/d1_raw 추출
- `map_and_ingest.py` — 원문라벨 매핑·VS표집·정합틸트·집계
- `patch_vs.py` — B1/C1/C2 재표집 패치
- `patch_e1.py` — E1 4지 재표집 패치(rows_final in-place)
- `patch_e2.py` — xlsx E2 열 교체

### 일회성 실험
- `e2_refine.py`, `e2_refine2.py`, `e2_refine3.py`, `e2_refine_v15b.py`, `e2_refine_v15c.py`, `e2_refine_oversample.py` — E2 서술형 3회 다듬기(표본별 pid 고정 문구, 수작업 산출물)

### 구세대 풀
- `build_oversample.py` — 향기피 오버샘플(N=58)

### 구형 산출
- `build_xlsx.py` — rows_final + e2_final → xlsx
- `build_sweep_xlsx.py` — 스윕 저널 → xlsx

### 미검증 A경로 (코드형 파이프라인)
- `run.py` — 오케스트레이터(mock/claude 백엔드)
- `run_live.py` — 워크플로 응답 → S7~S9
- `sim/backends.py` — MockBackend + ClaudeBackend(anthropic SDK 직접 호출)
- `sim/respondent.py` — S4 순차노출 상태기계
- `sim/aggregate.py` — §3 잠금 집계
- `sim/report.py` — §9.4 이중용도 리포트
- `sim/linter.py` — 정직성 린터
- `sim/ingest.py` — 라이브 응답 매핑

## 비고
- `sim/config.py`·`sim/sampler.py`는 **현행 계보의 공유 라이브러리**이므로 레거시가 아니다(SPEC §2). 단 Phase 0에서 이 두 파일 자체는 수정 대상이 아니며, 현행 계보 스크립트가 의존하는 범위로만 사용된다.
- 위 레거시 목록에도 세션 특정 경로(SP·저널 BASE)와 하드코딩이 남아 있으나(INVENTORY §4), Phase 0의 경로/시드 파라미터화는 **현행 계보에만** 적용한다. 레거시 파일의 하드코딩은 그대로 둔다.
