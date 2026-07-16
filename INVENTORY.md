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

---

## 1. 실행 스크립트 인터페이스

### 1.0 wf_*.js 공통 — 실행 모델 (중요)

- `wf_*.js`는 **표준 Node 스크립트가 아니다.** `node wf_x.js`로 실행 불가. `export const meta = {...}` 선언 후 본문에서 하니스 제공 전역(`agent()`, `parallel()`, `phase()`, `log()`, `args`)을 사용하는 **Claude Code Workflow 도구 전용 스크립트**다.
- **실행 커맨드**: Claude Code 세션 안에서 Workflow 도구 호출 — `Workflow({scriptPath: "/home/user/ggggg/wf_vs_all.js"})` (인자 필요 시 `args:` 추가). `[불명확: Claude Code 하니스 밖(순수 CLI/서버)에서 이 스크립트를 실행하는 방법은 repo에 존재하지 않음 — 웹 UI 백엔드는 ①Claude Code를 서브프로세스로 구동하거나 ②agent()/parallel()에 상응하는 자체 LLM 호출 러너를 구현해야 함]`
- **모델**: 모든 `agent()` 호출에 `model` 필드 없음 → **세션 메인루프 모델을 상속**(하니스 규칙). repo 코드만으로 모델이 결정되지 않음. **effort**만 파일별 명시(아래 각 항목).
- **런ID·출력**: 실행 시 하니스가 `wf_` + 12자 hex 형태 런ID를 부여(예: `wf_9971e46b-6d1`) → 저널 `/root/.claude/projects/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/subagents/workflows/<runId>/journal.jsonl`. `[불명확: 런ID 생성 규칙·저널 경로 규칙은 하니스 내부 — repo에서는 관측된 형식과 분석 스크립트의 하드코딩 경로로만 확인]`
- **저널 라인 스키마**(실측 발췌):
  ```json
  {"type": "started", "key": "v2:ab55…", "agentId": "a06d8ad670741a90d"}
  {"type": "result", "key": "…", "agentId": "…", "result": {"pid": 0, "A1_dist": [5,3,1,1], …}}
  ```
  결과 회수 관례: `type=="result" and isinstance(result, dict) and "<식별필드>" in result` 필터 후 `result["pid"]` 키로 dedup(예: extract_raw.py:7-13).
- **스키마 강제**: 각 파일의 `SCHEMA` 상수(JSON Schema)가 `agent(…, {schema})`로 전달되어 구조화 출력을 강제. 합=10 제약은 스키마가 아니라 프롬프트 지시(위반 시 검증 없음 — §5 리스크).

### 1.1 wf_vs_all.js — VS 전면화(전 문항 분포) ★현행

- **역할**: 페르소나별 A1/A2/B1/B2/B3/C1/C2/E1 분포 + D1 수용인원(buy_*)을 에이전트 1개/페르소나로 산출(v1.x 문항 세트).
- **실행**: `Workflow({scriptPath: "/home/user/ggggg/wf_vs_all.js"})` — args 불요(아래 참조).
- **입력**: personas가 **파일에 JSON 리터럴로 baked** — `wf_vs_all.js:51` `const personas = [{"pid":0,…} ×49]`. 필드: `pid, S1, S2, S3, S4, S5, 향기피, 매실청, 관여, 회의, 가격민감, 접근성, 정통기대, 식사량, 카테고리빈도`(0~1 실수). 특성 등급화는 `lvl()` 5단계(`wf_vs_all.js:29`). effort=`'medium'`(`wf_vs_all.js:53`). 시드: 없음(LLM 분포 생성은 비결정 — 표집 시드는 후처리 스크립트 몫).
- **출력**: 저널 result 스키마(`wf_vs_all.js:6-24`):
  ```json
  {"pid":0, "A1_dist":[3,3,1,3], "A2_dist":[1,2,3,1,1,2], "B1_dist":[0,1,3,4,2],
   "B2_dist":[3,1,1,2,2,1], "B3_dist":[1,2,2,2,1,1,1], "C1_dist":[2,3,3,1,1],
   "C2_dist":[2,5,3], "E1_dist":[3,3,3,1], "buy_5900":8, "buy_6900":7, "buy_7500":5, "buy_8500":3}
  ```
- **의존성**: Workflow 런타임(LLM 호출은 하니스가 수행 — repo 코드에 API 호출 없음).

### 1.2 wf_vs_v23.js — v2.3 문항 시뮬 ★현행

