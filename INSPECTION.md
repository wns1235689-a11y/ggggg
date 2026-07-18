# INSPECTION.md — 독립 검수 보고

> **지위**: "완료됐다"는 자기보고를 **실측으로 재검증**한 독립 검수. 구현 세션의 주장과 무관하게 **직접 실행·확인한 것만** 판정에 사용.
> **기준 문서**: SPEC.md · INVENTORY.md · LEGACY.md (RUNNER.md는 부재 — B2 참조). **기준 브랜치**: `claude/simulation-survey-planning-d9rlih`.
> **검수 시점**: HEAD=`6618113` · **정찰 시점(diff 기준)**: `e131c4a`(INVENTORY.md 최초 커밋) · 교차확인 baseline `badd0b8`(정찰 이전).
> **제약 준수**: 코드 무수정(유일 산출물=이 파일) · LLM 실행 0회(기존 dry_run 실물로 검증) · 모든 생성물은 `/tmp`·무시경로에만 → 검수 종료 후 추적 트리 무변경 확인.
> **표기**: 직접 재현 불가 항목은 FAIL이 아니라 **[검증불가]**. 모든 판정에 재현 커맨드/파일경로 병기.

---

## 종합 결론 (먼저)

- **블로커(완료기준 미달) FAIL: 0건.** 경미 FAIL: 0건.
- **PASS 18개 항목** — A1~A4, B1, C1~C4, D1~D5, 울타리6(D6), P2완료기준(a). 전부 실측 재현.
- **[검증불가] 3건**(제약상 직접 재현 불가 — 소유자 수동 확인 대상): **B2**(RUNNER.md 부재), **C2 시각 렌더**(브라우저 육안), **P2 완료기준 (b)**(콘솔 UI 신규 dry_run 트리거→화면 — 실제 LLM 실행 필요).
- **적대적 교차검증**: 읽기전용 서브에이전트 10종이 핵심 판정 9개를 독립 반증 시도 → **10/10 CONFIRMED**(전부 재현 성공·반증 실패).
- **자기보고 대비 정정 1건**(위반 아님): "v23_analyze/v23_multi_analyze/vs_verify 완전 무변경" 주장은 부정확 — 실제로 P0-1 경로치환 2줄 변경 있음(단 salt·임계·통계·프롬프트·스키마는 불변).

---

## A. P0 완료 기준 실측

| ID | 판정 | 근거(재현 커맨드/경로) | 비고 |
|---|---|---|---|
| **A1** 경로 독립성 | **PASS** | 임시경로 build: `HARNESS_SP=/tmp/inspect_sp HARNESS_RUNS=/tmp/inspect_runs python3 build_fresh_pool.py --seed 91551371 --n 49` → **rc=0**(경로에러 없음). 임시경로 분석: `HARNESS_SP=$PWD/runs/wf_9971e46b-6d1 HARNESS_JOURNAL_BASE=$PWD/runs python3 v23_analyze.py wf_9971e46b-6d1` → **exit 0**. | `harness_paths.py`가 HARNESS_SP/JOURNAL_BASE/RUNS로 일원화, 미지정 시 기본=원 세션경로. |
| **A2** 시드 재현 | **PASS** | A1의 재생성 풀 `pool_91551371/{prof,pool_meta,run_cfg}.json` vs 원본 `runs/wf_9971e46b-6d1/` → **bit-identical**. `md5(prof.json)=9d9c71a0f0430bc308113e00967a83f4` 양측 일치. | 휘발 필드 제외 불요(run_cfg=N/RUN_SEED, 시드로 완전 결정). 적대검증 A2 에이전트 독립 재현 md5 동일. |
| **A3** 저널 이관 | **PASS** | R3: 위 v23_analyze exit 0, 판정 37줄(유병률·세그교차·연속상관 B1 −0.08/C2 −0.28/D1 −0.38). R4: `HARNESS_SP=$PWD/runs/wf_6ff10eda-c1f HARNESS_JOURNAL_BASE=$PWD/runs python3 v23_multi_analyze.py wf_6ff10eda-c1f` → exit 0, 판정 42줄(통합 B1 −0.31***/부호일관). | 세션 보고값과 일치. (`head` 파이프로 인한 허위 exit 1은 재실행으로 exit 0 확정.) |
| **A4** 레거시 무변경 | **PASS** | `git diff --numstat e131c4a HEAD -- <레거시 29파일>` → **0줄**(추가0/삭제0). 교차: `badd0b8 HEAD`도 0줄. 29파일 전부 존재. | 레거시 목록=LEGACY.md/SPEC§2. 적대검증: blob-hash 29/29 바이트동일, name-status EMPTY. |

