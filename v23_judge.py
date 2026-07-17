# -*- coding: utf-8 -*-
"""v2.3 단일풀 판정 — 판정 계층 신규 파일(엔진 무수정), JSON을 stdout으로.

v23_analyze.py는 사람용 텍스트 출력이라 API 파싱에 부적합(취약한 텍스트 파싱 회피).
이 파일은 v23_analyze의 표집·통계 함수와 상수(SALT/SEED/pick/wmean/means/pearson/load/
is_target/옵션라벨)를 **그대로 import**해 동일 판정을 JSON으로 낸다 → 복사 divergence 0
(INVENTORY §4f salt 일치·재현 정합). main()의 인라인 판정 임계 리터럴만 출처 주석과 함께
동일 값 복사(임의변경 없음). 원본 v23_analyze.py는 무변경.

사용: python3 v23_judge.py <run_id>   (경로는 harness_paths 환경변수)
"""
import json
import statistics
from collections import Counter

import v23_analyze as VA   # 임포트 시 run_cfg/pool_meta/argv[1]로 모듈 초기화(동일 환경·값)

# ── v23_analyze.py main() 인라인 판정 임계(출처 주석·동일 값, 변경 금지) ──
SEG_B1_DELTA = 0.15      # 출처 v23_analyze.py:125-126
SEG_C2_DELTA = 0.03      # 출처 v23_analyze.py:125
DOSE_EPS = 0.01          # 출처 v23_analyze.py:152-153
T2_DOMINATE_FRAC = 0.15  # 출처 v23_analyze.py:167


