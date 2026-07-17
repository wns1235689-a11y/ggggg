import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import { RunContext } from './runContext.js'
import Console from './screens/Console.jsx'
import Diagnose from './screens/Diagnose.jsx'
import Judge from './screens/Judge.jsx'
import Report from './screens/Report.jsx'
import Design from './screens/Design.jsx'

// SPEC §5: 화면 4+1(이 목록이 상한). 자체 상태 없음 — runs/를 읽어 렌더.
const TABS = [
  { key: 'console', label: '실행 콘솔', el: Console },
  { key: 'diagnose', label: '진단', el: Diagnose },
  { key: 'judge', label: '판정', el: Judge },
  { key: 'report', label: '리포트', el: Report },
  { key: 'design', label: '설계 뷰어', el: Design },
]

export default function App() {
  const [tab, setTab] = useState('console')
  const [runId, setRunId] = useState(null)
  const [health, setHealth] = useState(null)
  const [healthErr, setHealthErr] = useState(null)

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setHealthErr(e.message))
  }, [])

  const Active = TABS.find((t) => t.key === tab).el

  return (
    <RunContext.Provider value={{ runId, setRunId }}>
      <div className="app">
        <header className="topbar">
          <div className="brand">게이트 C · Research Harness <span className="ver">UI 0.1</span></div>
          <div className="run-indicator">
            {runId ? <>선택된 런: <code>{runId}</code></> : <span className="muted">런 미선택</span>}
          </div>
        </header>

        {/* ⓪ 합성·비실측 경고 — 상시 노출(끌 수 없음), 리포트 하드코딩 헤더와 동일 규율 */}
        <div className="warn-banner" role="alert">
          <strong>합성·비실측(synthetic).</strong> 모든 수치는 LLM 합성 prior — 실측 설문 아님.
          방향(부호)만 참고, 절대값·유병률 수준은 신뢰 불가. <strong>인용 금지.</strong>
        </div>

        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={t.key === tab ? 'tab active' : 'tab'}
              onClick={() => setTab(t.key)}
            >{t.label}</button>
          ))}
        </nav>

        <main className="content">
          <Active />
        </main>

        <footer className="statusbar">
          {healthErr
            ? <span className="err">백엔드 연결 실패: {healthErr}</span>
            : health
              ? <span className="ok">백엔드 OK · runs: <code>{health.runs_dir}</code></span>
              : <span className="muted">백엔드 확인 중…</span>}
        </footer>
      </div>
    </RunContext.Provider>
  )
}
