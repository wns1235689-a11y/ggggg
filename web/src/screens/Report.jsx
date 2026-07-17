import React, { useContext, useState } from 'react'
import { api } from '../api.js'
import { RunContext } from '../runContext.js'
import { useAsync } from '../util.js'
import RunPicker from '../components/RunPicker.jsx'
import Markdown from '../components/Markdown.jsx'

// 리포트 — SPEC §5.4. 게이트C_시뮬결과_정리.md 포맷 자동 생성(런 데이터 채움).
// ⓪ 경고 헤더는 백엔드 하드코딩으로 항상 포함(끌 수 없음). 여기선 렌더 + 내보내기만.
export default function Report() {
  const { runId } = useContext(RunContext)
  return (
    <section className="screen">
      <h2>리포트 <span className="muted" style={{ fontSize: 12 }}>게이트C 결과정리 포맷 자동 생성</span></h2>
      <RunPicker title="리포트할 런 선택" />
      {runId ? <ReportView runId={runId} /> : <p className="muted">위에서 런을 선택하세요.</p>}
    </section>
  )
}

function ReportView({ runId }) {
  const { loading, data, error, reload } = useAsync(() => api.report(runId), [runId])
  const [raw, setRaw] = useState(false)

  if (loading) return <p className="spin">리포트 생성 중…</p>
  if (error) return <p className="err">리포트 실패: {error} <button className="ghost" onClick={reload}>재시도</button></p>

  const md = data.markdown || ''
  const copy = () => navigator.clipboard && navigator.clipboard.writeText(md)
  const download = () => {
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `리포트_${runId}.md`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <div className="panel row" style={{ justifyContent: 'space-between' }}>
        <div>
          <span className="badge ok">⓪ 경고 헤더 포함</span>
          <span className="muted"> · 포맷 {data.format} · {data.kind}</span>
        </div>
        <div className="row">
          <button className="ghost" onClick={() => setRaw(!raw)}>{raw ? '렌더 보기' : '원문(.md)'}</button>
          <button className="ghost" onClick={copy}>복사</button>
          <button className="action" onClick={download}>다운로드(.md)</button>
        </div>
      </div>
      {raw
        ? <pre className="md">{md}</pre>
        : <div className="panel"><Markdown text={md} /></div>}
    </>
  )
}
