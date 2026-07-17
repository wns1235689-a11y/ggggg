import { createContext } from 'react'

// 선택된 런은 화면 간 공유(진단·판정·리포트가 같은 런을 봄). App이 Provider.
export const RunContext = createContext({ runId: null, setRunId: () => {} })
