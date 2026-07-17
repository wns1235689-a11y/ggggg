# -*- coding: utf-8 -*-
"""동질성 저감 전/후 대조: 두 wf_vs_all 저널(구=low, 신=medium)에서
   ⑴ 페르소나간 분포 다양성(서로다른 패턴수·최빈점유)
   ⑵ 특성→응답 방향 대비(향기피·가격민감·관여 등)
   을 나란히 출력. 방향은 프롬프트에 심지 않았으므로 '모델이 스스로 만든 대비'."""
import json, sys, statistics
from collections import Counter

from harness_paths import JOURNAL_BASE as BASE
OLD, NEW = sys.argv[1], sys.argv[2]
_poolfile = sys.argv[3]  # 풀 파일(prof.json 또는 multipool_args.json 형식: pid+latent 리스트) — args_dump.txt 의존 제거(P0-6)
cat = json.load(open(_poolfile))
TR = {p['pid']: p for p in cat}   # pid → 특성


def load(runid):
    rows = {}
    for l in open(f"{BASE}/{runid}/journal.jsonl", encoding="utf-8"):
        o = json.loads(l); r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "E1_dist" in r:
            rows[r["pid"]] = r
    return rows


def diversity(rows, key):
    c = Counter(tuple(r[key]) for r in rows.values())
    modal = c.most_common(1)[0][1] / len(rows) * 100
    return len(c), modal


def contrast(rows, trait, hi_th, lo_th, dist_key, idx_pos, idx_neg=None):
    """특성 상/하위 그룹에서 dist의 (pos - neg) 평균 대비. neg=None이면 pos만."""
    hi = [r for r in rows.values() if TR[r['pid']][trait] >= hi_th]
    lo = [r for r in rows.values() if TR[r['pid']][trait] <= lo_th]

    def val(g):
        if not g:
            return 0.0
        if idx_neg is None:
            return statistics.mean(r[dist_key][idx_pos] for r in g)
        return statistics.mean(r[dist_key][idx_pos] - r[dist_key][idx_neg] for r in g)
    return val(hi), val(lo), len(hi), len(lo)


def report(tag, rows):
    print(f"\n【{tag}】 N={len(rows)}")
    print("  페르소나간 분포 다양성(서로다른 패턴수/최빈점유%):")
    for k in ['B1_dist', 'B2_dist', 'B3_dist', 'C1_dist', 'C2_dist', 'E1_dist', 'A2_dist']:
        n, m = diversity(rows, k)
        print(f"    {k:9s}: {n:2d}패턴  최빈 {m:4.0f}%")


def contrasts(tag, rows):
    print(f"\n【{tag}】 특성→응답 방향 대비(높을수록 대비 큼):")
    # 향기피 高 vs 低 : E1 나(1)-가(0)  /  A2 향부담①(0)
    a, b, na, nb = contrast(rows, '향기피', 0.55, 0.30, 'E1_dist', 1, 0)
    print(f"    향기피[高{na}/低{nb}] E1 (나-가): {a:+.2f} vs {b:+.2f}   Δ={a-b:+.2f}")
    a, b, na, nb = contrast(rows, '향기피', 0.55, 0.30, 'A2_dist', 0)
    print(f"    향기피[高{na}/低{nb}] A2 ①향부담 인원: {a:.2f} vs {b:.2f}   Δ={a-b:+.2f}")
    # 가격민감 高 vs 低 : buy_8500 수용  /  B3 가격걱정(3)
    a, b, na, nb = contrast(rows, '가격민감', 0.60, 0.35, 'B3_dist', 3)
    print(f"    가격민감[高{na}/低{nb}] B3 가격걱정 인원: {a:.2f} vs {b:.2f}   Δ={a-b:+.2f}")
    # 관여 高 vs 低 : E1 둘다안끌림(3) (관여낮으면 무관심↑ 예상)
    a, b, na, nb = contrast(rows, '관여', 0.60, 0.35, 'E1_dist', 3)
    print(f"    관여[高{na}/低{nb}] E1 둘다안끌림 인원: {a:.2f} vs {b:.2f}   Δ={a-b:+.2f}")
    # 회의 高 vs 低 : C2 기존유지(2)
    a, b, na, nb = contrast(rows, '회의', 0.55, 0.30, 'C2_dist', 2)
    print(f"    회의[高{na}/低{nb}] C2 기존유지 인원: {a:.2f} vs {b:.2f}   Δ={a-b:+.2f}")
    # buy_8500 가격민감
    hi = [r for r in rows.values() if TR[r['pid']]['가격민감'] >= 0.60]
    lo = [r for r in rows.values() if TR[r['pid']]['가격민감'] <= 0.35]
    ah = statistics.mean(r['buy_8500'] for r in hi) if hi else 0
    al = statistics.mean(r['buy_8500'] for r in lo) if lo else 0
    print(f"    가격민감[高{len(hi)}/低{len(lo)}] buy_8500 수용: {ah:.2f} vs {al:.2f}   Δ={ah-al:+.2f} (高가 낮아야 정상)")


def main():
    old, new = load(OLD), load(NEW)
    print("=" * 60)
    print(f"동질성 저감 대조   구(low)={OLD}   신(medium)={NEW}")
    report("구 low", old)
    report("신 medium", new)
    contrasts("구 low", old)
    contrasts("신 medium", new)
    print("\n" + "=" * 60)
    print("해석: 패턴수↑·최빈점유↓ = 페르소나 개인화↑(동질성↓).")
    print("      Δ의 절댓값↑ = 특성→응답 방향 대비↑(방향성 판독력↑).")
    print("      방향(부호)은 프롬프트에 심지 않음 → 모델 자체 추론.")


if __name__ == "__main__":
    main()
