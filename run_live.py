#!/usr/bin/env python3
"""
실 LLM(에이전트) 응답 → 파이프라인 리포트
==========================================
워크플로가 생성한 검증 응답 JSON(list[dict])을 받아 S7→S9를 실행.
사용:  python3 run_live.py <agent_responses.json>
출력:  out/responses_live.csv, aggregate_live.json, report_live_9_4.md
"""
from __future__ import annotations
import sys, json, csv, os
from sim import ingest, aggregate, report

OUT = os.path.join(os.path.dirname(__file__), "out")


def main(path):
    agent_resp = json.load(open(path))
    resp = ingest.ingest_live(agent_resp)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "responses_live.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(resp[0].keys()))
        w.writeheader(); w.writerows(resp)
    agg = aggregate.aggregate(resp)
    json.dump(agg, open(os.path.join(OUT, "aggregate_live.json"), "w"), ensure_ascii=False, indent=2)
    md, lint = report.build_report(agg, len(resp), "claude-live")
    open(os.path.join(OUT, "report_live_9_4.md"), "w").write(md)
    print(f"[live] N={len(resp)} · 린터 {'✅통과' if lint['pass'] else '❌'+str(lint['violations'])}")
    print("[out] responses_live.csv / aggregate_live.json / report_live_9_4.md")


if __name__ == "__main__":
    main(sys.argv[1])
