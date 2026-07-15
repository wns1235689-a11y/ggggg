# -*- coding: utf-8 -*-
"""
사전분포 스윕 응답 → 서식없음 xlsx.
journal.jsonl(응답) + sweep_prof.json(프로필·prior값) 병합. cfg(인구)·prior 열 포함.
raw 응답(VS·정합패치·E2 3회 미적용) — 방향 판별용임을 시트에 명시.
"""
import json, sys, openpyxl

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
J = sys.argv[1]
OUT = "/home/user/ggggg/exports/게이트C_합성시뮬응답_사전분포스윕120.xlsx"

meta = json.load(open(f"{SP}/sweep_meta.json"))
names = {int(k): v for k, v in meta["names"].items()}
prof = {p["pid"]: p for p in json.load(open(f"{SP}/sweep_prof.json"))}

res = {}
for line in open(J, encoding="utf-8"):
    o = json.loads(line)
    if o.get("type") == "result" and isinstance(o.get("result"), dict) and "pid" in o["result"]:
        res[o["result"]["pid"]] = o["result"]

HDR = ["응답자번호", "prior인구(cfg)", "세그먼트",
       "S1_연령대", "S2_신분", "S3_거주형태", "S4_간편식빈도", "S5_동남아여행",
       "prior_향기피", "prior_매실청친숙", "prior_관여", "prior_접근장벽",
       "A1_팟타이경험", "A2_동남아기피이유", "B1_첫인상(1-5)",
       "B2_구매이유_1순위", "B2_구매이유_2순위", "B3_가장망설이는점", "B4_주의력체크",
       "C1_현재대안", "C2_전환의향", "D1_5900원", "D1_6900원", "D1_7500원", "D1_8500원",
       "E1_헤드라인선호", "E2_이유(주관식)"]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "스윕120"
# 성격 명시 행(합성·비실측, raw)
ws.append(["※ 합성·비실측 LLM 시뮬 / 사전분포 스윕(4인구×30) / raw 응답: VS·정합패치·E2다듬기 미적용 — 방향 robust판별 전용"])
ws.append(HDR)

for pid in sorted(res):
    r = res[pid]
    p = prof.get(pid, {})
    cfg = pid // 100
    ws.append([
        pid, f"{cfg}:{names.get(cfg,'')}", p.get("seg", ""),
        p.get("S1"), p.get("S2"), p.get("S3"), p.get("S4"), p.get("S5"),
        p.get("향기피"), p.get("매실청"), p.get("관여"), p.get("접근성"),
        r.get("A1"), r.get("A2"), r.get("B1"),
        r.get("B2_1"), r.get("B2_2"), r.get("B3"), r.get("B4"),
        r.get("C1"), r.get("C2"),
        r.get("D1_5900"), r.get("D1_6900"), r.get("D1_7500"), r.get("D1_8500"),
        r.get("E1"), r.get("E2"),
    ])

wb.save(OUT)
print(f"저장: {OUT}  ({ws.max_row - 2}명 x {ws.max_column}열, 시트='{ws.title}')")
