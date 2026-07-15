# -*- coding: utf-8 -*-
"""E2 서술형 3회 다듬기 + 검토 (v1.5 표본). 동일 방법론, 신규 응답자."""
import json
from collections import Counter

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
work = json.load(open(f"{SP}/e2_work.json"))

# Pass1: 정형 어미 해체·자연화
P1 = {
    9:  "그냥 간편하게 5분이면 되는 게 낫죠",
    12: "매실청은 익숙해서 어떤 맛일지 그려져서",
    15: "매실청이라 익숙하고 향 부담 덜었다니 믿음이 가고",
    17: "그냥 5분에 되는 간편함 정도",
    18: "고수 향 없이 새콤하다니 나한테 딱이라",
    20: "매실청이면 맛이 대충 그려지니까 덜 부담스럽고",
    33: "혼자 사는데 5분이면 되니까",
    37: "어차피 자주 시켜 먹는데 이게 더 빠르니까",
    44: "매실청으로 진짜 팟타이 맛을 낼 수 있을지가 제일 궁금해서",
    45: "매실청으로 잡은 새콤함이 진짜 맛일지 궁금하고",
}

# Pass2: 구조/길이 다양화 + 인간질감
P2 = {
    9:  "그냥 간편하게 5분이면 되는 게 낫죠",
    12: "매실청은 익숙해서 어떤맛일지 그려짐",
    15: "매실청이라 익숙하고 향 부담 덜었다니 믿음이 감",
    17: "뭐 그냥 5분에 되는 간편함 정도?",
    18: "고수 향 없이 새콤하다니 나한테 딱이라",
    20: "매실청이면 맛이 대충 그려지니까 덜 부담스러움",
    33: "혼자사는데 5분이면 되니까요",
    37: "어차피 자주 시켜먹는데 이게 더 빠르니까 ㅇㅇ",
    44: "매실청으로 진짜 팟타이 맛 낼 수 있을지가 젤 궁금해서",
    45: "매실청으로 새콤함 잡았다는데 진짜 맛일지 좀 반신반의",
}

# Pass3: 성향(B1/세그/E1) 정합·현실성
P3 = {
    9:  "그냥 간편하게 5분이면 되는 게 낫죠",              # 확장,가,B1=5
    12: "매실청은 익숙해서 어떤맛일지 그려짐",             # 타깃,나,B1=3,향0.11
    15: "매실청이라 익숙하고 향 부담 덜었다니 믿음이 감",   # 타깃,나,B1=3
    17: "뭐 그냥 5분에 되는 간편함 정도?",                # 기타,가,B1=1 미온
    18: "고수 향 없이 새콤하다니 나한테 딱이라",           # 기타,나,향0.68
    20: "매실청이면 맛이 대충 그려지니까 덜 부담스러움",    # 타깃,나,B1=3,향0.19
    33: "혼자사는데 5분이면 되니까요",                     # 타깃,가,1인가구
    37: "어차피 자주 시켜먹는데 이게 더 빠르니까 ㅇㅇ",      # 타깃,가,B1=2 미온
    44: "매실청으로 진짜 팟타이 맛 낼 수 있을지가 젤 궁금해서",  # 타깃,나,B1=5
    45: "매실청으로 새콤함 잡았다는데 진짜 맛일지 좀 반신반의",  # 확장,나,B1=3
}

for tag, D in [("pass1", P1), ("pass2", P2), ("pass3", P3)]:
    json.dump([{"pid": w["pid"], "e2": D[w["pid"]]} for w in work],
              open(f"{SP}/e2_{tag}.json", "w"), ensure_ascii=False, indent=1)

finals = P3
texts = list(finals.values())
print("=== E2 3회 다듬기 검토 (v1.5) ===")
print(f"응답자 {len(texts)}명 (전체 47명 중 {len(texts)/47*100:.0f}%)")
print("완전중복:", [t for t, c in Counter(texts).items() if c > 1] or "없음")
print("어미 4자 최다:", Counter(t[-4:] for t in texts).most_common(3))
lens = sorted(len(t) for t in texts)
print(f"길이 min/median/max: {lens[0]}/{lens[len(lens)//2]}/{lens[-1]}자")
wd = {w["pid"]: w for w in work}
mis = []
for pid, t in finals.items():
    e1 = wd[pid]["E1"][0]
    ga = any(k in t for k in ["5분", "간편", "빠르", "빨리", "낫죠"])
    na = any(k in t for k in ["매실", "고수", "향", "맛", "새콤", "그려", "반신반의"])
    if e1 == "가" and not ga: mis.append((pid, "가", t))
    if e1 == "나" and not na: mis.append((pid, "나", t))
print("E1-내용 불일치:", mis or "없음")
b1low = [(pid, wd[pid]["B1"], t) for pid, t in finals.items() if wd[pid]["B1"] <= 2]
print(f"회의자(B1≤2) {len(b1low)}명:")
for p, b, t in b1low: print(f"   pid{p}(B1={b}): {t}")

json.dump([{"pid": w["pid"], "e2": finals[w["pid"]]} for w in work],
          open(f"{SP}/e2_final.json", "w"), ensure_ascii=False, indent=1)
print(f"\ne2_final.json 저장 ({len(work)}명)")