## B. P1 완료 기준

| ID | 판정 | 근거(재현 커맨드/경로) | 비고 |
|---|---|---|---|
| **B1** 러너 완주 | **PASS** | 기존 dry_run 런 `runs/wf_f27fa6bd-a74/` 실물 검증(새 실행 안 함): ① 저널 `journal.jsonl` result 2건·`A2a_dist` 존재 ② 풀 스냅샷 prof/pool_meta/run_cfg 존재 ③ `params.json` = dry_run:True·N:2·session_id 기록 ④ 판정연결 `v23_analyze wf_f27fa6bd-a74` exit 0. 러너 계약코드 `runner.py`(discover_run_id:97·poll_journal:116·persist_run 호출:196) 존재. | 규칙2 준수(기존 dry_run 산출물 사용, LLM 미실행). 이 산출물은 러너 **CLI 체인**(실행→런ID→저널→runs/→판정)을 입증. |
| **B2** RUNNER.md | **[검증불가]** | `ls RUNNER.md` → **부재**. | SPEC이 RUNNER.md를 요구하지 않음(§4는 러너 '계약'만 규정) → 완료기준 미달 아님. 러너는 `runner.py` 도크스트링(:1-16)+SPEC§4로 자기문서화. **정보성** — 소유자가 RUNNER.md를 원하면 별도 작성 대상. |

## C. P2 완료 기준 (코드 검증 가능 범위)

| ID | 판정 | 근거(재현 커맨드/경로) | 비고 |
|---|---|---|---|
| **C1** 백엔드 API | **PASS** | `uvicorn harness_api.main:app`(port 8799) 기동 후 curl: `/api/runs`(런 3개 R3·R4·dry_run) · `/api/design`(13문항·21latent·12anchor) · `/api/runs/wf_9971e46b-6d1/diagnose`(v2.3·N49) · `/judge`(single·B1 −0.08) · `/api/runs/wf_6ff10eda-c1f/judge`(multipool·통합 B1 −0.31***). | 4개 화면이 쓰는 엔드포인트 전부 R3/R4 실데이터 JSON 반환. |
| **C2** 프론트 빌드 | **PASS**(빌드) / **[검증불가]**(시각) | `cd web && npm run build` → **exit 0**(39모듈, dist 생성). | 브라우저 시각 렌더링은 소유자 수동 확인(비스킵 e2e는 렌더 검증하나, 본 검수는 빌드 통과까지 실측). |
| **C3** 리포트 ⓪ 헤더 | **PASS** | 실제 생성 `curl /api/runs/wf_9971e46b-6d1/report` → `warning_included:True`, `## ⓪ 문서 지위 · 필수 경고`·`LLM 합성·비실측`·`인용 불가` 전부 포함. 비활성화 옵션 부재: `grep -niE 'disable|skip.?warn|toggle' harness_api/report.py` → 0건. | `WARNING_HEADER`(report.py:15) 상수, build_markdown(:185)에 무조건 삽입(끌 분기 없음), warning_included 고정 True(:233). |
| **C4** 설계 읽기전용 | **PASS** | `/api/design`은 `@app.get`(main.py:59) 단일, design 대상 POST/PUT/PATCH/DELETE 없음. `Design.jsx`에 input/textarea/form/onSubmit/save 없음(유일 button=오류시 재시도). | 편집 UI·쓰기 엔드포인트 부재. |
| **P2완료기준 (a)** 이관 R3/R4 4화면 표시 | **PASS** | C1으로 입증(runs/의 R3·R4가 진단·판정·리포트·설계·콘솔이 읽는 API에서 정상 반환). | — |
| **P2완료기준 (b)** 콘솔 신규 dry_run 트리거→진단·판정 화면 | **[검증불가]** | 유일 커버리지 `web/e2e/full-chain.spec.js`는 **기본 skip**(`:6,9` test.skip(!enabled), enabled=RUN_FULL_CHAIN==='1' → **실제 claude 서브프로세스 필요**). `console.spec.js:49`는 '실행' 클릭을 의도적으로 생략(비용 회피). UI-트리거 산출물(wf_59ca0f21-584·wf_3505859a-2c1·pool_88888·pool_777) **커밋 트리에 전부 부재**. | **본 검수 제약(LLM 실행 금지)상 직접 재현 불가 → 규칙3에 따라 검증불가.** 백엔드 배선(POST /api/runs→actions.start_run→러너→get_job)은 **코드상 존재**하고 LLM-의존 러너체인은 B1으로 입증됨. 콘솔 UI→잡→화면 end-to-end만 미입증. **소유자 확인**: `RUN_FULL_CHAIN=1 npx playwright test full-chain`(실제 LLM). |

