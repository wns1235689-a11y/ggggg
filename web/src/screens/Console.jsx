import React, { useContext, useEffect, useState } from 'react'
import { api } from '../api.js'
import { RunContext } from '../runContext.js'
import { useAsync, fmtTime, dash } from '../util.js'
import RunPicker from '../components/RunPicker.jsx'

// 실행 콘솔 — SPEC §5.1. 풀 생성(동기) / 시뮬 실행(백그라운드 잡·비용 가드) /
// 잡 현황 / 런 히스토리. 단계별(풀→시뮬→진단→판정) 독립 — 진단·판정은 각 탭에서.
const SCRIPT_FOR = { single: 'wf_vs_v23.js', multipool: 'wf_v23_multi.js', sweep: 'wf_vs_v23.js' }
// runner.py와 동일 상수(예상 규모·가드 표시용) — 값 변경 시 runner.py와 동기 유지.
const LARGE_N = 50               // runner.py LARGE_N
const DRY_RUN_CAP = 2            // runner.py DRY_RUN_CAP
const PER_PERSONA_TOKENS = 24000 // runner.py PER_PERSONA_TOKENS(관측 대략치)
const QUESTIONS_V23 = 13         // v2.3 문항 수(설계 뷰어와 동일)

export default function Console() {
  const [poolsKey, setPoolsKey] = useState(0)     // 풀 생성 후 목록 갱신 트리거
  const [jobsKey, setJobsKey] = useState(0)
  return (
    <section className="screen">
      <h2>실행 콘솔 <span className="muted" style={{ fontSize: 12 }}>풀 생성 · 시뮬 트리거 · 잡 현황</span></h2>
      <PoolCreate onCreated={() => setPoolsKey((k) => k + 1)} />
      <RunTrigger poolsKey={poolsKey} onStarted={() => setJobsKey((k) => k + 1)} />
      <Jobs jobsKey={jobsKey} />
      <RunPicker title="런 히스토리 (클릭 → 진단·판정·리포트 탭에서 열림)" />
    </section>
  )
}

// ── 풀 생성(동기) ──
function PoolCreate({ onCreated }) {
  const [kind, setKind] = useState('single')
  const [seed, setSeed] = useState('')
  const [n, setN] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)

  const create = async () => {
    setBusy(true); setErr(null); setResult(null)
    try {
      const body = { kind }
      if (seed !== '') body.seed = Number(seed)
      if (n !== '') body.n = Number(n)
      const r = await api.createPool(body)
      setResult(r)
      onCreated && onCreated()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="panel">
      <h3>① 풀 생성 <span className="muted" style={{ fontSize: 12 }}>build_* 동기 실행 → runs/&lt;pool_id&gt;/</span></h3>
      <div className="row">
        <div><label>종류</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="single">single</option>
            <option value="multipool">multipool</option>
            <option value="sweep">sweep</option>
          </select>
        </div>
        <div><label>시드(선택)</label><input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="비우면 무작위" style={{ width: 130 }} /></div>
        <div><label>N(선택)</label><input value={n} onChange={(e) => setN(e.target.value)} placeholder="기본값" style={{ width: 90 }} /></div>
        <button className="action" onClick={create} disabled={busy}>{busy ? '생성 중…' : '풀 생성'}</button>
      </div>
      {err && <p className="err">생성 실패: {err}</p>}
      {result && (
        <div style={{ marginTop: 10 }}>
          <span className="badge ok">생성됨</span> pool_id=<code>{result.pool_id}</code>
          <pre className="md" style={{ maxHeight: 160, marginTop: 6 }}>{(result.summary || []).join('\n')}</pre>
        </div>
      )}
    </div>
  )
}

