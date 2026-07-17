import React from 'react'

// 경량 마크다운 렌더러 — 리포트가 쓰는 구성만 지원(헤딩·표·목록·인용·hr·굵게·code).
// 외부 라이브러리 없음(자족). 리포트 markdown은 백엔드가 조립한 신뢰 소스.
function renderInline(text, kp) {
  const nodes = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0, m, i = 0
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    const tok = m[0]
    if (tok.startsWith('**')) nodes.push(<strong key={kp + i}>{tok.slice(2, -2)}</strong>)
    else nodes.push(<code key={kp + i}>{tok.slice(1, -1)}</code>)
    last = m.index + tok.length
    i++
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

function splitRow(row) {
  return row.replace(/^\|/, '').replace(/\|$/, '').split('|').map((s) => s.trim())
}

function renderTable(rows, bi) {
  if (rows.length < 1) return null
  const header = splitRow(rows[0])
  const bodyStart = rows.length > 1 && /^\|[\s:|-]+\|?$/.test(rows[1]) ? 2 : 1
  const body = rows.slice(bodyStart).map(splitRow)
  return (
    <div key={bi} style={{ overflowX: 'auto' }}>
      <table>
        <thead><tr>{header.map((h, hi) => <th key={hi}>{renderInline(h, `th${bi}-${hi}-`)}</th>)}</tr></thead>
        <tbody>{body.map((r, ri) => (
          <tr key={ri}>{r.map((c, ci) => <td key={ci}>{renderInline(c, `td${bi}-${ri}-${ci}-`)}</td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  )
}

export default function Markdown({ text }) {
  const lines = (text || '').split('\n')
  const blocks = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (/^#{1,6}\s/.test(line)) {
      blocks.push({ type: 'h', level: line.match(/^#+/)[0].length, content: line.replace(/^#+\s/, '') })
      i++
    } else if (/^\|/.test(line)) {
      const tbl = []
      while (i < lines.length && /^\|/.test(lines[i])) { tbl.push(lines[i]); i++ }
      blocks.push({ type: 'table', rows: tbl })
    } else if (/^\s*[-*]\s/.test(line)) {
      const items = []
      while (i < lines.length && /^\s*[-*]\s/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s/, '')); i++ }
      blocks.push({ type: 'ul', items })
    } else if (/^>\s?/.test(line)) {
      const q = []
      while (i < lines.length && /^>\s?/.test(lines[i])) { q.push(lines[i].replace(/^>\s?/, '')); i++ }
      blocks.push({ type: 'quote', content: q.join(' ') })
    } else if (/^---+$/.test(line.trim())) {
      blocks.push({ type: 'hr' }); i++
    } else if (line.trim() === '') {
      i++
    } else {
      blocks.push({ type: 'p', content: line }); i++
    }
  }
  return (
    <div className="md-render">
      {blocks.map((b, bi) => {
        switch (b.type) {
          case 'h': {
            const Tag = `h${Math.min(b.level, 4)}`
            return React.createElement(Tag, { key: bi }, renderInline(b.content, `h${bi}-`))
          }
          case 'p': return <p key={bi}>{renderInline(b.content, `p${bi}-`)}</p>
          case 'ul': return <ul key={bi}>{b.items.map((it, ii) => <li key={ii}>{renderInline(it, `l${bi}-${ii}-`)}</li>)}</ul>
          case 'quote': return <blockquote key={bi}>{renderInline(b.content, `q${bi}-`)}</blockquote>
          case 'hr': return <hr key={bi} />
          case 'table': return renderTable(b.rows, bi)
          default: return null
        }
      })}
    </div>
  )
}
