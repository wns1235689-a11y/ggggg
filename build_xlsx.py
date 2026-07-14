#!/usr/bin/env python3
"""
rows_final.json + e2_final.json → 서식없음 xlsx (시트명 '응답100').
응답자×문항별 답변 평문. E2는 3회 다듬은 최종본(선택응답만 채움).
"""
import json, openpyxl

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
OUT = "/home/user/ggggg/exports/게이트C_합성시뮬응답_응답100.xlsx"

rows = json.load(open(f"{SP}/rows_final.json"))
e2 = {d["pid"]: d["e2"] for d in json.load(open(f"{SP}/e2_final.json"))}

HDR = ["응답자번호", "유입경로(F1)", "S1_연령대", "S2_신분", "S3_거주형태",
       "S4_간편식구매빈도(최근1개월)", "S5_동남아여행(최근2년)",
       "A1_팟타이경험", "A2_동남아음식_기피이유", "B1_첫인상(1-5)",
       "B2_구매이유_1순위", "B2_구매이유_2순위", "B3_가장망설이는점", "B4_주의력체크",
       "C1_현재대안", "C2_전환의향", "D1_5900원", "D1_6900원", "D1_7500원", "D1_8500원",
       "E1_헤드라인선호", "E2_이유(주관식,선택)", "세그먼트", "타깃적합(§3-1)", "B4통과"]


def seg(r):
    if r["_is_student"]: return "대학생"
    if r["_is_target"]: return "타깃"
    return "기타"


wb = openpyxl.Workbook()
ws = wb.active
ws.title = "응답100"
ws.append(HDR)
rows = sorted(rows, key=lambda r: r["respondent_id"])
for r in rows:
    pid = r["respondent_id"]
    ws.append([
        pid + 1, r["F1_channel"], r["S1"], r["S2"], r["S3"], r["S4"], r["S5"],
        r["A1"], r["A2"], r["B1"], r["B2_1순위"], r["B2_2순위"], r["B3"], r["B4"],
        r["C1"], r["C2"], r["D1_5900"], r["D1_6900"], r["D1_7500"], r["D1_8500"],
        r["E1"], e2.get(pid, ""), seg(r),
        "예" if r["_is_target"] else "아니오",
        "통과" if r["_flag_b4_pass"] else "실패",
    ])
wb.save(OUT)
print(f"저장: {OUT}  ({ws.max_row - 1}행 x {ws.max_column}열, 시트='{ws.title}')")
filled = sum(1 for r in rows if e2.get(r['respondent_id'], '').strip())
print(f"E2 채움: {filled}/{len(rows)}")
