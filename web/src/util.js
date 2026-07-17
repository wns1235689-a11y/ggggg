import { useEffect, useState, useCallback } from 'react'

// 로딩/에러/데이터 boilerplate 공용화. deps 바뀌면 재실행. reload()로 수동 재조회.
export function useAsync(fn, deps) {
  const [state, setState] = useState({ loading: true, data: null, error: null })
  const run = useCallback(() => {
    setState({ loading: true, data: null, error: null })
    fn()
      .then((d) => setState({ loading: false, data: d, error: null }))
      .catch((e) => setState({ loading: false, data: null, error: e.message }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { run() }, [run])
  return { ...state, reload: run }
}

export function fmtTime(epoch) {
  if (!epoch) return '—'
  const d = new Date(epoch * 1000)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export const dash = (v) => (v === null || v === undefined || v === '' ? '—' : v)
