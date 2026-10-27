#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""해외 패널 설문 v1.1 §8 리허설 엔진 lite — 진단(판정 없음).

문서 §8 '보는 것' ①~⑥만 본다:
  ① Q5 자유 해석에서 maesil·cilantro 등 어휘를 모른다는 반응 비율(콘셉트 이해)
  ② Q3 'A little' 쏠림(게이트 C '조금' 함정 재발 여부)
  ③ Q2a 'Other' 비율(선택지 누락)
  ④ Q6 바닥·천장($4.99 전원 Yes / $7.99 전원 No)
  ⑤ Q3 → Q5 일관성 압력(기록만)
  ⑥ Q7 자유응답이 Q5 문장을 되풀이하는지(문항 에코, 기록만)
고치는 기준(①~④)은 아래 THRESH에 적어 두고 결과를 보고 바꾸지 않는다.

사용: python3 us_lite_diagnose.py <run_id> [--out <md 경로>]
입력: HARNESS_JOURNAL_BASE/<run_id>/journal.jsonl (없으면 runs/<run_id>/journal.jsonl[.gz]),
      runs/<run_id>/{prof.json, run_cfg.json} (persist_run 뒤) 또는 --pool-id.
"""
import argparse, gzip, json, os, re, statistics, sys
from collections import Counter
import numpy as np

import harness_paths as H

WARNING = """## ⓪ 문서 지위 · 필수 경고
**LLM 합성 응답 · 비실측 · 인용 불가.** 이 문서는 설문 문항의 함정·어휘 이해·선택지 누락·가격 사다리 위치를
발행 전에 점검하는 **진단 전용** 산출물이다. 여기의 어떤 비율도 미국 소비자의 실제 비율이 아니며 PT 어디에도 쓰지 않는다
(해외 패널 설문 v1.1 §8 규칙). 페르소나 사전분포는 전부 [규범근사]이고 실측 앵커가 없다.
"""

Q1O = ["Never", "A few times a year", "About once a month", "A few times a month", "Once a week or more"]
Q2O = ["Yes, more than once", "Yes, once or twice", "No, never"]
Q2aO = ["Hard to find ingredients", "Don't know how / complicated", "Too much time or effort",
        "Don't like the taste", "Rather restaurant / delivery", "Other"]
Q3O = ["Yes, very much", "Yes, a little", "No"]
Q4O = ["Yes", "No", "Not sure"]
Q5O = ["1 Not at all", "2", "3", "4", "5 Very interested"]
Q8O = ["Yes, and I know Bibigo", "Had Korean food, don't know brands", "No"]
PRICES = [499, 599, 699, 799]
SALT = {"Q1": 70, "Q2": 71, "Q2a": 72, "Q3": 73, "Q4": 74, "Q5": 75, "Q6": 76, "Q8": 78}

# 고치는 기준(사전 고정) — 걸리면 문항을 고치고 발행(①~④). ⑤⑥은 기록만.
THRESH = {
    "①_term_unclear_share": 0.25,   # 한 어휘를 '모르겠다'로 꼽은 페르소나 비율 ≥ 25% → 설명(괄호 풀이) 추가 검토
    "②_a_little_mass": 0.50,        # Q3 'A little' 믿음질량 ≥ 50% → '조금' 함정 재발
    "③_other_share": 0.10,          # Q2a 'Other' 질량 ≥ 10% → 선택지 누락
    "④_floor_yes_499": 0.90,        # $4.99 Yes ≥ 90% → 바닥이 너무 낮음(사다리 위로)
    "④_ceiling_yes_799": 0.10,      # $7.99 Yes ≤ 10% → 천장이 너무 높음(사다리 아래로)
}
CONCEPT = ("A single-serving frozen pad thai you heat in the microwave for 5 minutes. Instead of tamarind, "
           "the sauce uses Korean green plum syrup (maesil), and there is no cilantro, so the flavor is milder "
           "and easier for people who find Thai dishes too strong, or who are trying pad thai for the first time.")
TERMS = {
    "maesil": r"\bmaesil\b", "green plum syrup": r"plum\s*syrup|green\s*plum", "tamarind": r"\btamarind\b",
    "cilantro": r"\bcilantro\b", "pad thai": r"\bpad\s*thai\b", "single-serving": r"single[-\s]serving",
    "fish sauce": r"fish\s*sauce", "coriander": r"\bcoriander\b",
}
STOP = set("a an the and or of to in for is are it its this that with you who people too so at on by be as from "
           "would i my me not no if".split())


def load_rows(run_id):
    cands = [os.path.join(H.JOURNAL_BASE, run_id, "journal.jsonl"),
             os.path.join(H.run_dir(run_id), "journal.jsonl"), os.path.join(H.run_dir(run_id), "journal.jsonl.gz")]
    for p in cands:
        if os.path.exists(p):
            opener = gzip.open if p.endswith(".gz") else open
            rows = {}
            with opener(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    r = o.get("result")
                    if o.get("type") == "result" and isinstance(r, dict) and "Q3_dist" in r:
                        rows[int(r["pid"])] = r
            return rows, p
    raise SystemExit(f"[diagnose] 저널 없음: {cands}")


def load_pool(run_id, pool_id):
    for base in ([H.run_dir(pool_id)] if pool_id else []) + [H.run_dir(run_id), H.SP]:
        pp, cp = os.path.join(base, "prof.json"), os.path.join(base, "run_cfg.json")
        if os.path.exists(pp) and os.path.exists(cp):
            cfg = json.load(open(cp))
            if cfg.get("pool_kind") == "us_lite":
                return {int(p["pid"]): p for p in json.load(open(pp))}, cfg, base
    raise SystemExit("[diagnose] us_lite 풀(prof.json+run_cfg.json) 없음 — persist_run 뒤 실행하거나 --pool-id 지정")


def norm(dist):
    w = np.array([max(float(x), 0.0) for x in dist], float)
    return w / w.sum() if w.sum() > 0 else None


def mass(rows, key, n):
    acc = np.zeros(n); k = 0
    for r in rows.values():
        w = norm(r[key])
        if w is not None:
            acc += w; k += 1
    return 100 * acc / max(k, 1)


def pick(dist, n, pid, salt, seed):
    w = norm(dist)
    if w is None:
        w = np.ones(n) / n
    return int(np.random.default_rng([seed, pid, salt]).choice(n, p=w))


def realized(rows, key, opts, salt, seed):
    c = Counter()
    for pid, r in rows.items():
        c[opts[pick(r[key], len(opts), pid, salt, seed)]] += 1
    return c


def bar(pct):
    return "█" * int(round(pct / 4))


def table(rows, key, opts, salt, seed, out, note=""):
    m = mass(rows, key, len(opts)); rz = realized(rows, key, opts, salt, seed); N = len(rows)
    out.append(f"\n**{key}** {note} (믿음질량% | realized n/{N})\n")
    out.append("| 보기 | 믿음질량 | | realized |\n|---|---:|---|---:|")
    for i, o in enumerate(opts):
        out.append(f"| {o} | {m[i]:.1f}% | {bar(m[i])} | {rz.get(o, 0)} |")
    return m


def words(s):
    return [w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP and len(w) > 2]


def ngrams(ws, n):
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id"); ap.add_argument("--pool-id", default=None); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows, jpath = load_rows(a.run_id)
    pool, cfg, pbase = load_pool(a.run_id, a.pool_id)
    SEED = cfg["RUN_SEED"]; N = len(rows)
    out = [f"# 해외 패널 설문 v1.1 §8 리허설 엔진 lite — 진단 (run {a.run_id})\n", WARNING,
           f"- 저널: `{jpath}`  · 풀: `{pbase}` (RUN_SEED={SEED}, N(풀)={cfg['N']}) · 결과 회수 {N}명\n"
           f"- 형식: 한 페르소나(에이전트 1개)가 '비슷한 미국 소비자 10명'의 분포를 추정(VS) + 본인 자유응답. "
           f"realized = 시드 결정론 표집(1인 1표). 판정 없음, 진단만.\n"]
    if not rows:
        print("결과 없음"); return
    flags = []

    # ── 분포 전체(참고) ──
    out.append("\n## 1. 문항별 분포(참고 — 수준 인용 금지)\n")
    table(rows, "Q1_dist", Q1O, SALT["Q1"], SEED, out, "태국·동남아 음식 빈도")
    table(rows, "Q2_dist", Q2O, SALT["Q2"], SEED, out, "집에서 팟타이 조리 경험")
    m2a = table(rows, "Q2a_dist", Q2aO, SALT["Q2a"], SEED, out, "못 만드는 이유(Q2 비해당자 분모)")
    m3 = table(rows, "Q3_dist", Q3O, SALT["Q3"], SEED, out, "향·소스·향신료 때문에 피함(게이트 C 향기피 3점 대응)")
    m4 = table(rows, "Q4_dist", Q4O, SALT["Q4"], SEED, out, "최근 12개월 냉동 태국 음식 구매")
    m5 = table(rows, "Q5_dist", Q5O, SALT["Q5"], SEED, out, "콘셉트 관심")
    m8 = table(rows, "Q8_dist", Q8O, SALT["Q8"], SEED, out, "한식·Bibigo 인지")

    # ── ① 어휘 이해 ──
    out.append("\n## 2. 진단 ① Q5 어휘 이해 — 'unclear' 로 꼽힌 어휘(페르소나 비율)\n")
    tc = Counter(); reading_flags = 0; examples = []
    for pid, r in rows.items():
        hit = set()
        for t in r.get("Q5_unclear_terms", []):
            tl = t.lower()
            for name, rx in TERMS.items():
                if re.search(rx, tl):
                    hit.add(name)
            if not any(re.search(rx, tl) for rx in TERMS.values()):
                hit.add(f"other: {t.strip()[:40]}")
        for h in hit:
            tc[h] += 1
        rd = r.get("Q5_reading", "")
        if re.search(r"(don't|do not|never heard|not sure what|no idea|unfamiliar|not familiar|never tried|what(ever)? (that|maesil|plum)|some kind of)", rd.lower()):
            reading_flags += 1
            if len(examples) < 6:
                examples.append((pid, rd.strip()))
    out.append("| 어휘 | 모르겠다로 꼽은 페르소나 | 비율 |\n|---|---:|---:|")
    for name, c in tc.most_common():
        share = c / N
        mark = " ⚠" if (not name.startswith("other") and share >= THRESH["①_term_unclear_share"]) else ""
        out.append(f"| {name} | {c} | {share*100:.0f}%{mark} |")
        if mark:
            flags.append(f"① '{name}' 모름 {share*100:.0f}% ≥ {THRESH['①_term_unclear_share']*100:.0f}% → 괄호 풀이 검토")
    out.append(f"\n- Q5_reading에 '모르겠다·들어본 적 없다·대충 ~같은 것' 류 표현이 있는 페르소나: {reading_flags}/{N} ({reading_flags/N*100:.0f}%)")
    for pid, rd in examples:
        out.append(f"  - pid{pid}: “{rd}”")
    # 한식 친숙도 낮은 그룹에서 maesil 모름 비율
    low_k = [pid for pid in rows if pool[pid]["kfood_familiarity"] < 0.42]
    hi_k = [pid for pid in rows if pool[pid]["kfood_familiarity"] >= 0.58]
    def unk_maesil(pids):
        return sum(1 for pid in pids if any(re.search(TERMS["maesil"], t.lower()) or re.search(TERMS["green plum syrup"], t.lower())
                                             for t in rows[pid].get("Q5_unclear_terms", []))) / max(len(pids), 1)
    out.append(f"- maesil/green plum syrup 모름: 한식친숙 낮음(n={len(low_k)}) {unk_maesil(low_k)*100:.0f}% vs 높음(n={len(hi_k)}) {unk_maesil(hi_k)*100:.0f}% "
               f"(페르소나 특성 → 어휘 반응 전사 여부, 기록)")

    # ── ② Q3 'A little' 쏠림 ──
    out.append("\n## 3. 진단 ② Q3 'A little' 쏠림\n")
    rz3 = realized(rows, "Q3_dist", Q3O, SALT["Q3"], SEED)
    out.append(f"- 믿음질량: Very much {m3[0]:.1f}% / A little {m3[1]:.1f}% / No {m3[2]:.1f}%  · realized: "
               f"{rz3.get(Q3O[0],0)}/{rz3.get(Q3O[1],0)}/{rz3.get(Q3O[2],0)} (n={N})")
    out.append(f"- 한국 게이트 C 대응치(참고 방향만): '매우' 33.0% / '조금'까지 71.6%")
    if m3[1] / 100 >= THRESH["②_a_little_mass"]:
        flags.append(f"② Q3 'A little' 질량 {m3[1]:.0f}% ≥ {THRESH['②_a_little_mass']*100:.0f}% → '조금' 함정 재발 의심")
        out.append("- ⚠ 임계 초과")
    else:
        out.append("- 임계 미달(쏠림 없음)")
    # 페르소나 기피 성향별 Q3
    for lab, cond in [("기피 매우높음(>0.75)", lambda p: p > 0.75), ("보통(0.42~0.58)", lambda p: 0.42 <= p <= 0.58), ("매우낮음(<0.25)", lambda p: p < 0.25)]:
        g = [pid for pid in rows if cond(pool[pid]["cilantro_aversion"])]
        if g:
            mm = mass({pid: rows[pid] for pid in g}, "Q3_dist", 3)
            out.append(f"  - 페르소나 {lab} n={len(g)}: Very much {mm[0]:.0f}% / A little {mm[1]:.0f}% / No {mm[2]:.0f}%")

    # ── ③ Q2a Other ──
    out.append("\n## 4. 진단 ③ Q2a 'Other' 비율(선택지 누락)\n")
    others = [(pid, r["Q2a_other_text"].strip()) for pid, r in rows.items() if r.get("Q2a_other_text", "").strip()]
    out.append(f"- 'Other' 믿음질량 {m2a[5]:.1f}% · Other 문구를 쓴 페르소나 {len(others)}/{N}")
    for pid, t in others[:15]:
        out.append(f"  - pid{pid}: “{t}”")
    if m2a[5] / 100 >= THRESH["③_other_share"]:
        flags.append(f"③ Q2a 'Other' 질량 {m2a[5]:.0f}% ≥ {THRESH['③_other_share']*100:.0f}% → 위 문구로 선택지 보강 검토")
        out.append("- ⚠ 임계 초과")
    else:
        out.append("- 임계 미달")

    # ── ④ Q6 사다리 ──
    out.append("\n## 5. 진단 ④ Q6 가격 사다리 바닥·천장\n")
    yes = {v: statistics.mean(min(max(r[f"buy_{v}"], 0), 10) / 10 for r in rows.values()) for v in PRICES}
    nonmono = sum(1 for r in rows.values() if any(r[f"buy_{PRICES[i]}"] > r[f"buy_{PRICES[i-1]}"] for i in range(1, 4)))
    # realized 곡선(v23 임계 표집과 같은 방식)
    acc = Counter()
    for pid, r in rows.items():
        p = [min(max(r[f"buy_{v}"] / 10.0, 0.0), 1.0) for v in PRICES]
        for i in range(1, 4):
            p[i] = min(p[i], p[i - 1])
        bins = [max(b, 0.0) for b in [1 - p[0], p[0] - p[1], p[1] - p[2], p[2] - p[3], p[3]]]
        s = sum(bins) or 1.0
        k = int(np.random.default_rng([SEED, pid, SALT["Q6"]]).choice(5, p=[b / s for b in bins]))
        for i, v in enumerate(PRICES):
            acc[v] += 1 if i < k else 0
    out.append("| 가격 | Yes 믿음질량 | realized Yes n/N |\n|---|---:|---:|")
    for v in PRICES:
        out.append(f"| ${v/100:.2f} | {yes[v]*100:.0f}% | {acc[v]}/{N} ({acc[v]/N*100:.0f}%) |")
    out.append(f"- 비단조 분포(가격↑인데 Yes 인원↑)를 낸 페르소나: {nonmono}/{N} (위생 지표, 기록)")
    out.append(f"- 한국 게이트 C 대응 자리: $4.99 ↔ 6,900원 65%(방향만)")
    if yes[499] >= THRESH["④_floor_yes_499"]:
        flags.append(f"④ $4.99 Yes {yes[499]*100:.0f}% ≥ {THRESH['④_floor_yes_499']*100:.0f}% → 바닥이 낮음, 사다리 위로")
    if yes[799] <= THRESH["④_ceiling_yes_799"]:
        flags.append(f"④ $7.99 Yes {yes[799]*100:.0f}% ≤ {THRESH['④_ceiling_yes_799']*100:.0f}% → 천장이 높음, 사다리 아래로")
    out.append("- " + ("⚠ 임계 초과" if any(f.startswith("④") for f in flags) else "바닥·천장 모두 임계 안(사다리 유지)"))

    # ── ⑤ Q3 → Q5 일관성 압력 ──
    out.append("\n## 6. 진단 ⑤ Q3 → Q5 일관성 압력(기록만)\n")
    pids = list(rows)
    vm = [norm(rows[p]["Q3_dist"])[0] for p in pids]
    top2 = [norm(rows[p]["Q5_dist"])[3:].sum() for p in pids]
    avers = [pool[p]["cilantro_aversion"] for p in pids]
    def pear(x, y):
        x, y = np.array(x), np.array(y)
        return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0
    out.append(f"- r(페르소나 고수기피, Q3 Very much 질량) = {pear(avers, vm):+.2f}  ← 특성→문항 전사 강도")
    out.append(f"- r(Q3 Very much 질량, Q5 4~5점 질량) = {pear(vm, top2):+.2f}  ← Q3가 Q5로 그대로 전사되는지")
    out.append(f"- r(페르소나 고수기피, Q5 4~5점 질량) = {pear(avers, top2):+.2f}")
    av = [p for p in pids if pick(rows[p]["Q3_dist"], 3, p, SALT["Q3"], SEED) == 0]
    nv = [p for p in pids if pick(rows[p]["Q3_dist"], 3, p, SALT["Q3"], SEED) != 0]
    if av and nv:
        t_av = statistics.mean(norm(rows[p]["Q5_dist"])[3:].sum() for p in av)
        t_nv = statistics.mean(norm(rows[p]["Q5_dist"])[3:].sum() for p in nv)
        out.append(f"- §4-5 축(향 기피층 Q3 Very much vs 나머지)의 Q5 4~5점: {t_av*100:.0f}% (n={len(av)}) vs {t_nv*100:.0f}% (n={len(nv)}) "
                   f"— 한국 52% vs 39%와 같은 축, 방향만 기록. 방향은 프롬프트에 심지 않았으므로 LLM prior.")
    for k in ("Q3_dist", "Q5_dist", "Q1_dist"):
        c = Counter(tuple(rows[p][k]) for p in pids)
        out.append(f"- {k} 최빈 패턴 점유 {c.most_common(1)[0][1]/N*100:.0f}% (동질성 잔존도)")

    # ── ⑥ Q7 에코 ──
    out.append("\n## 7. 진단 ⑥ Q7 자유응답의 Q5 문장 에코(기록만)\n")
    cw = words(CONCEPT); c3 = ngrams(cw, 3); cset = set(cw)
    echo = []
    for pid, r in rows.items():
        w = words(r.get("Q7_text", ""))
        if not w:
            continue
        jac = len(set(w) & cset) / len(set(w) | cset)
        tri = len(ngrams(w, 3) & c3)
        echo.append((pid, jac, tri, r["Q7_text"].strip()))
    strong = [e for e in echo if e[2] >= 2 or e[1] >= 0.25]
    out.append(f"- 콘셉트 문장 내용어와의 Jaccard 평균 {statistics.mean(e[1] for e in echo):.2f}, 3-gram 공유 ≥2 또는 Jaccard ≥0.25: {len(strong)}/{len(echo)}")
    out.append(f"- 콘셉트 핵심어 재사용 비율: " + ", ".join(
        f"{t} {sum(1 for e in echo if re.search(rx, e[3].lower()))/len(echo)*100:.0f}%" for t, rx in
        [("milder/mild", r"\bmild"), ("maesil/plum", r"maesil|plum"), ("cilantro", r"cilantro"), ("tamarind", r"tamarind"), ("5 minutes/microwave", r"5 minutes|microwave")]))
    out.append("- Q7 원문 전부(국가=US, 합성):")
    for pid, jac, tri, t in sorted(echo, key=lambda e: -e[1]):
        out.append(f"  - pid{pid} (J={jac:.2f}, tri={tri}): “{t}”")

    # ── 부수 기록: Q4a 브랜드·Q10 검색어 ──
    out.append("\n## 8. 부수 기록 — Q4a 브랜드·Q10 검색어(합성, 실측 아님)\n")
    bc = Counter()
    for r in rows.values():
        for b in ["trader joe", "costco", "bibigo", "whole foods", "amy's", "lean cuisine", "healthy choice", "target", "walmart", "kroger", "aldi", "tem toa", "p.f. chang", "ling ling", "feel good foods", "kevin's"]:
            if b in r.get("Q4a_text", "").lower():
                bc[b] += 1
    out.append(f"- Q4a 언급 브랜드·매장: {dict(bc.most_common())}")
    out.append("- Q4a 원문(있는 것만):")
    for pid, r in rows.items():
        if r.get("Q4a_text", "").strip():
            out.append(f"  - pid{pid}: “{r['Q4a_text'].strip()}”")
    qc = Counter()
    for r in rows.values():
        for w in re.findall(r"[a-z]+", r.get("Q10_text", "").lower()):
            if w not in STOP and len(w) > 2:
                qc[w] += 1
    out.append(f"- Q10 검색어 상위: {qc.most_common(20)}")
    out.append(f"- Q10 비움(선택 문항 건너뜀): {sum(1 for r in rows.values() if not r.get('Q10_text','').strip())}/{N}")

    # ── 요약 ──
    out.insert(3, "\n## 요약 — 고치는 기준(①~④) 판독\n" + ("\n".join(f"- ⚠ {f}" for f in flags) if flags else "- ①~④ 모두 사전 고정 임계 안. 문항 수정 없이 발행 가능(엔진 기준). 사람 2명 파일럿은 별도로 한다.")
               + "\n- ⑤⑥은 한계로 기록만(아래 6·7절).\n- 임계: " + json.dumps(THRESH, ensure_ascii=False) + "\n")
    md = "\n".join(out) + "\n"
    print(md)
    dest = a.out or os.path.join(H.run_dir(a.run_id, create=True), "us_lite_diagnose.md")
    open(dest, "w", encoding="utf-8").write(md)
    print(f"[diagnose] → {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
