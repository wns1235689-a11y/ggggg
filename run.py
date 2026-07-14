#!/usr/bin/env python3
"""
게이트 C 합성 시뮬레이션 — 오케스트레이터 (v0.3, S1–S3 단계)
=============================================================
현재 구현: S1 결합분포 표집 → S2 잠재특성 → S3 스크리닝 → 페르소나 풀 CSV + 요약.
다음 증분: S4(unprimed 순차노출 + SSR/VS 응답생성, pluggable backend) → S6~S9.

사용:  python3 run.py [N]
출력:  out/personas.csv, out/latents.csv, out/summary.json
"""
from __future__ import annotations
import sys, json, csv, os
from sim import sampler, respondent, backends, aggregate, report, config as C

OUT = os.path.join(os.path.dirname(__file__), "out")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else C.DEFAULT_N
    backend_name = sys.argv[2] if len(sys.argv) > 2 else "mock"
    os.makedirs(OUT, exist_ok=True)
    pool = sampler.build_pool(n)

    # 페르소나 원자료(Forms 태깅 컬럼과 동형 방향)
    with open(os.path.join(OUT, "personas.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pool[0].row().keys()))
        w.writeheader()
        for p in pool:
            w.writerow(p.row())

    # 잠재특성 사이드카(분석 전 비노출 — 감사·재현용)
    lat_keys = list(pool[0].latent.keys())
    with open(os.path.join(OUT, "latents.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pid"] + lat_keys)
        for p in pool:
            w.writerow([p.pid] + [round(p.latent[k], 4) for k in lat_keys])

    summary = sampler.summarize(pool)
    summary["_labels"] = "합성·비실측·편의표본·진술기준 — 게이트B/§3 판정 불변"
    summary["_seed"] = C.GLOBAL_SEED
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # ── S4: 순차노출 응답생성 (pluggable backend) ──────────────────────
    backend = backends.get_backend(backend_name)
    responses = respondent.run_survey(pool, backend)
    with open(os.path.join(OUT, "responses.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(responses[0].keys()))
        w.writeheader()
        w.writerows(responses)

    # ── S7 §3 집계 → S8 이중용도 리포트 → S9 정직성 린터 ────────────────
    agg = aggregate.aggregate(responses)
    with open(os.path.join(OUT, "aggregate.json"), "w") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
    md, lint = report.build_report(agg, n, backend.name)
    with open(os.path.join(OUT, "report_9_4.md"), "w") as f:
        f.write(md)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[린터] {'✅ 통과' if lint['pass'] else '❌ 위반 ' + str(lint['violations'])}")
    print(f"[out] personas / latents / summary / responses.csv / aggregate.json / report_9_4.md"
          f"  (N={n}, backend={backend.name}, seed={C.GLOBAL_SEED})")


if __name__ == "__main__":
    main()
