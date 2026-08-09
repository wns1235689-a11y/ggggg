export const meta = {
  name: 'genesis-eu26-v1',
  description: '제네시스 유럽 인지 설문 시뮬(로테르담 거리+GP 팬존) — 브랜드 인지 상태 주입(입력전파), LLM은 조건부 행동만: 비보조 브랜드 구성·예스세잉·마그마 회상 verbatim. 통대본 문구 동결',
  phases: [{ title: 'GENESIS', detail: 'Q1 비보조 → 로고카드 4종 Y/N → (GP·Genesis Y만) 마그마 (한 페르소나=한 에이전트, 10명 분포)' }],
}
const YN = { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 2, maxItems: 2 }
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    q1_lists: { type: 'array', items: { type: 'string' }, minItems: 10, maxItems: 10 }, // 10명 각자의 비보조 나열(쉼표 구분, 말한 순서)
    B_dist: YN, L_dist: YN, P_dist: YN, G_dist: YN,   // 카드 Y/N 각 합=10
    magma_dist: YN,                                    // [Y,N] 합 = G_dist의 Y 수 (GP 전용; 거리·해당없음이면 [0,0])
    magma_verbatim: { type: 'array', items: { type: 'string' }, maxItems: 10 },  // 마그마 Y 인원수만큼 회상 원문
  },
  required: ['pid', 'q1_lists', 'B_dist', 'L_dist', 'P_dist', 'G_dist', 'magma_dist', 'magma_verbatim'],
}
function prompt(p) {
  const isGP = p.모집단.includes('GP')
  const know = p['브랜드인지(사실)']
  const magma = p['마그마인지(사실)']
  const magmaLine = isGP
    ? `[마그마 상태(사실)] ${magma.안다 ? `Genesis의 레이싱(르망/WEC) 활동을 ${magma.깊이 === 'specific' ? '구체적으로 안다(팀명·드라이버·차량까지 떠올릴 수 있음)' : '막연히 들어봤다("르망 나왔다던데" 수준)'}` : 'Genesis의 레이싱 활동을 들어본 적 없다'}.`
    : `[마그마 질문 없음] 이 모집단(거리)에서는 레이싱 질문을 하지 않는다 → magma_dist=[0,0], magma_verbatim=[].`
  return `너는 유럽 길거리 설문의 응답 시뮬레이터다. 아래 '유형'과 비슷한 실제 행인/관중 10명이 이 설문에 어떻게 답할지 추정하라.
★브랜드 인지 상태는 이 유형의 **사실**이다. '모른다' 브랜드를 아는 것처럼 만들지 마라. 단 보조 카드에서는 실제 행인처럼 소수의 오인정("본 것 같은데?" — 이 유형의 예스세잉 바닥 ≈ ${Math.round(p.예스세잉바닥 * 100)}%)이 있을 수 있다.
★비보조(Q1)에서 어떤 브랜드를 몇 개, 어떤 순서로 떠올리는지는 **네가 이 유형답게** 구성하라(거주국·연령·자동차/EV 관심 반영). 이 지시문은 브랜드 후보를 제시하지 않는다. 10명이 똑같은 목록을 대게 하지 마라.

[유형 pid=${p.pid}] ${p.모집단} · ${p.접촉맥락}에서 접촉 · ${p.거주국} 거주 · 연령대 ${p.연령대} · 자동차관심 ${p.자동차관심} · EV관심 ${p.EV관심} · 모터스포츠/WEC ${p['모터스포츠/WEC']} · F1미디어소비 ${p.F1미디어소비} · 프리미엄지향 ${p.프리미엄지향}.
[브랜드 인지 상태(사실)] BMW: ${know.BMW} / Lexus: ${know.LEXUS} / Polestar: ${know.POLESTAR} / Genesis: ${know.GENESIS}.
${p.비보조Genesis상기 ? '[특이] 이 유형은 드물게도 비보조에서 Genesis를 스스로 떠올릴 수 있는 사람이다.' : '[규율] 비보조(Q1)에서 Genesis를 언급하게 하지 마라 — 이 유형은 무보조로는 떠올리지 못한다.'}
${magmaLine}

━━ 설문 (현장 통대본 원문·순서 고정) ━━
Q1 "Which premium or luxury car brands come to mind? Just name a few." ("Any others?"는 한 번만)
→ q1_lists: 10명 각각이 실제로 말할 목록(말한 순서대로, 쉼표 구분 영어 한 줄). 사람마다 2~5개가 보통, 0~1개인 무관심층도 있다.

Q2 로고 카드(BMW·Lexus·Polestar·Genesis, 워드마크 포함, 순서 로테이션) — "Do you recognize any of these brands?"
→ B_dist, L_dist, P_dist, G_dist: 각 [Yes / No] 10명 분포(합=10). 인지 상태와 정합하되 예스세잉 바닥 반영.

${isGP ? `Q3 (Genesis를 Yes라 한 사람만) "Have you heard anything about Genesis in racing — Le Mans, or the WEC?"
→ magma_dist [Yes / No], 합 = G_dist의 Yes 인원수. magma_verbatim: Yes 인원수만큼 짧은 회상 원문(영어 — 마그마 상태의 깊이와 정합: 구체면 팀·드라이버·차명 수준, 막연이면 "saw them at Le Mans?" 수준).` : `(이 모집단은 Q3 없음 — magma_dist=[0,0], magma_verbatim=[])`}`
}
phase('GENESIS')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `genesis:pid${p.pid}`, phase: 'GENESIS', schema: SCHEMA, effort: 'medium' })
))).filter(Boolean)
log(`제네시스 설문 분포 생성: ${out.length}/${personas.length}`)
return { genesis: out }
