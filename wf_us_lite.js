export const meta = {
  name: 'overseas-panel-us-lite',
  description: '해외 패널 설문 v1.1 §8 리허설 엔진 lite: 미국 페르소나 × 영문 문항 Q1~Q10(§2-1 그대로) VS 분포 + 자유응답(진단 전용·판정 없음)',
  phases: [{ title: 'USLITE', detail: '한 페르소나=한 에이전트, 10명 분포 + 본인 자유응답' }],
}
const D = (n) => ({ type: 'array', items: { type: 'integer', minimum: 0 }, minItems: n, maxItems: n })
const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    pid: { type: 'number' },
    Q1_dist: D(5),            // Never / A few times a year / About once a month / A few times a month / Once a week or more
    Q2_dist: D(3),            // Yes, more than once / Yes, once or twice / No, never
    Q2a_dist: D(6),           // (only Q2 once-or-twice + never) 6 reasons; sums to 10 - Q2_dist[0]
    Q2a_other_text: { type: 'string' },
    Q3_dist: D(3),            // Yes, very much / Yes, a little / No
    Q4_dist: D(3),            // Yes / No / Not sure
    Q4a_text: { type: 'string' },
    Q5_reading: { type: 'string' },
    Q5_unclear_terms: { type: 'array', items: { type: 'string' } },
    Q5_dist: D(5),            // 1 Not at all interested … 5 Very interested
    buy_499: { type: 'integer', minimum: 0, maximum: 10 },
    buy_599: { type: 'integer', minimum: 0, maximum: 10 },
    buy_699: { type: 'integer', minimum: 0, maximum: 10 },
    buy_799: { type: 'integer', minimum: 0, maximum: 10 },
    Q7_text: { type: 'string' },
    Q8_dist: D(3),            // Yes, and I know Bibigo / had Korean food but don't know brands / No
    Q10_text: { type: 'string' },
  },
  required: ['pid', 'Q1_dist', 'Q2_dist', 'Q2a_dist', 'Q2a_other_text', 'Q3_dist', 'Q4_dist', 'Q4a_text',
    'Q5_reading', 'Q5_unclear_terms', 'Q5_dist', 'buy_499', 'buy_599', 'buy_699', 'buy_799',
    'Q7_text', 'Q8_dist', 'Q10_text'],
}
const lvl = (x) => x > 0.75 ? 'very high' : x > 0.58 ? 'high' : x > 0.42 ? 'moderate' : x > 0.25 ? 'low' : 'very low'
const hh = (h) => h === '1' ? 'lives alone' : h === '2' ? 'household of 2' : 'household of 3 or more'
function prompt(p) {
  return `You are one specific American adult with a clearly defined profile (below), answering a short online panel survey (Prolific) about Thai food at home. For each multiple-choice question, estimate how 10 real US consumers with a profile like yours would answer: give an integer array in the exact option order, summing to 10 (price rows buy_*: number of the 10 who answer Yes, 0–10, non-increasing as price rises). For the open-text questions, answer as yourself, one person, in natural everyday American English.
★ Do not pile everyone on one option — real people spread out. Give neutral and negative options their realistic share.
★★ You are NOT an "average American". You are a particular type: when a trait below is extreme (very high / very low) lean the distribution clearly that way; spread widely only where your traits are moderate. Which trait maps to which answer is NOT specified — decide as this person would.

[Type pid=${p.pid}] ${p.gender}, age ${p.age}, ${p.urbanicity} ${p.region} (US), ${hh(p.household)}. Eats Thai or other Southeast Asian food: ${p.thai_freq}. Dislike of cilantro and strong herbs/sauces: ${lvl(p.cilantro_aversion)}. Cooks meals at home from scratch: ${lvl(p.home_cooking)}. Price sensitivity when grocery shopping: ${lvl(p.price_sensitivity)}. Familiarity with Korean food and Korean food brands: ${lvl(p.kfood_familiarity)}.

━━ Part 1 (before seeing any product) ━━
Q1_dist — How often do you eat Thai or other Southeast Asian food (at a restaurant, delivery, or at home)? [Never / A few times a year / About once a month / A few times a month / Once a week or more]
Q2_dist — Have you ever cooked pad thai (or a similar Thai noodle dish) at home? [Yes, more than once / Yes, once or twice / No, never]
Q2a_dist — (asked only of those who answered "Yes, once or twice" or "No, never" in Q2; so this array sums to 10 minus Q2_dist[0]) What is the main reason you don't cook it at home? [Hard to find the ingredients (tamarind, fish sauce, rice noodles) / I don't know how, it seems complicated / Too much time or effort / I don't like the taste / I'd rather eat it at a restaurant or order delivery / Other (please write)]
Q2a_other_text — if anyone in Q2a chose "Other", what would they write (one short phrase); otherwise an empty string.
Q3_dist — Do you ever avoid Thai or Southeast Asian dishes because of their herbs, sauces, or spices (for example cilantro/coriander leaves, fish sauce, or strong spices)? [Yes, very much / Yes, a little / No]
Q4_dist — In the last 12 months, have you bought a frozen or ready-to-eat Thai meal (for example frozen pad thai)? [Yes / No / Not sure]
Q4a_text — (only if anyone in Q4 answered Yes) Which brand or store was it, and how was it? One short sentence as one of those buyers would write it; otherwise an empty string.

━━ Part 2 (product idea shown here for the first time) ━━
Q5 — Please read this product idea: "A single-serving frozen pad thai you heat in the microwave for 5 minutes. Instead of tamarind, the sauce uses Korean green plum syrup (maesil), and there is no cilantro, so the flavor is milder and easier for people who find Thai dishes too strong, or who are trying pad thai for the first time."
Q5_reading — First, in one or two sentences and in your own words as this person, what do you understand this product to be?
Q5_unclear_terms — List any words or phrases in that description that you, as this person, would not know or would find confusing (for example an ingredient you have never heard of). Empty list if everything is clear to you.
Q5_dist — How interested would you be in trying it? [1 Not at all interested / 2 / 3 / 4 / 5 Very interested]
Q6 — If this product were sold at your usual grocery store (one serving, about 300 g / 10.5 oz), would you buy it at each of these prices? (answer every row) — number of the 10 who say Yes at each price:
buy_499 ($4.99) / buy_599 ($5.99) / buy_699 ($6.99) / buy_799 ($7.99)
Q7_text — In one sentence: what would make you buy it, or not buy it? (your own answer, as this person)
Q8_dist — Have you tried Korean food or Korean food brands (for example Bibigo)? [Yes, and I know Bibigo / I have had Korean food but don't know the brands / No]
Q10_text — (optional) If you wanted to find a product like this online, what words would you search for? (a few search words as this person would type them; empty string if you would skip this optional question)`
}
phase('USLITE')
const personas = typeof args === 'string' ? JSON.parse(args) : args
const out = (await parallel(personas.map(p => () =>
  agent(prompt(p), { label: `uslite:pid${p.pid}`, phase: 'USLITE', schema: SCHEMA, effort: 'medium' })
))).filter(Boolean)
log(`US lite 분포 생성: ${out.length}/${personas.length}`)
return { uslite: out }
