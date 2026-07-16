# INVENTORY.md — 시뮬레이션 엔진 인터페이스 기준 문서

> **목적**: 이 repo 위에 로컬 웹 UI(research harness: 설문 설계→풀 생성→시뮬 실행→붕괴 진단→판정→리포트)를 얹을 백엔드가 호출할 인터페이스의 단일 기준 문서.
> **기준 브랜치**: `claude/simulation-survey-planning-d9rlih` · **정찰 방식**: 정적 읽기 전용(코드 실행 없음) · **작성일**: 2026-07-16
> **표기 규율**: 정적으로 확정 불가한 내용은 `[불명확: 이유]`. API 키·토큰·정확한 모델 ID 문자열은 기재하지 않음(위치만 기재).

---

## 0. 전체 파이프라인 흐름

이 repo에는 **두 갈래의 실행 경로**가 공존한다. (A)는 초기 코드형 파이프라인(오프라인 mock 또는 anthropic SDK 직접 호출), (B)는 현행 주력 경로(Claude Code 하니스의 Workflow 도구로 LLM 에이전트를 돌리고, 그 저널을 파이썬으로 후처리).

### (A) 코드형 파이프라인 — `run.py` (오프라인 완결 가능)

```
sim/config.py (전역 상수: 시드·CPT·잠재분포·앵커)
      │
      ▼
run.py [N] [mock|claude]
  ├─ sim/sampler.py     S1–S3: 페르소나 풀 표집(결정론)
  ├─ sim/backends.py    S4: MockBackend(규칙) 또는 ClaudeBackend(anthropic SDK 직접 호출)
  ├─ sim/respondent.py  S4: 순차노출 상태기계 + 노이즈 주입
  ├─ sim/aggregate.py   S7: §3 잠금 집계(A/B 버킷)
  ├─ sim/report.py      S8: §9.4 이중용도 리포트
  └─ sim/linter.py      S9: 정직성 린터
      │
      ▼ 출력(디렉토리 out/ — .gitignore로 비추적)
out/personas.csv, latents.csv, summary.json, responses.csv, aggregate.json, report_9_4.md
```

변형: `run_live.py <agent_responses.json>` — 외부(워크플로)에서 만든 응답 JSON을 `sim/ingest.py`로 받아 S7→S9만 수행 → `out/responses_live.csv`, `aggregate_live.json`, `report_live_9_4.md`.

### (B) 워크플로 파이프라인 — 현행 주력 (Claude Code 하니스 필요)