def judge():
    rows = VA.load()
    SALT = VA.SALT
    result = {"run_id": VA.RUNID, "N": len(rows), "seed": VA.SEED,
              "salt_source": "import v23_analyze (동일 함수·SALT·SEED); 임계는 v23_analyze main() 인라인 동일 복사"}
    if not rows:
        result["empty"] = True
        return result

    tgt = [pid for pid in rows if VA.is_target(pid)]
    seg_ext = [pid for pid in rows if VA.meta[pid]["is_student_seg"]]
    result["base"] = {"target": len(tgt), "ext_seg": len(seg_ext), "total": len(rows)}
    result["discipline"] = "유병률'수준'은 latent앵커→신뢰X(실측 몫). 방향만 판독."

    # ── ⑴ A2 유병률(참고) ──
    prevalence = {}
    for label, base in [("1차대상", tgt), ("전체", list(rows))]:
        rs = [rows[p] for p in base]
        narrow = sum(1 for r in rs if VA.pick(r["A2a_dist"], 3, r["pid"], SALT["A2a"]) == 2) / len(rs)
        wide = sum(1 for r in rs if VA.pick(r["A2a_dist"], 3, r["pid"], SALT["A2a"]) >= 1) / len(rs)
        mass_wide = statistics.mean((r["A2a_dist"][1] + r["A2a_dist"][2]) / 10 for r in rs)
        prevalence[label] = {"n": len(rs), "narrow_pct": round(narrow * 100, 1),
                             "wide_pct": round(wide * 100, 1), "mass_wide_pct": round(mass_wide * 100, 1)}
    result["prevalence"] = {"data": prevalence, "band": [20, 48],
                            "note": "수준 신뢰X(latent앵커·실측 몫)"}

    # ── ⑵ 주판정: 매실청 깊이 세그 교차 ──
    base = tgt
    seg = []
    for cut_name, cut in [("협의(A2a=매우)", 2), ("광의(A2a≥조금)", 1)]:
        av = [p for p in base if VA.pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"]) >= cut]
        nv = [p for p in base if VA.pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"]) < cut]
        if not av or not nv:
            seg.append({"cut": cut_name, "verdict": "판정불가(한쪽 세그 빔)",
                        "hi_n": len(av), "lo_n": len(nv)})
            continue
        b1a = statistics.mean(VA.b1_mean(rows[p]) for p in av); b1n = statistics.mean(VA.b1_mean(rows[p]) for p in nv)
        c2a = statistics.mean(VA.c2_conv(rows[p]) for p in av); c2n = statistics.mean(VA.c2_conv(rows[p]) for p in nv)
        d1a = statistics.mean(VA.d1_acc(rows[p]) for p in av); d1n = statistics.mean(VA.d1_acc(rows[p]) for p in nv)
        verdict = "지지방향" if (b1a - b1n) > SEG_B1_DELTA and (c2a - c2n) > SEG_C2_DELTA else \
                  "평평(반증방향)" if abs(b1a - b1n) <= SEG_B1_DELTA else "혼조"
        seg.append({"cut": cut_name, "hi_n": len(av), "lo_n": len(nv),
                    "B1": {"hi": round(b1a, 2), "lo": round(b1n, 2), "delta": round(b1a - b1n, 2)},
                    "C2": {"hi": round(c2a, 2), "lo": round(c2n, 2), "delta": round(c2a - c2n, 2)},
                    "D1": {"hi_pct": round(d1a * 100), "lo_pct": round(d1n * 100),
                           "delta_pp": round((d1a - d1n) * 100)},
                    "verdict": verdict})
    result["segment_cross"] = seg

    # 연속상관(소표본 안정)
    ai = [VA.a2_intensity(rows[p]) for p in base]
    result["continuous_corr"] = {
        "B1": round(VA.pearson(ai, [VA.b1_mean(rows[p]) for p in base]), 2),
        "C2": round(VA.pearson(ai, [VA.c2_conv(rows[p]) for p in base]), 2),
        "D1": round(VA.pearson(ai, [VA.d1_acc(rows[p]) for p in base]), 2),
        "note": "A2a향부담강도 ↔ 반응"}

    # ── ⑶ dose-response ──
    grp = {0: [], 1: [], 2: []}
    for p in base:
        grp[VA.pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"])].append(p)
    groups = []; prevb = None; mono = True
    for k in [0, 1, 2]:
        g = grp[k]
        if not g:
            groups.append({"level": VA.A2c[k], "n": 0}); continue
        b = statistics.mean(VA.b1_mean(rows[p]) for p in g)
        c = statistics.mean(VA.c2_conv(rows[p]) for p in g)
        d = statistics.mean(VA.d1_acc(rows[p]) for p in g)
        if prevb is not None and b < prevb - DOSE_EPS:
            mono = False
        groups.append({"level": VA.A2c[k], "n": len(g), "B1": round(b, 2),
                       "C2": round(c, 2), "D1_pct": round(d * 100)})
        prevb = b
    result["dose_response"] = {"groups": groups, "b1_monotone": mono}

    # ── ⑷ 저커밋 · 진술≠행동 · A2x ──
    b3 = Counter(VA.B3O[VA.pick(rows[p]["B3_dist"], 7, p, SALT["B3"])] for p in base)
    yangmat = b3["양 부족"] + b3["맛 상상 안됨"]; price = b3["가격 걱정"]
    result["low_commitment"] = {"yang_mat": yangmat, "price": price,
                                "verdict": "양·맛 우위(지지)" if yangmat > price else "가격 우위(반증)"}
    e1 = Counter(VA.E1O[VA.pick(rows[p]["E1_dist"], 4, p, SALT["E1"])] for p in base)
    na, ga = e1["나(매실청)"], e1["가(완성도)"]; mush = e1["비슷"] + e1["둘 다 별로"]
    result["statement_vs_behavior"] = {
        "na": na, "ga": ga, "mush": mush,
        "verdict": "T2압도(행동일치·층철회방향)" if na > ga + len(base) * T2_DOMINATE_FRAC
                   else "뭉갬/표본민감(진술≠행동 지지)"}
    ax_yes = [p for p in base if VA.pick(rows[p]["A2x_dist"], 2, p, SALT["A2x"]) == 0]
    ax_no = [p for p in base if VA.pick(rows[p]["A2x_dist"], 2, p, SALT["A2x"]) == 1]
    if ax_yes and ax_no:
        iy = statistics.mean(VA.a2_intensity(rows[p]) for p in ax_yes)
        ino = statistics.mean(VA.a2_intensity(rows[p]) for p in ax_no)
        result["a2x_validity"] = {"yes_n": len(ax_yes), "no_n": len(ax_no),
                                  "intensity_yes": round(iy, 2), "intensity_no": round(ino, 2),
                                  "verdict": "앵커 정상(예가 낮음)" if iy < ino else "⚠앵커 역전"}
    else:
        result["a2x_validity"] = None

    # ── 한계(동질성 잔존) ──
    homog = {}
    for k in ["B1_dist", "C2_dist", "E1_dist"]:
        c = Counter(tuple(rows[p][k]) for p in base)
        homog[k] = round(c.most_common(1)[0][1] / len(base) * 100) if base else None
    result["homogeneity_residual"] = homog
    result["caveats"] = [
        "세그교차/상관 방향은 A2a와 B/C/D가 같은 향기피 latent서 파생된 LLM prior(측정 아님).",
        "문항에코(동어반복)는 v2가 제거했으나 sim의 latent공유 상관은 실측만 분리 가능.",
    ]
    return result


if __name__ == "__main__":
    print(json.dumps(judge(), ensure_ascii=False))
