import React, { useContext, useState } from 'react'
import { api } from '../api.js'
import { RunContext } from '../runContext.js'
import { useAsync, dash } from '../util.js'
import RunPicker from '../components/RunPicker.jsx'

// 진단 패널 — SPEC §5.2. 선택 런에 붕괴/동질성 진단(v23_verify JSON):
// 보기 사용률, 믿음질량 vs realized, 최빈패턴 점유율, 붕괴 3종 체크,
// 임계 초과 시 경고 배지 + 처방 문구(게이트C §2c).
export default function Diagnose() {
  const { runId } = useContext(RunContext)
  return (
    <section className="screen">
      <h2>진단 패널 <span className="muted" style={{ fontSize: 12 }}>붕괴·동질성 (v23_verify)</span></h2>
      <RunPicker title="진단할 런 선택" />
      {runId ? <DiagnoseResult runId={runId} /> : <p className="muted">위에서 런을 선택하세요.</p>}
    </section>
  )
}

function StatusBadge({ status }) {
  const cls = status === 'ok' ? 'badge ok' : status === '참고' ? 'badge' : 'badge warn'
  return <span className={cls}>{status}</span>
}

function DiagnoseResult({ runId }) {
  const { loading, data, error, reload } = useAsync(() => api.diagnose(runId), [runId])
  const [open, setOpen] = useState(null)

  if (loading) return <p className="spin">진단 실행 중…</p>
  if (error) return <p className="err">진단 실패: {error} <button className="ghost" onClick={reload}>재시도</button></p>
  if (!data.diagnosable) {
    return <div className="panel"><p className="muted">이 런은 진단 대상이 아닙니다 ({data.format}). {data.note}</p></div>
  }

  const cc = data.collapse_checks || {}
  const th = data.thresholds || {}
  const homog = cc.cross_persona_homogeneity || {}
  const e1n = cc.within_item_E1_neutral || {}
  const ou = cc.option_usage || {}
  const a2p = cc.A2_prevalence_info || {}
  const warnPct = th.homogeneity_modal_share_warn_pct
  const highPct = th.homogeneity_modal_share_high_pct
  const items = data.items || {}
  const warnings = data.warnings || []

  const shareBadge = (pct) => {
    if (pct == null) return null
    const cls = highPct != null && pct >= highPct ? 'badge err'
      : warnPct != null && pct >= warnPct ? 'badge warn' : 'badge ok'
    return <span className={cls}>{pct}%</span>
  }

  return (
    <>
      <div className="panel">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0 }}>붕괴/동질성 체크 · N={dash(data.N)}</h3>
          <button className="ghost" onClick={reload}>재실행</button>
        </div>
        <table>
          <thead><tr><th>체크</th><th>값</th><th>상태</th></tr></thead>
          <tbody>
            <tr>
              <td>페르소나 간 동질성(최빈패턴 점유 최악)</td>
              <td>{homog.worst_field} {shareBadge(homog.modal_share_pct)}</td>
              <td><StatusBadge status={homog.status} /></td>
            </tr>
            <tr>
              <td>문항 내 붕괴(E1 중립 realized)</td>
              <td>{dash(e1n['비슷+둘다_realized'])}</td>
              <td><StatusBadge status={e1n.status} /></td>
            </tr>
            <tr>
              <td>보기 사용률(최소)</td>
              <td>{ou.worst_field} · {dash(ou.min_used_ratio)}</td>
              <td>—</td>
            </tr>
            <tr>
              <td>A2 향부담 광의 믿음질량 <span className="muted">(참고·수준 신뢰X)</span></td>
              <td>{dash(a2p['향부담_광의_믿음질량_pct'])}%</td>
              <td><StatusBadge status="참고" /></td>
            </tr>
          </tbody>
        </table>
        <p className="muted" style={{ fontSize: 12 }}>
          휴리스틱 임계(진단계층·엔진 아님): 최빈패턴 점유 경고≥{dash(warnPct)}% / 높음≥{dash(highPct)}%.
        </p>
      </div>

      {warnings.length > 0 ? (
        <div className="panel" style={{ borderColor: '#6b4f0a' }}>
          <h3 style={{ color: 'var(--warn)' }}>⚠ 경고 배지</h3>
          <ul>{warnings.map((w, i) => (
            <li key={i}>
              {typeof w === 'string'
                ? w
                : <><b>{w.message}</b>{w.prescription ? <> — 처방: {w.prescription}</> : null}</>}
            </li>
          ))}</ul>
          <p className="muted" style={{ fontSize: 12 }}>
            처방(게이트C §2c): effort 상향(low→medium) · 특성 등급 5단계 · 특성-조건화 프롬프트 강화.
          </p>
        </div>
      ) : (
        <div className="panel"><span className="badge ok">경고 없음</span> <span className="muted">임계 내.</span></div>
      )}

      <div className="panel">
        <h3>문항별 — 보기 사용·최빈패턴 점유율 <span className="muted" style={{ fontSize: 12 }}>(행 클릭 → 믿음질량 vs realized)</span></h3>
        <table>
          <thead><tr><th>문항</th><th>보기사용</th><th>서로다른패턴</th><th>최빈패턴 점유</th></tr></thead>
          <tbody>
            {Object.entries(items).map(([key, it]) => (
              <React.Fragment key={key}>
                <tr onClick={() => setOpen(open === key ? null : key)} style={{ cursor: 'pointer' }}>
                  <td>{open === key ? '▾ ' : '▸ '}<code>{it.name || key}</code></td>
                  <td>{it.options_used}/{it.options_total}</td>
                  <td>{dash(it.distinct_patterns)}</td>
                  <td>{shareBadge(it.modal_pattern_share_pct)}</td>
                </tr>
                {open === key && (
                  <tr><td colSpan={4} style={{ background: 'var(--bg)' }}>
                    <BeliefVsRealized item={it} />
                  </td></tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

// 믿음질량(belief_mass_pct) vs realized(표집 실현 수) — 보기별.
function BeliefVsRealized({ item }) {
  const opts = item.options || []
  const belief = item.belief_mass_pct || []
  const realized = item.realized_counts || {}
  const maxB = Math.max(1, ...belief)
  return (
    <table style={{ margin: '4px 0' }}>
      <thead><tr><th>보기</th><th>믿음질량%</th><th></th><th>realized</th></tr></thead>
      <tbody>
        {opts.map((o, i) => (
          <tr key={o + i}>
            <td>{o}</td>
            <td style={{ width: 60 }}>{dash(belief[i])}</td>
            <td style={{ width: 160 }}>
              <span style={{
                display: 'inline-block', height: 8, borderRadius: 4,
                width: `${(belief[i] || 0) / maxB * 140}px`, background: 'var(--accent)',
              }} />
            </td>
            <td>{dash(realized[o])}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
