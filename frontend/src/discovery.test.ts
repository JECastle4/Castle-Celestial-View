import { describe, expect, it } from 'vitest'
import { renderRobots, renderSitemap } from './discovery'

describe('production discovery files', () => {
  it('allows crawling and declares the absolute production sitemap', () => {
    expect(renderRobots()).toBe('User-agent: *\nAllow: /\n\nSitemap: https://castlecelestialview.net/sitemap.xml\n')
  })

  it('emits valid XML with exactly the four canonical search landing URLs and reciprocal alternates', () => {
    const xml = renderSitemap()
    const document = new DOMParser().parseFromString(xml, 'application/xml')
    expect(document.querySelector('parsererror')).toBeNull()
    expect(document.documentElement.namespaceURI).toBe('http://www.sitemaps.org/schemas/sitemap/0.9')
    expect(document.documentElement.getAttribute('xmlns:xhtml')).toBe('http://www.w3.org/1999/xhtml')
    const entries = Array.from(document.getElementsByTagName('url'))
    expect(entries.map(entry => entry.querySelector('loc')?.textContent)).toEqual([
      'https://castlecelestialview.net/en-GB/',
      'https://castlecelestialview.net/en-GB/events',
      'https://castlecelestialview.net/en-US/',
      'https://castlecelestialview.net/en-US/events',
    ])
    for (const entry of entries) {
      const suffix = entry.querySelector('loc')!.textContent!.endsWith('/events') ? 'events' : ''
      const links = Array.from(entry.getElementsByTagName('xhtml:link'))
      expect(links.map(link => [link.getAttribute('hreflang'), link.getAttribute('href')])).toEqual([
        ['en-GB', `https://castlecelestialview.net/en-GB/${suffix}`],
        ['en-US', `https://castlecelestialview.net/en-US/${suffix}`],
        ['x-default', `https://castlecelestialview.net/en-GB/${suffix}`],
      ])
    }
    expect(xml).not.toMatch(/lastmod|xx-reverse|en-UK|localhost|about/)
  })
})
