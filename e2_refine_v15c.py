# -*- coding: utf-8 -*-
"""
E2 서술형 3회 다듬기 + 검토 — 깔끔 재추출본(N=50, 타깃72%·D1단조).
선택응답 현실 응답률(14/50=28%)만 채움. B4실패자 공란. seg·E1·B1 다양성.
3패스: P1 정형해체 → P2 구조·질감 다양화 → P3 성향정합·현실성.
"""
import json
from collections import Counter

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
rows = {r["respondent_id"]: r for r in json.load(open(f"{SP}/rows_final.json"))}
raw = {r["pid"]: r for r in json.load(open(f"{SP}/survey_raw.json"))}
prof = {p["pid"]: p for p in json.load(open(f"{SP}/prof.json"))}

SUBSET = [1, 22, 24, 43, 46, 48, 0, 5, 6, 11, 13, 21, 32, 38]  # 가6·나8, B1 1~5, B4통과만

work = []
for pid in SUBSET:
    r, a, p = rows[pid], raw[pid], prof[pid]
    seg = "타깃" if r.get("_is_target") else ("확장" if r.get("_is_student") else "기타")
    work.append({"pid": pid, "seg": seg, "E1": r["E1"], "B1": r["B1"],
                 "향기피": p.get("향기피"), "매실청": p.get("매실청"), "raw_E2": a.get("E2", "")})
json.dump(work, open(f"{SP}/e2_work.json", "w"), ensure_ascii=False, indent=1)

# ── Pass1: 정형 어미('~와닿아서/~궁금해서') 해체 ──
P1 = {
    1:  "팟타이 좋아해서 사 먹곤 했는데 집에서 5분이면 딱이다",
    22: "5분이면 간편하니까 그게 낫다",
    24: "파는 데 찾기 귀찮았는데 집에서 5분이면 되니까",
    43: "어차피 자주 먹는 거 5분이면 편하다",
    46: "그냥 간편한 게 제일 와닿는다",
    48: "혼자 살면 해먹기 귀찮은데 5분이면 딱이다",
    0:  "고수 부담 없다는 것 하나는 끌린다",
    5:  "매실청으로 바꿨다는데 진짜 그 맛 날지 반신반의다",
    6:  "고수 부담 없다는 게 딱 내 얘기다",
    11: "매실청 새콤한 맛이 어떨지 궁금하다",
    13: "매실청이라 향 부담도 없고 진짜 팟타이 맛일지 궁금하다",
    21: "매실청이라니 맛이 상상돼서 진짜 팟타이일지 걱정이 덜하다",
    32: "진짜 팟타이 맛일지가 제일 걱정인데 그걸 짚어준다",
    38: "매실청으로 잡았다는데 진짜 팟타이 맛일지 제일 궁금하다",
}

# ── Pass2: 구조·길이·질감(구어·말줄임) 다양화 ──
P2 = {
    1:  "팟타이 좋아해서 사먹곤 했는데 집에서 5분이면 딱이라",
    22: "뭐 5분이면 간편하니까 그게 낫죠",
    24: "파는 데 찾기 귀찮았는데 집에서 5분이면 되니까요",
    43: "어차피 자주 먹는 거 5분이면 편하긴 하죠",
    46: "그냥 간편한 게 제일 와닿아요",
    48: "혼자 살면 해먹기 귀찮은데 5분이면 딱이라",
    0:  "고수 부담 없다는 거 하나는 끌리네요",
    5:  "매실청으로 바꿨다는데 진짜 그 맛 날지 반신반의라",
    6:  "고수 부담 없다는 게 딱 내 얘기라",
    11: "매실청 새콤한 맛이 어떨지 궁금해서요",
    13: "매실청이라 향 부담도 없고 진짜 팟타이 맛일지 궁금",
    21: "매실청이라니 맛이 상상돼서 진짜 팟타이일지 걱정이 좀 덜함",
    32: "진짜 팟타이 맛일지가 젤 걱정인데 그걸 짚어주니 눈이 가긴 함",
    38: "매실청으로 잡았다는 거 진짜 팟타이 맛일지 제일 궁금해요",
}

