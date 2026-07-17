import React, { useContext } from 'react'
import { api } from '../api.js'
import { RunContext } from '../runContext.js'
import { useAsync, dash } from '../util.js'
import RunPicker from '../components/RunPicker.jsx'

// 판정 대시보드 — SPEC §5.3. 연속상관(부호·유의)·다풀 부호일관·세그교차(n<15 경고)·
// dose-response·D1 수용곡선. 각 신호에 등급 라벨(§⑨: sim-내 견고 / 참고 / 신뢰불가).
export default function Judge() {
  const { runId } = useContext(RunContext)
  return (
    <section className="screen">
      <h2>판정 대시보드 <span className="muted" style={{ fontSize: 12 }}>방향성 prior (v23_judge / multi)</span></h2>
      <RunPicker title="판정할 런 선택" />
      {runId ? <JudgeResult runId={runId} /> : <p className="muted">위에서 런을 선택하세요.</p>}
    </section>
  )
}

function Grade({ g }) {
  const map = {
    prior: ['badge ok', 'sim-내 견고(prior)'],
    ref: ['badge', '참고'],
    unreliable: ['badge warn', '신뢰불가(수준)'],
  }
  const [cls, label] = map[g] || ['badge', g]
  return <span className={cls}>{label}</span>
}

function sgn(v) {
  if (v == null) return '—'
  const s = v > 0 ? '+' : ''
  return `${s}${v}`
}

function JudgeResult({ runId }) {
  const jq = useAsync(() => api.judge(runId), [runId])
  const cq = useAsync(() => api.curve(runId), [runId])

  if (jq.loading) return <p className="spin">판정 실행 중…</p>
  if (jq.error) return <p className="err">판정 실패: {jq.error} <button className="ghost" onClick={jq.reload}>재시도</button></p>
  const j = jq.data
  if (!j.judgeable) {
    return <div className="panel"><p className="muted">이 런은 판정 대상이 아닙니다 ({j.format}). {j.note}</p></div>
  }
  const curve = cq.data && cq.data.available ? cq.data : null
  return (
    <>
      {j.kind === 'multipool' ? <JudgeMulti j={j} /> : <JudgeSingle j={j} />}
      <D1Curve curve={curve} loading={cq.loading} />
      {(j.caveats || []).length > 0 && (
        <div className="panel"><h3>한계 (덮지 않음)</h3>
          <ul>{j.caveats.map((c, i) => <li key={i} className="muted">{c}</li>)}</ul>
        </div>
      )}
    </>
  )
}

