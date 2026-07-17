import React, { useContext } from 'react'
import { api } from '../api.js'
import { RunContext } from '../runContext.js'
import { useAsync, fmtTime, dash } from '../util.js'

// 런 히스토리 테이블 + 선택(runs/ 스캔). 진단·판정·리포트가 공유.
// 자체 상태 없음 — /api/runs 를 읽어 렌더, 클릭 시 RunContext.runId 설정.
export default function RunPicker({ title = '런 선택', kindFilter }) {
  const { runId, setRunId } = useContext(RunContext)
  const { loading, data, error, reload } = useAsync(() => api.runs(), [])

  let runs = data?.runs || []
  if (kindFilter) runs = runs.filter((r) => r.kind === kindFilter)

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <button className="ghost" onClick={reload}>새로고침</button>
      </div>
      {loading && <p className="spin">런 목록 불러오는 중…</p>}
      {error && <p className="err">불러오기 실패: {error}</p>}
      {!loading && !error && runs.length === 0 && <p className="muted">런이 없습니다.</p>}
      {runs.length > 0 && (
        <table>
          <thead>
            <tr><th></th><th>run_id</th><th>종류</th><th>N</th><th>effort</th><th>시드</th><th>일시</th></tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id}
                  onClick={() => setRunId(r.run_id)}
                  style={{ cursor: 'pointer', background: r.run_id === runId ? 'var(--panel2)' : undefined }}>
                <td>{r.run_id === runId ? '●' : ''}</td>
                <td><code>{r.run_id}</code></td>
                <td>{r.kind}{r.dry_run ? ' (dry)' : ''}</td>
                <td>{dash(r.N)}</td>
                <td>{dash(r.effort)}</td>
                <td>{dash(r.seed)}</td>
                <td className="muted">{fmtTime(r.created)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
