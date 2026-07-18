# RUNNER.md — 게이트 C Research Harness 실행 가이드

> **독자**: 몇 주 뒤 맥락을 다 잊고 돌아온 소유자(=나).
> **지위**: 이 문서는 **사용법**만 담는다. 계약·설계 기준은 `SPEC.md`(§4 러너, §5 화면),
> 검수 근거는 `INSPECTION.md`. 충돌 시 SPEC이 우선.
> **범위**: 로컬 단일 유저. 배포·인증·DB 없음. 모든 상태는 `runs/` 파일.
>
> **표기 범례** (커맨드 신뢰도):
> - `✅` — 이 문서 작성 시 **실제 1회 실행**해 작동 확인.
> - `⟨코드근거⟩` — LLM 호출이 발생하는 커맨드라 실행하지 않고 **코드로만** 확인(runner.py/actions.py 등). 아직 실측 아님.
> - `[미확인]` — repo 코드로 확정하지 못한 값/절차.
>
> 문서 끝 **부록 A**에 `[미확인]`·`⟨코드근거⟩` 위치를 집계했다.

---

## 0. 이게 뭐였더라 (30초 리마인더)

LLM 합성 설문 시뮬레이션 엔진(게이트 C, v2.3) 위에 얹은 **개인용 research harness**.
수동 CLI로 하던 워크플로 — **풀 생성 → 시뮬 실행 → 진단 → 판정 → 리포트** — 를
로컬 웹 UI(React/Vite) + 얇은 백엔드(FastAPI)로 반복·유실없이 돌린다.

```
[브라우저 :5173]  ──HTTP──▶  [FastAPI :8781]  ──subprocess──▶  build_*.py / runner.py / v23_*.py
                                    │
                                    └── 파일 저장소: runs/<run_id>/   (git 추적)
```

- **화면 5개**: 실행 콘솔 · 진단 패널 · 판정 대시보드 · 리포트 · 설계 뷰어(읽기전용).
- 엔진 로직(프롬프트·스키마·통계·임계값·salt)은 **불변**. UI는 `runs/` 파일을 **읽어 렌더**만 한다.

---

## 1. 빠른 시작

### 1-a. 사전 준비 (환경당 1회)

```bash
# 파이썬 의존성 — 백엔드(fastapi/uvicorn) + 엔진 스크립트(numpy/scipy/pandas)
pip install -r requirements.txt -r harness_api/requirements.txt          # ✅

# 프론트 의존성 (web/ 안에서)
cd web && npm install && cd ..                                            # ✅
```

- `claude` CLI가 PATH에 있어야 시뮬 실행(러너)이 동작한다. 확인: `which claude` → `/opt/node22/bin/claude` ✅
- 시뮬 실행 자체는 §1-c에서 다룬다(빠른 시작에는 LLM 호출 없음).

### 1-b. 서버 두 개 띄우기

```bash
# 터미널 A — 백엔드 (repo 루트에서). 포트 8781.
python3 -m uvicorn harness_api.main:app --port 8781                       # ✅

# 터미널 B — 프론트 (web/ 에서). 포트 5173, /api 를 8781로 프록시.
cd web && npm run dev                                                     # ✅
```

- **브라우저 접속: <http://localhost:5173>** ✅ (제목 “게이트 C — Research Harness”)
- 백엔드 헬스체크: `curl http://127.0.0.1:8781/api/health` → `{"ok":true, ...}` ✅
- 백엔드 포트를 바꾸면 프론트에 `VITE_API_PORT=<포트>`를 주고 `npm run dev`
  (프록시 대상: `web/vite.config.js`). 기본 8781이면 설정 불필요.
- 배포판 미리보기가 필요하면 `npm run build` 후 `npm run preview`(포트 4173, 동일 프록시). `[미확인]`(preview 서버 미기동 — build만 ✅ 확인)

### 1-c. 최초 스모크 테스트 (권장)

기존 이관 런(`wf_9971e46b-6d1` 등)이 이미 `runs/`에 있으므로, 서버만 띄우면
진단·판정·리포트·설계 4화면은 **LLM 없이 즉시** 확인된다. 신규 dry_run 트리거는
LLM을 태우므로 §2-②, §6-c 참고.

---

## 2. 표준 워크플로 — UI 조작 ↔ CLI 병기

