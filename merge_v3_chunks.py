#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3-sim 청크 런 병합 + 프롬프트 대조 검증 (LLM 0회).

배경(기술적 결함 공개 — SPEC_V3 §5): personas를 스크립트에 리터럴로 박은
베이킹 사본으로 단일풀을 돌렸을 때 에이전트 도구 정의에 스키마가 실리지 않아
50/50이 검증 거부로 실패했다(런 wf_7aa3b5eb-961, 1,497,916 토큰, 결과 0건).
원본 스크립트 + args 방식은 정상 동작하므로, 사전등록된 동일 풀·동일 프롬프트를
**청크로 나눠 재실행**하고 그 저널을 하나로 병합한다. 페르소나·프롬프트·스키마·
판정 기준은 무변경이며 청크 경계는 판정에 개입하지 않는다(pid 서로소·전량 포함).

검증 항목:
  1. pid 집합 = 풀 pid 집합 (누락·중복·외래 pid 0)
  2. 각 dist 합 = 10 · buy_* 0~10 · 가격 단조 비증가(위반은 경고로 기록)
  3. **프롬프트 대조**: 에이전트 전사에 실린 프롬프트의 pid·특성 lvl 문자열이
     풀 prof.json에서 재계산한 값과 일치 (전사 오류·풀 불일치 차단)

사용:
  python3 merge_v3_chunks.py --out v3run_single_45069727 \
      --pool runs/v3pool_45069727 --chunks wf_4ff14243-17a wf_9dedeae4-ed0
