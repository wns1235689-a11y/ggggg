import React from 'react'
import { api } from '../api.js'
import { useAsync, dash } from '../util.js'

// 설계 뷰어(읽기 전용) — SPEC §5.5. v2.3 문항·페르소나 latent·ANCHOR_PRIORS를
// 코드에서 파싱해 표시. **편집 기능 없음(v2로 명시 이연).**
export default function Design() {
  const { loading, data, error, reload } = useAsync(() => api.design(), [])

  if (loading) return <section className="screen"><h2>설계 뷰어</h2><p className="spin">불러오는 중…</p></section>
  if (error) return <section className="screen"><h2>설계 뷰어</h2><p className="err">불러오기 실패: {error}</p><button className="ghost" onClick={reload}>재시도</button></section>

  const q = data.questions || {}
  const items = q.items || []
  const latent = data.latent_specs || {}
  const anchors = data.anchor_priors || {}

  return (
    <section className="screen">
      <h2>설계 뷰어 <span className="muted" style={{ fontSize: 12 }}>읽기 전용 · 편집은 v2 이연</span></h2>

      {/* 컨셉 카드 + 메타 */}
      <div className="panel">
        <h3>컨셉 · 설계 메타</h3>
        <p>{q.concept_card}</p>
        <table>
          <tbody>
            <tr><th>버전</th><td>{dash(q.version)}</td></tr>
            <tr><th>출처</th><td><code>{dash(q.source)}</code></td></tr>
            <tr><th>스키마 필드</th><td className="muted">{(q.schema_required || []).join(', ')}</td></tr>
          </tbody>
        </table>
        {q.note && <p className="muted" style={{ fontSize: 12 }}>※ {q.note}</p>}
      </div>

      {/* 문항 */}
      <div className="panel">
        <h3>v2.3 문항 ({items.length})</h3>
        <table>
          <thead><tr><th>필드</th><th>유형</th><th>문항</th><th>보기/척도</th></tr></thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.field}>
                <td><code>{it.field}</code></td>
                <td>{it.type}</td>
                <td>{it.label}</td>
                <td className="muted">{(it.options || it.scale || []).join(' · ') || dash(null)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Latent 스펙 */}
      <div className="panel">
        <h3>페르소나 latent 스펙 (μ / σ)</h3>
        <table>
          <thead><tr><th>latent</th><th>μ (평균)</th><th>σ (표준편차)</th></tr></thead>
          <tbody>
            {Object.entries(latent).map(([k, v]) => (
              <tr key={k}><td>{k}</td><td>{dash(v?.mu)}</td><td>{dash(v?.sd)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Anchor priors */}
      <div className="panel">
        <h3>ANCHOR_PRIORS (사전분포 앵커)</h3>
        <p className="muted" style={{ fontSize: 12 }}>유병률·수용률 '수준'은 이 앵커에 묶임 → 시뮬로 신뢰 불가(실측 몫).</p>
        <table>
          <thead><tr><th>앵커</th><th>값</th></tr></thead>
          <tbody>
            {Object.entries(anchors).map(([k, v]) => (
              <tr key={k}>
                <td><code>{k}</code></td>
                <td className="muted" style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>
                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
