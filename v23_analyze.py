# -*- coding: utf-8 -*-
"""v2.3 파일럿 시뮬 판정(엑셀 미생성).
   향기피(A2a·원인)와 제품반응(B1/C2/D1·결과)을 별도 문항서 재고 상관을 사후에 본다.
   ⑴ A2 유병률(협의/광의) — latent앵커라 '수준'은 신뢰X(실측 몫), 참고만.
   ⑵ 주판정: 매실청 깊이 = 향기피 세그 vs 비기피 B1/C2/D1 대비 (비순환).
   ⑶ 날카로운 판정: A2a 강도(아니다/조금/매우) → 반응 단조(dose-response).
   ⑷ 저커밋(B3 양·맛 vs 가격), 진술≠행동(E1), A2x 타당도.
   방향(부호)은 프롬프트에 미주입 → 나오는 방향은 'LLM prior'(측정 아님)."""
import json, sys, statistics
from collections import Counter
import numpy as np

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
cfg = json.load(open(f"{SP}/run_cfg.json"))
SEED = cfg["RUN_SEED"]
BASE = "/root/.claude/projects/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/subagents/workflows"
RUNID = sys.argv[1]
meta = {m["pid"]: m for m in json.load(open(f"{SP}/pool_meta.json"))}

A2c = ["아니다", "조금", "매우"]
B2O = ["5분 완조리", "외식 대비 가성비", "국산 새우·숙주", "매실청 새콤함", "이유 없음"]
B3O = ["맛 상상 안됨", "진짜 팟타이 아닐것", "냉동품질 불신", "가격 걱정", "양 부족", "팟타이 관심없음", "없음"]
C2O = ["꼭 산다", "가끔 산다", "기존 유지"]
E1O = ["가(완성도)", "나(매실청)", "비슷", "둘 다 별로"]
SALT = {"A1": 40, "A2a": 41, "A2b": 42, "A2c": 43, "A2d": 44, "A2x": 45,
        "B1": 1, "B2": 46, "B3": 47, "C1": 2, "C2": 3, "E1": 60}
D1P = [5900, 6900, 7500, 8500]


def load():
    rows = {}
    for l in open(f"{BASE}/{RUNID}/journal.jsonl", encoding="utf-8"):
        o = json.loads(l); r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
            rows[r["pid"]] = r
    return rows


def pick(dist, n, pid, salt):
    w = np.array([max(float(x), 0.0) for x in dist])
    if w.sum() <= 0:
        w = np.ones(n)
    rng = np.random.default_rng([SEED, pid, salt])
    return int(rng.choice(n, p=w / w.sum()))


def wmean(dist, vals):
    w = np.array([max(float(x), 0.0) for x in dist]); s = w.sum() or 1.0
    return float(np.dot(w, vals) / s)


def a2_intensity(r):          # 0..1 연속 향부담 강도(믿음질량 가중)
    return wmean(r["A2a_dist"], [0, 0.5, 1.0])


def b1_mean(r):
    return wmean(r["B1_dist"], [1, 2, 3, 4, 5])


def c2_conv(r):               # 전환성향 0..1 (꼭=1, 가끔=0.5)
    return wmean(r["C2_dist"], [1.0, 0.5, 0.0])


def d1_acc(r):                # 가격수용 0..1 (4가격 평균 인원/10)
    return statistics.mean(r[f"buy_{v}"] for v in D1P) / 10.0


def d1_curve_sample(r, pid):  # 단조 임계 표집 → '산다' 벡터
    p = [min(max(r[f"buy_{v}"] / 10.0, 0.0), 1.0) for v in D1P]
    for i in range(1, 4):
        p[i] = min(p[i], p[i - 1])
    bins = [1 - p[0], p[0] - p[1], p[1] - p[2], p[2] - p[3], p[3]]
    bins = [max(b, 0.0) for b in bins]; s = sum(bins) or 1.0
    rng = np.random.default_rng([SEED, pid, 51])
    k = int(rng.choice(5, p=[b / s for b in bins]))
    return [1 if i < k else 0 for i in range(4)]


