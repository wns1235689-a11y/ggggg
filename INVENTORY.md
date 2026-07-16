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

---

## 2. 분석 스크립트 인터페이스

공통: 전부 순수 python(numpy만, LLM 호출 없음). 저널 기반 4종은 `BASE`(저널 루트)와 `SP`(스크래치패드)가 파일 상단에 하드코딩. 표집 재현은 `SEED`(run_cfg의 RUN_SEED 또는 multipool_cfg의 SAMPLE_SEED)와 salt 정수로 `np.random.default_rng([SEED, pid, salt])` 결정론.

### 2.1 vs_verify.py — 붕괴 해소 검증

- **실행**: `python3 vs_verify.py <런ID>` (wf_vs_all 계열 저널 대상, 식별필드 `E1_dist`).
- **입력**: `BASE/<런ID>/journal.jsonl`(`:13,16`), `SP/run_cfg.json`(`:11` — SEED).
- **지표**: ① 문항별 믿음질량%(49명 dist 정규화 합산, `mass():51-59`) ② 결정적 표집 realized 분포(`pick():41-47`, salt 사전 `SALT:24-25` — A1=40·A2=41·B1=1·B2_1=42·B2_2=43·B3=44·C1=2·C2=3·E1=60) ③ D1 수용곡선(단조 강제 후 임계 표집, `d1_curve():66-88`, salt=51) ④ 붕괴해소 요약(E1 비슷+둘다 realized, A2 향부담 믿음질량, 문항별 사용 보기수).
- **출력**: stdout 전용(막대그래프 텍스트). 파일 출력 없음.

### 2.2 vs_compare.py — 탈동질화 전/후 대조

- **실행**: `python3 vs_compare.py <구런ID> <신런ID>`.
- **입력**: 두 저널 + **`/tmp/args_dump.txt`의 5번째 줄**(DIST 페르소나 JSON — `:11`). `[불명확: /tmp/args_dump.txt 생성 스크립트가 repo에 없음(세션 인라인 생성 임시파일). 이 파일이 없으면 즉시 실패]`
- **지표**: ① 페르소나간 분포 다양성(문항별 서로다른 패턴수·최빈 점유%, `diversity():27-30`) ② 특성→응답 방향 대비 Δ(향기피→E1(나-가)/A2①, 가격민감→B3가격걱정/buy_8500, 관여→E1둘다, 회의→C2기존유지 — `contrast():33-46`, `contrasts():57-77`).
- **출력**: stdout 전용.

### 2.3 v23_analyze.py — v2.3 단일풀 판정

- **실행**: `python3 v23_analyze.py <런ID>` (wf_vs_v23 저널, 식별필드 `A2a_dist`).
- **입력**: 저널(`:16`) + `SP/run_cfg.json`(`:14`) + `SP/pool_meta.json`(`:18` — is_target 판별).
- **지표**: ① A2a 유병률 협의(매우만)/광의(조금+매우) + 광의 믿음질량(1차대상/전체 분리) ② 주판정: 향기피 세그(협/광 컷) vs 비기피의 B1(가중평균)·C2 전환성향(꼭=1/가끔=0.5/유지=0)·D1 수용(buy_* 평균/10) Δ + 판정문(지지방향/평평/혼조 임계 `:121-123`) ③ 연속상관: A2a 강도(`a2_intensity()`=[0,.5,1] 가중) ↔ B1/C2/D1 pearson ④ dose-response: A2a 3단 그룹별 B1 단조성 ⑤ 저커밋(B3 양+맛 vs 가격), E1 분포(T2 압도 임계=나>가+n×0.15), A2x 타당도(예/아니오별 향부담 강도) ⑥ 한계 노출(B1/C2/E1 최빈패턴 점유%). salt 사전 `:25-26`(A2a=41…E1=60, D1임계=51).
- **출력**: stdout 전용.

### 2.4 v23_multi_analyze.py — 다풀 견고성 + 시드앙상블

