# -*- coding: utf-8 -*-
"""
E2 서술형 3회 다듬기 + 검토 — 3차 v1.5 표본(N=45).
선택응답 특성상 현실적 응답률(~27%)만 채움. B4실패자는 공란(부주의 응답자).
seg·E1·B1 다양성 확보. 3패스: P1 정형해체 → P2 구조·질감 다양화 → P3 성향정합·현실성.
"""
import json
from collections import Counter

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
rows = {r["respondent_id"]: r for r in json.load(open(f"{SP}/rows_final.json"))}
raw = {r["pid"]: r for r in json.load(open(f"{SP}/survey_raw.json"))}
prof = {p["pid"]: p for p in json.load(open(f"{SP}/prof.json"))}

# 현실적 응답 서브셋(12/45≈27%) — 가5·나7, B1 1~5, seg 혼합, B4실패 제외
SUBSET = [0, 14, 20, 24, 43, 1, 5, 11, 22, 31, 37, 39]

# e2_work.json 구성(맥락 동봉)
work = []
for pid in SUBSET:
    r, a, p = rows[pid], raw[pid], prof[pid]
    seg = "타깃" if r.get("_is_target") else ("확장" if r.get("_is_student") else "기타")
    work.append({"pid": pid, "seg": seg, "E1": r["E1"], "B1": r["B1"],
                 "향기피": p.get("향기피"), "매실청": p.get("매실청"),
                 "raw_E2": a.get("E2", "")})
json.dump(work, open(f"{SP}/e2_work.json", "w"), ensure_ascii=False, indent=1)

# ── Pass1: 정형 어미('~와닿아서/~궁금해서') 해체 ──
P1 = {
    0:  "혼자 살아서 5분이면 되는 게 제일 크다",
    14: "배달로 시켜 먹던 건데 집에서 5분이면 해결되니까",
    20: "5분이면 된다니 배달보단 낫겠지",
    24: "나가서 사 먹기 귀찮은데 5분이면 되니까 이게 낫다",
    43: "집에서 딱 5분이면 되는 게 좋다",
    1:  "고수 부담 없다는 게 딱 내 얘기라",
    5:  "매실청으로 새콤함 잡았다는데 진짜 팟타이 맛일지 궁금하다",
    11: "진짜 팟타이 맛일지 그게 걱정이었는데 그걸 짚어줘서",
    22: "매실청이면 그래도 맛 걱정은 좀 덜하다",
    31: "고수 향 부담 없다는 것 하나는 끌린다",
    37: "매실청으로 새콤함 잡았다는 게 진짜 궁금하다",
    39: "고수 냄새 싫은데 그게 없다니까",
}

# ── Pass2: 구조·길이·질감(구어·말줄임·ㅇㅇ) 다양화 ──
P2 = {
    0:  "혼자 살아서 5분이면 되는 게 제일 크죠",
    14: "배달로 시켜먹던 건데 집에서 5분이면 되니까 ㅇㅇ",
    20: "뭐 5분이면 된다니 배달보단 낫겠죠",
    24: "나가서 사먹기 귀찮은데 5분이면 되니까 이게 낫네요",
    43: "집에서 딱 5분이면 되는 게 진짜 좋아요",
    1:  "고수 부담 없다는 게 딱 내 얘기라서",
    5:  "매실청으로 새콤함 잡았다는데 진짜 팟타이 맛일지 궁금",
    11: "진짜 팟타이 맛일지 그게 걱정이었는데 딱 그 부분 짚어줘서",
    22: "매실청이면 그래도 맛 걱정은 좀 덜하니까... 반신반의지만",
    31: "고수 향 부담 없다는 거 하나는 끌리네요",
    37: "매실청으로 새콤함 잡았다는 거 궁금해서",
    39: "고수 냄새 진짜 싫은데 그게 없다니까 이건 됨",
}

# ── Pass3: 성향(B1/seg/E1) 정합·현실성 최종 ──
P3 = {
    0:  "혼자 살아서 5분이면 되는 게 제일 크죠",             # 타깃·가·B1=3 자취
    14: "배달로 시켜먹던 건데 집에서 5분이면 되니까 ㅇㅇ",     # 타깃·가·B1=4
    20: "뭐 5분이면 된다니 배달보단 낫겠죠",                # 타깃·가·B1=1 미온
    24: "나가서 사먹기 귀찮은데 5분이면 되니까 이게 낫네요",   # 기타·가·B1=4
    43: "집에서 딱 5분이면 되는 게 진짜 좋아요",            # 타깃·가·B1=5 호의
    1:  "고수 부담 없다는 게 딱 내 얘기라서",               # 타깃·나·B1=4
    5:  "매실청으로 새콤함 잡았다는데 진짜 팟타이 맛일지 궁금", # 기타·나·B1=4
    11: "진짜 팟타이 맛일지 그게 걱정이었는데 딱 그 부분 짚어줘서",  # 타깃·나·B1=3
    22: "매실청이면 그래도 맛 걱정은 좀 덜하니까... 반신반의지만",  # 기타·나·B1=2 회의
    31: "고수 향 부담 없다는 거 하나는 끌리네요 (나머진 글쎄)",   # 타깃·나·B1=1 회의
    37: "매실청으로 새콤함 잡았다는 게 궁금하긴 해요",              # 타깃·나·B1=5·기존유지(구조불일치)
    39: "고수 냄새 진짜 싫은데 그게 없다니까 이건 됨",           # 확장·나·B1=5 향0.95
}

for tag, D in [("pass1", P1), ("pass2", P2), ("pass3", P3)]:
    json.dump([{"pid": w["pid"], "e2": D[w["pid"]]} for w in work],
              open(f"{SP}/e2_{tag}.json", "w"), ensure_ascii=False, indent=1)

finals = P3
texts = list(finals.values())
print("=== E2 3회 다듬기 검토 (3차 v1.5) ===")
print(f"응답자 {len(texts)}명 (전체 45명 중 {len(texts)/45*100:.0f}% — 선택응답 현실 응답률)")
print("완전중복:", [t for t, c in Counter(texts).items() if c > 1] or "없음")
print("어미 4자 최다:", Counter(t[-4:] for t in texts).most_common(3))
lens = sorted(len(t) for t in texts)
print(f"길이 min/median/max: {lens[0]}/{lens[len(lens)//2]}/{lens[-1]}자")

wd = {w["pid"]: w for w in work}
mis = []
for pid, t in finals.items():
    e1 = wd[pid]["E1"][0]      # '가' or '나'
    ga = any(k in t for k in ["5분", "간편", "빠르", "배달", "나가", "혼자"])
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
