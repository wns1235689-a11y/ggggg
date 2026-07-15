export const meta = {
  name: 'gateC-e1-dist',
  description: 'E1 강제 양자택일 붕괴 수정: 페르소나별 가/나/비슷/둘다 4지 분포(10명 중 몇 명) → 하니스가 표집',
  phases: [{ title: 'E1dist', detail: '메시지 선호 4지 분포(비슷·둘다 포함)' }],
}
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    // [가(완성도), 나(매실청), 비슷(둘 다 비슷), 둘다(둘 다 안 끌림)] 합=10
    E1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 4, maxItems: 4 },
  },
  required: ['pid', 'E1_dist'],
}
const E1_GA = "사 먹어도 결국 손이 가던 팟타이 — 5분 끝판왕 등장."
const E1_NA = "타마린드 없이, 매실청으로 잡은 새콤함 — 부담 없는 진짜 팟타이."
const lvl = (x) => x > 0.6 ? '높음' : x > 0.4 ? '보통' : '낮음'
function prompt(p) {
  return `너와 성향이 비슷한 실제 한국 소비자 10명이 아래 두 광고 문구를 봤을 때, 어느 쪽이 '더 사고 싶게' 만드는지 고른다면 각 보기에 몇 명씩일지 '현실적 분포'(합=10)로 답하라.
★강제 양자택일이 아니다 — 실제로는 **"둘 다 비슷하다"**(차이를 못 느낌)거나 **"둘 다 안 끌린다"**(어느 쪽도 구매욕 없음)는 사람이 꽤 섞인다. 한쪽으로 몰지 말고, 비슷·둘다안끌림도 현실 비율로 배분하라.

[유형 pid=${p.pid}] ${p.S1}·${p.S3}·간편식 ${p.S4}. 향신료부담 ${lvl(p.향기피)}·매실청친숙 ${lvl(p.매실청)}·관여도 ${lvl(p.관여)}·회의도 ${lvl(p.회의)}.
[현실 힌트] 향 부담 큰 사람은 (나)에 끌리기 쉽고, 편의만 보는 사람은 (가)에 끌리기 쉽다. 단 관심 낮거나 회의적이면 '둘 다 안 끌린다', 둘 다 그럴듯하면 '둘 다 비슷하다'로 간다.

[제품] 팟타이를 매실청으로 재해석한 냉동 간편식(타마린드 대신 매실청, 고수·피시소스 향 부담↓, 국산 새우·숙주, 1인분 300g, 5분).
[문구]
 (가) "${E1_GA}"  — 완성도·간편 전면
 (나) "${E1_NA}"  — 매실청·향부담↓ 전면

정수 배열 E1_dist, 합=10, 순서 그대로: [가, 나, 비슷(둘 다 비슷), 둘다(둘 다 안 끌림)]`
}
phase('E1dist')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `e1:pid${p.pid}`, phase: 'E1dist', schema: SCHEMA, effort: 'low' })
))).filter(Boolean)
log(`E1 분포 생성: ${out.length}/${personas.length}`)
return { e1dists: out }
