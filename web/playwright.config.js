import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

// e2e: 백엔드(uvicorn) + 프론트(빌드→preview)를 자동 기동하고 브라우저로 검증.
// 브라우저는 env 프리설치 chromium 사용(재다운로드 안 함).
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const runsDir = path.join(repoRoot, 'runs')
const API_PORT = process.env.VITE_API_PORT || '8781'

export default defineConfig({
  testDir: './e2e',
  timeout: 45000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    launchOptions: { executablePath: '/opt/pw-browsers/chromium' },
  },
  webServer: [
    {
      command: `python3 -m uvicorn harness_api.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: repoRoot,
      env: { HARNESS_RUNS: runsDir },
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: true,
      timeout: 60000,
    },
    {
      command: 'npm run build && npm run preview',
      env: { VITE_API_PORT: API_PORT },
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: true,
      timeout: 90000,
    },
  ],
})
