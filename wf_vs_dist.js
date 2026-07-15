export const meta = {
  name: 'gateC-vs-dist',
  description: 'VS 전면화: B1(첫인상)·C1(현재대안)·C2(전환의향)을 페르소나별 분포(10명 중 몇 명)로 — 모드붕괴 방지',
  phases: [{ title: 'VSdist', detail: 'B1/C1/C2 분포 동시 산출' }],
}
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    B1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 5, maxItems: 5 },
    C1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 5, maxItems: 5 },
    C2_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 3, maxItems: 3 },
  },
  required: ['pid', 'B1_dist', 'C1_dist', 'C2_dist'],
}
const lvl = (x) => x > 0.6 ? '높음' : x > 0.4 ? '보통' : '낮음'
function prompt(p) {
  return `너와 성향이 비슷한 실제 한국 소비자 10명이 아래 컨셉을 봤을 때, 각 문항 보기를 몇 명이나 고를지 '현실적 분포'(합=10)로 답하라. ★한 보기에 몰아주지 마라 — 실제 사람은 흩어진다(좋아해도 안 사는 사람, 관심 없는 사람, 현재 방식이 제각각인 사람이 섞인다).

[유형 pid=${p.pid}] ${p.S1}·${p.S2}·${p.S3}·간편식 ${p.S4}·동남아여행 ${p.S5}. 향신료부담 ${lvl(p.향기피)}·매실청친숙 ${lvl(p.매실청)}·관여도 ${lvl(p.관여)}·회의도 ${lvl(p.회의)}·가격민감 ${lvl(p.가격민감)}·접근성장벽(파는곳/기회 부족) ${lvl(p.접근성)}·이 카테고리 평소 섭취빈도 ${lvl(p.카테고리빈도)}.
[현실 힌트] 이 음식을 평소 자주 안 먹으면 만족해도 '가끔만' 산다. 현재 방식은 직접만듦·냉동밀키트·배달외식·안먹음으로 갈린다. 접근성 장벽이 크면 냉동/밀키트나 안먹음으로 더 간다.

[컨셉] 태국 팟타이를 매실청으로 재해석한 냉동 간편식(타마린드 대신 매실청으로 새콤함, 고수·피시소스 향 부담↓, 국산 새우·숙주, 1인분 300g, 5분 완조리).

각 dist는 정수 배열, 합=10, 명시된 보기 순서 그대로:
- B1_dist [1점, 2점, 3점, 4점, 5점] — 첫인상(1=전혀 안 끌림 … 5=매우 끌림)
- C1_dist [직접 만든다, 냉동/밀키트, 배달·외식, 안 먹거나 참는다, 이런 맛 안 찾음] — 이런 팟타이 먹고싶을때 지금 주로
- C2_dist [꼭 산다, 가끔 산다, 기존 방식 유지] — 냉동완제품 나오면 기존 대신 시도?`
}
phase('VSdist')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `vsdist:pid${p.pid}`, phase: 'VSdist', schema: SCHEMA, effort: 'low' })
))).filter(Boolean)
log(`VS-dist 분포 생성: ${out.length}/${personas.length}`)
return { vsdist: out }
