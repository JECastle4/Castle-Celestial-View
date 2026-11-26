import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getCurrentLocale } from './i18n'
import router, { SUPPORTED_LOCALES } from './router'

vi.mock('./App.vue', () => ({ default: { template: '<div />' } }))
vi.mock('./views/AboutView.vue', () => ({ default: { template: '<div />' } }))
vi.mock('./views/EventsView.vue', () => ({ default: { template: '<div />' } }))

describe('regional routes', () => {
  beforeEach(async () => {
    await router.push('/en-US/')
  })

  it('defaults the root to British English', async () => {
    await router.push('/')
    expect(router.currentRoute.value.path).toBe('/en-GB/')
    expect(getCurrentLocale()).toBe('en-GB')
  })

  it.each(['', '/', '/events', '/about'])('preserves the legacy British route %s', async (suffix) => {
    await router.push(`/en-UK${suffix}?date=2026-11-03#details`)
    expect(router.currentRoute.value.path).toBe(`/en-GB${suffix}`)
    expect(router.currentRoute.value.query).toEqual({ date: '2026-11-03' })
    expect(router.currentRoute.value.hash).toBe('#details')
    expect(getCurrentLocale()).toBe('en-GB')
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href'))
      .not.toContain('en-UK')
  })

  it('uses the requested region rather than the browser default', async () => {
    await router.push('/en-US/events')
    expect(getCurrentLocale()).toBe('en-US')
    expect(document.documentElement.lang).toBe('en-US')
    expect(document.title).toContain('New Moons, Full Moons & Eclipses')
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href'))
      .toBe('https://castlecelestialview.net/en-US/events')
    await router.push('/en-GB/about')
    expect(document.title).toBe('About | Castle Celestial View')
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href'))
      .toBe('https://castlecelestialview.net/en-GB/about')
  })

  it.each([
    ['/en-uk/events', '/en-GB/events'],
    ['/EN-UK/about', '/en-GB/about'],
    ['/en-gb/', '/en-GB/'],
    ['/EN-us/events', '/en-US/events'],
  ])('normalizes %s without a redirect loop', async (input, expected) => {
    await router.push(`${input}?date=2026-11-03#details`)
    expect(router.currentRoute.value.fullPath).toBe(`${expected}?date=2026-11-03#details`)
    expect(getCurrentLocale()).toBe(expected.includes('en-US') ? 'en-US' : 'en-GB')
  })

  it('does not offer the legacy identifier as a selectable locale', () => {
    expect(SUPPORTED_LOCALES).toContain('en-GB')
    expect(SUPPORTED_LOCALES).toContain('en-US')
    expect(SUPPORTED_LOCALES).not.toContain('en-UK')
  })

  it('redirects unknown paths to the British homepage', async () => {
    await router.push('/missing-page')
    expect(router.currentRoute.value.path).toBe('/en-GB/')
    expect(getCurrentLocale()).toBe('en-GB')
  })

  it('does not overwrite metadata for non-page routes or unsupported route locales', async () => {
    const removeRoute = router.addRoute({
      path: '/diagnostic/:locale?',
      name: 'diagnostic',
      component: { template: '<div />' },
    })
    try {
      const title = document.title
      await router.push('/diagnostic')
      expect(document.title).toBe(title)
      expect(getCurrentLocale()).toBe('en-US')
      await router.push('/diagnostic/fr')
      expect(document.title).toBe(title)
      expect(getCurrentLocale()).toBe('en-US')
    } finally {
      removeRoute()
    }
  })

  it('does not change metadata when navigation is cancelled', async () => {
    const removeGuard = router.beforeEach(() => false)
    try {
      const title = document.title
      const canonical = document.querySelector('link[rel="canonical"]')?.getAttribute('href')
      await router.push('/en-US/events')
      expect(router.currentRoute.value.path).toBe('/en-US/')
      expect(document.title).toBe(title)
      expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(canonical)
    } finally {
      removeGuard()
    }
  })

  it('excludes the development locale from production routes', async () => {
    vi.resetModules()
    vi.stubEnv('DEV', false)
    try {
      const production = await import('./router')
      expect(production.SUPPORTED_LOCALES).toEqual(['en-GB', 'en-US'])
      expect(production.default.resolve('/xx-reverse/').name).toBeUndefined()
    } finally {
      vi.unstubAllEnvs()
    }
  })
})
