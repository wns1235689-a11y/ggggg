export const meta = {
  name: 'fidelity-assessment',
  description: '이 합성 설문이 실측 설문과 몇 % 유사할지 다각도(문헌·지표분해·아티팩트·회의론) 평가 후 종합',
  phases: [
    { title: 'Lenses', detail: '문헌/지표분해/아티팩트/회의론 병렬 분석' },
    { title: 'Verify', detail: '헤드라인 수치 적대적 검증' },
    { title: 'Synth', detail: '보정된 종합 추정' },
  ],
}

const CTX = `[평가 대상 — 합성 설문]
게이트C: 한국 냉동 간편식 신제품 컨셉(팟타이를 타마린드 대신 매실청으로 재해석) 수요검증 설문의 LLM 합성 시뮬레이션.
표본 N=74(타깃 25-39 직장인 30 + 대학생세그 17 + 비타깃/스크린 27), 채널혼합 blind/relay/student.
생성 방식:
- 인구통계·거주·간편식빈도는 통계청/KREI 2025 실측 앵커에 결합분포(Bayes-net) 표집(=입력 그라운딩)
- 21개 잠재특성(향기피·매실청친숙·가격민감 등)으로 페르소나 부여
- 실제 Claude(opus) 74개 에이전트가 순차노출(정보게이팅) 설문 응답 — 동결 컨셉카드·E1 헤드라인 원문·정확 문구·페르소나별 셔플
- 원 LLM 응답에서 C1/C2/B1/D1이 모드붕괴(전원 동일선택) → Verbalized Sampling(유형별 '10명 중 몇 명' 분포 생성 후 하니스가 표집)으로 수정
- D1 가격은 VS 수용곡선 → WTP 임계 이질표집(하향곡선 복원), 정합가드로 극단모순 완화
- E2 서술형은 자연어 3회 다듬기

[핵심 산출 지표]
- 인구/스크리닝 분포(입력 그라운딩)
- A2 동남아기피 사유 유병률(향기피 11.5% vs 접근성 57.7%)
- B1 첫인상 1~5(평균3, SD1.39, top2 38.5%)
- B2 구매이유 계열(간편/가성비 C계열 22 vs 매실청/향부담 A계열 4)
- C1 현재대안(냉동42·안먹27·배달19%) / C2 전환의향(가끔64·기존34·꼭2.7%)
- D1 가격수용곡선(유효타깃 5900/6900/7500/8500 = 81/58/42/23%)
- E1 헤드라인선호(가 완성도 54% vs 나 매실청 46%)
★ 실제 필드 설문은 시행된 적 없음 = ground truth 부재. '유사도 %'는 검증 불가한 추정.`

const LENS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    key_points: { type: 'array', items: { type: 'string' }, minItems: 3 },
    per_metric: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          metric: { type: 'string' },
          fidelity_low: { type: 'integer', minimum: 0, maximum: 100 },
          fidelity_high: { type: 'integer', minimum: 0, maximum: 100 },
          note: { type: 'string' },
        },
        required: ['metric', 'fidelity_low', 'fidelity_high', 'note'],
      },
    },
    headline_low: { type: 'integer', minimum: 0, maximum: 100 },
    headline_high: { type: 'integer', minimum: 0, maximum: 100 },
    basis: { type: 'string' },
    biggest_caveats: { type: 'array', items: { type: 'string' }, minItems: 2 },
  },
  required: ['lens', 'key_points', 'per_metric', 'headline_low', 'headline_high', 'basis', 'biggest_caveats'],
}

const LENSES = [
  {
    key: 'literature',
    prompt: `너는 실리콘 샘플링(LLM 합성 설문응답)의 실측 대비 정확도를 연구한 계량사회과학자다. **WebSearch/WebFetch로 실제 문헌을 찾아 근거로 삼아라**(예: Argyle et al 2023 "Out of One, Many"; Santurkar OpinionQA; Bisbee et al 2024 관련 비판; LLM synthetic survey validity, willingness-to-pay LLM 등). 실측과의 상관/오차가 지표 유형별로 어떻게 다른지(방향·순위는 잘, 절대수준·분산은 약함 등) 구체적 수치 근거로 답하라. 신제품·틈새시장·특정 문화(한국)·WTP는 정치/일반태도보다 근거가 약함을 반영하라.`,
  },
  {
    key: 'metric_decomp',
    prompt: `너는 이 설문 파이프라인을 지표별로 분해평가하는 측정전문가다. 각 산출지표(인구분포·A2유병률·B1수준·B2순위·C1구조·C2의향·D1가격곡선·E1메시지)마다 '실측과의 유사도 %'를 다르게 매겨라. 원칙: 입력 그라운딩(인구)은 높게, 옵션 순위/방향은 중간, 절대수준(구매의향 top-box·D1 수용률)은 낮게, 문화·로컬지식 결손 지표(A2·매실청)는 특히 낮게. 각 밴드에 이유를 붙여라.`,
  },
  {
    key: 'artifact',
    prompt: `너는 이 파이프라인의 '엔지니어링된 현실성'을 비판적으로 분리하는 방법론자다. 핵심 질문: 모드붕괴를 VS로 '수정'하고 D1을 임계모델로 '복원'하고 정합가드를 넣은 것은 face validity(그럴듯해 보임)를 올리지만 measured accuracy(실측과 실제 일치)를 올리는가? 손으로 빚은 분포(VS 프롬프트가 '흩어져라'라고 지시)는 실제 분산이 아니라 '가정된 분산'임을 지적하라. 이것이 '유사도 %' 해석에 주는 함의(오히려 더 신중해야 함)를 정량 밴드로 답하라.`,
  },
  {
    key: 'skeptic',
    prompt: `너는 이 수치가 실측과 크게 다를 것이라 보는 적대적 회의론자다. 엄격한 기준(옵션별 비율이 실측 ±5~10%p 안에 드는가)에서 유사도가 낮을(<40%) 강한 근거를 대라: LLM의 긍정편향·평균회귀·한국 냉동식품 시장/가격 로컬지식 결손·신규컨셉 상상응답·B4 통과율 과대·training cutoff 시점편향·매실청 팟타이라는 초신제품의 예측불가성. 그럼에도 '전혀 무용'은 아닌 지점(무엇은 그나마 맞을지)도 균형있게.`,
  },
]

