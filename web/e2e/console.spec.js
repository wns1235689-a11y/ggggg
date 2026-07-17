import { test, expect } from '@playwright/test'

// P2-6f: 실행 콘솔 — 패널 렌더 + 풀 생성(실제 build_*) + 비용 가드 UI.
// 실제 시뮬(claude 서브프로세스)은 트리거하지 않음(비용) — dry_run 전체 체인은 P2-6g.
test('실행 콘솔 — 4개 패널 렌더', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '실행 콘솔', exact: true }).click()
  const s = page.locator('.screen')
  await expect(s).toContainText('① 풀 생성')
  await expect(s).toContainText('② 시뮬 실행')
  await expect(s).toContainText('③ 잡 현황')
  await expect(s).toContainText('런 히스토리')
})

test('풀 생성(실제) + 비용 가드 UI', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '실행 콘솔', exact: true }).click()

  // 풀 생성: single, seed=20260717, N=53(>50 → 대규모 가드 테스트용)
  const poolPanel = page.locator('.panel').filter({ hasText: '① 풀 생성' })
  await poolPanel.locator('select').selectOption('single')
  await poolPanel.getByPlaceholder('비우면 무작위').fill('20260717')
  await poolPanel.getByPlaceholder('기본값').fill('53')
  await poolPanel.getByRole('button', { name: '풀 생성' }).click()
  // build_* 서브프로세스 — 넉넉한 타임아웃
  await expect(poolPanel.getByText('생성됨')).toBeVisible({ timeout: 40000 })
  await expect(poolPanel).toContainText('pool_20260717')

  // 시뮬 실행: 방금 만든 N=53 풀 선택
  const runPanel = page.locator('.panel').filter({ hasText: '② 시뮬 실행' })
  await runPanel.locator('select').first().selectOption('pool_20260717')
  // 스크립트 자동(single → wf_vs_v23.js)
  await expect(runPanel.locator('input[readonly]')).toHaveValue('wf_vs_v23.js')

  // dry-run 기본 ON → 2명 배지
  await expect(runPanel).toContainText('dry-run · 2명만')

  // dry-run OFF → 대규모 경고 + confirm 필요, 실행 버튼 비활성
  await runPanel.getByRole('checkbox').first().uncheck()
  await expect(runPanel).toContainText('대규모 N=53')
  const runBtn = runPanel.getByRole('button', { name: '시뮬 실행' })
  await expect(runBtn).toBeDisabled()
  // confirm 체크 → 실행 버튼 활성(클릭은 안 함 — 실제 claude 비용 회피)
  await runPanel.getByLabel('대규모 실행 확인(confirm_large)').check()
  await expect(runBtn).toBeEnabled()
})
