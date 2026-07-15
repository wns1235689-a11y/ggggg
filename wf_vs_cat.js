export const meta = {
  name: 'gateC-vs-cat',
  description: 'VS 전면화: A1·A2(컨셉前)·B2·B3·E1(컨셉後) 카테고리 문항을 페르소나별 분포(10명 중 몇 명)로 — 강제단발선택 붕괴 제거',
  phases: [{ title: 'VScat', detail: 'A1/A2/B2/B3/E1 분포 동시 산출' }],
}
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    A1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 4, maxItems: 4 },
    A2_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 6, maxItems: 6 },
    B2_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 6, maxItems: 6 },
    B3_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 7, maxItems: 7 },
    E1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 4, maxItems: 4 },
  },
  required: ['pid', 'A1_dist', 'A2_dist', 'B2_dist', 'B3_dist', 'E1_dist'],
}
const lvl = (x) => x > 0.6 ? '높음' : x > 0.4 ? '보통' : '낮음'
function prompt(p) {
  return `너와 성향이 비슷한 실제 한국 소비자 10명의 응답 분포를 문항별로 추정하라. 각 dist는 정수 배열·합=10, 보기 순서 그대로. ★한 보기에 몰지 마라 — 실제 사람은 흩어진다(관심 없는 사람, 잘 먹는 사람, 어느 쪽도 안 끌리는 사람이 섞인다). '비슷/둘 다 안 끌림/관심 없음/이유 없음' 같은 중립·부정 보기도 현실 비율로 반드시 배분하라.

[유형 pid=${p.pid}] ${p.S1}·${p.S3}·간편식 ${p.S4}·동남아여행 ${p.S5}. 향신료부담 ${lvl(p.향기피)}·매실청친숙 ${lvl(p.매실청)}·관여도 ${lvl(p.관여)}·회의도 ${lvl(p.회의)}·가격민감 ${lvl(p.가격민감)}·접근성장벽 ${lvl(p.접근성)}·카테고리섭취빈도 ${lvl(p.카테고리빈도)}.

━ ①②는 컨셉·가격을 전혀 모르는 상태(사전태도)의 분포 ━
A1_dist [먹어봤고 좋아한다 / 먹어봤고 보통이다 / 먹어봤지만 별로였다 / 먹어본 적 없다] — 팟타이 경험
A2_dist [고수 등 향신료 향 부담 / 피시소스 등 낯선 소스·재료 부담 / 먹을 기회·파는 곳 부족(접근성) / 가격 부담 / 동남아 음식 자체 비선호 / 지금도 거리낌 없이 잘 먹음] — 동남아 음식을 더 자주 안 먹는 '가장 큰 이유'

━ ③④⑤는 아래 컨셉 카드를 본 후의 분포 ━
[컨셉] 팟타이를 매실청으로 재해석한 냉동 간편식(타마린드 대신 매실청, 고수·피시소스 향 부담↓, 국산 새우·숙주, 1인분 300g, 5분 완조리. 가격 미공개)
B2_dist [5분 완조리(간편) / 외식 대비 가성비 / 국산 새우·숙주 등 재료 / 매실청의 새콤한 맛 / 향신료(고수) 부담 없음 / 사고 싶은 이유 없음] — 사고 싶게 만드는 '1순위 이유'
B3_dist [맛 상상 안 됨 / '진짜 팟타이 맛' 아닐 것 / 냉동품질 불신 / 가격 걱정 / 양(300g) 부족 / 팟타이 관심 없음 / 망설임 없음] — 가장 망설이게 하는 것
E1_dist [가(완성도: "5분 끝판왕") / 나(매실청: "부담 없는 진짜 팟타이") / 둘 다 비슷 / 둘 다 안 끌림] — 더 사고 싶게 만드는 문구`
}
phase('VScat')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `vscat:pid${p.pid}`, phase: 'VScat', schema: SCHEMA, effort: 'low' })
))).filter(Boolean)
log(`VS-cat 분포 생성: ${out.length}/${personas.length}`)
return { vscat: out }