## D. 울타리 준수 감사

| ID | 판정 | 근거(재현 커맨드/경로) | 비고 |
|---|---|---|---|
| **D1** 화면 ≤5 | **PASS** | `ls web/src/screens/*.jsx`=5(Console·Design·Diagnose·Judge·Report). `App.jsx` TABS `key:'…'`=5개. | 초과 없음. |
| **D2** 무 DB·인증·클라우드·배포 | **PASS** | `harness_api/requirements.txt`=fastapi+uvicorn뿐. `grep -rniE 'sqlalchemy\|sqlite\|mongo\|redis' harness_api/`=0. `grep -rniE 'jwt\|oauth\|passlib\|bcrypt\|login' harness_api/`=0(ANTHROPIC 제외). Dockerfile·*.tf·vercel.json·boto3·kubernetes 부재. web deps=react/react-dom+vite/playwright. | 유일 미들웨어=CORSMiddleware(인증 아님). |
| **D3** 비용 가드 3종 | **PASS** | ① dry_run N≤2: `runner.py:33`(DRY_RUN_CAP=2)·`:162`(N=min(N,DRY_RUN_CAP)). ② N>50 게이트: `:34`(LARGE_N=50)·`:168`(if N>LARGE_N and not confirm_large → status refused_large_N, return). ③ 재시도 1회: launch()가 `:179`에서 1회만 호출, `:91` subprocess.run 단일, retry/backoff 루프 0건(도크스트링 `:15` 명시). | 세 가드 임계(2·50) 코드와 정확히 일치. |
| **D4** salt 정합 | **PASS** | `v23_verify.py:40-41` SALT == `v23_analyze.py:25-26` SALT (ast.literal_eval 비교 True): `{A1:40,A2a:41,A2b:42,A2c:43,A2d:44,A2x:45,B1:1,B2:46,B3:47,C1:2,C2:3,E1:60}` 12키 전부 동일. | INVENTORY §4f '파일 간 salt 일치=재현 정합' 준수. |
| **D5** 엔진 불변 | **PASS** | `git diff -U0 e131c4a HEAD -- <현행계보>`: sim/config·sim/sampler=무변경(sha256 일치). 나머지 변경분 전부 **P0 허용범위만** — 경로치환(P0-1)·시드CLI(P0-2)·runs격리(P0-4)·전역복원(P0-5)·args정식화(P0-6)·personas주입(P0-7). **프롬프트·JSON스키마·통계임계값·표집salt 라인은 diff에 전무**(wf_vs_v23.js/wf_v23_multi.js는 personas 1줄만, 프롬프트/SCHEMA sha256 동일). | 정정: 자기보고의 "v23_analyze/multi/vs_verify 완전 무변경"은 부정확 — 실제 P0-1 경로 2줄 변경 있음(엔진 로직 불변이라 위반 아님, baseline 차이). 부수: build_multipool/build_sweep cfg에 master_seed 키 추가(시드CLI 메타, LLM 스키마·임계 무관). |
| **D6** 울타리6 Phase 게이팅 | **PASS** | `git log --oneline --reverse`: LEGACY(0892953)→p0×7(e21abc1..1f864cb)→p1(b51b182)→p2×14(54de560..6618113). 프리픽스 단조, 역행·건너뜀 없음. | 완결성 비평이 지적한 미포함 울타리 — 읽기전용 확인 결과 충족. |

