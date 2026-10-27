# 해외 패널 설문 v1.1 §8 리허설 엔진 lite — 진단 (run wf_c5375cc0-fd2)

## ⓪ 문서 지위 · 필수 경고
**LLM 합성 응답 · 비실측 · 인용 불가.** 이 문서는 설문 문항의 함정·어휘 이해·선택지 누락·가격 사다리 위치를
발행 전에 점검하는 **진단 전용** 산출물이다. 여기의 어떤 비율도 미국 소비자의 실제 비율이 아니며 PT 어디에도 쓰지 않는다
(해외 패널 설문 v1.1 §8 규칙). 페르소나 사전분포는 전부 [규범근사]이고 실측 앵커가 없다.

- 저널: `/home/user/ggggg/runs/wf_c5375cc0-fd2/journal.jsonl`  · 풀: `/home/user/ggggg/runs/wf_c5375cc0-fd2` (RUN_SEED=80928493, N(풀)=50) · 결과 회수 50명
- 형식: 한 페르소나(에이전트 1개)가 '비슷한 미국 소비자 10명'의 분포를 추정(VS) + 본인 자유응답. realized = 시드 결정론 표집(1인 1표). 판정 없음, 진단만.


## 요약 — 고치는 기준(①~④) 판독
- ⚠ ① 'maesil' 모름 64% ≥ 25% → 괄호 풀이 검토
- ⚠ ① 'green plum syrup' 모름 60% ≥ 25% → 괄호 풀이 검토
- ⚠ ④ $7.99 Yes 7% ≤ 10% → 천장이 높음, 사다리 아래로
- ⑤⑥은 한계로 기록만(아래 6·7절).
- 임계: {"①_term_unclear_share": 0.25, "②_a_little_mass": 0.5, "③_other_share": 0.1, "④_floor_yes_499": 0.9, "④_ceiling_yes_799": 0.1}


## 1. 문항별 분포(참고 — 수준 인용 금지)


**Q1_dist** 태국·동남아 음식 빈도 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Never | 11.0% | ███ | 9 |
| A few times a year | 34.2% | █████████ | 15 |
| About once a month | 27.6% | ███████ | 12 |
| A few times a month | 19.2% | █████ | 9 |
| Once a week or more | 8.0% | ██ | 5 |

**Q2_dist** 집에서 팟타이 조리 경험 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, more than once | 19.8% | █████ | 5 |
| Yes, once or twice | 25.4% | ██████ | 15 |
| No, never | 54.8% | ██████████████ | 30 |

