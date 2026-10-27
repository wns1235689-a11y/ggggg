# 해외 패널 설문 v1.1 §8 리허설 엔진 lite — 진단 (run wf_c6a68471-748)

## ⓪ 문서 지위 · 필수 경고
**LLM 합성 응답 · 비실측 · 인용 불가.** 이 문서는 설문 문항의 함정·어휘 이해·선택지 누락·가격 사다리 위치를
발행 전에 점검하는 **진단 전용** 산출물이다. 여기의 어떤 비율도 미국 소비자의 실제 비율이 아니며 PT 어디에도 쓰지 않는다
(해외 패널 설문 v1.1 §8 규칙). 페르소나 사전분포는 전부 [규범근사]이고 실측 앵커가 없다.

- 저널: `/home/user/ggggg/runs/wf_c6a68471-748/journal.jsonl`  · 풀: `/home/user/ggggg/runs/wf_c6a68471-748` (RUN_SEED=80928493, N(풀)=50) · 결과 회수 2명
- 형식: 한 페르소나(에이전트 1개)가 '비슷한 미국 소비자 10명'의 분포를 추정(VS) + 본인 자유응답. realized = 시드 결정론 표집(1인 1표). 판정 없음, 진단만.


## 요약 — 고치는 기준(①~④) 판독
- ⚠ ① 'maesil' 모름 100% ≥ 25% → 괄호 풀이 검토
- ⚠ ① 'green plum syrup' 모름 50% ≥ 25% → 괄호 풀이 검토
- ⚠ ④ $7.99 Yes 10% ≤ 10% → 천장이 높음, 사다리 아래로
- ⑤⑥은 한계로 기록만(아래 6·7절).
- 임계: {"①_term_unclear_share": 0.25, "②_a_little_mass": 0.5, "③_other_share": 0.1, "④_floor_yes_499": 0.9, "④_ceiling_yes_799": 0.1}


## 1. 문항별 분포(참고 — 수준 인용 금지)