- **역할**: 설문설계 v2.3 반영판 — A2를 4항목×3점(`A2a~A2d_dist`, 각 `[아니다,조금,매우]`) + `A2x_dist`([예,아니오]) 독립 측정, B2 5지(향 선택지 제거), E1 4지.
- **실행**: `Workflow({scriptPath: "/home/user/ggggg/wf_vs_v23.js"})`.
- **입력**: personas baked — `wf_vs_v23.js:59`(49명, wf_vs_all과 동일 풀). effort=`'medium'`(`wf_vs_v23.js:61`). 특성 등급 5단계(`:29`). 프롬프트·보기 정의 `:30-56`.
- **출력**: result 스키마(`wf_vs_v23.js:6-28`):
  ```json
  {"pid":0, "A1_dist":[5,3,1,1], "A2a_dist":[7,2,1], "A2b_dist":[6,3,1], "A2c_dist":[2,4,4],
   "A2d_dist":[3,4,3], "A2x_dist":[6,4], "B1_dist":[0,1,3,4,2], "B2_dist":[3,2,2,2,1],
   "B3_dist":[1,1,1,2,1,1,3], "C1_dist":[1,3,3,2,1], "C2_dist":[3,5,2], "E1_dist":[4,3,2,1],
   "buy_5900":8, "buy_6900":6, "buy_7500":5, "buy_8500":3}
  ```
- **의존성**: 1.1과 동일.

### 1.3 wf_v23_multi.js — v2.3 다풀(3×100) 견고성 ★현행

- **역할**: wf_vs_v23와 동일 프롬프트·스키마를 3개 독립 풀 300명에 적용(견고성 검정).
- **실행**: `Workflow({scriptPath: "/home/user/ggggg/wf_v23_multi.js"})`.
- **입력**: personas 300명 baked — `wf_v23_multi.js:59`. pid는 전역 유일화(`풀번호×1000 + 풀내pid`, build_multipool.py:37). effort=`'medium'`(`:61`). meta name=`gateC-v23-multi`(`:2`).
- **출력**: 1.2와 동일 result 스키마 ×300.
- **비고**: 이 파일은 wf_vs_v23.js에서 이름·personas만 치환한 파생본(§5 드리프트 리스크).

### 1.4 wf_precise_survey.js — 순차노출 단일선택 설문 (구형·mode collapse 확인됨)

- **역할**: 페르소나가 실제 설문처럼 **문항당 하나를 단일선택**(A1~E2 전항). 순차노출(정보 게이팅)·동결 문구·페르소나별 셔플. ※ 이 방식은 C1/C2 등에서 mode collapse가 실측 확인되어(§demo/README.md) VS 계열로 대체됨.
- **실행**: `Workflow({scriptPath:"...", args: <personas 배열>})` — personas는 **args로 주입**(`wf_precise_survey.js:109`).
- **입력**: args = `SP/prof.json` 내용(셔플 순서 `A2_order`/`B2_order`/`B3_order`/`E1_order` 포함 — 단 이 파일의 셔플은 자체 mulberry32(`:30-46`, 시드=`(pid+1)*1000003+salt*97`)로도 수행). effort=`'low'`(`:111`). 보기 문자열 상수 `:8-27`.
- **출력**: result 스키마(`:49-69`) — 분포가 아닌 **선택값**:
  ```json
  {"pid":0, "A1":"먹어봤고 좋아한다", "A2":"먹을 기회나 파는 곳이 마땅치 않아서", "B1":4,
   "B2_1":"5분 완조리(간편함)", "B2_2":"없음", "B3":"가격이 걱정된다", "B4":"그렇다",
   "C1":"배달·외식", "C2":"상황 보고 가끔 산다", "D1_5900":"산다", …, "E1":"가", "E2":"…"}
  ```
- **소비자**: extract_raw.py(식별필드 `A1`) → survey_raw.json → map_and_ingest.py.

### 1.5 wf_vs_dist.js / wf_vs_cat.js / wf_vs_d1.js / wf_e1_dist.js — 부분 VS 분포 (구형 보조)

| 파일 | 역할 | 입력(args) | 출력 result 필드 | effort |
|---|---|---|---|---|
| wf_vs_dist.js | B1/C1/C2 분포(모드붕괴 패치용) | personas(args, `:31`) | `pid, B1_dist[5], C1_dist[5], C2_dist[3]` | `'low'`(`:33`) |
| wf_vs_cat.js | A1/A2/B2/B3/E1 분포(컨셉前/後 구분) | personas(args, `:35`) | `pid, A1_dist[4], A2_dist[6], B2_dist[6], B3_dist[7], E1_dist[4]` | `'low'`(`:37`) |
| wf_vs_d1.js | 가격별 수용인원(Gabor-Granger 원료) | personas(args, `:34`) | `pid, buy_5900, buy_6900, buy_7500, buy_8500`(0~10 정수) | `'low'`(`:36`) |
| wf_e1_dist.js | E1 4지 분포(양자택일 붕괴 보정) | personas(args, `:33`) | `pid, E1_dist[4]` | `'low'`(`:35`) |

