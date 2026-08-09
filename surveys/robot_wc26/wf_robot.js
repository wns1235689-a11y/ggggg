export const meta = {
  name: 'robot-wc26-v1',
  description: '월드컵 하프타임 로봇 인지 설문 시뮬 — 노출·지식 상태 주입(입력전파), LLM은 조건부 행동만: 오답구성(verbatim)·프로브·Q3. 정답·오답 후보 미주입(순환 차단)',
  phases: [{ title: 'ROBOT', detail: '통대본 Q1→Q2(+프로브)→Q3 (한 페르소나=한 에이전트, 10명 분포)' }],
}
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    Q1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 2, maxItems: 2 }, // [Yes, No] 합=10
    q2_verbatim: { type: 'array', items: { type: 'string' }, maxItems: 10 },      // Yes 인원수만큼, 각자 답 원문(영어)
    probeA_verbatim: { type: 'array', items: { type: 'string' }, maxItems: 10 },  // q2에서 Boston Dynamics 명명자 수만큼
    probeB_verbatim: { type: 'array', items: { type: 'string' }, maxItems: 10 },  // q2에서 Hyundai 명명자 수만큼
    Q3_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 3, maxItems: 3 }, // [excited, worried, mixed] 합=10
  },
  required: ['pid', 'Q1_dist', 'q2_verbatim', 'probeA_verbatim', 'probeB_verbatim', 'Q3_dist'],
}
function prompt(p) {
  const expo = p.노출.상태 === '노출됨'
    ? `이 유형은 그 행사를 **${p.노출.경로}**로 접했다. 기억 강도: **${p.노출.강도}** (행사는 7주 전).`
    : `이 유형은 그 행사를 **접한 적 없다** (못 봤고 못 들었다).`
  const confl = p.혼동주의
    ? `\n[주의] 이 유형의 기억은 실제 하프타임 공연이 아니라 대회 기간 로봇개(4족 로봇) 순찰 뉴스 등과 **섞였을 수 있는 희미한 기억**이다 — 답변이 그 혼동을 반영할 수 있다.`
    : ''
  return `너는 유럽 길거리 설문의 응답 시뮬레이터다. 아래 '유형'과 비슷한 실제 유럽 행인 10명이 이 설문에 어떻게 답할지 추정하라.
★노출·지식 상태는 이 유형의 **사실**이다. 모르는 사람에게 정답을 만들어주지 마라 — 실제 행인은 모르면 "no idea"라 하거나, 틀린 회사를 자기 나름대로 추측하거나, 이름 없이 서술("that robot dog company")로만 기억한다. 어떤 회사명 후보도 이 지시문은 제시하지 않는다 — **오답·추측의 구성은 네가 이 유형답게** 만들어라.
★★[절대 규율] 지식 상태가 '모름' 또는 '서술만 가능'이면, 10명 중 **누구도 실제 제조사의 정확한 이름을 입 밖에 내지 않는다** — 추측이 우연히 정답을 적중하는 일은 없어야 한다(추측은 오답 브랜드나 막연한 서술로만). "~회사였나?" 같은 반문 형태라도 정답 이름이면 규율 위반이다.
★한 값에 몰지 마라 — 10명은 흩어진다. verbatim은 실제 발화처럼 짧고 제각각으로(대소문자·말끝 다양).

[유형 pid=${p.pid}] ${p.도시} 거리에서 접촉 · ${p.거주국} 거주${p.관광객 ? '(여행 중)' : ''} · 연령대 ${p.연령대} · 축구관심 ${p.축구관심} · 숏폼SNS ${p.숏폼SNS} · 기술뉴스관심 ${p.기술뉴스관심} · 로봇 일상화 정서: ${p.로봇정서성향}.
[노출 상태(사실)] ${expo}${confl}
[지식 상태(사실)] ${p.지식상태}

━━ 설문 (2026-07-05 월드컵 16강 하프타임의 휴머노이드 로봇 골 세리머니 공연에 대한 현장 통대본 · 문구 동결) ━━
Q1 "Did you happen to see or hear about a humanoid robot performing at this summer's World Cup — doing football celebrations on the pitch?"
→ Q1_dist [Yes / No] 10명 분포. 저문턱 설계: "들어본 것 같기도" 같은 애매한 답은 Yes로 처리된다. 노출 강도가 '희미'면 일부만 기억을 끄집어내고, '비노출'이면 Yes는 0이거나 극소수(잘못된 기억)여야 한다.

Q2 (Q1=Yes인 사람만) "Do you happen to know which company is behind that robot?"
→ q2_verbatim: **Yes 인원수와 같은 개수**의 문자열. 각 사람이 실제로 입으로 말할 답 원문(영어 한 줄). 모름·엉뚱한 추측·부분 서술·반문 전부 허용 — 이 유형의 지식 상태와 모순되지 않게. (지식이 없어도 추측하는 사람은 있다 — 단 그 추측이 우연히 정답이 되게 하지 마라.)

프로브A (q2에서 **Boston Dynamics만**(현대 미언급) 말한 사람만) "Do you know who owns Boston Dynamics these days?"
→ probeA_verbatim: 그 인원수만큼의 답 원문. 없으면 [].
프로브B (q2에서 **Hyundai만**(BD 미언급) 말한 사람만) "Do you know the name of the robot company that built it?"
→ probeB_verbatim: 그 인원수만큼의 답 원문. 없으면 [].
★분기C(통대본 §4): 한 사람이 두 회사를 한꺼번에 말하면("Boston Dynamics... it's Hyundai's, right?") **추가 질문 없음** — 그 사람은 어느 프로브에도 답하지 않는다.

Q3 (전원) "Last one — in general, when you think about robots becoming part of everyday life, would you say you feel more excited, more worried, or mixed?"
→ Q3_dist [more excited / more worried / mixed] 10명 분포. 이 유형의 정서 성향·거주국·연령대를 반영하되 한쪽에 몰지 마라.`
}
phase('ROBOT')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `robot:pid${p.pid}`, phase: 'ROBOT', schema: SCHEMA, effort: 'medium' })
))).filter(Boolean)
log(`로봇 설문 분포 생성: ${out.length}/${personas.length}`)
return { robot: out }
