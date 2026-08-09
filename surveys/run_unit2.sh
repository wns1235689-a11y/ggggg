#!/bin/bash
# B안 2단위 드라이버 — 3시나리오 × 1시드(드리프트 게이트) × 2설문, 순차 실행.
# 각 조합: 풀 생성 → pool_gate(|z|>2면 시드+7 재추첨, 최대 3회) → 러너(--confirm-large).
# 연속 2회 결과 0이면 중단(세션 한도 등 환경 문제로 판단).
set -u
cd "$(dirname "$0")/.."
export HARNESS_RUNS=$PWD/runs
LOG=runs/_unit2_log.jsonl
: > "$LOG"
ZERO_STREAK=0

run_combo() {
  local survey=$1 scen=$2 seed=$3 build_args=$4 wf=$5 prefix=$6
  local attempt pool_id
  for attempt in 1 2 3; do
    python3 surveys/$survey/build_pool.py $build_args --seed $seed --scenario $scen >> "$LOG.txt" 2>&1
    pool_id="${prefix}_${seed}"
    if python3 surveys/pool_gate.py "$pool_id" >> "$LOG.txt" 2>&1; then
      break
    fi
    echo "{\"event\":\"reseed\",\"survey\":\"$survey\",\"scenario\":\"$scen\",\"seed\":$seed}" >> "$LOG"
    rm -rf "runs/$pool_id"
    seed=$((seed + 7))
    pool_id="${prefix}_${seed}"
  done
  echo "{\"event\":\"run_start\",\"survey\":\"$survey\",\"scenario\":\"$scen\",\"pool\":\"$pool_id\"}" >> "$LOG"
  local out
  out=$(python3 runner.py --script "surveys/$survey/$wf" --pool-id "$pool_id" --confirm-large 2>>"$LOG.txt")
  echo "$out" | python3 -c "
import json,sys
d=json.loads(sys.stdin.read())
print(json.dumps({'event':'run_done','survey':'$survey','scenario':'$scen','pool':'$pool_id',
                  'run_id':d.get('run_id'),'status':d.get('status'),
                  'results':d.get('results_captured'),'tokens_est':d.get('token_estimate')},
                 ensure_ascii=False))" >> "$LOG"
  local got
  got=$(echo "$out" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('results_captured') or 0)")
  if [ "$got" -eq 0 ]; then
    ZERO_STREAK=$((ZERO_STREAK + 1))
  else
    ZERO_STREAK=0
  fi
  if [ "$ZERO_STREAK" -ge 2 ]; then
    echo '{"event":"abort","reason":"연속 2회 결과 0 — 환경 문제 추정(세션 한도 등)"}' >> "$LOG"
    exit 2
  fi
}

# 시나리오별 고정 기본 시드(재현 기록용) — 게이트 통과 실패 시 +7 재추첨
run_combo robot_wc26   conservative 61000101 "--n 110"                 wf_robot.js   pool_robot
run_combo robot_wc26   neutral      61000102 "--n 110"                 wf_robot.js   pool_robot
run_combo robot_wc26   optimistic   61000103 "--n 110"                 wf_robot.js   pool_robot
run_combo genesis_eu26 conservative 62000101 "--n-street 25 --n-gp 40" wf_genesis.js pool_genesis
run_combo genesis_eu26 neutral      62000102 "--n-street 25 --n-gp 40" wf_genesis.js pool_genesis
run_combo genesis_eu26 optimistic   62000103 "--n-street 25 --n-gp 40" wf_genesis.js pool_genesis
echo '{"event":"all_done"}' >> "$LOG"