- 소비자: dist→extract_raw(식별필드 `B1_dist`)→map_and_ingest 또는 patch_vs.py / d1→extract_raw(식별필드 `buy_5900`) / e1_dist→patch_e1.py.

### 1.6 wf_fidelity.js — 충실도 메타평가 (특수)

- **역할**: 이 합성 설문이 실측과 얼마나 유사할지를 4렌즈(문헌/지표분해/아티팩트/회의론) 병렬 분석→적대 검증→종합. 설문 생성이 아니라 **평가** 워크플로.
- **실행**: `Workflow({scriptPath})` — args 불요(`:78` `const personas = null`). 평가 대상 컨텍스트가 `CTX` 상수에 하드코딩(`:11-30`, N=74 세대 기준 — 최신 런과 불일치).
- **입력/출력**: 렌즈별 `LENS_SCHEMA`(`:32-56`)·검증 `VER_SCHEMA`(`:86-96`)·종합 `SYN_SCHEMA`(`:103-120`). effort=`'high'`(`:81,99,123`). 렌즈 에이전트는 WebSearch/WebFetch 사용을 프롬프트로 지시(`:61`).

### 1.7 build_fresh_pool.py — 표본 풀 생성(단일)

- **역할**: v1.5 인구 프레임으로 N=44~53 무작위 표본 + 셔플 순서 생성.
- **실행**: `python3 build_fresh_pool.py` (CLI 인자 없음).
- **입력**: 코드 상수만 — N: `random.randint(44,53)`(`:16`), RUN_SEED: `randint(10_000_000, 99_999_999)`(`:17`), **시드의 시드는 `os.urandom(8)`**(`:14`, 비결정 — §5). `C.GLOBAL_SEED = RUN_SEED` 전역 덮어쓰기(`:20`). 라벨 사전 `:48-53`, 문항 원문 `:26-37`.
- **출력**: `SP/prof.json`(워크플로 args용 — pid/seg/S1~S5/9개 latent 반올림/4개 셔플순서), `SP/pool_meta.json`(ingest용 — `Persona.row()`: pid, channel, S1_age…, is_target, is_student_seg, screenout_reason), `SP/run_cfg.json`(`{"N":…, "RUN_SEED":…}`). stdout에 표본 요약.
- **의존성**: numpy, `sim.sampler`·`sim.config`. 외부 API 없음.

### 1.8 build_oversample.py — 향기피 오버샘플(N=58)

- **역할**: `spice_aversion (0.84,0.20)`·`access_barrier (0.26,0.15)` 상향/하향 오버라이드(`:23-24`)로 향기피 세그 검정력 확보용 표본. 대표성 없음(주석 명시 `:7`).
- **실행**: `python3 build_oversample.py`. 입력: N=58 고정(`:16`), RUN_SEED 무작위(`:17`, os.urandom 기원 `:14`). 전역 덮어쓰기 `:20-24`.
- **출력**: 1.7과 동일 3종(단 run_cfg에 `"oversample":"spice"` 추가 `:79`) — **같은 파일명에 덮어씀**(§5).

### 1.9 build_sweep.py — 사전분포 스윕(4인구×30)

- **역할**: 심리 latent만 4개 상반 인구로 오버라이드(SWEEPS `:18-32`)해 robust/fragile 판별용 120명 생성.
- **실행**: `python3 build_sweep.py`. 입력: N_PER=30(`:10`), 인구별 시드 무작위(`:48-50`). pid = `cfg*100 + 풀내pid`(`:60`).
- **출력**: `SP/sweep_prof.json`(120명·latent 포함, 셔플순서 없음), `SP/sweep_meta.json`(`{"meta":{pid:cfg}, "seeds":{cfg:seed}, "names":{cfg:이름}}`).

### 1.10 build_multipool.py — 다풀 3×100 생성 ★현행

- **역할**: 상이 시드 3개 독립 풀(각 N=100) — 매실청 깊이 반증의 풀-견고성 검정용.
- **실행**: `python3 build_multipool.py`. 입력: N_PER=100(`:9`), N_POOLS=3(`:10`), 풀시드·SAMPLE_SEED 무작위(`:16-17`, os.urandom). pid = `풀번호*1000 + 풀내pid`(`:37`).
- **출력**: `SP/multipool_args.json`(300명 — pid/S1~S5/9 latent, 셔플·seg 없음), `SP/multipool_meta.json`(row()+`pool` 필드), `SP/multipool_cfg.json`:
  ```json
  {"pools":[{"pool":0,"seed":99758933,"N":100,"target":66,"target_rate":0.66},…],
   "SAMPLE_SEED":53783624, "N_PER":100, "N_POOLS":3}
  ```

