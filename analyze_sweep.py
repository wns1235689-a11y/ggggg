# -*- coding: utf-8 -*-
"""
사전분포 스윕 결과 분석 — 4개 상반 인구(cfg)별로 가설 방향을 산출하고
robust(전 인구에서 동일 부호) vs fragile(뒤집힘)로 분류.
입력: 스윕 설문 워크플로 journal.jsonl (pid 보존) + sweep_meta.json(pid→cfg)
"""
import json, sys
from collections import Counter, defaultdict

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
JOURNAL = sys.argv[1] if len(sys.argv) > 1 else None

meta = json.load(open(f"{SP}/sweep_meta.json"))
pid2cfg = {int(k): v for k, v in meta["meta"].items()}
names = {int(k): v for k, v in meta["names"].items()}

# ── journal에서 결과 회수(pid 기준 최신) ──
res = {}
for line in open(JOURNAL, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    o = json.loads(line)
    if o.get("type") == "result" and isinstance(o.get("result"), dict) and "pid" in o["result"]:
        r = o["result"]
        res[r["pid"]] = r

print(f"회수 응답 {len(res)} / 예상 {len(pid2cfg)}")
missing = sorted(set(pid2cfg) - set(res))
if missing:
    print(f"미회수 pid({len(missing)}):", missing[:20], "..." if len(missing) > 20 else "")

# ── 선택지 계열 매핑 ──
A2_ACCESS = "먹을 기회나 파는 곳이 마땅치 않아서"   # 접근성 장벽
A2_SPICE = "고수 등 향신료 향이 부담스러워서"       # 향 기피
# B2 포지셔닝 축
B2_T1 = {"5분 완조리(간편함)", "외식 대비 가성비"}          # 완성도(가) 축
B2_T2 = {"매실청의 새콤한 맛", "향신료(고수 등) 부담 없음"}  # 매실청(나) 축
C2_BUY = {"꼭 산다", "상황 보고 가끔 산다"}

by = defaultdict(list)
for pid, r in res.items():
    by[pid2cfg[pid]].append(r)

def pct(sub, pred):
    n = len(sub)
    return 100.0 * sum(1 for r in sub if pred(r)) / n if n else 0.0

rows = []
for cfg in sorted(by):
    sub = by[cfg]
    n = len(sub)
    # A2: 접근성 vs 향기피 (전체 응답 중, '잘 먹는다' 포함 분모)
    a2_access = pct(sub, lambda r: r["A2"] == A2_ACCESS)
    a2_spice = pct(sub, lambda r: r["A2"] == A2_SPICE)
    # B2 1순위 축
    b2_t1 = pct(sub, lambda r: r["B2_1"] in B2_T1)
    b2_t2 = pct(sub, lambda r: r["B2_1"] in B2_T2)
    # E1
    e1 = Counter(r["E1"] for r in sub)
    e1_ga = 100.0 * e1.get("가", 0) / n
    e1_na = 100.0 * e1.get("나", 0) / n
    # B1 평균
    b1 = sum(r["B1"] for r in sub) / n
    # C2 구매의향
    c2_buy = pct(sub, lambda r: r["C2"] in C2_BUY)
    c2_strong = pct(sub, lambda r: r["C2"] == "꼭 산다")
    # D1 5900 수용
    d1_59 = pct(sub, lambda r: r.get("D1_5900") == "산다")
    d1_69 = pct(sub, lambda r: r.get("D1_6900") == "산다")
    rows.append(dict(cfg=cfg, name=names[cfg], n=n,
                     a2_access=a2_access, a2_spice=a2_spice,
                     b2_t1=b2_t1, b2_t2=b2_t2, e1_ga=e1_ga, e1_na=e1_na,
                     b1=b1, c2_buy=c2_buy, c2_strong=c2_strong,
                     d1_59=d1_59, d1_69=d1_69))

print("\n=== 인구별 지표 ===")
hdr = f"{'cfg':>3} {'인구':<8} {'N':>3} | A2접근:향기피 | B2 완성도:매실청 | E1 가:나 | B1 | C2구매% | D1_59%"
print(hdr)
for r in rows:
    print(f"{r['cfg']:>3} {r['name']:<8} {r['n']:>3} | "
          f"{r['a2_access']:4.0f}:{r['a2_spice']:<4.0f} | "
          f"{r['b2_t1']:4.0f}:{r['b2_t2']:<4.0f} | "
          f"{r['e1_ga']:3.0f}:{r['e1_na']:<3.0f} | {r['b1']:.2f} | "
          f"{r['c2_buy']:4.0f} | {r['d1_59']:4.0f}")

# ── robust/fragile 판별 ──
def classify(name, values, label_pos, label_neg):
    """values: cfg별 (pos-neg) 부호. 전부 같은 부호면 robust."""
    signs = [1 if v > 3 else (-1 if v < -3 else 0) for v in values]  # ±3%p 데드존
    nonzero = [s for s in signs if s != 0]
    if not nonzero:
        verdict = "무방향(평탄)"
    elif all(s > 0 for s in nonzero) and len(nonzero) >= 3:
        verdict = f"ROBUST → {label_pos}"
    elif all(s < 0 for s in nonzero) and len(nonzero) >= 3:
        verdict = f"ROBUST → {label_neg}"
    else:
        verdict = "FRAGILE(뒤집힘)"
    detail = " ".join(f"{v:+.0f}" for v in values)
    return f"{name:<20} [{detail}]  {verdict}"

print("\n=== 방향 판별 (cfg0매실청 cfg1완성도 cfg2저접근 cfg3평탄 순, +는 앞항목 우세) ===")
print(classify("A2 접근성vs향기피", [r["a2_access"] - r["a2_spice"] for r in rows],
               "접근성 우세", "향기피 우세"))
print(classify("B2 완성도vs매실청", [r["b2_t1"] - r["b2_t2"] for r in rows],
               "완성도(가) 우세", "매실청(나) 우세"))
print(classify("E1 가vs나", [r["e1_ga"] - r["e1_na"] for r in rows],
               "완성도헤드라인(가)", "매실청헤드라인(나)"))
print(classify("C2 구매vs유지", [r["c2_buy"] - (100 - r["c2_buy"]) for r in rows],
               "구매의향 우세", "기존유지 우세"))

json.dump(rows, open(f"{SP}/sweep_analysis.json", "w"), ensure_ascii=False, indent=1)
print(f"\nsweep_analysis.json 저장")
