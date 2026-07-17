import { test, expect } from '@playwright/test'

// P2-6b: 설계 뷰어 + 앱 셸(ⓠ 경고 배너) 렌더 검증.
test('앱 셸 — ⓪ 합성·비실측 경고 배너 상시', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.warn-banner')).toContainText('합성·비실측')
  await expect(page.locator('.warn-banner')).toContainText('인용 금지')
  // 5개 탭 존재
  for (const t of ['실행 콘솔', '진단', '판정', '리포트', '설계 뷰어']) {
    await expect(page.getByRole('button', { name: t, exact: true })).toBeVisible()
  }
  // 백엔드 health 표시
  await expect(page.locator('.statusbar')).toContainText('백엔드 OK')
})

test('설계 뷰어 — 문항·latent·anchor 렌더', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '설계 뷰어', exact: true }).click()
  const screen = page.locator('.screen')
  // 컨셉 카드(매실청 재해석)
  await expect(screen).toContainText('매실청')
  // 문항(스키마 필드)
  await expect(screen).toContainText('A2a_dist')
  await expect(screen).toContainText('v2.3 문항')
  // latent 스펙
  await expect(screen).toContainText('spice_aversion')
  // anchor priors + 실측 몫 규율 문구
  await expect(screen).toContainText('ANCHOR_PRIORS')
  await expect(screen).toContainText('실측 몫')
})
