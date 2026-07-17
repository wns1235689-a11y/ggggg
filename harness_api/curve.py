# -*- coding: utf-8 -*-
"""D1 가격-수용 곡선 (서술적 read 계층, SPEC §5.3 'D1 수용곡선 차트').

가격별 수용률 = mean(buy_price)/10. **판정 아님·서술적** — 저널의 buy_ 필드를 평균낼
뿐이라 v23_judge/analyze의 통계·임계를 전혀 건드리지 않는다(엔진 무변경). 유병률/수용률
'수준'은 latent 앵커에 묶여 신뢰 불가(실측 몫) → 곡선의 절대 높이가 아니라 가격에 따른
기울기(방향)만 참고한다.
"""
import gzip
import json
import os

import harness_paths as H

D1_PRICES = [5900, 6900, 7500, 8500]


def _read_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def _target_pids(rundir):
    """pool_meta.json(단일) 또는 multipool_meta.json(다풀)에서 is_target pid 집합."""
    for name in ("pool_meta.json", "multipool_meta.json"):
        m = _read_json(os.path.join(rundir, name))
        if isinstance(m, list):
            return {row["pid"] for row in m if row.get("is_target")}
    return None


def _iter_results(rundir):
    for name in ("journal.jsonl", "journal.jsonl.gz"):
        p = os.path.join(rundir, name)
        if not os.path.exists(p):
            continue
        opener = (lambda: gzip.open(p, "rt", encoding="utf-8")) if name.endswith(".gz") \
            else (lambda: open(p, encoding="utf-8"))
        with opener() as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                r = o.get("result")
                if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
                    yield r
        return


def _accept(subset):
    out = []
    for price in D1_PRICES:
        key = f"buy_{price}"
        vals = [r[key] for r in subset if isinstance(r.get(key), (int, float))]
        out.append(round(sum(vals) / len(vals) / 10 * 100, 1) if vals else None)
    return out


def d1_curve(run_id):
    rundir = os.path.join(H.RUNS_DIR, run_id)
    if not os.path.isdir(rundir):
        return None
    targets = _target_pids(rundir)
    rows = list(_iter_results(rundir))
    if not rows:
        return {"run_id": run_id, "empty": True, "prices": D1_PRICES}
    tgt_rows = [r for r in rows if targets is not None and r.get("pid") in targets]
    return {
        "run_id": run_id,
        "prices": D1_PRICES,
        "n_all": len(rows),
        "n_target": len(tgt_rows),
        "accept_all_pct": _accept(rows),
        "accept_target_pct": _accept(tgt_rows) if tgt_rows else None,
        "discipline": "서술적(판정 아님). 수용률 '수준'은 앵커에 묶임 → 신뢰 불가(실측 몫). "
                      "가격에 따른 기울기(방향)만 참고.",
    }
