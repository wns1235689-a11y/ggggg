export const meta = {
  name: 'gateC-vs-d1',
  description: 'D1 가격수용 동질성 수정: 페르소나별 Gabor-Granger 수용분포(각 가격 10명 중 몇 명) 생성 → 하니스가 임계 표집',
  phases: [{ title: 'D1dist', detail: '가격별 수용 인원(10명 중) 분포' }],
}
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    // 각 가격에서 '산다'는 인원(0~10). 가격이 오르면 같거나 줄어드는 게 자연스러움.
    buy_5900: { type: 'integer', minimum: 0, maximum: 10 },
    buy_6900: { type: 'integer', minimum: 0, maximum: 10 },
    buy_7500: { type: 'integer', minimum: 0, maximum: 10 },
    buy_8500: { type: 'integer', minimum: 0, maximum: 10 },
  },
  required: ['pid', 'buy_5900', 'buy_6900', 'buy_7500', 'buy_8500'],
}
const lvl = (x) => x > 0.6 ? '높음' : x > 0.4 ? '보통' : '낮음'
function prompt(p) {
  return `너와 성향이 비슷한 실제 한국 소비자 10명이 아래 냉동 간편식을 '각 가격'에 살지 답하라. ★사람마다 지불의사(WTP)가 다르다 — 싼 값에도 안 사는 사람, 비싸도 사는 사람이 섞인다. 한 가격에 10명이 몰리거나(전원 산다) 0명(전원 안 산다)으로 만들지 마라. 가격이 오를수록 '산다' 인원은 같거나 줄어드는 게 자연스럽다.

[유형 pid=${p.pid}] ${p.S1}·${p.S2}·${p.S3}·간편식 ${p.S4}. 가격민감 ${lvl(p.가격민감)}·이 카테고리 섭취빈도 ${lvl(p.카테고리빈도)}·관여도 ${lvl(p.관여)}·정통성기대 ${lvl(p.정통기대)}·식사량기대 ${lvl(p.식사량)}.
[기준] 편의점 냉동면·밀키트 1인분 통상 4,000~9,000원대. 1인분 300g. 5분 완조리. 가격민감 높으면 6,000원대에서 급감, 낮으면 8,000원도 수용.

[제품] 팟타이를 매실청으로 재해석한 냉동 간편식(국산 새우·숙주, 1인분 300g, 5분).

각 가격에서 10명 중 '산다' 인원(정수 0~10), 오름차순 가격:
- buy_5900 (5,900원)
- buy_6900 (6,900원)
- buy_7500 (7,500원)
- buy_8500 (8,500원)`
}
phase('D1dist')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `d1:pid${p.pid}`, phase: 'D1dist', schema: SCHEMA, effort: 'low' })
))).filter(Boolean)
log(`D1 분포 생성: ${out.length}/${personas.length}`)
return { d1dists: out }