모든 단계는 **실행 콘솔(UI)** 또는 **CLI** 어느 쪽으로도 가능하다. 백엔드는 아래 CLI를
서브프로세스로 부르는 얇은 래퍼일 뿐이다.

### ① 풀 생성 (표본 생성 — LLM 없음)

| | 내용 |
|---|---|
| **UI** | 실행 콘솔 → `① 풀 생성` → 종류(single/multipool/sweep)·시드(선택)·N(선택) → **풀 생성** |
| **CLI** | `python3 build_fresh_pool.py [--seed S] [--n N]` (single) ✅ / `build_multipool.py` / `build_sweep.py` |
| **결과** | `runs/pool_<seed>/`(+ 스크래치패드 사본)에 `prof.json`·`pool_meta.json`·`run_cfg.json` |
| **배선** | `POST /api/pools {kind,seed,n}` → `actions.gen_pool` → `build_*` 동기 실행 |

- pool_id는 시드로 결정: single = `pool_<RUN_SEED>`. 시드를 주면 **bit-identical 재현**(INSPECTION A2).
- 기본값: single N=44~53 무작위, multipool N_PER=100, sweep N_PER=30(미지정 시 `os.urandom` 시드).
- 예시(✅ 실행 확인): `python3 build_fresh_pool.py --seed 91551371 --n 49` → `N=49 RUN_SEED=91551371`, rc=0.

### ② 시뮬 실행 (dry_run / 본실행 — **LLM 호출**)

| | 내용 |
|---|---|
| **UI** | 실행 콘솔 → `② 시뮬 실행` → 풀 선택 → effort(low/medium/high) → **dry-run(2명)** 체크 → **시뮬 실행** → `③ 잡 현황`에서 자동 폴링 |
| **CLI** | `python3 runner.py --script wf_vs_v23.js --pool-id <pool_id> [--effort medium] [--dry-run] [--n-limit N] [--confirm-large]` ⟨코드근거⟩ |
| **배선** | `POST /api/runs {script,pool_id,effort,dry_run,n_limit,confirm_large}` → `actions.start_run` → `runner.py`를 **백그라운드 잡**으로 Popen → `GET /api/jobs/<job_id>` 폴링 |

- 스크립트 매핑(UI가 자동 선택): single 풀 → `wf_vs_v23.js`, multipool 풀 → `wf_v23_multi.js`.
- **dry-run은 UI 기본 ON**(2명만). 실제 파이프라인 확인용 스모크. 러너 상세는 §3, 비용 가드는 §4.
- 잡 완료 시 `runs/<run_id>/`가 생기고, 이후 진단·판정·리포트 탭에서 그 run_id를 고른다.
- ⚠️ dry_run이든 본실행이든 `claude -p`로 실제 LLM을 태운다 → 본 문서에서는 실행하지 않았다(⟨코드근거⟩).

### ③ 진단 (붕괴/동질성 — LLM 없음)

| | 내용 |
|---|---|
| **UI** | `진단` 탭 → 런 선택 → 보기 사용률 · 최빈패턴 점유율(동질성) · 붕괴 3종 · 임계 초과 시 경고 배지 |
| **CLI** | `HARNESS_SP=$PWD/runs/<run_id> HARNESS_JOURNAL_BASE=$PWD/runs python3 v23_verify.py <run_id>` → JSON ✅ |
| **배선** | `GET /api/runs/<run_id>/diagnose` → `v23_verify.py`(v2.3 저널만) |

- 진단 대상은 **v2.3 저널(첫 result에 `A2a_dist`)** 만. 레거시 포맷이면 `diagnosable:false`.
- ✅ 확인: `wf_9971e46b-6d1` → `format v2.3 diagnosable True`.

### ④ 판정 (방향성 — LLM 없음)

| | 내용 |
|---|---|
| **UI** | `판정` 탭 → 런 선택 → 연속상관표(부호·유의도) · 다풀 부호일관 · 세그교차 · D1 수용곡선 · 등급 라벨 |
| **CLI (JSON)** | single: `HARNESS_SP=$PWD/runs/<id> HARNESS_JOURNAL_BASE=$PWD/runs python3 v23_judge.py <id>` ✅ · multipool: `… v23_multi_judge.py <id>` ✅ |
| **CLI (콘솔 판정문)** | `… python3 v23_analyze.py <id>` ✅ / 다풀 `… v23_multi_analyze.py <id>` ✅ (사람이 읽는 텍스트) |
| **배선** | `GET /api/runs/<id>/judge` → kind에 따라 `v23_judge.py`/`v23_multi_judge.py` · D1 곡선은 `GET …/curve` |