---

## 적대적 교차검증 (읽기전용 서브에이전트 10종)

핵심 판정 9개 + 완결성 비평 1개를 독립 재현·반증 시도. **결과: 9/9 CONFIRMED**(전부 reproduced=true, refuted=false):

| 대상 | 독립 재현 결과 |
|---|---|
| A4 레거시 0diff | 29파일 numstat EMPTY·blob-hash 바이트동일·name-status EMPTY |
| D5 엔진 불변 | 변경분 전부 P0 카테고리, SALT/임계/프롬프트/SCHEMA sha256 base==HEAD 동일 |
| D3 비용가드 | 임계 2·50 정확, 재시도 루프 0건(폴링 루프 3개만) |
| D4 salt 동일 | ast 파싱 12키 per-key 일치, 각 파일 정의 1회뿐 |
| C3 경고 하드코딩 | 무조건 삽입·비활성화 분기 0·재할당/몽키패치 0 |
| C4 설계 읽기전용 | GET 12+POST 2(pool/run만)·PUT/PATCH/DELETE 0·Design.jsx 편집요소 0 |
| D2 무DB/인증/클라우드 | requirements=fastapi+uvicorn·DB/인증/클라우드 grep 0 |
| A2 시드 재현 | 독립 재실행 prof.json md5 9d9c71a0… 원본과 동일 |
| D1 화면 수 | screens 5·TABS 5 |

**완결성 비평**이 검증 목록의 갭 2건을 지적 → 본 보고에 반영: **P2완료기준(b)**([검증불가]로 명시)·**울타리6**(D6, PASS로 추가). 그 외 완료기준·울타리는 A~D에 모두 매핑됨.

---

## FAIL 심각도 분류

- **[블로커]** (완료기준 미달): **없음**.
- **[경미]** (작동 지장 없는 결함): **없음**.

## 소유자 수동 확인 필요 항목 (검증불가 3건)

1. **P2 완료기준 (b)** — 콘솔에서 신규 dry_run 트리거 → 진단·판정 화면까지 무개입 완주. 실제 LLM 실행이 필요해 본 검수(LLM 금지)로 재현 불가. 확인: `cd web && RUN_FULL_CHAIN=1 npx playwright test full-chain`. (백엔드 배선은 코드 존재, LLM-의존 러너체인은 B1으로 입증됨 — 미입증분은 UI→잡→화면 end-to-end 뿐.)
2. **C2 시각 렌더** — 브라우저에서 4+1 화면의 실제 렌더링 육안 확인(빌드 통과는 실측됨).
3. **B2 RUNNER.md** — 문서 부재. SPEC 미요구라 완료기준엔 무관하나, 소유자가 러너 사용법 문서를 원하면 작성 대상.

---

*본 검수는 읽기전용 실측으로 수행됨 — 코드 무수정, LLM 0회 실행, 생성물은 전부 /tmp. 근거는 재현 커맨드/파일:줄로 역추적 가능.*
