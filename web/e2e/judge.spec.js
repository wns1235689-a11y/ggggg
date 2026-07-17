import { test, expect } from '@playwright/test'

// P2-6d: 판정 대시보드 — 단일(R3)·다풀(R4) 분기 + D1 수용곡선.
test('판정 — R3 단일풀: 연속상관·세그교차·dose·D1곡선', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '판정', exact: true }).click()
  await page.locator('tr', { hasText: 'wf_9971e46b-6d1' }).first().click()

  const s = page.locator('.screen')
  await expect(s).toContainText('향부담강도 ↔ 반응 연속상관')
  await expect(s).toContainText('sim-내 견고(prior)')
  await expect(s).toContainText('매실청 깊이 세그 교차')
  await expect(s).toContainText('dose-response')
  // D1 수용곡선(서술적·신뢰불가 라벨)
  await expect(s).toContainText('D1 가격-수용 곡선')
  await expect(s).toContainText('₩5,900')
  await expect(s).toContainText('신뢰불가(수준)')
})

test('판정 — R4 다풀: 통합 연속상관(유의)·부호일관', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '판정', exact: true }).click()
  await page.locator('tr', { hasText: 'wf_6ff10eda-c1f' }).first().click()

  const s = page.locator('.screen')
  await expect(s).toContainText('통합 향부담강도 ↔ 반응 연속상관')
  await expect(s).toContainText('풀-부호 일관성')
  // 유의 마커(*** 등) — E1_na_ga 지표 존재
  await expect(s).toContainText('E1_na_ga')
  await expect(s).toContainText('D1 가격-수용 곡선')
})