**Q1_dist** 태국·동남아 음식 빈도 (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Never | 5.0% | █ | 0 |
| A few times a year | 30.0% | ████████ | 1 |
| About once a month | 45.0% | ███████████ | 0 |
| A few times a month | 15.0% | ████ | 1 |
| Once a week or more | 5.0% | █ | 0 |

**Q2_dist** 집에서 팟타이 조리 경험 (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, more than once | 30.0% | ████████ | 0 |
| Yes, once or twice | 30.0% | ████████ | 2 |
| No, never | 40.0% | ██████████ | 0 |

**Q2a_dist** 못 만드는 이유(Q2 비해당자 분모) (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Hard to find ingredients | 14.6% | ████ | 0 |
| Don't know how / complicated | 14.6% | ████ | 0 |
| Too much time or effort | 20.8% | █████ | 1 |
| Don't like the taste | 0.0% |  | 0 |
| Rather restaurant / delivery | 43.8% | ███████████ | 1 |
| Other | 6.2% | ██ | 0 |

**Q3_dist** 향·소스·향신료 때문에 피함(게이트 C 향기피 3점 대응) (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, very much | 5.0% | █ | 0 |
| Yes, a little | 30.0% | ████████ | 0 |
| No | 65.0% | ████████████████ | 2 |

**Q4_dist** 최근 12개월 냉동 태국 음식 구매 (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes | 35.0% | █████████ | 1 |
| No | 55.0% | ██████████████ | 1 |
| Not sure | 10.0% | ██ | 0 |

**Q5_dist** 콘셉트 관심 (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| 1 Not at all | 20.0% | █████ | 1 |
| 2 | 20.0% | █████ | 1 |
| 3 | 30.0% | ████████ | 0 |
| 4 | 20.0% | █████ | 0 |
| 5 Very interested | 10.0% | ██ | 0 |

**Q8_dist** 한식·Bibigo 인지 (믿음질량% | realized n/2)

| 보기 | 믿음질량 | | realized |
|---|---:|---|---:|
| Yes, and I know Bibigo | 20.0% | █████ | 0 |
| Had Korean food, don't know brands | 60.0% | ███████████████ | 1 |
| No | 20.0% | █████ | 1 |

## 2. 진단 ① Q5 어휘 이해 — 'unclear' 로 꼽힌 어휘(페르소나 비율)

| 어휘 | 모르겠다로 꼽은 페르소나 | 비율 |
|---|---:|---:|
| maesil | 2 | 100% ⚠ |
| green plum syrup | 1 | 50% ⚠ |

- Q5_reading에 '모르겠다·들어본 적 없다·대충 ~같은 것' 류 표현이 있는 페르소나: 0/2 (0%)
- maesil/green plum syrup 모름: 한식친숙 낮음(n=1) 100% vs 높음(n=1) 100% (페르소나 특성 → 어휘 반응 전사 여부, 기록)

## 3. 진단 ② Q3 'A little' 쏠림

- 믿음질량: Very much 5.0% / A little 30.0% / No 65.0%  · realized: 0/0/2 (n=2)
- 한국 게이트 C 대응치(참고 방향만): '매우' 33.0% / '조금'까지 71.6%
- 임계 미달(쏠림 없음)
  - 페르소나 보통(0.42~0.58) n=1: Very much 10% / A little 40% / No 50%

## 4. 진단 ③ Q2a 'Other' 비율(선택지 누락)

- 'Other' 믿음질량 6.2% · Other 문구를 쓴 페르소나 1/2
  - pid0: “Never really thought about it, we just order it out”
- 임계 미달

## 5. 진단 ④ Q6 가격 사다리 바닥·천장

| 가격 | Yes 믿음질량 | realized Yes n/N |
|---|---:|---:|
| $4.99 | 60% | 1/2 (50%) |
| $5.99 | 40% | 1/2 (50%) |
| $6.99 | 20% | 0/2 (0%) |
| $7.99 | 10% | 0/2 (0%) |
- 비단조 분포(가격↑인데 Yes 인원↑)를 낸 페르소나: 0/2 (위생 지표, 기록)
- 한국 게이트 C 대응 자리: $4.99 ↔ 6,900원 65%(방향만)
- ⚠ 임계 초과

## 6. 진단 ⑤ Q3 → Q5 일관성 압력(기록만)

- r(페르소나 고수기피, Q3 Very much 질량) = +1.00  ← 특성→문항 전사 강도
- r(Q3 Very much 질량, Q5 4~5점 질량) = +0.00  ← Q3가 Q5로 그대로 전사되는지
- r(페르소나 고수기피, Q5 4~5점 질량) = +0.00
- Q3_dist 최빈 패턴 점유 50% (동질성 잔존도)
- Q5_dist 최빈 패턴 점유 100% (동질성 잔존도)
- Q1_dist 최빈 패턴 점유 50% (동질성 잔존도)

## 7. 진단 ⑥ Q7 자유응답의 Q5 문장 에코(기록만)

- 콘셉트 문장 내용어와의 Jaccard 평균 0.06, 3-gram 공유 ≥2 또는 Jaccard ≥0.25: 0/2
- 콘셉트 핵심어 재사용 비율: milder/mild 0%, maesil/plum 50%, cilantro 0%, tamarind 0%, 5 minutes/microwave 50%
- Q7 원문 전부(국가=US, 합성):
  - pid1 (J=0.10, tri=0): “I'd buy it if the reviews said it tasted like real pad thai and not a sweet, mushy microwave meal; the plum substitution makes me skeptical.”
  - pid0 (J=0.02, tri=0): “I'd only buy it if it's under about five bucks or on sale and tastes decent, otherwise I'd just grab a cheaper frozen meal.”

## 8. 부수 기록 — Q4a 브랜드·Q10 검색어(합성, 실측 아님)

- Q4a 언급 브랜드·매장: {'trader joe': 2}
- Q4a 원문(있는 것만):
  - pid0: “Trader Joe's frozen pad thai, it was okay and cheap but a little bland.”
  - pid1: “Trader Joe's frozen pad thai, it was decent for a quick lunch but a little sweet.”
- Q10 검색어 상위: [('frozen', 2), ('pad', 2), ('thai', 2), ('microwave', 2), ('mild', 1), ('single', 1), ('serve', 1)]
- Q10 비움(선택 문항 건너뜀): 0/2
