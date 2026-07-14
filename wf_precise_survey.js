export const meta = {
  name: 'gateC-precise-survey',
  description: '게이트C 순차노출 설문 정밀판: 동결 컨셉카드·E1 원문·정확 문구·페르소나별 셔플(ⓢ)로 실 Claude 응답',
  phases: [{ title: 'Respond', detail: '동결자극·셔플 적용 순차노출 응답' }],
}

// ── 원 라벨(설문설계 v1.4 §2 정확 문자열) ──
const A1 = ["먹어봤고 좋아한다", "먹어봤고 보통이다", "먹어봤지만 별로였다", "먹어본 적 없다"]
const A2 = ["고수 등 향신료 향이 부담스러워서", "피시소스 등 낯선 소스·재료가 부담스러워서",
            "먹을 기회나 파는 곳이 마땅치 않아서", "가격이 부담스러워서",
            "동남아 음식 자체를 즐기지 않아서", "지금도 거리낌 없이 잘 먹는다"]
const B2 = ["5분 완조리(간편함)", "외식 대비 가성비", "국산 새우·숙주 등 재료",
            "매실청의 새콤한 맛", "향신료(고수 등) 부담 없음", "사고 싶은 이유 없음"]
const B3 = ["맛이 상상이 안 된다", "'진짜 팟타이 맛'이 아닐 것 같다", "냉동식품 품질을 믿기 어렵다",
            "가격이 걱정된다", "양(1인분 300g)이 부족할 것 같다", "팟타이 자체에 관심이 없다",
            "망설여지는 점 없다"]
const B4 = ["매우 그렇다", "그렇다", "아니다", "모르겠다"]            // 셔플 OFF(순서 고정)
const C1 = ["직접 만든다", "냉동/밀키트를 사 먹는다", "배달·외식", "안 먹거나 참는다", "이런 맛을 안 찾는다"]
const C2 = ["꼭 산다", "상황 보고 가끔 산다", "아니오, 기존 방식 유지"]
const SD = ["산다", "안 산다"]
// E1 동결 헤드라인 원문(글자 일치) — (가)=T1 완성도, (나)=T2 매실청. ③④ 자기완결(전체 셔플)
const E1_GA = "사 먹어도 결국 손이 가던 팟타이 — 5분 끝판왕 등장."
const E1_NA = "타마린드 없이, 매실청으로 잡은 새콤함 — 부담 없는 진짜 팟타이."
const E1_ITEMS = [
  { tag: "가", text: E1_GA }, { tag: "나", text: E1_NA },
  { tag: "비슷", text: "두 문구가 비슷하다" }, { tag: "둘다", text: "둘 다 끌리지 않는다" },
]

// ── 결정론 셔플(재현): mulberry32 + Fisher–Yates ──
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
function shuffle(arr, pid, salt) {
  const rng = mulberry32((pid + 1) * 1000003 + salt * 97)
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
      ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}
const bullets = (a) => a.map(x => `· ${x}`).join('  ')

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    A1: { type: 'string', enum: A1 },
    A2: { type: 'string', enum: A2 },
    B1: { type: 'integer', minimum: 1, maximum: 5 },
    B2_1: { type: 'string', enum: B2 },
    B2_2: { type: 'string', enum: [...B2, "없음"] },
    B3: { type: 'string', enum: B3 },
    B4: { type: 'string', enum: B4 },
    C1: { type: 'string', enum: C1 },
    C2: { type: 'string', enum: C2 },
    D1_5900: { type: 'string', enum: SD }, D1_6900: { type: 'string', enum: SD },
    D1_7500: { type: 'string', enum: SD }, D1_8500: { type: 'string', enum: SD },
    E1: { type: 'string', enum: ["가", "나", "비슷", "둘다"] },
    E2: { type: 'string' },
  },
  required: ['pid', 'A1', 'A2', 'B1', 'B2_1', 'B2_2', 'B3', 'B4', 'C1', 'C2',
    'D1_5900', 'D1_6900', 'D1_7500', 'D1_8500', 'E1', 'E2'],
}

const lvl = (x) => x > 0.66 ? '높음' : x > 0.4 ? '보통' : '낮음'