# ── Pass3: 성향(B1/seg/E1) 정합·현실성 최종 ──
P3 = {
    1:  "팟타이 좋아해서 사먹곤 했는데 집에서 5분이면 딱이라",        # 타깃·가·B1=4
    22: "뭐 5분이면 간편하니까 그게 낫죠",                        # 타깃·가·B1=2 미온
    24: "파는 데 찾기 귀찮았는데 집에서 5분이면 되니까요",           # 타깃·가·B1=4
    43: "어차피 자주 먹는 거 5분이면 편하긴 하죠",                 # 타깃·가·B1=1 미온
    46: "그냥 간편한 게 제일 와닿아요",                          # 기타·가·B1=5 호의
    48: "혼자 살면 해먹기 귀찮은데 5분이면 되니까 딱 좋죠",         # 타깃·가·B1=4
    0:  "고수 부담 없다는 거 하나는 끌리네요 (나머진 글쎄)",         # 타깃·나·B1=2 회의
    5:  "매실청으로 바꿨다는데 진짜 그 맛 날지 반신반의라",          # 타깃·나·B1=1 회의
    6:  "고수 부담 없다는 게 딱 내 얘기라",                       # 기타·나·B1=4
    11: "매실청 새콤한 맛이 어떨지 궁금해서요",                    # 확장·나·B1=4
    13: "매실청이라 향 부담도 없고 진짜 팟타이 맛일지 궁금",         # 타깃·나·B1=3
    21: "매실청이라니 맛이 상상돼서 진짜 팟타이일지 걱정이 좀 덜함",   # 타깃·나·B1=3
    32: "진짜 팟타이 맛일지가 젤 걱정인데 그걸 짚어주니 눈이 가긴 함", # 타깃·나·B1=1 회의
    38: "매실청으로 잡았다는 거 진짜 팟타이 맛일지 제일 궁금해요",     # 타깃·나·B1=5 호의
}

for tag, D in [("pass1", P1), ("pass2", P2), ("pass3", P3)]:
    json.dump([{"pid": w["pid"], "e2": D[w["pid"]]} for w in work],
              open(f"{SP}/e2_{tag}.json", "w"), ensure_ascii=False, indent=1)

finals = P3
texts = list(finals.values())
print("=== E2 3회 다듬기 검토 (깔끔 재추출 N=50) ===")
print(f"응답자 {len(texts)}명 (전체 50명 중 {len(texts)/50*100:.0f}% — 선택응답 현실 응답률)")
print("완전중복:", [t for t, c in Counter(texts).items() if c > 1] or "없음")
print("어미 4자 최다:", Counter(t[-4:] for t in texts).most_common(3))
lens = sorted(len(t) for t in texts)
print(f"길이 min/median/max: {lens[0]}/{lens[len(lens)//2]}/{lens[-1]}자")
wd = {w["pid"]: w for w in work}
mis = []
for pid, t in finals.items():
    e1 = wd[pid]["E1"][0]
    ga = any(k in t for k in ["5분", "간편", "편", "사먹", "귀찮", "자주"])
    na = any(k in t for k in ["매실", "고수", "향", "맛", "새콤", "팟타이", "반신반의"])
    if e1 == "가" and not ga: mis.append((pid, "가", t))
    if e1 == "나" and not na: mis.append((pid, "나", t))
print("E1-내용 불일치:", mis or "없음")
b1low = [(pid, wd[pid]["B1"], t) for pid, t in finals.items() if wd[pid]["B1"] <= 2]
print(f"회의자(B1≤2) {len(b1low)}명 — 미온/유보 톤 확인:")
for p, b, t in b1low: print(f"   pid{p}(B1={b}): {t}")
json.dump([{"pid": w["pid"], "e2": finals[w["pid"]]} for w in work],
          open(f"{SP}/e2_final.json", "w"), ensure_ascii=False, indent=1)
print(f"\ne2_final.json 저장 ({len(work)}명)")
