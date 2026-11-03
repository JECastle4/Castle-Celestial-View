import { describe, expect, it } from 'vitest'
import { Window } from 'happy-dom'
import { escapeHtml, renderLandingPage } from './landing'
import { getLandingContent, getPageMetadata, PAGES, PRODUCTION_LOCALES } from './metadata'

import template from '../index.html?raw'

describe('build-time landing documents', () => {
  it.each(PRODUCTION_LOCALES)('renders accurate content and metadata for %s without runtime dependencies', (locale) => {
    const window = new Window({
      settings: {
        disableCSSFileLoading: true,
        disableJavaScriptFileLoading: true,
        disableJavaScriptEvaluation: true,
      },
    })
    for (const page of PAGES) {
      const document = new window.DOMParser().parseFromString(renderLandingPage(template, page, locale), 'text/html')
      const metadata = getPageMetadata(page, locale)
      const content = getLandingContent(page, locale)
      expect(document.documentElement.lang).toBe(locale)
      expect(document.querySelectorAll('title')).toHaveLength(1)
      expect(document.title).toBe(metadata.title)
      expect(document.querySelector('meta[name="description"]')?.getAttribute('content')).toBe(metadata.description)
      expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(metadata.canonical)
      expect(document.querySelectorAll('link[hreflang]')).toHaveLength(3)
      for (const tag of metadata.socialTags) {
        const matches = document.querySelectorAll(`meta[${tag.attribute}="${tag.key}"]`)
        expect(matches).toHaveLength(1)
        expect(matches[0].getAttribute('content')).toBe(tag.content)
      }
      expect(document.querySelectorAll('h1')).toHaveLength(1)
      expect(document.querySelector('h1')?.textContent).toBe('Castle Celestial View')
      expect(document.querySelector('main')?.textContent).toContain(content.introduction)
      expect(document.querySelector('noscript')?.textContent).toContain(content.interactiveNotice)
      expect(document.querySelector('#startup-error')?.hasAttribute('hidden')).toBe(true)
      expect(document.querySelector('#startup-error')?.textContent).toBe(content.startupError)
      expect(document.querySelectorAll('nav a')).toHaveLength(3)
      expect(document.querySelector('nav [aria-current="page"]')?.getAttribute('href'))
        .toBe(content.navigation.find(link => link.page === page)?.href)
      expect(document.querySelectorAll('footer a[hreflang]')).toHaveLength(2)
      expect(document.querySelector('main h2')?.textContent).toBe(page === 'home' ? undefined : content.heading)
      expect(document.querySelectorAll('script')).toHaveLength(1)
    }
    window.close()
  })

  it('escapes text and attribute delimiters', () => {
    expect(escapeHtml(`<script title="A&B">'quoted'</script>`))
      .toBe('&lt;script title=&quot;A&amp;B&quot;&gt;&#39;quoted&#39;&lt;/script&gt;')
  })

  it.each(['<!--landing-head-->', '<div id="app"></div>'])('fails explicitly when template placeholder %s is missing', (placeholder) => {
    expect(() => renderLandingPage(template.replace(placeholder, ''), 'home', 'en-GB'))
      .toThrow('Landing document template is missing its head or app placeholder')
  })
})