- ✅ 확인: `wf_9971e46b-6d1` judge → `judgeable True kind single`; `wf_6ff10eda-c1f` → `kind multipool`.
- ⚠️ **주의**: `v23_analyze.py`·`v23_multi_analyze.py`는 성공해도 **`| head` 등 파이프로 자르면 exit 1**(SIGPIPE)이 뜬다. 파이프 없이 돌리면 exit 0(INSPECTION A3). ✅ 확인: 파이프 없이 각각 exit 0(37줄/42줄). JSON 스크립트(`v23_verify`/`v23_judge`/`v23_multi_judge`)는 exit 0.

### ⑤ 리포트 (게이트C 포맷 — LLM 없음)

| | 내용 |
|---|---|
| **UI** | `리포트` 탭 → 런 선택 → `게이트C_시뮬결과_정리.md` 포맷 자동 렌더 + 내보내기 |
| **CLI** | 별도 스크립트 없음 → `curl http://127.0.0.1:8781/api/runs/<run_id>/report` ✅ |
| **배선** | `GET /api/runs/<run_id>/report` → `harness_api/report.py` |

- **⓪ 경고 헤더(합성·비실측·인용불가)는 하드코딩·항상 포함** — 끄는 옵션 자체가 없다(SPEC §5.4, INSPECTION C3).
- ✅ 확인: report → `warning_included True`.

### (참고) 설계 뷰어

- `설계` 탭 = v2.3 문항·보기·latent 스펙·ANCHOR_PRIORS **읽기전용 표시**. 편집 UI 없음(SPEC §5.5).
- CLI 대응: `GET /api/design` (keys: `questions`·`latent_specs`·`anchor_priors`) ✅.

---

## 3. 러너 직접 호출 (`runner.py`)

`runner.py`는 SPEC §4 계약의 구현체 — Claude Code CLI를 **중첩 세션 서브프로세스**로 띄워
Workflow를 실행하고, 저널을 회수해 `runs/<run_id>/`로 영속화한다(ClaudeBackend 이식 아님).

```
usage: runner.py [-h] --script {wf_v23_multi.js,wf_vs_v23.js} --pool-id POOL_ID
                 [--effort EFFORT] [--dry-run] [--n-limit N_LIMIT]
                 [--confirm-large] [--timeout TIMEOUT]
```
(✅ `python3 runner.py --help` 출력 그대로)

**인자**

| 인자 | 의미 |
|---|---|
| `--script` (필수) | `wf_vs_v23.js`(단일) 또는 `wf_v23_multi.js`(다풀). 이 둘만 허용. |
| `--pool-id` (필수) | 풀 식별자. `runs/<pool_id>/` 또는 스크래치패드에서 `prof.json`/`multipool_args.json`을 찾아 personas 로드. |
| `--effort` | 기록용 라벨(기본 `medium`). 실제 effort는 임시 wf에 이미 내장 — 이 값은 params에만 남는다. |
| `--dry-run` | N을 **≤2로 강제 축소**(파이프라인 검증용). §4-①. |
| `--n-limit N` | 실행 페르소나 상한. `N = min(전체, n_limit)` 후 dry_run이면 다시 min(N,2). |
| `--confirm-large` | N>50 실행 확인. 없으면 거부. §4-②. |
| `--timeout S` | 저널 폴링 타임아웃(초). 미지정 시 dry_run=300, 본실행=3600. |

**표준 출력(JSON, 1회)**: `{run_id, journal_path, status, token_estimate, results_captured, log}`
- `status` ∈ `completed` / `timeout` / `refused_large_N` / `launch_failed`.
- `journal_path`는 완료 시 `runs/<run_id>/journal.jsonl`.

**호출 예 (⟨코드근거⟩ — LLM 호출이라 미실행)**
```bash
# dry_run 스모크 (2명)
python3 runner.py --script wf_vs_v23.js --pool-id pool_91551371 --dry-run        # ⟨코드근거⟩
# 본실행 (소형)
python3 runner.py --script wf_vs_v23.js --pool-id pool_91551371 --effort medium  # ⟨코드근거⟩
# 대규모 (N>50)
python3 runner.py --script wf_v23_multi.js --pool-id multipool_xxx --confirm-large # ⟨코드근거⟩
```

