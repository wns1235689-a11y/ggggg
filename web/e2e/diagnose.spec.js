import { test, expect } from '@playwright/test'

// P2-6c: 진단 패널 — R3(단일 wf_9971e46b-6d1) 선택 후 붕괴/동질성 진단 렌더.
test('진단 패널 — R3 선택 후 붕괴/동질성·per-item 렌더', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '진단', exact: true }).click()

  // 런 선택기에서 R3 행 클릭
  const r3 = page.locator('tr', { hasText: 'wf_9971e46b-6d1' }).first()
  await expect(r3).toBeVisible()
  await r3.click()

  // 붕괴/동질성 체크 패널
  await expect(page.locator('.screen')).toContainText('붕괴/동질성 체크')
  await expect(page.locator('.screen')).toContainText('N=49')
  // 붕괴 3종 + 유병률 체크 항목
  await expect(page.locator('.screen')).toContainText('페르소나 간 동질성')
  await expect(page.locator('.screen')).toContainText('향부담 광의 믿음질량')
  // 임계 문구(휴리스틱·엔진 아님)
  await expect(page.locator('.screen')).toContainText('엔진 아님')

  // 문항별 패널로 스코프 — B1 행 클릭 시 믿음질량 vs realized 펼침
  const itemPanel = page.locator('.panel').filter({ hasText: '문항별' })
  await expect(itemPanel).toContainText('보기사용')
  await itemPanel.locator('tr', { hasText: 'B1' }).first().click()
  await expect(itemPanel).toContainText('믿음질량%')
  await expect(itemPanel).toContainText('realized')
})
