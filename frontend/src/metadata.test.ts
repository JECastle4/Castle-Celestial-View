import { beforeEach, describe, expect, it } from 'vitest'
import { getPageMetadata, PRODUCTION_LOCALES, updatePageMetadata } from './metadata'
import type { Page } from './metadata'

describe('regional page metadata', () => {
  beforeEach(() => {
    document.head.innerHTML = ''
  })

  it.each(PRODUCTION_LOCALES)('self-canonicalises every page in %s', (locale) => {
    for (const [page, suffix] of Object.entries({ home: '/', events: '/events', about: '/about' })) {
      const metadata = getPageMetadata(page as Page, locale)
      expect(metadata.canonical).toBe(`https://castlecelestialview.net/${locale}${suffix}`)
      expect(metadata.alternates).toEqual([
        { language: 'en-GB', href: `https://castlecelestialview.net/en-GB${suffix}` },
        { language: 'en-US', href: `https://castlecelestialview.net/en-US${suffix}` },
        { language: 'x-default', href: `https://castlecelestialview.net/en-GB${suffix}` },
      ])
    }
  })

  it('preserves regional spelling in descriptions', () => {
    expect(getPageMetadata('home', 'en-GB').description).toContain('Visualise')
    expect(getPageMetadata('home', 'en-US').description).toContain('Visualize')
    expect(getPageMetadata('about', 'en-GB').description).toContain('licence')
    expect(getPageMetadata('about', 'en-US').description).toContain('license')
  })

  it('replaces metadata across page and locale changes without duplicates', () => {
    document.head.innerHTML = '<meta name="description" content="Old description">'
    for (const locale of PRODUCTION_LOCALES) {
      for (const page of ['home', 'events', 'about', 'home'] as const) {
        updatePageMetadata(page, locale)
        const metadata = getPageMetadata(page, locale)
        expect(document.title).toBe(metadata.title)
        expect(document.documentElement.lang).toBe(locale)
        expect(document.head.querySelectorAll('meta[name="description"]')).toHaveLength(1)
        expect(document.head.querySelector('meta[name="description"]')?.getAttribute('content'))
          .toBe(metadata.description)
        expect(document.head.querySelectorAll('link[rel="canonical"]')).toHaveLength(1)
        expect(document.head.querySelector('link[rel="canonical"]')?.getAttribute('href'))
          .toBe(metadata.canonical)
        expect(document.head.querySelectorAll('link[hreflang]')).toHaveLength(3)
      }
    }
  })

  it('does not advertise production canonical/alternate links for a development locale', () => {
    updatePageMetadata('home', 'en-US')
    updatePageMetadata('home', 'xx-reverse')
    expect(document.documentElement.lang).toBe('en-GB')
    expect(document.head.querySelectorAll('link[rel="canonical"], link[hreflang]')).toHaveLength(0)
  })
})
