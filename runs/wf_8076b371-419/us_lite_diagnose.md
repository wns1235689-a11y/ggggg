# 해외 패널 설문 v1.1 §8 리허설 엔진 lite — 진단 (run wf_8076b371-419)

## ⓪ 문서 지위 · 필수 경고
**LLM 합성 응답 · 비실측 · 인용 불가.** 이 문서는 설문 문항의 함정·어휘 이해·선택지 누락·가격 사다리 위치를
발행 전에 점검하는 **진단 전용** 산출물이다. 여기의 어떤 비율도 미국 소비자의 실제 비율이 아니며 PT 어디에도 쓰지 않는다
(해외 패널 설문 v1.1 §8 규칙). 페르소나 사전분포는 전부 [규범근사]이고 실측 앵커가 없다.

- 저널: `/home/user/ggggg/runs/wf_8076b371-419/journal.jsonl`  · 풀: `/home/user/ggggg/runs/wf_8076b371-419` (RUN_SEED=80928493, N(풀)=50) · 결과 회수 50명
- 형식: 한 페르소나(에이전트 1개)가 '비슷한 미국 소비자 10명'의 분포를 추정(VS) + 본인 자유응답. realized = 시드 결정론 표집(1인 1표). 판정 없음, 진단만.


## 요약 — 고치는 기준(①~④) 판독
- ⚠ ① 'maesil' 모름 64% ≥ 25% → 괄호 풀이 검토
- ⚠ ① 'green plum syrup' 모름 62% ≥ 25% → 괄호 풀이 검토
- ⚠ ① 'tamarind' 모름 34% ≥ 25% → 괄호 풀이 검토
- ⚠ ④ $7.99 Yes 8% ≤ 10% → 천장이 높음, 사다리 아래로
- ⑤⑥은 한계로 기록만(아래 6·7절).
- 임계: {"①_term_unclear_share": 0.25, "②_a_little_mass": 0.5, "③_other_share": 0.1, "④_floor_yes_499": 0.9, "④_ceiling_yes_799": 0.1}


## 1. 문항별 분포(참고 — 수준 인용 금지)


**Q1_dist** 태국·동남아 음식 빈도 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Never | 10.4% | ███ | 8 |
| A few times a year | 34.0% | ████████ | 16 |
| About once a month | 27.4% | ███████ | 13 |
| A few times a month | 20.0% | █████ | 7 |
| Once a week or more | 8.2% | ██ | 6 |

**Q2_dist** 집에서 팟타이 조리 경험 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, more than once | 21.6% | █████ | 6 |
| Yes, once or twice | 25.8% | ██████ | 14 |
| No, never | 52.6% | █████████████ | 30 |