- UI의 `② 시뮬 실행`은 위 CLI를 백그라운드 잡으로 감싼 것뿐이다(`actions.start_run`). CLI를 직접 쓰면 잡·폴링 없이 러너 JSON을 그대로 받는다.

---

## 4. 비용 가드 (SPEC §4 · 코드 위치 `runner.py`)

세 가드 모두 **러너에서 강제**된다. UI는 같은 기준을 미리 표시할 뿐 실제 차단은 러너가 한다.

| # | 가드 | 언제 발동 | 어떻게 해제 | 코드 |
|---|---|---|---|---|
| ① | **dry_run N≤2** | `--dry-run`(UI: dry-run 체크, 기본 ON) → `N = min(N, 2)` | dry-run 체크 해제(=본실행). 그러면 전체 N. | `DRY_RUN_CAP=2` (runner.py:33), 적용 `:162` |
| ② | **N>50 확인 게이트** | 본실행이고 실효 N > 50 → `status=refused_large_N`, 실행 안 함 | `--confirm-large`(UI: “대규모 실행 확인” 체크) | `LARGE_N=50` (runner.py:34), 분기 `:168` |
| ③ | **재시도 1회 상한** | 항상. 러너는 `claude -p`를 **정확히 1회만** 호출 — 자동 재실행/백오프 루프 없음 | (해제 대상 아님 — 실패하면 사람이 다시 부른다) | `launch()` 단일 호출 `:179`, subprocess 단일 `:91` |

- ②의 “실효 N”은 다풀이면 `N_PER × 풀수`. dry_run이면 ①이 먼저 걸려 N≤2가 되므로 ②는 사실상 본실행에서만 의미.
- ✅ 임계값(2·50)은 `runner.py`·UI(`web/src/screens/Console.jsx`의 `DRY_RUN_CAP`/`LARGE_N`)에서 동일 확인. 값 변경 시 양쪽 동기 필요.
- 예상 토큰 견적 = 실효 N × `PER_PERSONA_TOKENS`(24000, 관측 대략치). 판정 아님, 규모 감각용.

---

## 5. 산출물 위치

### 5-a. `runs/<run_id>/` — 한 번의 시뮬 실행

`persist_run.py`가 시뮬 종료 직후 아래를 복사한다(러너가 자동 호출; SPEC P0-3).

| 파일 | 내용 |
|---|---|
| `journal.jsonl` | 워크플로 저널(에이전트별 응답 분포). **>20MB면 `journal.jsonl.gz`** (§5-c) |
| `prof.json` / `pool_meta.json` / `run_cfg.json` | 단일풀 스냅샷(그 런이 쓴 풀 전체 — 재현용) |
| `multipool_args.json` / `multipool_cfg.json` / `multipool_meta.json` | 다풀 스냅샷(다풀 런일 때) |
| `params.json` | 실행 파라미터 매니페스트 |

실제 예시(`runs/wf_f27fa6bd-a74/` = 기존 dry_run 산출물, INSPECTION B1) — `params.json`:
```json
{ "run_id": "wf_f27fa6bd-a74", "journal_file": "journal.jsonl", "journal_mb": 0.001,
  "gzipped": false, "pool_source": ".../runs/wf_9971e46b-6d1",
  "pool_files": ["run_cfg.json","pool_meta.json","prof.json"],
  "params": { "script": "wf_vs_v23.js", "pool_id": "wf_9971e46b-6d1",
              "effort": "medium", "dry_run": true, "N": 2, "session_id": "…" } }
```
(✅ 파일 구조·필드 실측)

**현재 `runs/`에 이관돼 있는 런**(✅ `/api/runs` 확인):
- `wf_9971e46b-6d1` — single, N=49 (R3)
- `wf_6ff10eda-c1f` — multipool, N=300 (R4)
- `wf_f27fa6bd-a74` — dry_run, N=2

### 5-b. 풀 디렉토리 & 런타임(비커밋)

- 풀: `runs/pool_*/`·`runs/multipool_*/`·`runs/sweep_*/` (접두어로 런과 구분 — `store.py`).
- 런타임(git 무시, `.gitignore`): `runs/_jobs/`(백그라운드 잡 레코드·stdout/err), `runs/_sp/`(UI 풀 생성 스크래치 사본), `runs/_tmp_runs/`.

