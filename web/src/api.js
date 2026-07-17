// 얇은 API 클라이언트 — FastAPI 백엔드(SPEC §1). 자체 상태 없음, runs/를 읽는 GET 위주.
// 개발 시 Vite 프록시가 /api → 백엔드로 넘김(vite.config.js).

async function j(path, opts) {
  const res = await fetch(path, opts)
  const text = await res.text()
  let data
  try { data = text ? JSON.parse(text) : null } catch { data = { raw: text } }
  if (!res.ok) {
    const msg = (data && (data.detail || data.error)) || res.statusText
    throw new Error(`${res.status} ${msg}`)
  }
  return data
}

export const api = {
  health: () => j('/api/health'),

  // 읽기(런/풀/설계)
  runs: () => j('/api/runs'),
  pools: () => j('/api/pools'),
  run: (id) => j(`/api/runs/${id}`),
  pool: (id) => j(`/api/pools/${id}`),
  design: () => j('/api/design'),

  // 진단·판정·리포트·수용곡선
  diagnose: (id) => j(`/api/runs/${id}/diagnose`),
  judge: (id) => j(`/api/runs/${id}/judge`),
  curve: (id) => j(`/api/runs/${id}/curve`),
  report: (id) => j(`/api/runs/${id}/report`),

  // 액션(실행 콘솔)
  createPool: (body) => j('/api/pools', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }),
  createRun: (body) => j('/api/runs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }),
  jobs: () => j('/api/jobs'),
  job: (id) => j(`/api/jobs/${id}`),
}
