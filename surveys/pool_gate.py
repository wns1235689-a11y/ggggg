#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""풀 드리프트 게이트(B안 봉인 프로토콜) — 실 LLM 런 전에 나쁜 시드를 걸러낸다.

pool_meta의 기대확률(p_know/p_exposed) 대비 실현 상태의 z를 계산해 |z|>2 셀이 있으면
비영 종료(드라이버가 시드를 바꿔 재추첨). LLM 불필요·즉시 실행.

사용: python3 surveys/pool_gate.py <pool_id>   (HARNESS_RUNS 기준)
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import harness_paths as H   # noqa: E402


def zcell(ms, p_key, hit):
    sum_p = sum(m[p_key] for m in ms) if isinstance(ms[0][p_key], float) else None
    var = sum(m[p_key] * (1 - m[p_key]) for m in ms)
    realized = sum(1 for m in ms if hit(m))
    return (realized - sum_p) / (var ** 0.5) if var > 0 else 0.0, realized, sum_p


def main():
    pool_id = sys.argv[1]
    metas = json.load(open(os.path.join(H.RUNS_DIR, pool_id, "pool_meta.json"), encoding="utf-8"))
    bad = []
    if pool_id.startswith("pool_genesis"):
        for pop in ("street_rtm", "gp_zandvoort"):
            ms = [m for m in metas if m["pop"] == pop]
            for b in ("BMW", "LEXUS", "POLESTAR", "GENESIS"):
                mm = [{"p": m["p_know"][b], "k": m["know"][b]} for m in ms]
                sum_p = sum(x["p"] for x in mm)
                var = sum(x["p"] * (1 - x["p"]) for x in mm)
                realized = sum(1 for x in mm if x["k"] == "knows")
                z = (realized - sum_p) / (var ** 0.5) if var > 0 else 0.0
                if abs(z) > 2.0:
                    bad.append(f"{pop}/{b} z={z:+.2f} (실현 {realized} vs 기대 {sum_p:.1f})")
    elif pool_id.startswith("pool_robot"):
        sum_p = sum(m["p_exposed"] for m in metas)
        var = sum(m["p_exposed"] * (1 - m["p_exposed"]) for m in metas)
        realized = sum(1 for m in metas if m["exposed"])
        z = (realized - sum_p) / (var ** 0.5) if var > 0 else 0.0
        if abs(z) > 2.0:
            bad.append(f"exposure z={z:+.2f} (실현 {realized} vs 기대 {sum_p:.1f})")
        # 프로브 경로 최소 재료: BD 계열 지식층이 0이면 H3·H4 판독 불능
        n_bdish = sum(1 for m in metas if m["knowledge"] in ("both", "bd_only"))
        if n_bdish < 2:
            bad.append(f"BD 지식층 {n_bdish}명(<2) — 프로브 경로 판독 불능")
    else:
        raise SystemExit(f"[pool_gate] 알 수 없는 풀 접두어: {pool_id}")

    if bad:
        print(f"[pool_gate] DRIFT {pool_id}: " + "; ".join(bad))
        sys.exit(1)
    print(f"[pool_gate] OK {pool_id}")


if __name__ == "__main__":
    main()