### 5-c. 20MB 저널 gzip 규칙

`persist_run.py`: 저널 크기 > `--gzip-threshold-mb`(**기본 20.0**)이면 `journal.jsonl.gz`로 저장,
아니면 `journal.jsonl` 평문. 읽는 쪽(`store.py`·`analysis.py`)은 `.gz`를 투명 처리한다.
(✅ 규칙은 코드 `persist_run.py:48-55`에서 확인 — LLM과 무관한 순수 파일 크기 분기다. 단 >20MB 저널 실물이 현재 repo에 없어 **분기 자체는 미실행** → `[미확인]`.)

---

## 6. 트러블슈팅

### 6-a. 경로 환경변수 3종 (`harness_paths.py`)

미지정 시 **원 세션 경로가 기본값** — 무-환경변수 동작은 원본과 바이트 동일.

| 변수 | 의미 | 기본값 |
|---|---|---|
| `HARNESS_SP` | 스크래치패드(풀 파일·중간 JSON) | `/tmp/claude-0/-home-user-ggggg/8fffd176-…/scratchpad` |
| `HARNESS_JOURNAL_BASE` | 워크플로 저널 루트 (`<BASE>/<run_id>/journal.jsonl`) | `/root/.claude/projects/-home-user-ggggg/8fffd176-…/subagents/workflows` |
| `HARNESS_RUNS` | 런 영속 저장소 | `<repo>/runs` |

- 분석 CLI를 이관된 런에 직접 돌릴 때 쓰는 관용구(✅):
  `HARNESS_SP=$PWD/runs/<run_id> HARNESS_JOURNAL_BASE=$PWD/runs python3 v23_verify.py <run_id>`
  (백엔드도 동일: `HARNESS_JOURNAL_BASE=runs`, `HARNESS_SP=runs/<run_id>` — `analysis.run_env`).

### 6-b. “저널이 안 잡힐 때” — 러너 저널 탐색 순서 (코드 그대로)

시뮬 실행이 `launch_failed`/`timeout`으로 끝나면, `runner.py`가 저널을 찾는 **실제 순서**는 다음과 같다(추측 없이 코드 그대로):

1. **저널 base 계산** — `nested_journal_base(sid)` (runner.py:48–52):
   `HARNESS_JOURNAL_BASE`를 `rstrip('/')` 후 **`dirname` 3번** 적용해 `projdir`를 얻고,
   `jbase = <projdir>/<새 세션 sid>/subagents/workflows`를 만든다.
   (즉 기본값의 `8fffd176-…` 세션 조각은 벗겨지고 `…/projects/-home-user-ggggg`만 남아, 러너가 새로 생성한 sid가 붙는다.)

2. **run_id 발견** — `discover_run_id(jbase, out, 30, log)` (runner.py:97–113):
   - 최대 **30초**, **2초 간격**으로 `jbase` 디렉토리를 확인 → `wf_`로 시작하는 하위 디렉토리가 있으면 **mtime 최신**을 run_id로 반환.
   - 없으면 **폴백**: `claude` stdout(`out`)에서 정규식 `\bwf_[a-z0-9]{6,}-[a-z0-9]{2,}\b`로 파싱.
   - 그래도 없으면 `None` → `status=launch_failed`.

3. **완료 폴링** — `poll_journal(jbase, run_id, N, timeout, log)` (runner.py:116–137):
   `jbase/<run_id>/journal.jsonl`을 열어 `type=="result"`이고 `result`가 dict인 라인 수를 센다.
   그 수 ≥ N이면 `completed`, 아니면 timeout(dry_run 300s / 본실행 3600s / `--timeout`)까지 **5초 간격** 재확인 → 초과 시 `timeout`.

4. **영속화** — `completed`면 `persist_run.py <run_id> --pool-dir runs/<pool_id> --params '…'`을
   `HARNESS_JOURNAL_BASE=jbase` 환경으로 호출 → `jbase/<run_id>/journal.jsonl` → `runs/<run_id>/` 복사 (runner.py:193–200).

