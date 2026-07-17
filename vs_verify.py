# -*- coding: utf-8 -*-
"""VS 전면화 검증(엑셀 미생성): wf_vs_all 저널 → 문항별
   ⑴ 원분포 집계(49명 dist 합산 = 모델 믿음 질량, %)
   ⑵ 결정적 표집 realized 응답분포 — 강제단발선택 붕괴가 실제로 풀렸는지 확인.
   구 모델(강제선택)에서 0이던 보기(E1 비슷/둘다, B3 망설임없음 등)가 살아났는지 대조."""
import json, sys
from collections import Counter
import numpy as np

from harness_paths import SP
cfg = json.load(open(f"{SP}/run_cfg.json"))
SEED = cfg["RUN_SEED"]
from harness_paths import JOURNAL_BASE as BASE
RUNID = sys.argv[1]

OPTS = {
    "A1": ["팟타이 좋아함", "먹어봄·보통", "먹어봤지만 별로", "먹어본 적 없음"],
    "A2": ["①향신료향 부담", "②낯선 소스·재료", "③접근성 부족", "④가격 부담", "⑤단순 비선호", "⑥지금도 잘 먹음"],
    "B1": ["1점", "2점", "3점", "4점", "5점"],
    "B2": ["5분 완조리", "외식 대비 가성비", "국산 새우·숙주", "매실청 새콤함", "향신료 부담없음", "이유 없음"],
    "B3": ["맛 상상 안됨", "진짜 팟타이 아닐것", "냉동품질 불신", "가격 걱정", "양(300g) 부족", "팟타이 관심없음", "망설임 없음"],
    "C1": ["직접 만든다", "냉동/밀키트", "배달·외식", "안 먹거나 참음", "이런 맛 안찾음"],
    "C2": ["꼭 산다", "가끔 산다", "기존 방식 유지"],
    "E1": ["가(완성도)", "나(매실청)", "둘 다 비슷", "둘 다 안 끌림"],
}
SALT = {"A1": 40, "A2": 41, "B1": 1, "B2_1": 42, "B2_2": 43, "B3": 44, "C1": 2, "C2": 3, "E1": 60}


def load():
    rows = {}
    for line in open(f"{BASE}/{RUNID}/journal.jsonl", encoding="utf-8"):
        o = json.loads(line)
        r = o.get("result")
        if o.get("type") == "result" and isinstance(r, dict) and "E1_dist" in r:
            rows[r["pid"]] = r
    return rows


def pick(dist, opts, pid, salt):
    w = np.array([max(float(x), 0.0) for x in dist])
    if w.sum() <= 0:
        w = np.ones(len(opts))
    rng = np.random.default_rng([SEED, pid, salt])
    return opts[int(rng.choice(len(opts), p=w / w.sum()))]


def mass(rows, key):
    """49명 dist 합산 → % (모델 믿음 질량)."""
    n = len(OPTS[key])
    acc = np.zeros(n)
    for r in rows.values():
        d = np.array([max(float(x), 0.0) for x in r[f"{key}_dist"]], float)
        if d.sum() > 0:
            acc += d / d.sum()          # 페르소나당 동일가중
    return 100 * acc / acc.sum()


def realized(rows, key, salt):
    c = Counter()
    for pid, r in rows.items():
        c[pick(r[f"{key}_dist"], OPTS[key], pid, salt)] += 1
    return c


def bar(pct):
    return "█" * int(round(pct / 4))


def show(rows, key, salt):
    m = mass(rows, key)
    opts = OPTS[key]
    if key == "B2":
        rz = realized(rows, key, SALT["B2_1"])
    else:
        rz = realized(rows, key, salt)
    N = len(rows)
    print(f"\n── {key} ──  (믿음질량% | realized n/{N})")
    for i, o in enumerate(opts):
        rc = rz.get(o, 0)
        flag = "  ◀ 구모델 0" if (key == "E1" and i >= 2) or (key == "B3" and i == 6) else ""
        print(f"  {o:<16} {m[i]:5.1f}%  {bar(m[i]):<25} | {rc:2d}{flag}")


def d1_curve(rows):
    """VS 수용인원 → 단조 강제 → 임계 표집(map_and_ingest d1_from_curve 축약)."""
    D1P = [5900, 6900, 7500, 8500]
    acc = Counter()
    for pid, r in rows.items():
        p = [min(max(r[f"buy_{v}"] / 10.0, 0.0), 1.0) for v in D1P]
        for i in range(1, 4):
            p[i] = min(p[i], p[i - 1])
        bins = [1 - p[0], p[0] - p[1], p[1] - p[2], p[2] - p[3], p[3]]
        bins = [max(b, 0.0) for b in bins]
        s = sum(bins) or 1.0
        bins = [b / s for b in bins]
        rng = np.random.default_rng([SEED, pid, 51])
        k = int(rng.choice(5, p=bins))
        for i, v in enumerate(D1P):
            acc[v] += 1 if i < k else 0
    N = len(rows)
    print(f"\n── D1 수용곡선 (realized '산다' n/{N}) ──")
    prev = None
    for v in D1P:
        c = acc[v]
        mono = "" if prev is None or c <= prev else "  ⚠비단조"
        print(f"  {v:>5}원  {c:2d}/{N}  ({100*c//N}%)  {'█'*int(round(20*c/N))}{mono}")
        prev = c


def main():
    rows = load()
    print(f"VS 전면화 검증 — RUNID={RUNID}  N={len(rows)}  SEED={SEED}")
    if not rows:
        print("아직 결과 없음(워크플로 진행 중).")
        return
    for key in ["A1", "A2", "B1", "B2", "B3", "C1", "C2", "E1"]:
        show(rows, key, SALT.get(key, 0))
    d1_curve(rows)
    # 붕괴 해소 핵심 지표
    e1r = realized(rows, "E1", SALT["E1"])
    nb = e1r.get("둘 다 비슷", 0) + e1r.get("둘 다 안 끌림", 0)
    a2m = mass(rows, "A2")
    print("\n" + "=" * 52)
    print(f"[붕괴해소] E1 '비슷+둘다' realized = {nb}/{len(rows)}명 (구모델: 0명)")
    print(f"[유병률 미압박] A2 향부담(①②) 믿음질량 = {a2m[0]+a2m[1]:.1f}%  (강제선택 압축 없이)")
    print(f"[스프레드] 각 문항 realized 사용 보기수:")
    for key in ["A2", "B2", "B3", "C2", "E1"]:
        used = len(realized(rows, key, SALT.get(f"{key}_1", SALT.get(key, 0))))
        print(f"    {key}: {used}/{len(OPTS[key])} 보기 사용")


if __name__ == "__main__":
    main()