phase('Lenses')
const personas = null
const lensOut = await parallel(LENSES.map(L => () =>
  agent(`${CTX}\n\n━━━\n${L.prompt}\n\nper_metric에는 위 핵심 산출 지표들을 개별 항목으로 넣어라. fidelity는 '실측과의 유사도 %' 밴드(low~high). headline은 이 렌즈가 보는 전체 유사도 밴드.`,
    { label: `lens:${L.key}`, phase: 'Lenses', schema: LENS_SCHEMA, effort: 'high' })
)).then(a => a.filter(Boolean))

phase('Verify')
// 각 렌즈 헤드라인을 적대적으로 검증: 과대/과소인지, 어떤 기준(엄격 vs 방향)인지 혼동 없는지
const VER_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    verdict: { type: 'string', enum: ['타당', '과대추정', '과소추정', '기준혼동'] },
    corrected_low: { type: 'integer', minimum: 0, maximum: 100 },
    corrected_high: { type: 'integer', minimum: 0, maximum: 100 },
    reason: { type: 'string' },
  },
  required: ['lens', 'verdict', 'corrected_low', 'corrected_high', 'reason'],
}
const verified = await parallel(lensOut.map(L => () =>
  agent(`${CTX}\n\n아래 한 렌즈의 판단을 적대적으로 검증하라. '엄격 기준(옵션비율 ±5-10%p 일치)'과 '방향/순위 기준'을 반드시 구분해서, 이 렌즈가 둘을 혼동했는지, 밴드가 과대/과소인지 판정하고 보정 밴드를 제시하라.\n\n[렌즈=${L.lens}] headline ${L.headline_low}-${L.headline_high}% / basis: ${L.basis}\nkey_points: ${JSON.stringify(L.key_points, null, 1)}\nper_metric: ${JSON.stringify(L.per_metric, null, 1)}\ncaveats: ${JSON.stringify(L.biggest_caveats)}`,
    { label: `verify:${L.lens}`, phase: 'Verify', schema: VER_SCHEMA, effort: 'high' })
)).then(a => a.filter(Boolean))

phase('Synth')
const SYN_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    framing: { type: 'string' },                       // 왜 단일 %는 잘못된 질문인가
    strict_range: { type: 'object', additionalProperties: false,
      properties: { low: { type: 'integer' }, high: { type: 'integer' } }, required: ['low', 'high'] },
    directional_range: { type: 'object', additionalProperties: false,
      properties: { low: { type: 'integer' }, high: { type: 'integer' } }, required: ['low', 'high'] },
    by_metric: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: { metric: { type: 'string' }, low: { type: 'integer' }, high: { type: 'integer' }, tier: { type: 'string' } },
      required: ['metric', 'low', 'high', 'tier'] } },
    top_reasons_high: { type: 'array', items: { type: 'string' } },
    top_reasons_low: { type: 'array', items: { type: 'string' } },
    honest_bottom_line: { type: 'string' },
  },
  required: ['framing', 'strict_range', 'directional_range', 'by_metric', 'top_reasons_high', 'top_reasons_low', 'honest_bottom_line'],
}
const synth = await agent(
  `${CTX}\n\n아래는 4개 렌즈의 평가와 그에 대한 적대적 검증(보정)이다. 이를 종합해 '보정된' 유사도 추정을 내라. 반드시 두 기준을 분리하라: (1) strict_range=옵션별 비율이 실측 ±5-10%p 안에 드는 정도, (2) directional_range=순위·방향·부호가 맞는 정도. by_metric은 지표별 밴드+tier(높음/중간/낮음). ground truth 부재로 이 추정 자체가 검증불가한 메타추정임을 framing과 bottom_line에 명확히.\n\n[렌즈들]\n${JSON.stringify(lensOut, null, 1)}\n\n[검증/보정]\n${JSON.stringify(verified, null, 1)}`,
  { label: 'synthesis', phase: 'Synth', schema: SYN_SCHEMA, effort: 'high' })

return { lenses: lensOut, verified, synth }