// ── 단일풀 판정 ──
function JudgeSingle({ j }) {
  const cc = j.continuous_corr || {}
  const seg = j.segment_cross || []
  const dr = j.dose_response || {}
  const base = j.base || {}
  const smallN = base.target != null && base.target < 15
  const prev = j.prevalence || {}
  return (
    <>
      <div className="panel">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0 }}>향부담강도 ↔ 반응 연속상관 <Grade g="prior" /></h3>
          <span className="muted">1차대상 n={dash(base.target)} · 전체 n={dash(base.total)}</span>
        </div>
        <p className="muted" style={{ fontSize: 12 }}>{cc.note} · 주지표(seed-free, 소표본 안정)</p>
        <table>
          <thead><tr><th>지표</th><th>r (부호=방향)</th></tr></thead>
          <tbody>
            {['B1', 'C2', 'D1'].map((k) => (
              <tr key={k}>
                <td>{k}</td>
                <td style={{ color: cc[k] < 0 ? 'var(--err)' : cc[k] > 0 ? 'var(--ok)' : 'var(--muted)' }}>{sgn(cc[k])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>매실청 깊이 세그 교차 {smallN && <span className="badge warn">소표본 n={base.target}&lt;15</span>}</h3>
        {smallN && <p className="muted" style={{ fontSize: 12 }}>세그 분할 불안정 — 연속상관을 우선 신뢰.</p>}
        <table>
          <thead><tr><th>컷</th><th>hi n</th><th>lo n</th><th>ΔB1</th><th>ΔC2</th><th>ΔD1(pp)</th><th>판정</th></tr></thead>
          <tbody>
            {seg.map((s, i) => (
              <tr key={i}>
                <td>{s.cut}</td><td>{dash(s.hi_n)}</td><td>{dash(s.lo_n)}</td>
                <td>{s.B1 ? sgn(s.B1.delta) : '—'}</td>
                <td>{s.C2 ? sgn(s.C2.delta) : '—'}</td>
                <td>{s.D1 ? sgn(s.D1.delta_pp) : '—'}</td>
                <td>{s.verdict}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>dose-response · B1 단조 = <span className={dr.b1_monotone ? 'badge ok' : 'badge warn'}>{String(dr.b1_monotone)}</span></h3>
        <table>
          <thead><tr><th>수준</th><th>n</th><th>B1</th><th>C2</th><th>D1%</th></tr></thead>
          <tbody>
            {(dr.groups || []).map((g, i) => (
              <tr key={i}><td>{g.level}</td><td>{g.n}</td><td>{dash(g.B1)}</td><td>{dash(g.C2)}</td><td>{dash(g.D1_pct)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>보조 판정</h3>
        <ul className="muted">
          {j.low_commitment && <li>저커밋(B3): 양·맛={j.low_commitment.yang_mat} vs 가격={j.low_commitment.price} → <b>{j.low_commitment.verdict}</b></li>}
          {j.statement_vs_behavior && <li>진술≠행동(E1): 나={j.statement_vs_behavior.na} 가={j.statement_vs_behavior.ga} 뭉갬={j.statement_vs_behavior.mush} → <b>{j.statement_vs_behavior.verdict}</b></li>}
          {j.a2x_validity && <li>A2x 앵커: 예 강도={j.a2x_validity.intensity_yes} vs 아니오={j.a2x_validity.intensity_no} → <b>{j.a2x_validity.verdict}</b></li>}
        </ul>
      </div>

      {prev.data && (
        <div className="panel">
          <h3>유병률 <Grade g="unreliable" /></h3>
          <p className="muted" style={{ fontSize: 12 }}>{prev.note}</p>
          <table>
            <thead><tr><th>기준</th><th>n</th><th>협의%</th><th>광의%</th><th>질량%</th></tr></thead>
            <tbody>
              {Object.entries(prev.data).map(([label, d]) => (
                <tr key={label}><td>{label}</td><td>{d.n}</td><td>{d.narrow_pct}</td><td>{d.wide_pct}</td><td>{d.mass_wide_pct}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

// ── 다풀 판정 ──
function JudgeMulti({ j }) {
  const integ = j.integrated || {}
  const cc = integ.continuous_corr || {}
  const ens = integ.seed_ensemble
  const sc = j.sign_consistency || {}
  return (
    <>
      <div className="panel">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0 }}>통합 향부담강도 ↔ 반응 연속상관 <Grade g="prior" /></h3>
          <span className="muted">N={dash(j.N)} · 풀={JSON.stringify(j.pools)} · seed={dash(j.sample_seed)}</span>
        </div>
        <table>
          <thead><tr><th>지표</th><th>r</th><th>p</th><th>유의</th></tr></thead>
          <tbody>
            {Object.entries(cc).map(([k, v]) => (
              <tr key={k}>
                <td>{k}</td>
                <td style={{ color: v.r < 0 ? 'var(--err)' : v.r > 0 ? 'var(--ok)' : 'var(--muted)' }}>{sgn(v.r)}</td>
                <td>{dash(v.p)}</td>
                <td><span className={v.sig === 'ns' ? 'badge' : 'badge ok'}>{v.sig}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {ens && <p className="muted" style={{ fontSize: 12 }}>시드앙상블 세그교차 ΔB1 = {sgn(ens.delta_b1_mean)} ± {ens.sd} (seed {ens.seeds}회)</p>}
      </div>

      <div className="panel">
        <h3>풀-부호 일관성 <Grade g="prior" /></h3>
        <table>
          <thead><tr><th>지표</th><th>풀별 r</th><th>부호일관</th></tr></thead>
          <tbody>
            {Object.entries(sc).map(([k, v]) => (
              <tr key={k}>
                <td>{k}</td>
                <td className="muted">{JSON.stringify(v.per_pool_r)}</td>
                <td><span className={v.consistent ? 'badge ok' : 'badge warn'}>{v.consistent ? '일관' : '혼조'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(j.interpretation || []).length > 0 && (
        <div className="panel"><h3>해석</h3>
          <ul className="muted">{j.interpretation.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
    </>
  )
}

// ── D1 가격-수용 곡선(서술적) ──
function D1Curve({ curve, loading }) {
  if (loading) return <div className="panel"><h3>D1 수용곡선</h3><p className="spin">불러오는 중…</p></div>
  if (!curve) return null
  const prices = curve.prices || []
  const tgt = curve.accept_target_pct
  const all = curve.accept_all_pct || []
  const series = tgt || all
  return (
    <div className="panel">
      <h3>D1 가격-수용 곡선 <Grade g="unreliable" /></h3>
      <p className="muted" style={{ fontSize: 12 }}>{curve.discipline}</p>
      <table>
        <thead><tr><th>가격</th><th>수용률(막대)</th><th>{tgt ? '타깃%' : '전체%'}</th>{tgt && <th>전체%</th>}</tr></thead>
        <tbody>
          {prices.map((p, i) => (
            <tr key={p}>
              <td>₩{p.toLocaleString()}</td>
              <td style={{ width: 220 }}>
                <span style={{
                  display: 'inline-block', height: 12, borderRadius: 4,
                  width: `${(series[i] || 0) * 2}px`, background: 'var(--accent)',
                }} />
              </td>
              <td>{dash(series[i])}</td>
              {tgt && <td className="muted">{dash(all[i])}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted" style={{ fontSize: 12 }}>n(타깃)={dash(curve.n_target)} · n(전체)={dash(curve.n_all)} — 절대 높이 신뢰X, 기울기(방향)만 참고.</p>
    </div>
  )
}