function prompt(p) {
  const a2 = shuffle(A2, p.pid, 2)
  const b2 = shuffle(B2, p.pid, 3)
  const b3 = shuffle(B3, p.pid, 4)
  const e1 = shuffle(E1_ITEMS, p.pid, 6)
  const e1lines = e1.map(it =>
    (it.tag === "가" || it.tag === "나") ? `"${it.text}"` : it.text).map(s => ` - ${s}`).join('\n')
  return `너는 실제 한국 소비자 1명(pid=${p.pid})이다. 설문을 '평가'하지 말고 그 사람으로서 응답하라. 회의적으로, 마찰(맛 상상 어려움·'진짜 팟타이' 논쟁·냉동 품질·가격·양 300g)을 눈감지 말고 성향을 자연스럽게 반영하되 과장 금지. **이 제품의 사전 광고실험 결과를 전혀 모른다.**

[프로필] ${p.S1}·${p.S2}·${p.S3}·최근1개월 간편식 ${p.S4}·최근2년 동남아여행 ${p.S5}. 향신료부담 ${lvl(p.향기피)}·매실청친숙 ${lvl(p.매실청)}·관여도 ${lvl(p.관여)}·회의도 ${lvl(p.회의)}·가격민감 ${lvl(p.가격민감)}·접근성장벽(파는곳/기회 부족) ${lvl(p.접근성)}·정통성기대 ${lvl(p.정통기대)}·식사량기대 ${lvl(p.식사량)}·이 카테고리 평소 섭취빈도 ${lvl(p.카테고리빈도)}.
[현실 힌트] 1인가구면 고수·대파 같은 고명을 따로 사두지 않는다. 표기 1인분 300g이 성인 한 끼로는 적게 느껴질 수 있다. 이 음식을 평소 자주 먹지 않으면 맛이 괜찮아도 '가끔만' 재구매한다. 좋아하지만 안 사거나, 만족해도 가끔만 사는 현실적 불일치도 자연스럽다. 보기 순서는 무작위이니 위치가 아니라 내용으로 고른다.

━ 순서 엄수(정보 게이팅) ━
【1단계 사전태도 — 아직 어떤 제품/가격도 모름】
 A1 팟타이(태국식 볶음쌀국수) 경험 [${A1.join(' / ')}]
 A2 동남아 음식을 지금보다 자주 먹지 않는 '가장 큰' 이유 하나 [${a2.join(' / ')}]
【2단계 컨셉카드를 지금 처음 봄(가격 없음)】
 "태국 볶음쌀국수 '팟타이'를 한국 재료로 재해석한 냉동 간편식입니다. 새콤한 맛을 내는 타마린드 대신 매실청을 써서, 고수·피시소스 같은 향 부담을 덜었습니다. 냉동 쌀면 + 매실청 소스 + 국산 새우·숙주·부추 구성, 1인분(300g), 5분 완조리."
 B1 첫인상 선형 1~5 정수 (1=전혀 안 끌린다, 5=매우 끌린다)
 B2 사고 싶게 만드는 이유 1순위(B2_1)/2순위(B2_2, 없으면 "없음"). '사고 싶은 이유 없음' 고르면 2순위는 "없음". [행: ${bullets(b2)}]
 B3 가장 망설여지게 하는 것 하나 [${b3.join(' / ')}]
 B4 성실 응답 확인: 지시대로 '그렇다'를 고르라. [${B4.join(' / ')}]
【3단계 현재 행동·전환(가격 아직 없음)】
 C1 위 컨셉 같은 팟타이가 먹고 싶을 때 지금 주로 [${C1.join(' / ')}]
 C2 위 컨셉 냉동완제품이 나오면 방금 고른 방식 '대신' 시도? [${C2.join(' / ')}]
【4단계 가격 첫 공개 — 각 가격에서 살지/안 살지(보통 한 임계 이하에서만 산다)】
 D1_5900 / D1_6900 / D1_7500 / D1_8500 각각 [${SD.join(' / ')}]
【5단계 메시지 — 더 사고 싶게 만드는 쪽(보기 순서 무작위)】
${e1lines}
 E1 위 중 더 끌리는 쪽의 태그를 고른다: 가=("${E1_GA}") / 나=("${E1_NA}") / 비슷 / 둘다
 E2 그렇게 고른 이유를 한 문장(또는 한 단어)으로. 없으면 빈 문자열. 실제 사람이 설문 칸에 급히 적듯 편하게.

pid는 ${p.pid} 그대로. 모든 선택은 위 보기 문자열을 정확히 사용(E1은 태그).`
}

phase('Respond')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const responses = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `resp:pid${p.pid}(${p.seg})`, phase: 'Respond', schema: SCHEMA, effort: 'low' })
))).filter(Boolean)
log(`생성 완료: ${responses.length}/${personas.length}`)
return { responses }