"""
import argparse
import json
import os
import shutil

import harness_paths as H

DIST_LEN = {"A1_dist": 4, "A2a_dist": 3, "A2b_dist": 3, "A2c_dist": 3, "A2d_dist": 3,
            "A2x_dist": 2, "B1_dist": 5, "B2_dist": 5, "B3_dist": 7, "C1_dist": 5,
            "C2_dist": 3, "E1_dist": 4}
BUY = ["buy_5900", "buy_6900", "buy_7500", "buy_8500"]
LVL_FIELDS = ["향기피", "매실청", "관여", "회의", "가격민감", "접근성",
              "정통기대", "식사량", "카테고리빈도", "과거경험부정", "해결지향"]


def lvl(x):
    """wf_vs_v3.js:29의 lvl()과 동일 임계(출처 wf_vs_v23.js:29)."""
    return ("매우높음" if x > 0.75 else "높음" if x > 0.58 else
            "보통" if x > 0.42 else "낮음" if x > 0.25 else "매우낮음")


def read_journal(run_id):
    p = os.path.join(H.JOURNAL_BASE, run_id, "journal.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")], p


def agent_prompts(run_id):
    """에이전트 전사에서 (pid, 프롬프트 첫 특성줄) 추출."""
    import glob
    out = {}
    for f in glob.glob(os.path.join(H.JOURNAL_BASE, run_id, "agent-*.jsonl")):
        for line in open(f, encoding="utf-8"):
            o = json.loads(line)
            m = o.get("message") or {}
            if m.get("role") != "user":
                continue
            c = m.get("content")
            txt = c if isinstance(c, str) else ""
            if "[유형 pid=" in txt:
                pid = int(txt.split("[유형 pid=")[1].split("]")[0])
                out[pid] = txt
                break
    return out


def main():
    ap = argparse.ArgumentParser(description="v3 청크 저널 병합·검증")
    ap.add_argument("--out", required=True, help="병합 런 디렉토리명(runs/<out>/)")
    ap.add_argument("--pool", required=True, help="풀 디렉토리(runs/v3pool_... 또는 v3multi_...)")
    ap.add_argument("--chunks", nargs="+", required=True, help="청크 run_id 목록")
    ap.add_argument("--failed-run", default=None, help="공개할 실패 런 id(params 기록용)")
    ap.add_argument("--multipool", action="store_true",
                    help="멀티풀 런(multipool_args/meta/cfg 사용 · 풀 파일 3종 복사)")
    a = ap.parse_args()

    if a.multipool:
        prof = {p["pid"]: p for p in json.load(open(f"{a.pool}/multipool_args.json",
                                                    encoding="utf-8"))}
        pool_files = ("multipool_args.json", "multipool_meta.json", "multipool_cfg.json")
    else:
        prof = {p["pid"]: p for p in json.load(open(f"{a.pool}/prof.json", encoding="utf-8"))}
        pool_files = ("prof.json", "pool_meta.json", "run_cfg.json")
    lines, results, prompts, warn = [], {}, {}, []
    for rid in a.chunks:
        rows, path = read_journal(rid)
        n_res = 0
        for o in rows:
            lines.append(json.dumps(o, ensure_ascii=False))
            r = o.get("result")
            if o.get("type") == "result" and isinstance(r, dict) and "A2a_dist" in r:
                if r["pid"] in results:
                    warn.append(f"pid {r['pid']} 중복 — {rid}")
                results[r["pid"]] = r
                n_res += 1
        prompts.update(agent_prompts(rid))
        print(f"[청크] {rid}: 저널 {len(rows)}행 · 결과 {n_res}건  ({path})")

    # 1. pid 집합
    miss = sorted(set(prof) - set(results))
    extra = sorted(set(results) - set(prof))
    print(f"\n[1] pid 집합: 풀 {len(prof)} · 결과 {len(results)} · 누락 {miss} · 외래 {extra}")

    # 2. 분포 정합
    bad = []
    for pid, r in sorted(results.items()):
        for k, n in DIST_LEN.items():
            v = r.get(k)
            if not isinstance(v, list) or len(v) != n or sum(v) != 10:
                bad.append(f"pid {pid} {k}={v}")
        b = [r.get(k) for k in BUY]
        if any(not isinstance(x, int) or not 0 <= x <= 10 for x in b):
            bad.append(f"pid {pid} buy={b}")
        elif any(b[i] < b[i + 1] for i in range(3)):
            warn.append(f"pid {pid} 가격 비단조 buy={b}")
    print(f"[2] 분포 정합 위반: {len(bad)}건" + ("" if not bad else " → " + "; ".join(bad[:5])))

    # 3. 프롬프트 대조 — 세그먼트 문자열(S1~S5) + 특성 lvl 전량
    mism = []
    for pid, p in prof.items():
        t = prompts.get(pid)
        if t is None:
            mism.append(f"pid {pid} 프롬프트 없음")
            continue
        for f in ("S1", "S2", "S3", "S4", "S5"):
            if str(p[f]) not in t:
                mism.append(f"pid {pid} {f}: 기대 '{p[f]}' 프롬프트에 없음")
        for f in LVL_FIELDS:
            want = lvl(p[f])
            # 프롬프트는 "<라벨> <lvl>" 형태 — 필드명 직후 값 확인
            seg = t.split("·")
            hit = [s for s in seg if f in s or (f == "향기피" and "향신료부담" in s)
                   or (f == "매실청" and "매실청친숙" in s)
                   or (f == "관여" and "관여도" in s) or (f == "회의" and "회의도" in s)
                   or (f == "접근성" and "접근성장벽" in s)
                   or (f == "정통기대" and "정통성기대" in s)
                   or (f == "식사량" and "식사량기대" in s)
                   or (f == "카테고리빈도" and "섭취빈도" in s)
                   or (f == "과거경험부정" and "부정적 평가" in s)
                   or (f == "해결지향" and "거부 소거" in s)]
            if not hit or want not in " ".join(hit):
                mism.append(f"pid {pid} {f}: 기대 {want}")
    print(f"[3] 프롬프트 대조 불일치: {len(mism)}건" + ("" if not mism else " → " + "; ".join(mism[:5])))

    ok = not miss and not extra and not bad and not mism
    print(f"\n▶ 검증 {'통과' if ok else '실패'} · 경고 {len(warn)}건")
    for w in warn[:10]:
        print(f"   경고: {w}")
    if not ok:
        raise SystemExit(1)

    # 병합 저장
    d = H.run_dir(a.out, create=True)
    with open(f"{d}/journal.jsonl", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    for fn in pool_files:
        shutil.copy2(f"{a.pool}/{fn}", f"{d}/{fn}")
    json.dump({"merged_from": a.chunks, "pool": os.path.basename(a.pool),
               "n_results": len(results), "engine": "v3-sim", "script": "wf_vs_v3.js",
               "launch": "Workflow(scriptPath=wf_vs_v3.js, args=personas) — 청크 분할",
               "failed_run_disclosed": a.failed_run,
               "note": "기술적 결함(베이킹 사본에서 스키마 미전달)로 1차 런 전량 실패 → "
                       "동일 풀·동일 프롬프트로 청크 재실행. 판정 기준·풀·시드 무변경.",
               "verify": {"pid_set": "ok", "dist_sum": "ok", "prompt_match": "ok",
                          "warnings": warn}},
              open(f"{d}/params.json", "w"), ensure_ascii=False, indent=1)
    print(f"[병합] runs/{a.out}/ ← 저널 {len(lines)}행 · 결과 {len(results)}건 · 풀 파일 3종")
    print(f"[다음] HARNESS_SP=$PWD/runs/{a.out} HARNESS_JOURNAL_BASE=$PWD/runs "
          f"python3 v3_analyze.py {a.out}")


if __name__ == "__main__":
    main()