**Q2a_dist** 못 만드는 이유(Q2 비해당자 분모) (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Hard to find ingredients | 18.0% | █████ | 8 |
| Don't know how / complicated | 16.7% | ████ | 11 |
| Too much time or effort | 15.9% | ████ | 5 |
| Don't like the taste | 5.6% | █ | 3 |
| Rather restaurant / delivery | 36.2% | █████████ | 19 |
| Other | 7.6% | ██ | 4 |

**Q3_dist** 향·소스·향신료 때문에 피함(게이트 C 향기피 3점 대응) (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, very much | 10.8% | ███ | 4 |
| Yes, a little | 23.2% | ██████ | 9 |
| No | 66.0% | ████████████████ | 37 |

**Q4_dist** 최근 12개월 냉동 태국 음식 구매 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes | 28.6% | ███████ | 15 |
| No | 65.0% | ████████████████ | 32 |
| Not sure | 6.4% | ██ | 3 |

**Q5_dist** 콘셉트 관심 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| 1 Not at all | 16.0% | ████ | 6 |
| 2 | 23.2% | ██████ | 12 |
| 3 | 30.4% | ████████ | 14 |
| 4 | 22.4% | ██████ | 13 |
| 5 Very interested | 8.0% | ██ | 5 |

**Q8_dist** 한식·Bibigo 인지 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, and I know Bibigo | 37.2% | █████████ | 18 |
| Had Korean food, don't know brands | 35.8% | █████████ | 21 |
| No | 27.0% | ███████ | 11 |

## 2. 진단 ① Q5 어휘 이해 — 'unclear' 로 꼽힌 어휘(페르소나 비율)

| 어휘 | 모르겠다로 꼽은 페르소나 | 비율 |
|---|---:|---:|
| maesil | 32 | 64% ⚠ |
| green plum syrup | 31 | 62% ⚠ |
| tamarind | 17 | 34% ⚠ |
| pad thai | 3 | 6% |

- Q5_reading에 '모르겠다·들어본 적 없다·대충 ~같은 것' 류 표현이 있는 페르소나: 12/50 (24%)
  - pid2: “It's a microwave frozen pad thai for one, but they swapped the tamarind for some Korean plum syrup and left out the cilantro so it's not as intense. Basically a toned-down pad thai for people like me who don't love strong herbs.”
  - pid3: “It's a microwave frozen pad thai, one serving, where they swapped the tamarind for some Korean plum syrup and left out the cilantro so it's milder. Sounds like it's aimed at people who don't usually like Thai food.”
  - pid5: “It's a frozen microwave pad thai noodle meal for one, made with some kind of Korean plum syrup instead of the usual sauce and no cilantro, so it's supposed to be less strong tasting for people who don't usually eat Thai.”
  - pid10: “It's a frozen microwave pad thai for one person, made milder by using some kind of Korean plum syrup instead of tamarind and leaving out the cilantro.”
  - pid15: “It's a frozen microwave pad thai for one, where they swapped out the tamarind for some kind of Korean plum syrup and left out the cilantro so it's not as strong tasting.”
  - pid20: “It's a microwave frozen pad thai for one, but the sauce uses a Korean plum syrup instead of tamarind and there's no cilantro, so it's a milder, toned-down version for people who don't like strong flavors.”
- maesil/green plum syrup 모름: 한식친숙 낮음(n=20) 100% vs 높음(n=19) 5% (페르소나 특성 → 어휘 반응 전사 여부, 기록)

## 3. 진단 ② Q3 'A little' 쏠림

- 믿음질량: Very much 10.8% / A little 23.2% / No 66.0%  · realized: 4/9/37 (n=50)
- 한국 게이트 C 대응치(참고 방향만): '매우' 33.0% / '조금'까지 71.6%
- 임계 미달(쏠림 없음)
  - 페르소나 기피 매우높음(>0.75) n=4: Very much 60% / A little 30% / No 10%
  - 페르소나 보통(0.42~0.58) n=7: Very much 14% / A little 43% / No 43%
  - 페르소나 매우낮음(<0.25) n=20: Very much 0% / A little 14% / No 86%

## 4. 진단 ③ Q2a 'Other' 비율(선택지 누락)

- 'Other' 믿음질량 7.6% · Other 문구를 쓴 페르소나 20/50
  - pid2: “I always have to pick out the cilantro anyway”
  - pid4: “Never really thought about making it”
  - pid5: “Never really tried it, not my kind of food”
  - pid6: “just never got around to trying it”
  - pid7: “Never really had Thai food, it's just not something we eat around here”
  - pid9: “Never really thought about it, it's just not something we eat”
  - pid10: “Don't eat it often enough to bother learning”
  - pid12: “Never really tried it, it's just not something we eat around here”
  - pid13: “just haven't gotten around to it yet”
  - pid19: “I don't really cook, I live alone”
  - pid18: “Just never really thought about making it”
  - pid22: “Never really thought about making it”
  - pid24: “Never really thought to try it”
  - pid28: “Just never got around to it”
  - pid29: “Never really tried Thai food, so it never crossed my mind”
- 임계 미달

## 5. 진단 ④ Q6 가격 사다리 바닥·천장

| 가격 | Yes 믿음질량 | realized Yes n/N |
|---|---:|---:|
| $4.99 | 49% | 30/50 (60%) |
| $5.99 | 32% | 23/50 (46%) |
| $6.99 | 17% | 8/50 (16%) |
| $7.99 | 8% | 3/50 (6%) |
- 비단조 분포(가격↑인데 Yes 인원↑)를 낸 페르소나: 0/50 (위생 지표, 기록)
- 한국 게이트 C 대응 자리: $4.99 ↔ 6,900원 65%(방향만)
- ⚠ 임계 초과

## 6. 진단 ⑤ Q3 → Q5 일관성 압력(기록만)

- r(페르소나 고수기피, Q3 Very much 질량) = +0.84  ← 특성→문항 전사 강도
- r(Q3 Very much 질량, Q5 4~5점 질량) = +0.01  ← Q3가 Q5로 그대로 전사되는지
- r(페르소나 고수기피, Q5 4~5점 질량) = +0.09
- §4-5 축(향 기피층 Q3 Very much vs 나머지)의 Q5 4~5점: 30% (n=4) vs 30% (n=46) — 한국 52% vs 39%와 같은 축, 방향만 기록. 방향은 프롬프트에 심지 않았으므로 LLM prior.
- Q3_dist 최빈 패턴 점유 44% (동질성 잔존도)
- Q5_dist 최빈 패턴 점유 20% (동질성 잔존도)
- Q1_dist 최빈 패턴 점유 28% (동질성 잔존도)

## 7. 진단 ⑥ Q7 자유응답의 Q5 문장 에코(기록만)

- 콘셉트 문장 내용어와의 Jaccard 평균 0.08, 3-gram 공유 ≥2 또는 Jaccard ≥0.25: 0/50
- 콘셉트 핵심어 재사용 비율: milder/mild 38%, maesil/plum 54%, cilantro 58%, tamarind 18%, 5 minutes/microwave 4%
- Q7 원문 전부(국가=US, 합성):
  - pid1 (J=0.18, tri=0): “I'd try it out of curiosity about the plum syrup, but honestly I like cilantro and the tangy tamarind flavor, so a "milder" pad thai doesn't really grab me unless the reviews say it tastes great.”
  - pid11 (J=0.16, tri=0): “I'm curious about the maesil twist since I use it in Korean cooking, but I actually like cilantro and strong flavors, and I'd rather make pad thai myself than pay more than five bucks for one small frozen serving.”
  - pid36 (J=0.16, tri=0): “Probably not. I make pad thai from scratch and I actually like the tamarind and cilantro, so a toned-down frozen version isn't for me, though I might grab one on sale out of curiosity about the plum syrup.”
  - pid38 (J=0.15, tri=0): “I like that it's easy and has no cilantro, and I'd trust the Korean plum syrup, but I'd only grab it if the fish sauce taste isn't strong since I've never really cared for Thai food.”
  - pid39 (J=0.13, tri=0): “The maesil twist sounds fun and I'd try it once if it was under five bucks, but I actually like cilantro and strong flavors so a "milder" pad thai isn't really selling me.”
  - pid41 (J=0.13, tri=0): “I like the maesil idea, but I actually love cilantro and strong flavors, so a milder single serving for over five bucks probably isn't worth it when I've got a family to feed.”
  - pid15 (J=0.12, tri=0): “No cilantro and only five minutes in the microwave is honestly what would get me to try it, as long as it doesn't taste weird or overly sweet from the plum syrup.”
  - pid14 (J=0.12, tri=0): “I usually make pad thai myself and I like the tamarind and herbs, so I'd only grab this if it was cheap and I was curious how the plum syrup tastes.”
  - pid16 (J=0.12, tri=0): “I like pad thai with the tamarind tang and lots of herbs, and I make it from scratch anyway, so a toned-down frozen one probably isn't for me, though I might grab it once at around five bucks just to see what the plum syrup tastes like.”
  - pid35 (J=0.11, tri=0): “I'd try it for the maesil twist if it's around $5, but I actually like strong Thai flavors and cilantro, so "milder" isn't really selling it to me, and over $6 I'd just get takeout or make my own.”
  - pid31 (J=0.10, tri=0): “I'd try it because I like maesil and want an easy dinner, but I don't really need it milder, so if it's bland or over $6 I'd just grab Bibigo dumplings or order real pad thai instead.”
  - pid13 (J=0.10, tri=0): “I'd maybe try it once if it was on sale under five bucks out of curiosity about the maesil, but I make my own pad thai cheaper and I actually like the tamarind and cilantro, so a toned-down version isn't really for me.”
  - pid21 (J=0.10, tri=0): “It'd be easy for a quick dinner, but I actually like the strong stuff and cilantro, so a watered-down pad thai doesn't really sell me.”
  - pid29 (J=0.09, tri=0): “I like Korean flavors and maesil, and a quick microwave meal suits me, so I'd try it once if it looked good, though I'm honestly not sure I need it to be milder.”
  - pid23 (J=0.09, tri=0): “Honestly I like the cilantro and the tangy tamarind, and I can make a bigger batch of pad thai at home for the family for less, so I'd only grab this if it was on sale for a quick lunch.”
  - pid25 (J=0.09, tri=0): “I usually just make my own pad thai, so I'd only grab this if the reviews say the noodles don't turn to mush and the plum sauce actually tastes good, not just sweet.”
  - pid33 (J=0.09, tri=0): “Probably wouldn't buy it, since I can make a whole pot of pad thai for the family for less than a few of these cost, and I actually like the cilantro and the tamarind taste.”
  - pid37 (J=0.09, tri=0): “I'd try it if it was on sale and the reviews said it actually tastes like pad thai, but I'm not sure what plum syrup would do to it, so I'd probably stick with something I know.”
  - pid20 (J=0.09, tri=0): “I'd maybe try it once for an easy dinner if it was around five bucks, but I actually like cilantro and the tangy tamarind flavor, so a milder version doesn't really appeal to me.”
  - pid8 (J=0.09, tri=0): “I'd grab it for an easy dinner if the reviews were good and it actually tasted like pad thai, but I don't really need it milder since I'm fine with cilantro and stronger flavors.”
  - pid49 (J=0.09, tri=0): “I know maesil and I'd try it if it was around five bucks, but I like the cilantro and the bold flavor so "milder" doesn't really sell me, and at seven or eight dollars I'd just go get takeout.”
  - pid3 (J=0.08, tri=0): “I'd probably skip it, since I actually like the tamarind and cilantro and I'd rather make pad thai myself, but I might grab one to try if it was on sale and the reviews said it tasted good.”
  - pid7 (J=0.08, tri=0): “If it was on sale for under five bucks I might grab one to see what pad thai even tastes like, but I usually just cook at home so I'm not paying much for a single frozen meal.”
  - pid32 (J=0.08, tri=0): “I'd grab it because it's easy for a busy night, but honestly I love cilantro and bold flavors so a "milder" pad thai kind of sounds like a watered-down version of what I'd get from my local Thai place.”
  - pid2 (J=0.08, tri=0): “No cilantro is a huge plus for me, so I'd grab it if it's around five bucks and the plum sauce doesn't end up too sweet.”
  - pid26 (J=0.07, tri=0): “I'd try it if it was on sale for under five bucks, but I don't really need it milder since I like cilantro and the regular flavor anyway.”
  - pid17 (J=0.07, tri=0): “I'd grab it if it was around five bucks and easy for a quick dinner, but I don't really need it milder since I don't mind cilantro or strong flavors.”
  - pid22 (J=0.07, tri=0): “I'd maybe try it if it was on sale for under five bucks, but I don't really need it milder and I'm not paying seven dollars for a single frozen meal.”
  - pid44 (J=0.07, tri=0): “I'd maybe grab it for an easy dinner if it was around five bucks, but honestly I like cilantro and the tangy flavor, so a "milder" version sounds a little bland to me.”
  - pid28 (J=0.07, tri=0): “I make pad thai from scratch for way less money, so I'd only grab this if it was on sale for under five bucks and the maesil actually tasted good, not just sweet.”
  - pid43 (J=0.06, tri=0): “Honestly I like cilantro and bold flavors and I'd usually just cook something myself, so I'd only grab it if I needed a fast lunch and was curious what the plum syrup tastes like.”
  - pid4 (J=0.06, tri=0): “I'd try it if it was around five bucks or on sale since I like maesil, but I don't really need it milder and anything over six dollars for one frozen meal is too much for me.”
  - pid6 (J=0.06, tri=0): “I'd maybe grab it if it was on sale for under five bucks, but honestly I can make a bigger batch of pad thai myself for way cheaper and I don't mind cilantro anyway.”
  - pid46 (J=0.06, tri=0): “I like maesil so I'd try it once if it's around five bucks, but at seven or eight dollars for one small serving I'd just go get takeout or grab a Bibigo pack instead.”
  - pid45 (J=0.06, tri=0): “I'd grab it if it's around five bucks and the noodles don't come out gummy, since I love maesil, but if it just tastes sweet and bland I'd go back to ordering real pad thai.”
  - pid19 (J=0.05, tri=0): “I like that there's no cilantro, but I'd only grab it if it was under five bucks or on sale, otherwise I'd just get the cheaper frozen stuff.”
  - pid27 (J=0.04, tri=0): “I'd try it because the maesil twist sounds interesting, but honestly I like cilantro and bold flavors, so if it tastes too mild or sweet I wouldn't buy it again.”
  - pid30 (J=0.04, tri=0): “The maesil twist sounds interesting and I'd try it once, but I actually like cilantro and bold flavors, so if it tastes too mild or sweet I wouldn't buy it again.”
  - pid48 (J=0.04, tri=0): “I'd try it because the maesil twist sounds interesting, but I actually like cilantro and bold flavors, so if it tastes too mild or sweet I wouldn't buy it again.”
  - pid10 (J=0.04, tri=0): “No cilantro is a big plus for me, but I usually cook from scratch and wouldn't pay more than about five bucks for one frozen meal unless it was on sale.”
  - pid42 (J=0.04, tri=0): “No cilantro is a big plus for me, but I'd only grab it if it's around five bucks and doesn't still taste fishy, since one serving doesn't go far with my family.”
  - pid34 (J=0.04, tri=0): “I'd maybe try it on sale since I like maesil, but honestly I'd rather make my own from scratch for less than $5 a serving, and one serving doesn't help when I'm feeding the whole family.”
  - pid40 (J=0.02, tri=0): “I'd try it if it was on sale for under five bucks, but at seven or eight dollars I'd just grab a cheaper frozen meal or save up for takeout.”
  - pid24 (J=0.02, tri=0): “Probably not, since I'd rather cook noodles myself for a lot less than five bucks a serving, but I might grab one if it was on sale.”
  - pid0 (J=0.02, tri=0): “Honestly it comes down to price, if it's under five bucks or on sale I'd give it a shot, but anything more and I'd just grab a cheaper frozen meal.”
  - pid18 (J=0.02, tri=0): “The maesil idea sounds cool and I'd try it once if it's around five bucks, but anything more and I'd just cook noodles myself for way cheaper.”
  - pid5 (J=0.02, tri=0): “Probably wouldn't buy it, since I can cook my own noodles cheaper and I'm not paying five or six bucks to gamble on a flavor I might not like, unless it was on sale for like three dollars.”
  - pid9 (J=0.00, tri=0): “Probably not, since I've never cared for that kind of food, but if a friend said it was mild and tasted good I might pick one up to try.”
  - pid12 (J=0.00, tri=0): “Honestly it'd have to be on sale for like three or four bucks for me to take a chance on something I've never had, otherwise I'm sticking to what I know.”
  - pid47 (J=0.00, tri=0): “If it was under five bucks and actually filled me up I'd grab it, but at seven or eight dollars I'd just get takeout or something cheaper.”

## 8. 부수 기록 — Q4a 브랜드·Q10 검색어(합성, 실측 아님)

- Q4a 언급 브랜드·매장: {'trader joe': 44, 'walmart': 5}
- Q4a 원문(있는 것만):
  - pid0: “Got the Trader Joe's frozen pad thai, it was fine for the price but kind of sweet and mushy.”
  - pid1: “Trader Joe's frozen pad thai, it was decent for a quick lunch but a little sweet.”
  - pid2: “Got the Trader Joe's frozen pad thai, it was fine but the sauce was kinda too sweet and fishy for me.”
  - pid3: “Got a frozen pad thai at Trader Joe's, it was okay for a quick lunch but kind of sweet and mushy.”
  - pid4: “Got the Trader Joe's frozen pad thai on a trip to the city, it was pretty good for the price.”
  - pid5: “Grabbed a frozen pad thai at Walmart once on sale, it was too sweet and kind of weird, wouldn't get it again.”
  - pid6: “Trader Joe's frozen pad thai, it was fine for the price but kinda sweet and mushy.”
  - pid8: “Got the Trader Joe's frozen pad thai, it was pretty good for a quick lunch, a little sweet though.”
  - pid9: “Got a frozen pad thai at Walmart for my husband to try, it was too sweet and kind of mushy.”
  - pid10: “Grabbed a Saffron Road pad thai at Walmart once, it was okay but kind of sweet and small for the price.”
  - pid11: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and the noodles got a little mushy.”
  - pid12: “Got a frozen pad thai at Walmart one time, it was okay but kind of sweet.”
  - pid13: “Trader Joe's frozen pad thai, it was fine for the price but kind of sweet and the noodles got mushy.”
  - pid14: “Trader Joe's frozen pad thai, it was okay for a quick lunch but kind of sweet and mushy.”
  - pid15: “I got the Trader Joe's frozen pad thai, it was okay but kind of sweet and mushy.”
  - pid16: “Got the Trader Joe's frozen pad thai once. It was fine for a quick lunch, but kind of sweet and the noodles went mushy.”
  - pid17: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet.”
  - pid19: “Trader Joe's frozen pad thai, it was fine for the price but kinda sweet and mushy.”
  - pid18: “Got the Trader Joe's pad thai once, it was alright but kinda sweet and mushy.”
  - pid20: “Trader Joe's frozen pad thai. It was fine for a quick lunch but kind of sweet and the noodles got a little mushy.”
  - pid21: “Got a Trader Joe's frozen pad thai once, it was alright for a quick lunch but kinda sweet.”
  - pid22: “Trader Joe's frozen pad thai, it was decent for the price but kind of sweet.”
  - pid23: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and the noodles got a little mushy.”
  - pid24: “Got the Trader Joe's frozen pad thai once, it was okay but kind of sweet and mushy.”
  - pid25: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kinda sweet and the noodles got mushy.”
  - pid26: “Trader Joe's frozen pad thai, it was decent for the price but kind of sweet.”
  - pid27: “Got the Trader Joe's pad thai once, it was fine for a quick dinner but kind of sweet and the noodles got clumpy.”
  - pid28: “Trader Joe's pad thai, decent for a quick lunch but the noodles got gummy.”
  - pid29: “Grabbed a frozen pad thai at Trader Joe's once, it was okay but a little sweet.”
  - pid30: “Got the Trader Joe's frozen pad thai, it was fine for a quick lunch but kinda sweet and mushy.”
  - pid31: “Got the Trader Joe's frozen pad thai, it was decent for a quick lunch but kinda sweet.”
  - pid32: “Got the Trader Joe's frozen pad thai, it was pretty good for a quick lunch but a little sweet.”
  - pid33: “Got the Trader Joe's frozen pad thai once, it was okay but kind of sweet and mushy.”
  - pid34: “Got a frozen pad thai at Walmart, it was okay but kind of sweet and mushy.”
  - pid35: “Trader Joe's pad thai, it was fine for a quick lunch but kind of sweet and the noodles got a little mushy.”
  - pid36: “Trader Joe's frozen pad thai, it was okay for a quick lunch but way too sweet and the noodles got mushy.”
  - pid37: “Trader Joe's frozen pad thai, it was okay but a little sweet and the noodles got kind of mushy.”
  - pid39: “Got the Trader Joe's frozen pad thai, it was decent for the price but kinda sweet and the noodles got a little mushy.”
  - pid38: “Tried a Trader Joe's frozen pad thai once and it was okay, a little too sweet for me.”
  - pid40: “Got the Trader Joe's frozen pad thai, it was fine for the price but kinda sweet and mushy.”
  - pid41: “Got the Trader Joe's pad thai, it was decent for the price but kind of sweet and mushy.”
  - pid42: “Got a Trader Joe's pad thai once, it was okay but kind of sweet and mushy.”
  - pid43: “Got the Trader Joe's frozen pad thai once, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid44: “Got the Trader Joe's pad thai, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid45: “Trader Joe's frozen pad thai, it was fine for a quick dinner but kind of sweet and the noodles got mushy.”
  - pid46: “Got the Trader Joe's pad thai, it was okay for the price but a little sweet and the noodles got gummy.”
  - pid47: “Got a Trader Joe's frozen pad thai, it was decent for the price but kinda sweet.”
  - pid49: “Got the Trader Joe's frozen pad thai, it was okay for the price but a little sweet.”
  - pid48: “Trader Joe's pad thai, it was fine for a quick lunch but kind of sweet and the noodles got a little mushy.”
- Q10 검색어 상위: [('pad', 49), ('thai', 49), ('frozen', 48), ('microwave', 24), ('maesil', 14), ('mild', 11), ('cheap', 10), ('cilantro', 9), ('korean', 8), ('plum', 8), ('sauce', 8), ('single', 2), ('serving', 2), ('fusion', 2)]
- Q10 비움(선택 문항 건너뜀): 2/50