### 1.11 run.py / run_live.py — 코드형 오케스트레이터

- **run.py**: `python3 run.py [N] [mock|claude]`(기본 N=`C.DEFAULT_N`=100, backend=mock — `:19-20`). 출력 `out/` 6종(§0-A). backend='claude'면 `sim/backends.py`의 ClaudeBackend가 **anthropic SDK를 직접 호출**: 클라이언트 생성 `sim/backends.py:205`(환경변수 `ANTHROPIC_API_KEY`에서 주입), API 호출 지점 `messages.create` `sim/backends.py:252-256`, 모델 기본값 상수 `sim/backends.py:199`(정확한 문자열은 정책상 미기재 — 생성자 인자 `model`로 오버라이드 가능 `:201-202`).
- **run_live.py**: `python3 run_live.py <agent_responses.json>` — 워크플로 산출 응답 리스트를 `ingest.ingest_live()`(기본 n=100 풀 재구성, `sim/ingest.py:16,20`)로 매핑 후 S7~S9. 출력 `out/responses_live.csv`, `aggregate_live.json`, `report_live_9_4.md`.
- **의존성**: numpy(+ scipy/pandas는 requirements에 있으나 코드에서 미사용 확인 — `[불명확: scipy·pandas 사용처를 정적으로 못 찾음, requirements.txt 잔재로 추정]`), anthropic(claude 백엔드 시).

### 1.12 후처리·패치·산출 스크립트

| 스크립트 | 실행 커맨드 | 입력 | 출력 |
|---|---|---|---|
| extract_raw.py | `python3 extract_raw.py <survey런ID> <dist런ID> <d1런ID>` | 각 저널(BASE 하드코딩 `:5`) — 식별필드 A1/B1_dist/buy_5900(`:15-17`) | `SP/survey_raw.json`·`dist_raw.json`·`d1_raw.json` |
| map_and_ingest.py | `python3 map_and_ingest.py` | `SP/run_cfg.json`(`:10`)·`survey_raw.json`(`:122`)·`dist_raw.json`(`:123`)·`d1_raw.json`(있으면, `:155-157`) + `sim.ingest` | `SP/rows_final.json`·`agg_final.json` + stdout 요약. 원문라벨→표준라벨 매핑사전 `:19-44`, VS표집 `vs_sample():60-67`, 정합틸트 `d1_c2_tilt():73-80`·`c2_tilt():113-118`·`b1_channel_tilt():109-110`, D1 단조화 `d1_from_curve():83-101`, `CLEAN_MONOTONE_D1=True`(`:15`) |
| patch_vs.py | `python3 patch_vs.py <resp.json> <dist.json> <out.json>` | 응답+분포 JSON | B1/C1/C2 재표집한 응답 JSON(경로 인자) |
| patch_e1.py | `python3 patch_e1.py <e1dist런ID>` | 저널(E1_dist)+`SP/run_cfg.json`+`SP/rows_final.json` | `SP/rows_final.json` **in-place 덮어씀**(`:38`), salt=60(`:25`) |
| patch_e2.py | `python3 patch_e2.py <xlsx경로> <e2json경로>` | 기존 xlsx + e2_new.json | 같은 xlsx의 E2_이유 열만 교체(in-place, `응답자번호=pid+1` 규약 `:13`) |
| e2_refine\*.py (6종: e2_refine·refine2·refine3·_v15b·_v15c·_oversample) | `python3 e2_refine_v15c.py` (인자 없음) | `SP/rows_final.json`·`survey_raw.json`(·`prof.json`) | `SP/e2_work.json`·`e2_pass1~3.json`·`e2_final.json` + stdout 검토. **P1/P2/P3 문구가 특정 pid에 하드코딩된 정적 사전**(예: v15c `:26-77`) — LLM 호출 없음, 다른 표본 재사용 불가 |
| build_xlsx.py | `python3 build_xlsx.py` | `SP/rows_final.json`·`e2_final.json` | `exports/게이트C_합성시뮬응답_향기피오버샘플.xlsx`(OUT `:9`·시트명 `:30` — **마지막 납품 상태로 하드코딩**, 매 납품 시 수정해온 파일) |
| build_sweep_xlsx.py | `python3 build_sweep_xlsx.py <저널경로>` | 저널+`SP/sweep_prof.json`·`sweep_meta.json` | `exports/…사전분포스윕120.xlsx`(OUT `:11`) |
