# -*- coding: utf-8 -*-
"""
E2 3회 다듬기 — 향기피 오버샘플본. 이전 웨이브의 '~와닿아서/와닿음/끌림' 말투를 폐기하고
해요체·구어·음슴 혼합으로 레지스터 전환. 선택응답 현실 응답률(12/35≈34%)만 채움.
P1 정형해체 → P2 레지스터 다양화+질감 → P3 성향(B1/E1) 정합.
"""
import json
from collections import Counter

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
rows = {r["respondent_id"]: r for r in json.load(open(f"{SP}/rows_final.json"))}
raw = {r["pid"]: r for r in json.load(open(f"{SP}/survey_raw.json"))}
A2sp = ("①향신료향 부담", "②낯선 소스·재료")

SUBSET = [14, 6, 56, 24, 43, 28, 47, 38, 30, 37, 20, 26]  # B1 1~5, 향기피/비향기, 가/나

work = []
for pid in SUBSET:
    r, a = rows[pid], raw[pid]
    seg = "향기피" if r["A2"] in A2sp else "비향기"
    work.append({"pid": pid, "seg": seg, "E1": r["E1"], "B1": r["B1"], "raw_E2": a.get("E2", "")})
json.dump(work, open(f"{SP}/e2_work.json", "w"), ensure_ascii=False, indent=1)

# ── Pass1: 원문 '와닿/끌림' 어미 폐기, 사유 중심으로 재진술 ──
P1 = {
    14: "매실청이면 어떤 맛인지는 그려지긴 한다",
    6:  "고수를 워낙 못 먹어서 그거 빠졌다는 것만 봤다",
    56: "고수랑 피시소스 냄새를 못 견디는데 그걸 뺐다니 눈길은 간다",
    24: "향 강한 게 싫은 편이라 그 부분이 좋다",
    43: "나한텐 고수 있냐 없냐가 제일 크다",
    28: "딱 나 같은 고수 못 먹는 사람 겨냥한 문구 같다",
    47: "고수 빼고 매실청으로 갔다는 조합이 내 입맛에 정확하다",
    38: "고수만 없으면 무조건인데 그걸 없앴다니 취향저격이다",
    30: "혼자 사는 입장에선 5분 컷이 제일 크다",
    37: "맨날 배달로 시켰는데 집에서 5분이면 그게 낫겠다 싶다",
    20: "타마린드 대신 매실청이라니 그 맛이 진짜 궁금하다",
    26: "자취하는데 5분이면 바로 한 끼 되니까 그게 제일 크다",
}

# ── Pass2: 레지스터 다양화(해요체·음슴·ㅋㅋ) + 구어 질감 ──
P2 = {
    14: "매실청이면 어떤 맛인지는 그려지긴 해요, 살진 모르겠지만",
    6:  "고수를 워낙 못 먹어서 그거 빠졌다는 것만 봤어요",
    56: "고수랑 피시소스 냄새를 못 견디는데 그걸 뺐다니 일단 눈길은 가네요",
    24: "향 강한 게 싫은 편이라 그 부분이 좋더라고요",
    43: "저한텐 고수 있냐 없냐가 제일 크거든요",
    28: "딱 저 같은 고수 못 먹는 사람 겨냥한 문구 같아서요",
    47: "고수 빼고 매실청으로 갔다는 조합이 제 입맛에 정확해요",
    38: "고수만 없으면 무조건인데 그걸 없앴다니 완전 취향저격 ㅋㅋ",
    30: "혼자 사는 입장에선 5분 컷이 제일 크죠 뭐",
    37: "맨날 배달로 시켰는데 집에서 5분이면 그게 낫겠다 싶었어요",
    20: "타마린드 대신 매실청이라니 그 맛이 진짜 궁금하네요",
    26: "자취하는데 5분이면 바로 한 끼 되니까 그게 제일 크죠",
}

# ── Pass3: 성향(B1/E1) 정합 — 회의자는 유보, 호의자는 확신 ──
P3 = {
    14: "매실청이면 어떤 맛인지 그려지긴 하는데, 실제로 살진 모르겠어요",   # 향기피·나·B1=1 회의
    6:  "고수를 워낙 못 먹어서 그거 빠졌다는 것만 보고요",                # 향기피·나·B1=2 회의
    56: "고수랑 피시소스 냄새를 못 견디는데 그걸 뺐다니 일단 눈길은 가네요", # 향기피·나·B1=2 회의
    24: "향 강한 게 싫은 편이라 그 부분이 좋더라고요",                    # 향기피·나·B1=3
    43: "저한텐 고수 있냐 없냐가 제일 크거든요",                         # 향기피·나·B1=3
    28: "딱 저 같은 고수 못 먹는 사람 겨냥한 문구 같아서요",              # 향기피·나·B1=4
    47: "고수 빼고 매실청으로 갔다는 조합이 제 입맛에 정확해요",           # 향기피·나·B1=5 호의
    38: "고수만 없으면 무조건인데 그걸 없앴다니 완전 취향저격 ㅋㅋ",         # 향기피·나·B1=5 호의
    30: "혼자 사는 입장에선 5분 컷이 제일 크죠 뭐",                      # 향기피·가·B1=4
    37: "맨날 배달로 시켰는데 집에서 5분이면 그게 낫겠다 싶었어요",         # 향기피·가·B1=4
    20: "타마린드 대신 매실청이라니 그 맛이 진짜 궁금하네요",              # 비향기·나·B1=5 호의
    26: "자취하는데 5분이면 바로 한 끼 되니까 그게 제일 크죠",            # 비향기·가·B1=5 호의
}

for tag, D in [("pass1", P1), ("pass2", P2), ("pass3", P3)]:
    json.dump([{"pid": w["pid"], "e2": D[w["pid"]]} for w in work],
              open(f"{SP}/e2_{tag}.json", "w"), ensure_ascii=False, indent=1)

finals = P3
texts = list(finals.values())
print("=== E2 3회 다듬기 검토 (향기피 오버샘플·말투 전환) ===")
print(f"응답자 {len(texts)}명 (유효 35 중 {len(texts)/35*100:.0f}%)")
print("완전중복:", [t for t, c in Counter(texts).items() if c > 1] or "없음")
print("어미 4자 최다:", Counter(t[-4:] for t in texts).most_common(4))
lens = sorted(len(t) for t in texts)
print(f"길이 min/median/max: {lens[0]}/{lens[len(lens)//2]}/{lens[-1]}자")
print("이전말투('와닿') 잔존:", [p for p, t in finals.items() if "와닿" in t] or "없음(전환 완료)")
wd = {w["pid"]: w for w in work}
mis = []
for pid, t in finals.items():
    e1 = wd[pid]["E1"][0]
    ga = any(k in t for k in ["5분", "간편", "배달", "컷", "한 끼", "혼자"])
    na = any(k in t for k in ["매실", "고수", "향", "맛", "피시소스", "취향"])
    if e1 == "가" and not ga: mis.append((pid, "가", t))
    if e1 == "나" and not na: mis.append((pid, "나", t))
print("E1-내용 불일치:", mis or "없음")
b1low = [(pid, wd[pid]["B1"], t) for pid, t in finals.items() if wd[pid]["B1"] <= 2]
print(f"회의자(B1≤2) {len(b1low)}명 — 유보 톤:")
for p, b, t in b1low: print(f"   pid{p}(B1={b}): {t}")

json.dump([{"pid": w["pid"], "e2": finals[w["pid"]]} for w in work],
          open(f"{SP}/e2_final.json", "w"), ensure_ascii=False, indent=1)
print(f"\ne2_final.json 저장 ({len(work)}명)")