- **실행**: `python3 v23_multi_analyze.py <런ID>` (wf_v23_multi 저널).
- **입력**: 저널(`:14`) + `SP/multipool_cfg.json`(`:12` — SAMPLE_SEED) + `multipool_meta.json`(`:16`) + `multipool_args.json`(`:17` — latent 원값).
- **지표**: ① 풀별(pid//1000)·통합 연속상관 r + p(정규근사 양측, `pearson():44-58`): 향부담강도 ↔ B1/C2/D1/E1(나-가) ② 시드앙상블(K_ENS=12, `:18`): 실현 A2a 협의컷 세그교차 ΔB1 평균±sd(`ens_seg_delta():61-75`, rng=[SSEED,pid,41,e]) ③ 강한 축: 가격민감↔D1수용, 관여↔E1둘다별로 ④ 풀-일관성(부호 일치 여부).
- **출력**: stdout 전용.

### 2.5 analyze_sweep.py — 사전분포 스윕 robust/fragile 분류

- **실행**: `python3 analyze_sweep.py <저널경로>` (※ 런ID가 아니라 **저널 파일 전체 경로**를 받음 — 다른 4종과 인터페이스 불일치).
- **입력**: 저널 + `SP/sweep_meta.json`(`:13` — pid→cfg).
- **지표**: cfg(인구)별 A2 접근성vs향기피%, B2 1순위 T1축(완조리·가성비)vsT2축(매실청·향부담없음)%, E1 가:나%, B1 평균, C2 구매%, D1 5900/6900 수용% → `classify()`(`:88-101`): 전 인구 동일 부호(±3%p 데드존, 비영 3개 이상)=ROBUST, 뒤집힘=FRAGILE, 전부 데드존=무방향.
- **출력**: stdout + **`SP/sweep_analysis.json`**(`:113` — cfg별 지표 rows).

### 2.6 라이브러리 수준 분석 (sim/ — run.py·run_live.py·map_and_ingest.py가 호출)

- `sim/aggregate.py` — `aggregate(responses:list[dict]) -> dict`: §3 잠금 규칙 집계. 산출 2버킷: `A_설계리스크_운영점검`(인용가능 — N·B4실패·직진·E1 순서역전율·D1 비단조율·채널플래그·C1⑤)과 `B_방향성_사전분포`(인용금지 — B1/B2/B3/C1/C2/D1/A2/E1, 등급 🟡/🔴). 셀 구조 `{"value","grade","cite","label"}`(`_cell():19-20`).
- `sim/report.py` — `build_report(agg, n, backend_name) -> (md문자열, lint결과)`: §9.4 5블록 리포트.
- `sim/linter.py` — `lint(agg) -> {"pass","violations","note"}`: A/B 계약·🔴 강제(`_MUST_BE_RED:10`)·금지어(`_FORBIDDEN_WORDS:11` — "검증됨/보정된/예측된/정확/실측 확인") 검사.

---

## 3. 데이터 구조

### 3.1 결과 저장 디렉토리 구조 (실제 발췌)

```
/home/user/ggggg/                    ← repo 루트 (git)
├── sim/                             ← 엔진(config·sampler·backends·respondent·ingest·aggregate·report·linter)
├── wf_*.js ×9                       ← Workflow 스크립트
├── build_*.py, *_analyze.py 등      ← 풀생성·후처리·분석
├── out/                             ← run.py/run_live.py 산출 (.gitignore — 비추적)
│   ├── personas.csv latents.csv summary.json responses.csv aggregate.json report_9_4.md
│   └── responses_live.csv aggregate_live.json report_live_9_4.md
├── exports/                         ← 납품 xlsx·분석 md (git 추적)
│   └── 게이트C_합성시뮬응답_{100명,응답2차,v1.5_3차,74_E1보정,…,향기피오버샘플,사전분포스윕120}.xlsx
├── demo/                            ← 초기 라이브 실증 산출물(응답 json·csv·리포트)
└── docs/source/                     ← 원본 설문설계 v1.4·파일럿프로토콜 md

/tmp/claude-0/-home-user-ggggg/8fffd176-…-c1238d2e4b2b/scratchpad/   ← "SP" (세션 임시 — repo 밖)
├── run_cfg.json prof.json pool_meta.json          ← 현행 단일 풀
├── multipool_args.json multipool_meta.json multipool_cfg.json
├── sweep_prof.json sweep_meta.json sweep_analysis.json
├── survey_raw.json dist_raw.json d1_raw.json      ← 저널 추출본
├── rows_final.json agg_final.json                 ← 매핑·집계 결과
└── e2_work.json e2_pass1~3.json e2_final.json     ← E2 다듬기

/root/.claude/projects/-home-user-ggggg/8fffd176-…-c1238d2e4b2b/subagents/workflows/   ← "BASE" (하니스 저널 — repo 밖)
└── wf_<hex>/journal.jsonl  (+ agent-<id>.jsonl 개별 트랜스크립트)
```

⚠️ SP·BASE는 **이 세션 컨테이너가 사라지면 소실**된다. repo에 커밋된 것은 스크립트·exports·문서뿐, 원 저널/중간 JSON은 비커밋(§5).

### 3.2 런ID·식별자 체계

| 식별자 | 형식/규칙 | 발급 주체 |
|---|---|---|
| 워크플로 런ID | `wf_` + hex(예: `wf_9971e46b-6d1`) | Claude Code Workflow 도구. `[불명확: 정확한 생성 규칙은 하니스 내부]` |
| RUN_SEED | 8자리 정수(10,000,000~99,999,999). `run_cfg.json`에 기록 | build_fresh_pool.py:17 / build_oversample.py:17 (엔트로피 기원) |
| 풀시드·SAMPLE_SEED | 동일 범위. `multipool_cfg.json`·`sweep_meta.json`에 기록 | build_multipool.py:16-17 / build_sweep.py:48-50 |
| pid (단일 풀) | 0..N-1 | sampler.build_pool |
| pid (스윕) | `cfg*100 + 풀내pid` (0~329) | build_sweep.py:60 |
| pid (다풀) | `풀번호*1000 + 풀내pid` (0~2099) | build_multipool.py:37 |
| xlsx 응답자번호 | `pid + 1` | build_xlsx.py:35 / patch_e2.py:13 |
| 표집 재현 | `np.random.default_rng([SEED, pid, salt])` — salt는 문항별 정수(§2 참조) | 전 후처리 스크립트 공통 관례 |

### 3.3 페르소나 latent 스키마

**정의 위치**: `sim/config.py:150-173` `LATENT_SPECS` — 필드별 `(평균, SD)` 정규분포 표집 후 [0,1] clip(`sim/sampler.py:30-34`). 전 21개 필드:

| 필드 | (μ, σ) | 용도(주석 기준) |
|---|---|---|
| midpoint_bias | (0.55, 0.18) | 중간범주 편중 |
| acquiescence | (0.50, 0.18) | 묵인 경향 |
| extremity_low | (0.60, 0.18) | 극단값 회피 |
| skepticism | (0.50, 0.22) | 회의도 |
| spice_aversion | (0.34, 0.25) | A2 향기피 구동 [스윕: 밴드 20~48%] |
| plum_familiarity | (0.62, 0.20) | 매실청 친숙도 |
| price_sensitivity | (0.55, 0.22) | 가격민감 |
| verbosity | (0.50, 0.20) | E1 verbosity 진단용 |
| attentiveness | (0.80, 0.18) | 낮을수록 B4 실패·직진 |
| involvement | (0.50, 0.22) | 관여(S4 빈도로 재보정) |
| quality_trust | (0.55, 0.22) | 냉동 품질 신뢰 |
| authenticity_goal | (0.45, 0.25) | 정통성 기대 |
| access_barrier | (0.50, 0.22) | 접근 장벽 |
| sauce_barrier | (0.40, 0.22) | 낯선 소스 부담 |
| portion_expect | (0.50, 0.22) | 식사량 기대 |
| pantry_constraint | (0.45, 0.24) | 팬트리 제약 |
| category_frequency | (0.50, 0.24) | 카테고리 섭취빈도 |
| social_desirability | (0.45, 0.18) | 사회적 바람직성 |
| message_orientation | (0.50, 0.25) | T1↔T2 선호(※ MockBackend/backends 경로에서만 사용 — wf 경로에선 미노출) |
| novelty_seeking | (0.50, 0.22) | 신메뉴 탐색 |
| trial_propensity | (0.45, 0.22) | 시도 의향 |

**파생 상관**(`sim/sampler.py:35-51`): spice_aversion ← −0.20×(plum_familiarity−0.5) 완충 / involvement·category_frequency ← S4 빈도 bump(0회 −0.15 ~ 6+회 +0.20) / sauce_barrier ← +0.3×(spice−0.5) / pantry_constraint ← 1인가구·기숙사 +0.20 / message_orientation ← +0.30×(spice−0.5) −0.20×(involvement−0.5) / channel_favor_offset ← `CHANNEL_FAVOR_OFFSET`(config:188) + N(0,0.1).

**워크플로 노출 필드 매핑**(build_* → wf 프롬프트, 한국어 9개): `향기피`=spice_aversion · `매실청`=plum_familiarity · `관여`=involvement · `회의`=skepticism · `가격민감`=price_sensitivity · `접근성`=access_barrier · `정통기대`=authenticity_goal · `식사량`=portion_expect · `카테고리빈도`=category_frequency (예: build_fresh_pool.py:74-78). 나머지 12개 latent는 wf 경로에 미노출.

**등급화(lvl) 이원화 주의**: 구형 wf·backends는 3단(`>0.66/0.4` — wf_precise_survey.js:71, build_sweep.py:82 / `>0.6/0.4` — sim/backends.py:219), 신형 wf는 5단(`>0.75/0.58/0.42/0.25` — wf_vs_all.js:29, wf_vs_v23.js:29, wf_v23_multi.js:29).

**인구 CPT**(결합분포): `sim/config.py:87-144` — S1_AGE·S2_STATUS·S3_RESIDENCE·S4_FREQ·S5_TRAVEL 옵션(`:87-91`), CPT_AGE(`:94-98`), cpt_status(`:100-110`), cpt_residence(`:115-128`), cpt_freq(`:131-137`), cpt_travel(`:141-144`), CHANNEL_MIX(`:39`). 타깃 판정: `sim/sampler.py:83-90`(§3-1 = S3∈{1인,2인가구} AND S4≥1회; 확장세그 = 기숙사 OR 0회).

### 3.4 설문 문항·보기 정의 위치 (버전별로 분산 — 단일 소스 없음 ⚠️)

| 버전/용도 | 자료구조 | 위치 |
|---|---|---|
| 표준라벨(집계용) | `OPT` dict(A1/A1_key/A2/B3/B4/C1/C2/C2_key/E1/B2_rows) + `D1_PRICES`·`B4_CORRECT` | sim/respondent.py:16-33 |
| v1.4/1.5 원문(설문지 문자열) | JS 상수 A1/A2/B2/B3/B4/C1/C2/SD/E1_ITEMS | wf_precise_survey.js:8-27 |
| v1.4/1.5 원문(파이썬 측) | A2_FULL/B2_FULL/B3_FULL/E1_GA/E1_NA/E1_ITEMS | build_fresh_pool.py:26-37 (동일 상수가 build_oversample.py:30-40에 중복) |
| 원문→표준 매핑 | A2_MAP/B2_MAP/B3_MAP/C1_MAP/C2_MAP/E1_MAP | map_and_ingest.py:19-44 |
| VS 전면화 문항(프롬프트 내장) | 템플릿 리터럴(보기 대괄호 나열) | wf_vs_all.js:31-47 |
| **v2.3 문항**(A2 4×3점+A2x·B2 5지·E1 4지) | 템플릿 리터럴 + SCHEMA | wf_vs_v23.js:30-56·6-28 (wf_v23_multi.js 동일) |
| E1 헤드라인(동결 원문+패러프레이즈) | `E1_HEADLINES` dict | sim/config.py:252-260 |
| 컨셉 카드 | `CONCEPT_CARD` 문자열 | sim/backends.py:323-327 (wf 파일들에는 프롬프트 내 별도 중복) |
| 분석용 축약 보기 | `OPTS`/`B2O`/`B3O`/`C2O`/`E1O` 등 | vs_verify.py:15-23, v23_analyze.py:19-24 |
| 문항 앵커 사전분포 | `ANCHOR_PRIORS`(A1/A2유병률/B1/C2/D1/노이즈율) | sim/config.py:193-230 |
| §3 잠금 분석규칙 | `LOCKED_RULES` | sim/config.py:265-275 |

같은 보기가 **최소 4곳 이상에 표기 변형**(예: C1 "냉동/밀키트" vs "냉동/밀키트를 사 먹는다" vs "냉동·밀키트")으로 존재하며 map_and_ingest의 매핑 사전이 이를 흡수한다 — UI가 문항을 편집 가능하게 만들려면 이 다중 정의를 단일 소스로 통합해야 함(§5).

### 3.5 주요 파일 스키마 발췌

`SP/prof.json` 항목(fresh/oversample — 워크플로 args용):
```json
{"pid":0, "seg":"타깃", "S1":"만 35–39", "S2":"직장인", "S3":"2인 가구", "S4":"6회 이상", "S5":"없다",
 "향기피":0.134, "매실청":0.634, "관여":0.7, "회의":0.214, "가격민감":0.567, "접근성":0.622,
 "정통기대":0.337, "식사량":0.277, "카테고리빈도":0.555,
 "A2_order":[…6개 원문 셔플], "B2_order":[…6], "B3_order":[…7], "E1_order":[{"tag":"가","text":"…"},…]}
```
`SP/pool_meta.json` 항목(ingest·타깃 판정용): `{"pid","channel","S1_age","S2_status","S3_residence","S4_freq","S5_travel","is_target","is_student_seg","screenout_reason"}` (+multipool은 `"pool"` 추가).

`SP/rows_final.json` 항목(응답 최종 — build_xlsx 입력): `respondent_id, F1_channel, S1~S5, A1, A2, B1, B2_1순위, B2_2순위, B3, B4, C1, C2, D1_5900~D1_8500("산다"/"안 산다"), E1, E2, F2, _is_target, _is_student, _screenout, _flag_b4_pass, _flag_straightline, _flag_d1_nonmonotone, _flag_e1_swap_flip, _flag_unprimed_ok, _flag_structural_inconsistency, _backend` (sim/respondent.py:120-134 및 sim/ingest.py:32-45와 동형).

`SP/agg_final.json` / `out/aggregate.json`: §2.6 aggregate 산출(`A_설계리스크_운영점검`·`B_방향성_사전분포`·`_invariant`·`_labels`).

---

## 4. 하드코딩 지점 목록 (UI 주입 후보 — 변경하지 않음, 목록만)

난이도: **하**=단순 파라미터화(CLI 인자/환경변수/설정파일로 즉시 전환 가능), **중**=여러 파일 동기 수정 또는 데이터 재생성 필요, **상**=구조 변경(단일 소스화·러너 구현) 필요.

### 4a. 경로 (최우선 교체 대상)

| 값 | 파일:줄 | 난이도 | 이유 |
|---|---|---|---|
| SP=`/tmp/claude-0/…/scratchpad`(세션 특정) | 19개 py 파일 상단 — analyze_sweep.py:10, build_fresh_pool.py:11, build_multipool.py:8, build_oversample.py:12, build_sweep.py:9, build_sweep_xlsx.py:9, build_xlsx.py:8, e2_refine*.py(6종):10-11, extract_raw.py:4, map_and_ingest.py:9, patch_e1.py:6, v23_analyze.py:12, v23_multi_analyze.py:10, vs_verify.py:10, vs_compare.py:7 | 하 | 문자열 상수 1개씩 — 환경변수/공통 config 모듈로 치환 용이. 단 19곳 동기 수정 |
| BASE=`/root/.claude/projects/…/subagents/workflows`(세션 특정) | extract_raw.py:5, patch_e1.py:9, v23_analyze.py:16, v23_multi_analyze.py:14, vs_compare.py:9, vs_verify.py:13 | 하 | 동일 — 6곳 |
| `/tmp/args_dump.txt` 5번째 줄 의존 | vs_compare.py:11 | 중 | 생성 스크립트가 repo에 없는 세션 임시파일 — 입력을 정식 파일(multipool_args 형식)로 교체 필요 |
| xlsx 출력 경로+시트명(마지막 납품 상태) | build_xlsx.py:9(OUT)·30(ws.title="향기피오버샘플"), build_sweep_xlsx.py:11·33 | 하 | CLI 인자화하면 끝 — 현재는 납품마다 수동 수정해 온 파일 |
| out/ 상대경로 | run.py:15, run_live.py:13 | 하 | 이미 `__file__` 기준 상대라 이식성 있음(참고용 기재) |

### 4b. 시드·N·표본 구성

| 값 | 파일:줄 | 난이도 | 이유 |
|---|---|---|---|
| `GLOBAL_SEED = 20260713` | sim/config.py:20 | 하 | 모듈 전역 — 단 모든 스크립트가 런타임에 덮어쓰는 관례(§5 전역상태) |
| `DEFAULT_N = 100` | sim/config.py:21 | 하 | run.py CLI로 이미 오버라이드 가능 |
| N=`randint(44,53)`·RUN_SEED=`randint(1e7,1e8-1)`·엔트로피 `os.urandom(8)` | build_fresh_pool.py:14-17 | 하 | CLI 인자(N, seed)로 전환하면 재현 가능한 재실행도 확보 |
| N=58 고정·오버라이드 (0.84,0.20)/(0.26,0.15) | build_oversample.py:16, 23-24 | 하 | 오버샘플 파라미터를 설정으로 |
| N_PER=30·SWEEPS 4개 인구 정의 | build_sweep.py:10, 18-32 | 중 | 스윕 시나리오 자체가 UI 편집 대상(사전분포 사전) |
| N_PER=100·N_POOLS=3 | build_multipool.py:9-10 | 하 | 즉시 인자화 가능 |
| personas **JSON 리터럴 baked**(49명/49명/300명) | wf_vs_all.js:51, wf_vs_v23.js:59, wf_v23_multi.js:59 | 중 | args 주입 방식(구형 wf처럼 `:33-35` 패턴)으로 되돌리면 해소 — 현재는 풀 바꿀 때마다 파일 재생성 필요 |
| ingest 풀 재구성 기본 n=100 | sim/ingest.py:16, 20 | 하 | 호출부(map_and_ingest.py:126)는 n=N 전달로 회피 중 — run_live.py는 기본값 사용(N≠100 풀이면 KeyError 위험) |

### 4c. LLM 실행 파라미터

| 값 | 파일:줄 | 난이도 | 이유 |
|---|---|---|---|
| effort `'low'` | wf_precise_survey.js:111, wf_vs_dist.js:33, wf_vs_cat.js:37, wf_vs_d1.js:36, wf_e1_dist.js:35 | 하 | agent() 옵션 문자열 1개 |
| effort `'medium'` | wf_vs_all.js:53, wf_vs_v23.js:61, wf_v23_multi.js:61 | 하 | 〃 |
| effort `'high'` | wf_fidelity.js:81, 99, 123 | 하 | 〃 |
| 모델: wf 전 파일 `model` 미지정(세션 상속) | (부재 자체가 값) | 중 | UI가 모델을 지정하려면 agent() 옵션 추가 또는 하니스 세션 모델 제어 필요 |
| ClaudeBackend 기본 모델 ID 상수(문자열 미기재) | sim/backends.py:199 (오버라이드 생성자 인자 `:201`) | 하 | 생성자 인자·환경변수화 용이. API 키는 `ANTHROPIC_API_KEY` 환경변수(`:205`) |
| VS 표집 max_tokens=500 | sim/backends.py:253 | 하 | 상수 1개 |

### 4d. 설문 문항·보기·프롬프트 (UI '설문 설계' 기능의 핵심 교체 대상)

| 값 | 파일:줄 | 난이도 | 이유 |
|---|---|---|---|
| 표준라벨 OPT 사전 | sim/respondent.py:16-30 | 상 | 집계(aggregate)·린터의 라벨 문자열과 결합 — 문항 변경 시 §3 규칙까지 연쇄 |
| v1.4/1.5 원문 보기 상수 | wf_precise_survey.js:8-27 / build_fresh_pool.py:26-37 / build_oversample.py:30-40 (3중 중복) | 상 | 동일 문자열이 3파일+매핑사전에 분산 — 단일 문항 정의 소스 필요 |
| 원문→표준 매핑 사전 | map_and_ingest.py:19-44 | 상 | 문항 개정 때마다 수동 동기화 필요한 지점 |
| VS 전면화 프롬프트(문항+지시문+컨셉카드) | wf_vs_all.js:26-47 | 중 | 템플릿 함수 1개 — 문항 정의를 인자로 빼면 재사용 가능 |
| v2.3 프롬프트+SCHEMA(보기 개수가 스키마에 고정: A2a~d minItems=3, B2=5 등) | wf_vs_v23.js:6-28, 30-56 (wf_v23_multi 동일) | 중 | 보기 수를 바꾸면 스키마·프롬프트 동시 수정 필요 |
| D1 가격 4점(5900/6900/7500/8500) | sim/respondent.py:32, map_and_ingest.py:70, wf 프롬프트들, v23_analyze.py:27, sim/config.py:208-209 등 | 상 | 가격축이 스키마 필드명(buy_5900)에까지 박혀 있음 — 가격 변경은 전 계층 연쇄 |
| E1 헤드라인 원문·패러프레이즈 | sim/config.py:252-260, wf_precise_survey.js:22-23, build_fresh_pool.py:35-36 등 | 중 | 중복 정의 — 단일화 필요 |
| 컨셉 카드 | sim/backends.py:323-327 + 각 wf 프롬프트 내 중복 | 중 | 〃 |
| B4 정답 `"그렇다"` | sim/respondent.py:33 | 하 | 상수 1개 |

### 4e. 페르소나·행동 모델 상수

| 값 | 파일:줄 | 난이도 | 이유 |
|---|---|---|---|
| LATENT_SPECS 21개 (μ,σ) | sim/config.py:150-173 | 하 | dict 교체로 스윕 가능(빌드 스크립트들이 이미 그렇게 함) — UI의 '사전분포 편집' 표적 |
| 인구 CPT(CPT_AGE·cpt_status·cpt_residence·cpt_freq·cpt_travel·CHANNEL_MIX) | sim/config.py:39, 94-144 | 중 | 함수 내 분기 하드코딩 — 표 형태 설정으로 재구조화 필요 |
| 파생 상관 계수(−0.20 완충, +0.3 sauce, ±bump 등) | sim/sampler.py:36-51 | 중 | 수식 내 매직넘버 |
| ANCHOR_PRIORS(A1분포·A2 밴드 20~48%·B1 mean/sd·C2·D1 수용밴드·노이즈율) | sim/config.py:193-230 | 중 | 시뮬 '현실 앵커' 전체 — UI 노출 가치 높음 |
| STRUCTURAL_INCONSISTENCY_RATE=0.12 / CHANNEL_FAVOR_OFFSET | sim/config.py:186, 188 | 하 | 상수 |
| 정합 틸트 계수(c2_tilt ±0.8, d1_c2_tilt 벡터, CH_FAVOR, b1_channel_tilt 0.5) | map_and_ingest.py:73-80, 106-118 | 중 | 손튜닝 결합 — 방향성 해석에 영향(문서화된 설계 선택) |
| lvl 등급 임계(3단 0.66/0.4 · 5단 0.75/0.58/0.42/0.25) | wf_precise_survey.js:71 / wf_vs_all.js:29 등 | 하 | 파일별 상수 — 단 이원화 자체가 혼선 요인 |
| MockBackend 응답 규칙 계수 전체 | sim/backends.py:66-191 | 상 | 규칙 기반 백엔드의 본체 — 교체보다는 유지 대상 |

### 4f. 후처리·분석 상수

| 값 | 파일:줄 | 난이도 | 이유 |
|---|---|---|---|
| 표집 salt 사전(A1=40…E1=60, D1임계=51) | vs_verify.py:24-25, v23_analyze.py:25-27, patch_e1.py:25(60), map_and_ingest.py:66·94(51) 등 | 중 | 파일 간 **일치해야 재현 정합** — 공통 모듈화 필요 |
| K_ENS=12(시드앙상블 횟수)·SALT_A2a=41 | v23_multi_analyze.py:18, 20 | 하 | 상수 |
| CLEAN_MONOTONE_D1=True | map_and_ingest.py:15 | 하 | 플래그 1개(D1 비단조 주입 on/off) |
| 판정 임계(세그Δ 0.15/0.03, dose 0.01, T2압도 0.15n, robust ±3%p 데드존) | v23_analyze.py:121-123·147-150, analyze_sweep.py:90 | 중 | 판정 규칙 — UI '판정' 단계에서 명시 노출 권장 |
| e2_refine 계열 SUBSET·P1/P2/P3 문구(pid 고정) | e2_refine_v15c.py:15·26-77, e2_refine_oversample.py:15·25-70, e2_refine_v15b.py:16 등 | 상 | **일회성 수작업 산출물** — 새 표본마다 사람이 새 파일을 써 온 패턴. UI화하려면 LLM 호출 단계로 재설계 필요 |
| 유병률 기준 분모 상수(v15c의 `/50`, oversample의 `/35`) | e2_refine_v15c.py:86, e2_refine_oversample.py:79 | 하 | 표본 크기 하드코딩 |
| wf_fidelity CTX(N=74 세대 기준 서술) | wf_fidelity.js:11-30 | 중 | 평가 대상 요약이 구세대 고정 — 재사용 시 재작성 필요 |
