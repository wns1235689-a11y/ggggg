import { test, expect } from '@playwright/test'

// P2-6e: 리포트 화면 — R3 선택 후 게이트C 포맷 렌더 + ⓪ 경고 + 원문/렌더 토글.
test('리포트 — R3 선택: ⓪ 경고 헤더·판정 렌더·원문 토글', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '리포트', exact: true }).click()
  await page.locator('tr', { hasText: 'wf_9971e46b-6d1' }).first().click()

  const s = page.locator('.screen')
  // ⓪ 경고 헤더 포함 배지 + 렌더된 헤딩
  await expect(s).toContainText('⓪ 경고 헤더 포함')
  await expect(s.locator('.md-render')).toContainText('문서 지위 · 필수 경고')
  await expect(s.locator('.md-render')).toContainText('LLM 합성·비실측')
  await expect(s.locator('.md-render')).toContainText('인용 불가')
  // 실행 로그 + 판정 렌더(표)
  await expect(s.locator('.md-render')).toContainText('실행 로그')
  await expect(s.locator('.md-render')).toContainText('연속상관')
  await expect(s.locator('.md-render table')).toHaveCount(await s.locator('.md-render table').count())

  // 원문(.md) 토글 → pre 노출
  await page.getByRole('button', { name: '원문(.md)' }).click()
  await expect(s.locator('pre.md')).toContainText('## ⓪ 문서 지위')
})
