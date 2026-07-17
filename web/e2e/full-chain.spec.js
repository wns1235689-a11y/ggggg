import { test, expect } from '@playwright/test'

// P2-6g: P2 완료 기준 — dry_run 신규 런을 콘솔에서 트리거 → 잡 완료 → 진단·판정까지
// 화면에서 확인. 실제 claude 서브프로세스(2명·비용)를 띄우므로 기본 skip.
// 검증 실행:  RUN_FULL_CHAIN=1 npx playwright test full-chain
const enabled = process.env.RUN_FULL_CHAIN === '1'

test.describe('P2 완료기준 전체 체인 (dry_run)', () => {
  test.skip(!enabled, 'RUN_FULL_CHAIN=1 필요 — 실제 claude 서브프로세스 비용')

  test('콘솔 dry_run 트리거 → 잡 완료 → 진단·판정 UI', async ({ page }) => {
    test.setTimeout(200000)
    await page.goto('/')
    await page.getByRole('button', { name: '실행 콘솔', exact: true }).click()

    // ① 소형 풀 생성
    const poolPanel = page.locator('.panel').filter({ hasText: '① 풀 생성' })
    await poolPanel.locator('select').selectOption('single')
    await poolPanel.getByPlaceholder('비우면 무작위').fill('88888')
    await poolPanel.getByPlaceholder('기본값').fill('8')
    await poolPanel.getByRole('button', { name: '풀 생성' }).click()
    await expect(poolPanel.getByText('생성됨')).toBeVisible({ timeout: 40000 })

    // ② dry-run 트리거(기본 ON)
    const runPanel = page.locator('.panel').filter({ hasText: '② 시뮬 실행' })
    await runPanel.locator('select').first().selectOption('pool_88888')
    await expect(runPanel).toContainText('dry-run · 2명만')
    await runPanel.getByRole('button', { name: '시뮬 실행' }).click()
    const startedP = runPanel.locator('p', { hasText: '잡 시작' })
    await expect(startedP).toBeVisible()
    const jobId = (await startedP.locator('code').textContent()).trim()

    // ③ 잡 완료까지 자동 폴링
    const jobsPanel = page.locator('.panel').filter({ hasText: '③ 잡 현황' })
    const jobRow = jobsPanel.locator('tr', { hasText: jobId })
    await expect(jobRow.locator('.badge', { hasText: 'completed' })).toBeVisible({ timeout: 170000 })
    const runId = (await jobRow.locator('code').last().textContent()).trim()
    expect(runId).toMatch(/^wf_/)

    // 진단 탭 → 신규 런 선택 → diagnosable
    await page.getByRole('button', { name: '진단', exact: true }).click()
    await page.locator('tr', { hasText: runId }).first().click()
    await expect(page.locator('.screen')).toContainText('붕괴/동질성 체크')

    // 판정 탭 → 신규 런 선택 → judgeable
    await page.getByRole('button', { name: '판정', exact: true }).click()
    await page.locator('tr', { hasText: runId }).first().click()
    await expect(page.locator('.screen')).toContainText('연속상관')
  })
})