**Q2a_dist** 못 만드는 이유(Q2 비해당자 분모) (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Hard to find ingredients | 18.4% | █████ | 9 |
| Don't know how / complicated | 17.7% | ████ | 10 |
| Too much time or effort | 15.2% | ████ | 10 |
| Don't like the taste | 4.4% | █ | 0 |
| Rather restaurant / delivery | 37.2% | █████████ | 18 |
| Other | 7.1% | ██ | 3 |

**Q3_dist** 향·소스·향신료 때문에 피함(게이트 C 향기피 3점 대응) (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, very much | 10.0% | ██ | 4 |
| Yes, a little | 23.6% | ██████ | 9 |
| No | 66.4% | █████████████████ | 37 |

**Q4_dist** 최근 12개월 냉동 태국 음식 구매 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes | 28.2% | ███████ | 14 |
| No | 66.0% | ████████████████ | 32 |
| Not sure | 5.8% | █ | 4 |

**Q5_dist** 콘셉트 관심 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| 1 Not at all | 15.8% | ████ | 6 |
| 2 | 24.0% | ██████ | 14 |
| 3 | 30.4% | ████████ | 11 |
| 4 | 23.0% | ██████ | 15 |
| 5 Very interested | 6.8% | ██ | 4 |

**Q8_dist** 한식·Bibigo 인지 (믿음질량% | realized n/50)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, and I know Bibigo | 37.2% | █████████ | 17 |
| Had Korean food, don't know brands | 37.4% | █████████ | 24 |
| No | 25.4% | ██████ | 9 |

## 2. 진단 ① Q5 어휘 이해 — 'unclear' 로 꼽힌 어휘(페르소나 비율)

| 어휘 | 모르겠다로 꼽은 페르소나 | 비율 |
|---|---:|---:|
| maesil | 32 | 64% ⚠ |
| green plum syrup | 30 | 60% ⚠ |
| tamarind | 8 | 16% |
| pad thai | 3 | 6% |
| fish sauce | 1 | 2% |

- Q5_reading에 '모르겠다·들어본 적 없다·대충 ~같은 것' 류 표현이 있는 페르소나: 8/50 (16%)
  - pid5: “It's a microwave frozen pad thai, a noodle dish, but they took out the cilantro and swapped the sour stuff for some Korean plum syrup so it doesn't taste as strong. Sounds like it's meant for people who don't usually eat Thai food.”
  - pid8: “It's a frozen microwave pad thai for one, but they swapped the usual sour tamarind sauce for some kind of Korean plum syrup and left out the cilantro, so it's supposed to taste milder.”
  - pid12: “So it's a frozen microwave dinner of pad thai, which is some kind of Thai noodle dish, but they swapped the sour stuff for a Korean plum syrup so it's sweeter and not as strong. Basically a starter version for people who haven't had Thai food.”
  - pid14: “It's a frozen microwave pad thai for one person. They've swapped the tamarind for a Korean plum syrup and left out the cilantro, so it's a milder version for people who don't like strong Thai flavors.”
  - pid20: “It's a microwave frozen pad thai for one, but they swapped the tamarind for some Korean plum syrup and left out the cilantro so it tastes milder for people who don't like strong Thai flavors.”
  - pid37: “It's a frozen microwave pad thai for one, but they swapped the usual sour tamarind for some kind of Korean plum syrup and left out the cilantro so it's milder.”
- maesil/green plum syrup 모름: 한식친숙 낮음(n=20) 100% vs 높음(n=19) 5% (페르소나 특성 → 어휘 반응 전사 여부, 기록)

## 3. 진단 ② Q3 'A little' 쏠림

- 믿음질량: Very much 10.0% / A little 23.6% / No 66.4%  · realized: 4/9/37 (n=50)
- 한국 게이트 C 대응치(참고 방향만): '매우' 33.0% / '조금'까지 71.6%
- 임계 미달(쏠림 없음)
  - 페르소나 기피 매우높음(>0.75) n=4: Very much 60% / A little 30% / No 10%
  - 페르소나 보통(0.42~0.58) n=7: Very much 11% / A little 46% / No 43%
  - 페르소나 매우낮음(<0.25) n=20: Very much 0% / A little 14% / No 86%

## 4. 진단 ③ Q2a 'Other' 비율(선택지 누락)

- 'Other' 믿음질량 7.1% · Other 문구를 쓴 페르소나 20/50
  - pid1: “Never really thought about making it myself”
  - pid4: “Buying all the sauces costs too much for one dish”
  - pid5: “Never really had it, not something I'm interested in”
  - pid6: “just haven't gotten around to it yet”
  - pid7: “I've never really had it, so it's just not something I think to make”
  - pid9: “Never really thought about making it”
  - pid11: “Never really thought about making it”
  - pid10: “Just never think to make it”
  - pid12: “I've just never really had it”
  - pid13: “Just haven't gotten around to trying it yet”
  - pid18: “never really thought about making it”
  - pid22: “Never really thought about making it”
  - pid24: “Don't eat it often enough to bother”
  - pid26: “Never really thought about making it”
  - pid29: “Just never really tried Thai food”
- 임계 미달

## 5. 진단 ④ Q6 가격 사다리 바닥·천장

| 가격 | Yes 믿음질량 | realized Yes n/N |
|---|---:|---:|
| $4.99 | 48% | 31/50 (62%) |
| $5.99 | 30% | 17/50 (34%) |
| $6.99 | 16% | 8/50 (16%) |
| $7.99 | 7% | 3/50 (6%) |
- 비단조 분포(가격↑인데 Yes 인원↑)를 낸 페르소나: 0/50 (위생 지표, 기록)
- 한국 게이트 C 대응 자리: $4.99 ↔ 6,900원 65%(방향만)
- ⚠ 임계 초과

## 6. 진단 ⑤ Q3 → Q5 일관성 압력(기록만)

- r(페르소나 고수기피, Q3 Very much 질량) = +0.84  ← 특성→문항 전사 강도
- r(Q3 Very much 질량, Q5 4~5점 질량) = +0.16  ← Q3가 Q5로 그대로 전사되는지
- r(페르소나 고수기피, Q5 4~5점 질량) = +0.15
- §4-5 축(향 기피층 Q3 Very much vs 나머지)의 Q5 4~5점: 32% (n=4) vs 30% (n=46) — 한국 52% vs 39%와 같은 축, 방향만 기록. 방향은 프롬프트에 심지 않았으므로 LLM prior.
- Q3_dist 최빈 패턴 점유 44% (동질성 잔존도)
- Q5_dist 최빈 패턴 점유 30% (동질성 잔존도)
- Q1_dist 최빈 패턴 점유 20% (동질성 잔존도)

## 7. 진단 ⑥ Q7 자유응답의 Q5 문장 에코(기록만)

- 콘셉트 문장 내용어와의 Jaccard 평균 0.07, 3-gram 공유 ≥2 또는 Jaccard ≥0.25: 0/50
- 콘셉트 핵심어 재사용 비율: milder/mild 38%, maesil/plum 46%, cilantro 62%, tamarind 20%, 5 minutes/microwave 2%
- Q7 원문 전부(국가=US, 합성):
  - pid36 (J=0.16, tri=0): “I make my own pad thai and I actually like the tamarind and cilantro, so a milder frozen version isn't really for me, but I might try one at a lower price just to see what the plum syrup tastes like.”
  - pid28 (J=0.13, tri=0): “I'd maybe grab one at five bucks out of curiosity about the maesil twist, but I make pad thai myself for less and I actually like the cilantro and the tamarind kick, so a milder frozen version isn't really for me.”
  - pid1 (J=0.13, tri=0): “I'd try it once out of curiosity about the plum syrup, but I actually like cilantro and the bold flavors, so a "milder" pad thai doesn't really sell me.”
  - pid8 (J=0.13, tri=0): “I'd grab it for an easy dinner if it actually tastes like pad thai, but I don't really need it milder and I'm not sure what plum syrup would do to the flavor.”
  - pid35 (J=0.12, tri=0): “The maesil twist makes me curious enough to try it once if it's on sale, but I actually like strong Thai flavors and cilantro, so a "milder" pad thai over $5 isn't really for me.”
  - pid39 (J=0.12, tri=0): “I'd try it for the maesil twist if it was under five bucks, but honestly I like my pad thai strong with cilantro and lime so "milder" isn't really a selling point for me.”
  - pid44 (J=0.11, tri=0): “I'd maybe try it if it was on sale for a quick lunch, but I actually like cilantro and the tangy flavor, so a "milder" pad thai doesn't really sell me.”
  - pid33 (J=0.10, tri=0): “Probably not, since I can make a whole pan of pad thai for my family for what a few of these single frozen trays would cost, and I don't mind cilantro anyway.”
  - pid30 (J=0.10, tri=0): “I'd try it because maesil in pad thai sounds like a cool combo, but honestly I like cilantro and real tamarind funk, so if it tastes too watered-down I wouldn't buy it again.”
  - pid13 (J=0.09, tri=0): “The maesil twist makes me curious enough to try it once if it's under five bucks, but I can make real pad thai cheaper at home and I actually like the cilantro and funk, so "milder" isn't selling me.”
  - pid15 (J=0.09, tri=0): “No cilantro and a quick microwave meal sounds great to me, but I'd want to know it actually tastes good and isn't weirdly sweet from the plum syrup.”
  - pid26 (J=0.08, tri=0): “I'd try it if it was on sale or under five bucks, but honestly I like cilantro and real pad thai so the "milder" thing doesn't really sell me.”
  - pid22 (J=0.08, tri=0): “I'd maybe try it if it was on sale for under five bucks, but I actually like cilantro and the regular tamarind flavor, so "milder" isn't really a selling point for me.”
  - pid3 (J=0.08, tri=0): “Honestly I like the cilantro and the tang from tamarind, so a toned-down version doesn't do much for me, though I might grab one for a quick lunch out of curiosity about the plum syrup.”
  - pid23 (J=0.08, tri=0): “Probably not, since I like the cilantro and tang in real pad thai and I can make a whole batch for my family for less than what a few of these single servings would cost.”
  - pid16 (J=0.08, tri=0): “I like the tamarind and cilantro, so a toned-down version doesn't really appeal to me, though I might try it once out of curiosity about the plum syrup if it was under five bucks.”
  - pid37 (J=0.08, tri=0): “I'd try it if it were around five dollars and actually tasted like pad thai, but I'm not sure about the plum syrup thing and I don't eat Thai food that often.”
  - pid17 (J=0.08, tri=0): “If it was around five bucks and actually tasted like pad thai I'd grab one for a lazy night, but I don't really need it milder so the plum thing doesn't sell me.”
  - pid6 (J=0.07, tri=0): “Probably wouldn't buy it since I can make a bigger batch of pad thai myself for less than five bucks, and I actually like the tamarind and cilantro, but I might grab one if it was on sale for a lazy night.”
  - pid49 (J=0.07, tri=0): “I like maesil and I'd try the Korean twist if it was around five bucks, but I don't need it milder and I'm not paying seven or eight dollars for one frozen meal when takeout isn't much more.”
  - pid38 (J=0.07, tri=0): “I'd maybe try it since it's easy and has no cilantro, but if there's still fish sauce or it smells strong, I'd pass.”
  - pid21 (J=0.06, tri=0): “I'd grab it if it was quick and actually tasted good, but I don't really need it milder since cilantro and strong flavors don't bother me.”
  - pid27 (J=0.06, tri=0): “I'd try it because the maesil twist sounds interesting, but honestly I love cilantro and bold flavors so "milder" makes me worry it'll taste bland.”
  - pid41 (J=0.06, tri=0): “I'd try it if it was on sale for under five bucks, but I actually like cilantro and the tangy flavor so a milder version isn't really a selling point for me.”
  - pid34 (J=0.06, tri=0): “I cook most everything from scratch for my family, so I'd only grab one if it was on sale, and I don't really need it milder since I like cilantro and fish sauce fine.”
  - pid48 (J=0.06, tri=0): “I love maesil so I'd try it out of curiosity at around five bucks, but I actually like cilantro and the funky tamarind taste, so if it ends up too sweet and bland I wouldn't buy it again.”
  - pid2 (J=0.06, tri=0): “No cilantro is honestly a big selling point for me, so I'd try it if it's around five bucks and the noodles don't come out soggy, but I wouldn't pay eight for one frozen serving.”
  - pid4 (J=0.06, tri=0): “I'd grab it if it was on sale for under five bucks since I like maesil, but I don't need it milder, so at full price I'd probably just get a Bibigo bag or ramen instead.”
  - pid11 (J=0.06, tri=0): “The maesil idea is kind of fun since I love Korean flavors, but I'd only grab it on sale because I don't mind cilantro and I can make noodles at home for way cheaper.”
  - pid25 (J=0.06, tri=0): “I'd maybe grab one for a busy workday lunch if it tasted decent, but I usually make pad thai myself, and I'm not sure I want a toned-down version without the tamarind.”
  - pid9 (J=0.06, tri=0): “Probably not, since I've never cared for Thai food and I'd rather make a regular supper at home, though no cilantro is a point in its favor if it was on sale and I felt like trying something new.”
  - pid14 (J=0.06, tri=0): “I'd maybe grab it for a busy work-from-home lunch if it was under $5, but I like the tang of real pad thai and usually just make it myself, so a "milder" version doesn't really sell me.”
  - pid43 (J=0.06, tri=0): “Honestly I like cilantro and bold flavors and I'd rather cook from scratch, so a milder frozen version doesn't really pull me in unless I needed a quick lunch and the reviews said it actually tasted good.”
  - pid45 (J=0.06, tri=0): “I'd grab it if it's around five bucks and the noodles don't turn to mush, since I love maesil and I'm curious how it works in pad thai, but if it's too sweet I wouldn't buy it again.”
  - pid31 (J=0.05, tri=0): “I'd try it because maesil is a cool twist and I don't cook much, but if it's over six bucks or tastes like sweet ketchup noodles I'd just stick with Bibigo or order real pad thai.”
  - pid46 (J=0.05, tri=0): “I'd try it if it's under five bucks or on sale, since I like maesil, but at seven or eight dollars for one small serving I'd just get takeout or buy a multi-pack of Bibigo dumplings instead.”
  - pid19 (J=0.04, tri=0): “I'd grab it if it was under five bucks or on sale since no cilantro is a big plus for me, but at seven or eight dollars I'd just order takeout instead.”
  - pid20 (J=0.04, tri=0): “I actually like the cilantro and the tangy tamarind, so a toned-down version doesn't really appeal to me unless it was cheap and the reviews said it still tasted good.”
  - pid7 (J=0.04, tri=0): “I might grab it if it was on sale for like four bucks just to see what pad thai tastes like, but otherwise I'd rather cook something myself for that money.”
  - pid29 (J=0.04, tri=0): “I like Korean flavors and maesil, so I'd probably grab one to try if it was next to the Bibigo stuff, but I'd only keep buying it if it actually tasted good and not like a sugary noodle bowl.”
  - pid12 (J=0.02, tri=0): “Honestly it's the price, I can get a whole frozen meal for like $2-3 so I'd only try it if it was on sale.”
  - pid47 (J=0.02, tri=0): “If it was under five bucks and actually filled me up I'd try it, but over that I'd just grab a cheaper frozen meal or takeout.”
  - pid42 (J=0.02, tri=0): “No cilantro is a big plus for me, but I usually cook from scratch, so I'd only grab it if it was cheap and actually tasted decent, not just sweet.”
  - pid10 (J=0.02, tri=0): “No cilantro is a big plus for me, but I'd only grab it if it was on sale for under five bucks since I usually just cook my own stuff.”
  - pid32 (J=0.02, tri=0): “I'd grab it for an easy lunch if it actually tastes good, but honestly I love cilantro and the bold flavors so a toned-down version doesn't really sell me.”
  - pid0 (J=0.02, tri=0): “If it was under five bucks or on sale I'd give it a shot, but at six or seven dollars for one frozen meal I'd just skip it and get something cheaper.”
  - pid5 (J=0.02, tri=0): “Five bucks or more for one frozen meal is too much when I can cook something myself for less, so I'd only try it if it went on sale for like three bucks.”
  - pid40 (J=0.02, tri=0): “If it was on sale for around $4 I'd try it since I don't cook, but over $5 for one frozen meal is too much when I can get other ones cheaper.”
  - pid18 (J=0.02, tri=0): “The maesil idea sounds cool, but I'd only grab it if it's on sale for around four bucks, since I can make a bigger batch of noodles at home for way cheaper.”
  - pid24 (J=0.02, tri=0): “Probably wouldn't buy it, since five bucks or more for one small frozen dinner is steep when I can cook a whole pot of noodles at home for less, but I might try it once if it was on sale.”

## 8. 부수 기록 — Q4a 브랜드·Q10 검색어(합성, 실측 아님)

- Q4a 언급 브랜드·매장: {'trader joe': 43, 'walmart': 7, 'healthy choice': 1}
- Q4a 원문(있는 것만):
  - pid0: “Trader Joe's pad thai, it was decent for the price but a little sweet and the noodles got clumpy.”
  - pid1: “Trader Joe's frozen pad thai, it was decent for a quick lunch but a little sweet and the noodles got kind of gummy.”
  - pid2: “Got the Trader Joe's pad thai, it was fine but kinda sweet and mushy.”
  - pid3: “Got a Trader Joe's frozen pad thai once, it was okay but kind of sweet and bland.”
  - pid4: “Got a Trader Joe's-style pad thai on sale at Walmart, it was okay but kinda sweet and the noodles got mushy.”
  - pid5: “Grabbed a frozen pad thai at Walmart once, it was way too sweet and kind of mushy.”
  - pid6: “Trader Joe's pad thai, it was fine for the price but kind of sweet and mushy.”
  - pid7: “Got a frozen pad thai bowl at Walmart once, it was okay but kind of sweet and small for the price.”
  - pid8: “Got the Trader Joe's frozen pad thai, it was honestly pretty decent for a microwave meal, just a little sweet.”
  - pid11: “Got the Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid10: “Grabbed a Saffron Road pad thai at Walmart once, it was okay but kind of sweet and small for the price.”
  - pid12: “Got a frozen pad thai at Walmart, it was okay but kinda small for the price.”
  - pid13: “Trader Joe's frozen pad thai, it was fine for a lazy night but way too sweet.”
  - pid15: “Trader Joe's frozen pad thai, it was okay but kind of sweet and mushy.”
  - pid14: “Trader Joe's frozen pad thai. It was fine for a quick lunch, just a little sweet and the noodles got kind of mushy.”
  - pid17: “Got a frozen pad thai from Trader Joe's, it was decent for a quick dinner but a little sweet.”
  - pid16: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid19: “Trader Joe's frozen pad thai, it was okay for the price but kind of sweet and mushy.”
  - pid18: “Got the Trader Joe's frozen pad thai, it was fine for the price but kinda sweet and mushy.”
  - pid20: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and bland compared to takeout.”
  - pid21: “Got a frozen pad thai from Walmart, I think it was Healthy Choice or something, it was alright for a quick lunch.”
  - pid22: “Got the Trader Joe's frozen pad thai, it was decent for the price but kind of sweet and the noodles got a little mushy.”
  - pid23: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and the noodles got mushy.”
  - pid25: “Trader Joe's pad thai, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid24: “Trader Joe's frozen pad thai, it was okay but kind of sweet and mushy.”
  - pid26: “Trader Joe's pad thai, it was pretty good for the price but kind of sweet.”
  - pid27: “Got the Trader Joe's frozen pad thai, it was fine for a quick dinner but kind of sweet and mushy.”
  - pid28: “Trader Joe's pad thai, fine for a quick lunch but the sauce was too sweet.”
  - pid29: “Picked up a Trader Joe's pad thai once, it was okay but a little sweet.”
  - pid30: “Trader Joe's pad thai, it was fine for a quick lunch but kinda sweet and the noodles got mushy.”
  - pid31: “Got the Trader Joe's frozen pad thai, it was fine for a quick lunch but kinda sweet and the noodles got a little mushy.”
  - pid33: “Trader Joe's frozen pad thai, it was okay but kind of sweet and mushy.”
  - pid32: “Trader Joe's frozen pad thai, it was decent for a quick lunch but kind of sweet.”
  - pid34: “Got a frozen pad thai at Walmart, it was okay but kind of sweet and mushy.”
  - pid35: “Trader Joe's pad thai, it was fine for a quick lunch but way too sweet and kind of mushy.”
  - pid36: “Trader Joe's frozen pad thai. It was okay for a quick lunch, but kind of sweet and the noodles got mushy.”
  - pid37: “Trader Joe's frozen pad thai, it was fine for a quick lunch but a little sweet.”
  - pid38: “Got a Trader Joe's frozen pad thai once and it was okay but a little too sweet and fishy for me.”
  - pid39: “Got the Trader Joe's frozen pad thai, it was decent for the price but kinda sweet and the noodles got a little mushy.”
  - pid40: “Got the Trader Joe's frozen pad thai, it was okay for the price but kinda sweet and mushy.”
  - pid41: “Got the Trader Joe's pad thai, it was decent for the price but kinda sweet.”
  - pid42: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid43: “Got the Trader Joe's frozen pad thai once, it was fine for a quick lunch but kind of sweet and mushy.”
  - pid44: “Got the Trader Joe's frozen pad thai, it was decent for a quick dinner but kinda sweet and the noodles got a little mushy.”
  - pid45: “Trader Joe's pad thai, it was fine for a quick lunch but kinda sweet and the noodles got mushy.”
  - pid46: “Got the Trader Joe's frozen pad thai, it was okay for the price but kind of sweet and mushy.”
  - pid47: “Got a Trader Joe's pad thai, it was fine for the price but kinda sweet.”
  - pid48: “Trader Joe's frozen pad thai, it was fine for a quick lunch but kind of sweet and the noodles got a little gummy.”
  - pid49: “Got the Trader Joe's frozen pad thai, it was decent for the money but kind of sweet and the noodles got a little mushy.”
- Q10 검색어 상위: [('frozen', 48), ('pad', 48), ('thai', 48), ('microwave', 21), ('maesil', 14), ('plum', 12), ('mild', 10), ('sauce', 10), ('cilantro', 9), ('cheap', 7), ('korean', 6), ('single', 1), ('serving', 1)]
- Q10 비움(선택 문항 건너뜀): 2/50
