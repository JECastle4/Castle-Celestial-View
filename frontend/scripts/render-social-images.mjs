import { chromium } from '@playwright/test'
import { mkdir, readFile } from 'node:fs/promises'

const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 })
  await mkdir(new URL('../public/social/', import.meta.url), { recursive: true })
  for (const name of ['home-v1', 'events-v1']) {
    const svg = await readFile(new URL(`../artwork/${name}.svg`, import.meta.url), 'utf8')
    await page.setContent(`<style>body{margin:0}</style>${svg}`)
    await page.evaluate(() => document.fonts.ready)
    await page.screenshot({ path: new URL(`../public/social/${name}.png`, import.meta.url).pathname })
  }
} finally {
  await browser.close()
}