// ── 시뮬 실행(백그라운드 잡 · 비용 가드) ──
function RunTrigger({ poolsKey, onStarted }) {
  const { data, loading, error, reload } = useAsync(() => api.pools(), [poolsKey])
  const [poolId, setPoolId] = useState('')
  const [effort, setEffort] = useState('medium')
  const [dryRun, setDryRun] = useState(true)
  const [confirmLarge, setConfirmLarge] = useState(false)
  const [busy, setBusy] = useState(false)
  const [started, setStarted] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => { reload() }, [poolsKey]) // eslint-disable-line
  const pools = data?.pools || []
  const sel = pools.find((p) => p.pool_id === poolId)
  const script = sel ? (SCRIPT_FOR[sel.kind] || 'wf_vs_v23.js') : ''
  // 실효 규모: 다풀은 N_per × 풀수, dry-run이면 DRY_RUN_CAP로 축소(러너와 동일).
  const perPool = sel?.N
  const nPools = sel?.N_pools || 1
  const fullN = typeof perPool === 'number' ? perPool * nPools : undefined
  const effPersonas = fullN == null ? undefined : (dryRun ? Math.min(fullN, DRY_RUN_CAP) : fullN)
  const estTokens = effPersonas == null ? undefined : effPersonas * PER_PERSONA_TOKENS
  const large = !dryRun && typeof fullN === 'number' && fullN > LARGE_N
  const blocked = !poolId || (large && !confirmLarge)

  const start = async () => {
    setBusy(true); setErr(null); setStarted(null)
    try {
      const r = await api.createRun({
        script, pool_id: poolId, effort, dry_run: dryRun, confirm_large: confirmLarge,
      })
      setStarted(r)
      onStarted && onStarted()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="panel">
      <h3>② 시뮬 실행 <span className="muted" style={{ fontSize: 12 }}>러너(Claude Code 서브프로세스) · 백그라운드 잡</span></h3>
      {loading && <p className="spin">풀 목록…</p>}
      {error && <p className="err">풀 목록 실패: {error}</p>}
      <div className="row">
        <div><label>풀</label>
          <select value={poolId} onChange={(e) => { setPoolId(e.target.value); setConfirmLarge(false) }}>
            <option value="">— 풀 선택 —</option>
            {pools.map((p) => <option key={p.pool_id} value={p.pool_id}>{p.pool_id} ({p.kind}, N={dash(p.N)})</option>)}
          </select>
        </div>
        <div><label>스크립트</label><input value={script} readOnly style={{ width: 140 }} /></div>
        <div><label>effort</label>
          <select value={effort} onChange={(e) => setEffort(e.target.value)}>
            <option value="low">low</option><option value="medium">medium</option><option value="high">high</option>
          </select>
        </div>
        <div><label>&nbsp;</label><label style={{ color: 'var(--text)' }}><input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} /> dry-run(2명)</label></div>
        <button className="action" onClick={start} disabled={busy || blocked}>{busy ? '트리거 중…' : '시뮬 실행'}</button>
      </div>

      {/* 실행 전 예상 규모(SPEC §4 비용가드②) — 러너 견적과 동일 산식 */}
      {sel && effPersonas != null && (
        <div style={{ marginTop: 8, fontSize: 12 }} className="muted">
          예상 규모: <b>{effPersonas.toLocaleString()}</b>명 × {QUESTIONS_V23}문항 · 1에이전트/명 ·
          예상 토큰 <b>~{estTokens.toLocaleString()}</b>
          {dryRun && fullN > DRY_RUN_CAP && <> <span className="badge ok">dry-run 축소 {fullN.toLocaleString()}→{DRY_RUN_CAP}명</span></>}
          {nPools > 1 && <> <span className="muted">(다풀 {perPool}명×{nPools}풀)</span></>}
        </div>
      )}

      {/* 비용 가드 UI — runner.py가 강제하는 기준을 미리 표시 */}
      <div style={{ marginTop: 6, fontSize: 12 }}>
        {dryRun
          ? <span className="badge ok">dry-run · {DRY_RUN_CAP}명만 실행(비용 최소)</span>
          : large
            ? <>
                <span className="badge warn">대규모 N={fullN} &gt; {LARGE_N}</span>{' '}
                <label style={{ display: 'inline', color: 'var(--warn)' }}>
                  <input type="checkbox" checked={confirmLarge} onChange={(e) => setConfirmLarge(e.target.checked)} /> 대규모 실행 확인(confirm_large)
                </label>
                {!confirmLarge && <span className="muted"> — 확인 없으면 러너가 거부.</span>}
              </>
            : <span className="muted">실비용 실행(N={dash(fullN)}).</span>}
      </div>

      {err && <p className="err">트리거 실패: {err}</p>}
      {started && (
        <p style={{ marginTop: 8 }}><span className="badge ok">잡 시작</span> job_id=<code>{started.job_id}</code> · 아래 잡 현황에서 추적.</p>
      )}
    </div>
  )
}

// ── 잡 현황(폴링) ──
function Jobs({ jobsKey }) {
  const [jobs, setJobs] = useState([])
  const [err, setErr] = useState(null)

  const load = async () => {
    try { const r = await api.jobs(); setJobs(r.jobs || []); setErr(null) } catch (e) { setErr(e.message) }
  }
  useEffect(() => { load() }, [jobsKey]) // eslint-disable-line
  useEffect(() => {
    const running = jobs.some((j) => j.status === 'running')
    if (!running) return
    const t = setInterval(load, 2500)
    return () => clearInterval(t)
  }, [jobs]) // eslint-disable-line

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3 style={{ margin: 0 }}>③ 잡 현황 <span className="muted" style={{ fontSize: 12 }}>running이면 자동 폴링</span></h3>
        <button className="ghost" onClick={load}>새로고침</button>
      </div>
      {err && <p className="err">{err}</p>}
      {jobs.length === 0 ? <p className="muted">잡 없음.</p> : (
        <table>
          <thead><tr><th>job_id</th><th>스크립트</th><th>풀</th><th>dry</th><th>상태</th><th>run_id</th></tr></thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.job_id}>
                <td><code>{j.job_id}</code></td>
                <td>{j.script}</td>
                <td><code>{j.pool_id}</code></td>
                <td>{String(j.dry_run)}</td>
                <td>
                  <span className={j.status === 'completed' ? 'badge ok' : j.status === 'failed' ? 'badge err' : 'badge warn'}>{j.status}</span>
                </td>
                <td>{j.result?.run_id ? <code>{j.result.run_id}</code> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
