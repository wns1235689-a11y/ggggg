# -*- coding: utf-8 -*-
"""v2.3 다풀(3×100) 견고성 판정 — 판정 계층 신규 파일(엔진 무수정), JSON stdout.

v23_multi_analyze.py는 사람용 텍스트 출력이라 API 파싱에 부적합. 이 파일은
v23_multi_analyze의 표집·통계 함수·상수(load/pearson/ens_seg_delta/a2int/b1m/c2c/d1a/
e1ng/wmean/meta/lat/SSEED/SALT_A2a/K_ENS/D1P)를 **그대로 import**해 동일 판정을 JSON으로
낸다 → 복사 divergence 0. 유의도 마커(*** ** * ns)와 부호일관 판정은 원본 인라인과 동일 복사.
원본 v23_multi_analyze.py는 무변경.

사용: python3 v23_multi_judge.py <run_id>   (경로는 harness_paths 환경변수)
"""
import json
import statistics

import v23_multi_analyze as VMA   # 임포트 시 multipool_cfg/meta/args·argv[1]로 초기화(동일 값)


def _sig(p):                       # 출처 v23_multi_analyze.py:83 (동일)
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"


def _block(rows, base):
    ai = [VMA.a2int(rows[p]) for p in base]
    corr = {}
    for lbl, fn in [("B1", VMA.b1m), ("C2", VMA.c2c), ("D1", VMA.d1a), ("E1_na_ga", VMA.e1ng)]:
        r, p = VMA.pearson(ai, [fn(rows[q]) for q in base])
        corr[lbl] = {"r": round(r, 2), "p": round(p, 3), "sig": _sig(p)}
    ens = VMA.ens_seg_delta(rows, base, cut=2)
    ens_out = {"delta_b1_mean": round(ens[0], 2), "sd": round(ens[1], 2), "seeds": ens[2]} if ens else None
    price = [VMA.lat[p]["가격민감"] for p in base]
    invo = [VMA.lat[p]["관여"] for p in base]
    rp, pp = VMA.pearson(price, [VMA.d1a(rows[q]) for q in base])
    ri, pi = VMA.pearson(invo, [VMA.wmean(rows[q]["E1_dist"], [0, 0, 0, 1]) for q in base])  # E1 둘다별로
    strong = {"price_sens_vs_D1": {"r": round(rp, 2), "p": round(pp, 3)},
              "involve_vs_E1last": {"r": round(ri, 2), "p": round(pi, 3)}}
    return {"n": len(base), "continuous_corr": corr, "seed_ensemble": ens_out, "strong_axes": strong}


def judge():
    rows = VMA.load()
    pools = sorted({p // 1000 for p in rows})
    result = {"run_id": VMA.RUNID, "N": len(rows), "sample_seed": VMA.SSEED, "pools": pools,
              "salt_source": "import v23_multi_analyze (동일 함수·SSEED·SALT_A2a·K_ENS)"}
    if not rows:
        result["empty"] = True
        return result

    per_pool = {}; all_t = []
    for k in pools:
        base = [p for p in rows if p // 1000 == k and VMA.meta[p]["is_target"]]
        per_pool[f"pool{k}"] = _block(rows, base)
        all_t += base
    result["per_pool"] = per_pool
    result["integrated"] = _block(rows, all_t)

    # 부호 일관성 — 원본과 동일( f"{r:+.2f}" 첫 글자 집합 )
    consistency = {}
    for lbl, fn in [("B1", VMA.b1m), ("C2", VMA.c2c), ("D1", VMA.d1a), ("E1_na_ga", VMA.e1ng)]:
        rs = []
        for k in pools:
            base = [p for p in rows if p // 1000 == k and VMA.meta[p]["is_target"]]
            r, _ = VMA.pearson([VMA.a2int(rows[p]) for p in base], [fn(rows[p]) for p in base])
            rs.append(r)
        sign_chars = {f"{r:+.2f}"[0] for r in rs}     # 출처 v23_multi_analyze.py:117
        consistency[lbl] = {"per_pool_r": [round(r, 2) for r in rs], "consistent": len(sign_chars) == 1}
    result["sign_consistency"] = consistency
    result["interpretation"] = [
        "통합 n으로 유의성 확정 = N증대 효과의 실증", "부호일관 = 풀-견고",
        "방향은 LLM prior(진실 아님) — 실측만이 최종"]
    return result


if __name__ == "__main__":
    print(json.dumps(judge(), ensure_ascii=False))
