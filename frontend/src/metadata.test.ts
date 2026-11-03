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
    document.head.innerHTML = '<meta name="description" content="Old description"><meta property="og:url" content="stale"><meta name="twitter:image" content="stale">'
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
        expect(document.head.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]'))
          .toHaveLength(metadata.socialTags.length)
        for (const tag of metadata.socialTags) {
          const matches = document.head.querySelectorAll(`meta[${tag.attribute}="${tag.key}"]`)
          expect(matches).toHaveLength(1)
          expect(matches[0].getAttribute('content')).toBe(tag.content)
        }
      }
    }
  })

  it('does not advertise production canonical/alternate links for a development locale', () => {
    updatePageMetadata('home', 'en-US')
    updatePageMetadata('home', 'xx-reverse')
    expect(document.documentElement.lang).toBe('en-GB')
    expect(document.head.querySelectorAll('link[rel="canonical"], link[hreflang]')).toHaveLength(0)
    expect(document.head.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]')).toHaveLength(0)
  })

  it.each(PRODUCTION_LOCALES)('provides accurate regional sharing tags for %s', (locale) => {
    for (const page of ['home', 'events', 'about'] as const) {
      const metadata = getPageMetadata(page, locale)
      const tags = Object.fromEntries(metadata.socialTags.map(tag => [tag.key, tag.content]))
      expect(tags['og:title']).toBe(metadata.title)
      expect(tags['og:description']).toBe(metadata.description)
      expect(tags['og:url']).toBe(metadata.canonical)
      expect(tags['og:type']).toBe('website')
      expect(tags['og:locale']).toBe(locale.replace('-', '_'))
      expect(tags['og:locale:alternate']).toBe(locale === 'en-GB' ? 'en_US' : 'en_GB')
      expect(tags['og:image']).toBe(`https://castlecelestialview.net/social/${page === 'events' ? 'events' : 'home'}-v1.png`)
      expect(tags['og:image:type']).toBe('image/png')
      expect(tags['og:image:width']).toBe('1200')
      expect(tags['og:image:height']).toBe('630')
      expect(tags['og:image:alt']).toContain(page === 'events' ? 'moon phases' : 'planetary orbits')
      expect(tags['twitter:card']).toBe('summary_large_image')
      expect(tags['twitter:title']).toBe(metadata.title)
      expect(tags['twitter:description']).toBe(metadata.description)
      expect(tags['twitter:image']).toBe(tags['og:image'])
      expect(tags['twitter:image:alt']).toBe(tags['og:image:alt'])
    }
  })
})