```
[1. 풀 생성 — python, LLM 불요]
build_fresh_pool.py │ build_oversample.py │ build_sweep.py │ build_multipool.py
      │ (sim/config.py의 C.GLOBAL_SEED·C.LATENT_SPECS를 전역 덮어쓰기 후 sampler.build_pool)
      ▼ 출력(모두 세션 스크래치패드 SP = /tmp/claude-0/.../scratchpad — 경로 하드코딩)
  prof.json + pool_meta.json + run_cfg.json          (fresh/oversample)
  sweep_prof.json + sweep_meta.json                  (sweep)
  multipool_args.json + multipool_meta.json + multipool_cfg.json  (multipool)

[2. 시뮬 실행 — wf_*.js, Claude Code Workflow 도구 전용(§1 참조; node 단독 실행 불가)]
  구형 3-워크플로 경로: wf_precise_survey.js(설문) + wf_vs_dist.js(B1/C1/C2 분포) + wf_vs_d1.js(가격분포)
  신형 VS-전면화 경로:  wf_vs_all.js(전 문항 분포) │ wf_vs_v23.js(v2.3 문항) │ wf_v23_multi.js(3풀×100)
      │ 입력: personas — 구형은 Workflow args로 주입, 신형 3종은 파일에 JSON 리터럴로 baked
      ▼ 출력(하니스 저널 — repo 밖, 세션 컨테이너 경로)
  /root/.claude/projects/<프로젝트>/subagents/workflows/<runId>/journal.jsonl
  (라인 스키마: {"type":"started"|"result","key","agentId"[,"result":{...}]})

[3. 추출·매핑·정합 — python (구형 경로)]
extract_raw.py <survey런ID> <dist런ID> <d1런ID>
      ▼ SP/survey_raw.json + dist_raw.json + d1_raw.json
map_and_ingest.py  (survey_raw + dist_raw + d1_raw + run_cfg → 라벨 매핑·VS표집·정합틸트·집계)
      ▼ SP/rows_final.json + agg_final.json
(보조 패치: patch_vs.py=B1/C1/C2 재표집, patch_e1.py <런ID>=E1 4지 재표집)

[4. E2 서술형 다듬기 — python, 정적 텍스트 사전(pid 하드코딩)]
e2_refine*.py  (rows_final + survey_raw + prof → 3패스)
      ▼ SP/e2_work.json, e2_pass1~3.json, e2_final.json

[5. 산출 — python]
build_xlsx.py        (rows_final + e2_final → exports/게이트C_합성시뮬응답_*.xlsx)
build_sweep_xlsx.py <저널경로>  (저널 + sweep_prof/meta → exports/..사전분포스윕120.xlsx)
patch_e2.py <xlsx> <e2json>     (기존 xlsx의 E2 열만 교체)

[6. 진단·판정 — python, stdout 전용 (신형 경로는 저널을 직접 읽음)]
vs_verify.py <런ID>              붕괴 해소 검증(믿음질량·realized)
vs_compare.py <구런ID> <신런ID>   탈동질화 전/후 대조
v23_analyze.py <런ID>            v2.3 단일풀 판정(세그교차·dose-response 등)
v23_multi_analyze.py <런ID>      다풀 견고성 + 시드앙상블
analyze_sweep.py <저널경로>       사전분포 스윕 robust/fragile 분류 (+ SP/sweep_analysis.json)
```

### 단계 간 파일 계약 요약

| 생산자 | 파일 | 소비자 |
|---|---|---|
| build_fresh_pool / build_oversample | `SP/prof.json`(워크플로용 페르소나), `SP/pool_meta.json`(ingest용 메타), `SP/run_cfg.json`(`{"N","RUN_SEED"}`) | wf_*(args), map_and_ingest, v23_analyze, vs_verify, e2_refine* |
| build_sweep | `SP/sweep_prof.json`, `SP/sweep_meta.json`(pid→cfg·시드) | 스윕 설문 워크플로, analyze_sweep, build_sweep_xlsx |
| build_multipool | `SP/multipool_args.json`(300명), `SP/multipool_meta.json`, `SP/multipool_cfg.json`(풀시드·SAMPLE_SEED) | wf_v23_multi(베이크 원료), v23_multi_analyze |
| wf_*(Workflow 도구) | `<하니스>/workflows/<runId>/journal.jsonl` | extract_raw, patch_e1, analyze_sweep, build_sweep_xlsx, vs_verify, vs_compare, v23_analyze, v23_multi_analyze |
| extract_raw | `SP/survey_raw.json`, `SP/dist_raw.json`, `SP/d1_raw.json` | map_and_ingest, e2_refine* |
| map_and_ingest | `SP/rows_final.json`, `SP/agg_final.json` | build_xlsx, e2_refine*, patch_e1 |
| e2_refine* | `SP/e2_final.json`(+ e2_work/pass1~3) | build_xlsx, patch_e2 |
| build_xlsx / build_sweep_xlsx | `exports/*.xlsx`(git 추적) | (최종 납품물) |

핵심 주의: **SP(스크래치패드)와 저널 경로는 특정 세션 컨테이너에 하드코딩**되어 있다(§4·§5). 웹 UI를 얹으면 이 두 경로의 파라미터화가 최우선 작업이다.