def pearson(xs, ys):
    if len(xs) < 3:
        return 0.0
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** .5
    dy = (sum((y - my) ** 2 for y in ys)) ** .5
    return num / (dx * dy) if dx * dy else 0.0


def is_target(pid):
    return meta[pid]["is_target"]      # S3①②·S4②~④ (v2.3 1차대상 core, B4 별도)


def main():
    rows = load()
    print(f"════ v2.3 파일럿 시뮬 판정  RUNID={RUNID}  N={len(rows)}  SEED={SEED} ════")
    if not rows:
        print("결과 없음(진행 중).")
        return
    tgt = [pid for pid in rows if is_target(pid)]
    seg_ext = [pid for pid in rows if meta[pid]["is_student_seg"]]
    print(f"1차 대상(S3①②·S4②~④)={len(tgt)}  확장세그={len(seg_ext)}  전체={len(rows)}")
    print("[규율] 유병률'수준'은 latent앵커→신뢰X(실측 몫). 여기선 '방향'만 판독.\n")

    # ── ⑴ A2 유병률(참고) ──
    print("── ⑴ A2 향부담(a) 유병률 [참고·수준신뢰X] ──")
    for label, base in [("1차대상", tgt), ("전체", list(rows))]:
        rs = [rows[p] for p in base]
        narrow = sum(1 for r in rs if pick(r["A2a_dist"], 3, r["pid"], SALT["A2a"]) == 2) / len(rs)
        wide = sum(1 for r in rs if pick(r["A2a_dist"], 3, r["pid"], SALT["A2a"]) >= 1) / len(rs)
        mass_wide = statistics.mean((r["A2a_dist"][1] + r["A2a_dist"][2]) / 10 for r in rs)
        print(f"  {label}(n={len(rs)}): 협의(매우만)={narrow*100:.0f}%  광의(조금+매우)={wide*100:.0f}%  "
              f"광의믿음질량={mass_wide*100:.0f}%  (밴드 20~48% 대조)")

    # ── ⑵ 주판정: 매실청 깊이 세그 교차 ──
    print("\n── ⑵ 주판정: 매실청 깊이 = 향기피 세그 vs 비기피 (비순환) ──")
    base = tgt
    for cut_name, cut in [("협의(A2a=매우)", 2), ("광의(A2a≥조금)", 1)]:
        av = [p for p in base if pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"]) >= cut]
        nv = [p for p in base if pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"]) < cut]
        if not av or not nv:
            print(f"  {cut_name}: 한쪽 세그 비어 판정불가(av={len(av)},nv={len(nv)})"); continue
        b1a = statistics.mean(b1_mean(rows[p]) for p in av); b1n = statistics.mean(b1_mean(rows[p]) for p in nv)
        c2a = statistics.mean(c2_conv(rows[p]) for p in av); c2n = statistics.mean(c2_conv(rows[p]) for p in nv)
        d1a = statistics.mean(d1_acc(rows[p]) for p in av); d1n = statistics.mean(d1_acc(rows[p]) for p in nv)
        verdict = "지지방향" if (b1a - b1n) > 0.15 and (c2a - c2n) > 0.03 else \
                  "평평(반증방향)" if abs(b1a - b1n) <= 0.15 else "혼조"
        print(f"  [{cut_name}] 향기피={len(av)} vs 비기피={len(nv)}")
        print(f"     B1첫인상: {b1a:.2f} vs {b1n:.2f}  Δ={b1a-b1n:+.2f}")
        print(f"     C2전환성향: {c2a:.2f} vs {c2n:.2f}  Δ={c2a-c2n:+.2f}")
        print(f"     D1수용: {d1a*100:.0f}% vs {d1n*100:.0f}%  Δ={(d1a-d1n)*100:+.0f}%p  → {verdict}")

    # 연속 상관(소표본 안정): A2a강도 ↔ 반응
    ai = [a2_intensity(rows[p]) for p in base]
    print("  [연속상관·소표본안정] A2a향부담강도 ↔")
    print(f"     B1: r={pearson(ai,[b1_mean(rows[p]) for p in base]):+.2f}   "
          f"C2전환: r={pearson(ai,[c2_conv(rows[p]) for p in base]):+.2f}   "
          f"D1수용: r={pearson(ai,[d1_acc(rows[p]) for p in base]):+.2f}")

    # ── ⑶ 날카로운 판정: dose-response ──
    print("\n── ⑶ dose-response: A2a 강도 3단 → 반응 단조성 ──")
    grp = {0: [], 1: [], 2: []}
    for p in base:
        grp[pick(rows[p]["A2a_dist"], 3, p, SALT["A2a"])].append(p)
    prevb = None; mono = True
    for k in [0, 1, 2]:
        g = grp[k]
        if not g:
            print(f"  {A2c[k]:<4}: n=0"); continue
        b = statistics.mean(b1_mean(rows[p]) for p in g)
        c = statistics.mean(c2_conv(rows[p]) for p in g)
        d = statistics.mean(d1_acc(rows[p]) for p in g)
        arrow = "" if prevb is None else (" ↑" if b >= prevb - 0.01 else " ↓(비단조)")
        if prevb is not None and b < prevb - 0.01:
            mono = False
        print(f"  {A2c[k]:<4}(n={len(g):2d}): B1={b:.2f}{arrow}  C2전환={c:.2f}  D1수용={d*100:.0f}%")
        prevb = b
    print(f"  → B1 단조상승? {'예(dose-response 성립)' if mono else '아니오(단조 아님)'}")

    # ── ⑷ 저커밋 · 진술≠행동 · A2x 타당도 ──
    print("\n── ⑷ 저커밋 / 진술≠행동 / A2x 타당도 ──")
    b3 = Counter(B3O[pick(rows[p]["B3_dist"], 7, p, SALT["B3"])] for p in base)
    yangmat = b3["양 부족"] + b3["맛 상상 안됨"]; price = b3["가격 걱정"]
    print(f"  저커밋 B3: 양+맛={yangmat} vs 가격={price}  → {'양·맛 우위(지지)' if yangmat>price else '가격 우위(반증)'}")
    e1 = Counter(E1O[pick(rows[p]["E1_dist"], 4, p, SALT["E1"])] for p in base)
    na, ga = e1["나(매실청)"], e1["가(완성도)"]; mush = e1["비슷"] + e1["둘 다 별로"]
    print(f"  진술 E1: 나(T2)={na} 가(T1)={ga} 뭉갬(비슷+별로)={mush}  → "
          f"{'T2압도(행동일치·층철회방향)' if na>ga+len(base)*0.15 else '뭉갬/표본민감(진술≠행동 지지)'}")
    # A2x 타당도: 예(지금도 잘먹음)면 A2a 향부담 낮아야
    ax_yes = [p for p in base if pick(rows[p]["A2x_dist"], 2, p, SALT["A2x"]) == 0]
    ax_no = [p for p in base if pick(rows[p]["A2x_dist"], 2, p, SALT["A2x"]) == 1]
    if ax_yes and ax_no:
        iy = statistics.mean(a2_intensity(rows[p]) for p in ax_yes)
        ino = statistics.mean(a2_intensity(rows[p]) for p in ax_no)
        print(f"  A2x 타당도: '지금도잘먹음=예'({len(ax_yes)})의 향부담강도 {iy:.2f} vs '아니오'({len(ax_no)}) {ino:.2f}  "
              f"→ {'앵커 정상(예가 낮음)' if iy < ino else '⚠앵커 역전'}")

    # ── 한계 노출 ──
    print("\n── 드러난 한계 ──")
    # 세그교차 상관이 곧 latent라는 점(순환 아님이나 prior임) 정량화
    print("  · 세그교차/상관의 방향은 A2a와 B/C/D가 같은 향기피 latent서 파생된 'LLM prior'.")
    print("    문항에코(동어반복)는 v2가 제거했으나, sim의 latent공유 상관은 실측만 분리 가능.")
    # 동질성 잔존
    for k in ["B1_dist", "C2_dist", "E1_dist"]:
        c = Counter(tuple(rows[p][k]) for p in base)
        print(f"  · {k} 최빈패턴 점유 {c.most_common(1)[0][1]/len(base)*100:.0f}% (동질성 잔존도)")


if __name__ == "__main__":
    main()
