#!/bin/bash
# B안 2단위 재개 드라이버 — 게이트 통과한 기존 풀은 재사용, 러너 타임아웃 수정판으로 6콤보 실행.
# (콤보1·2의 300초-킬 부분런 wf_78b2c32f/wf_a91db033은 미영속 증적으로 두고 신규 런으로 대체)
set -u
cd "$(dirname "$0")/.."
export HARNESS_RUNS=$PWD/runs
LOG=runs/_unit2b_log.jsonl
: > "$LOG"
ZERO_STREAK=0

run_combo() {
  local survey=$1 scen=$2 seed=$3 build_args=$4 wf=$5 prefix=$6
  local attempt pool_id
  pool_id="${prefix}_${seed}"
  if [ -d "runs/$pool_id" ]; then
    echo "{\"event\":\"pool_reuse\",\"pool\":\"$pool_id\"}" >> "$LOG"
  else
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
  fi
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

run_combo robot_wc26   conservative 61000101 "--n 110"                 wf_robot.js   pool_robot
run_combo robot_wc26   neutral      61000102 "--n 110"                 wf_robot.js   pool_robot
run_combo robot_wc26   optimistic   61000103 "--n 110"                 wf_robot.js   pool_robot
run_combo genesis_eu26 conservative 62000101 "--n-street 25 --n-gp 40" wf_genesis.js pool_genesis
run_combo genesis_eu26 neutral      62000102 "--n-street 25 --n-gp 40" wf_genesis.js pool_genesis
run_combo genesis_eu26 optimistic   62000103 "--n-street 25 --n-gp 40" wf_genesis.js pool_genesis
echo '{"event":"all_done"}' >> "$LOG"
