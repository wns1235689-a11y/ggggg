export const meta = {
  name: 'gateC-v23-multi',
  description: 'v2.3 다풀(3×100) 견고성 시뮬: A2 4항목×3점(독립)+A2x 앵커, B2 향선택지 제거, E1 4지 — 향기피(원인)와 제품반응(B/C/D) 별도 측정, 방향 미주입(순환 차단)',
  phases: [{ title: 'V23', detail: 'v2.3 전 문항 분포(한 페르소나=한 에이전트)' }],
}
const D3 = { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 3, maxItems: 3 }
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    A1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 4, maxItems: 4 },
    A2a_dist: D3, A2b_dist: D3, A2c_dist: D3, A2d_dist: D3,   // 각 [아니다, 조금, 매우]
    A2x_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 2, maxItems: 2 }, // [예, 아니오]
    B1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 5, maxItems: 5 },
    B2_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 5, maxItems: 5 },  // 향선택지 제거→5지
    B3_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 7, maxItems: 7 },
    C1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 5, maxItems: 5 },
    C2_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 3, maxItems: 3 },
    E1_dist: { type: 'array', items: { type: 'integer', minimum: 0 }, minItems: 4, maxItems: 4 },
    buy_5900: { type: 'integer', minimum: 0, maximum: 10 },
    buy_6900: { type: 'integer', minimum: 0, maximum: 10 },
    buy_7500: { type: 'integer', minimum: 0, maximum: 10 },
    buy_8500: { type: 'integer', minimum: 0, maximum: 10 },
  },
  required: ['pid', 'A1_dist', 'A2a_dist', 'A2b_dist', 'A2c_dist', 'A2d_dist', 'A2x_dist',
    'B1_dist', 'B2_dist', 'B3_dist', 'C1_dist', 'C2_dist', 'E1_dist',
    'buy_5900', 'buy_6900', 'buy_7500', 'buy_8500'],
}
const lvl = (x) => x > 0.75 ? '매우높음' : x > 0.58 ? '높음' : x > 0.42 ? '보통' : x > 0.25 ? '낮음' : '매우낮음'
function prompt(p) {
  return `너와 성향이 비슷한 실제 한국 소비자 10명의 응답 분포를 문항별로 추정하라. 각 dist는 정수 배열·합=10(가격문항 buy_*는 0~10 인원), 보기 순서 그대로.
★문항 안에서 한 보기에 몰지 마라 — 사람은 흩어진다. 중립·부정 보기(아니다/비슷/둘 다 별로/이유 없음/없음)도 현실 비율로 반드시 배분하라.
★★너는 '평균 한국인'이 아니라 아래 특성이 뚜렷하게 규정된 '특정 유형' 한 명이다. 무난한 분포를 복붙하지 말고, 특성이 극단(매우높음/매우낮음)일수록 그 방향으로 분포를 확실히 치우치게 하라(특성이 '보통'인 문항에서만 넓게 흩뿌림). 어느 특성→어느 보기 매핑은 지정하지 않는다 — 네 판단으로 이 사람답게 답하라.

[유형 pid=${p.pid}] ${p.S1}·${p.S2}·${p.S3}·간편식 ${p.S4}·동남아여행 ${p.S5}. 향신료부담 ${lvl(p.향기피)}·매실청친숙 ${lvl(p.매실청)}·관여도 ${lvl(p.관여)}·회의도 ${lvl(p.회의)}·가격민감 ${lvl(p.가격민감)}·접근성장벽 ${lvl(p.접근성)}·정통성기대 ${lvl(p.정통기대)}·식사량기대 ${lvl(p.식사량)}·이 카테고리 섭취빈도 ${lvl(p.카테고리빈도)}.

━━ 사전태도 (컨셉·가격 전혀 모름 · 프라이밍 없음) ━━
A1_dist [좋아한다 / 보통이다 / 별로였다 / 먹어본 적 없다] — 팟타이(태국식 볶음쌀국수) 경험
▷ 아래 A2는 "동남아 음식(태국·베트남 등)을 지금보다 자주 먹지 않는다면, 그 이유로 각 항목이 얼마나 해당되나"를 항목별 독립으로. 각 항목 [아니다 / 조금 그렇다 / 매우 그렇다] 10명 분포:
A2a_dist — (a) 고수 등 향신료 '향'이 부담된다
A2b_dist — (b) 피시소스 등 낯선 소스·재료가 부담된다
A2c_dist — (c) 파는 곳·먹을 기회가 마땅치 않다
A2d_dist — (d) 가격이 부담된다
A2x_dist [예 / 아니오] — "나는 지금도 동남아 음식을 거리낌 없이 자주 먹는다"

━━ 컨셉 카드 본 후 (매실청 여기서 처음 등장) ━━
[컨셉] 태국 팟타이를 한국 재료로 재해석한 냉동 간편식. 새콤한 맛을 내는 타마린드 대신 매실청을 써서 향 부담을 덜었습니다. 냉동 쌀면+매실청 소스+국산 새우·숙주·부추, 1인분 300g, 5분 완조리. (가격 미공개)
B1_dist [1점 / 2점 / 3점 / 4점 / 5점] — 첫인상(1=전혀 안 끌림 … 5=매우 끌림)
B2_dist [5분 완조리 / 외식 대비 가성비 / 국산 새우·숙주 등 재료 / 매실청의 새콤한 맛 / 사고 싶은 이유 없음] — 사고 싶게 만드는 1순위 이유 (※'향 부담 없음' 보기는 일부러 없음)
B3_dist [맛 상상 안 됨 / 진짜 팟타이 맛 아닐 것 / 냉동품질 불신 / 가격 걱정 / 양(300g) 부족 / 팟타이 관심 없음 / 없음] — 가장 망설이게 하는 것 하나
C1_dist [직접 만든다 / 냉동·밀키트 / 배달·외식 / 안 먹음·참음 / 이런 맛 안 찾음] — 이런 팟타이 먹고 싶을 때 지금은
C2_dist [꼭 산다 / 가끔 산다 / 기존 유지] — 이 냉동 완제품 나오면 기존 방식 대신 시도?
E1_dist [가(완성도: "5분 끝판왕") / 나(매실청: "부담 없는 진짜 팟타이") / 비슷하다 / 둘 다 별로] — 더 사고 싶게 만드는 문구 (★강제 양자택일 아님)

━━ 가격 수용(각 가격 10명 중 '산다' 인원, 0~10 · 가격↑→같거나 감소) ━━
buy_5900 (5,900원) / buy_6900 (6,900원) / buy_7500 (7,500원) / buy_8500 (8,500원)`
}
phase('V23')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `v23:pid${p.pid}`, phase: 'V23', schema: SCHEMA, effort: 'medium' })
))).filter(Boolean)
log(`v2.3 분포 생성: ${out.length}/${personas.length}`)
return { v23: out }