→ **함의**: run_id를 못 찾는다(1·2 실패)는 건 `dirname³(HARNESS_JOURNAL_BASE)`로 유도된 `projdir`가
실제 `claude`가 중첩 세션의 Workflow 저널을 쓰는 위치와 다르다는 뜻이다. `HARNESS_JOURNAL_BASE`를
현재 환경의 실제 `~/.claude/projects/<이 repo>/…/subagents/workflows` 형태로 맞춘 뒤 재실행한다.
(위 4단계는 `runner.py` 로직 그대로이며, 그 이상은 추측하지 않는다.)

### 6-c. full-chain e2e (`RUN_FULL_CHAIN=1`) — **실행 예정 절차**

SPEC §5 P2 완료기준 (b)(콘솔에서 신규 dry_run 트리거 → 잡 완료 → 진단·판정 화면까지 무개입 완주)를
검증하는 유일한 커버리지. `web/e2e/full-chain.spec.js`는 실제 `claude` 서브프로세스(2명) 비용 때문에 **기본 skip**이다.

```bash
# 백엔드(:8781)·프론트가 떠 있는 상태에서, web/ 안에서:
RUN_FULL_CHAIN=1 npx playwright test full-chain          # ⟨코드근거⟩ · 실행 예정(아직 미실행)
```

- 이 절차는 **아직 소유자가 실행하지 않았다** — INSPECTION의 `P2 완료기준 (b)`는 `[검증불가]`(LLM 실행 필요)로 남아 있다. 따라서 “검증된 절차”가 아니라 **“실행 예정 절차”**다.
- 실행 조건: `enabled = process.env.RUN_FULL_CHAIN === '1'`일 때만 test가 돈다(spec `:6,9`). 88888 시드로 8명 풀 생성 → dry-run(2명) 트리거 → 잡 completed 대기(≤170s) → 진단·판정 탭 확인.
- 백엔드 배선(`POST /api/runs → actions.start_run → runner → get_job`)은 **코드상 존재**하고, LLM-의존 러너 체인 자체는 기존 dry_run 산출물(`runs/wf_f27fa6bd-a74/`)로 INSPECTION B1에서 입증됐다. 미입증분은 **콘솔 UI → 잡 → 화면** end-to-end 뿐.

---

## 부록 A. `[미확인]` · `⟨코드근거⟩` 집계

작성 규율(§표기)에 따라, 실측하지 못한 항목의 위치를 모은다.

### A-1. `[미확인]` (3건)
| 위치 | 항목 |
|---|---|
| §1-b | `npm run preview`(포트 4173) 서버 기동 — `build`(✅)만 확인, preview 미기동. |
| §1-a (묵시) | `pip install -r …` **정확한 -r 형식**은 미실행 — 개별 패키지(fastapi/uvicorn/numpy/scipy/pandas) import는 ✅ 확인. |
| §5-c | 20MB 초과 저널 gzip **분기 실행** — 규칙은 코드 ✅(`persist_run.py:48-55`)이나 >20MB 실물이 없어 분기 미실행(LLM 무관, 순수 파일 연산). |

### A-2. `⟨코드근거⟩` — LLM 호출이라 미실행 (4건)
| 위치 | 항목 | 근거 코드 |
|---|---|---|
| §2-② | 시뮬 실행(dry_run/본실행) UI 트리거·잡 | `actions.start_run` / `main.py POST /api/runs` |
| §3 | `runner.py` 직접 호출 3예(dry_run·본실행·대규모) | `runner.py` (launch/discover/poll/persist) |
| §6-c | `RUN_FULL_CHAIN=1 npx playwright test full-chain` | `web/e2e/full-chain.spec.js` — **실행 예정 절차**(미실행) |
| §2-② 각주 | dry_run도 `claude -p`로 실 LLM 호출 | `runner.py:launch` |

### A-3. ✅ 실측 확인 (참고 — 실행한 것)
서버 기동(백엔드 `:8781`·프론트 `:5173`) · `/api/health`·`/api/runs`·`/api/pools`·`/api/design`
· 읽기 엔드포인트 diagnose/judge/curve/report · `runner.py --help` · `persist_run.py --help`
· `build_fresh_pool/multipool/sweep --help` · 풀 생성(`build_fresh_pool.py --seed 91551371 --n 49`, rc=0)
· 분석 CLI(`v23_analyze`/`v23_multi_analyze`/`v23_verify`/`v23_judge`/`v23_multi_judge`, 파이프 없이 exit 0)
· 프론트 `npm install`·`npm run build`(rc=0). 근거는 각 절의 `✅` 표기 참조.
