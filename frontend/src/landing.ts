import { getLandingContent, getPageMetadata } from './metadata'
import type { Page, ProductionLocale } from './metadata'

export function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

export function renderLandingPage(template: string, page: Page, locale: ProductionLocale) {
  const metadata = getPageMetadata(page, locale)
  const content = getLandingContent(page, locale)
  const head = [
    `<title>${escapeHtml(metadata.title)}</title>`,
    `<meta name="description" content="${escapeHtml(metadata.description)}">`,
    `<link rel="canonical" href="${escapeHtml(metadata.canonical)}">`,
    ...metadata.socialTags.map(tag =>
      `<meta ${tag.attribute}="${tag.key}" content="${escapeHtml(tag.content)}">`),
    ...metadata.alternates.map(alternate =>
      `<link rel="alternate" hreflang="${alternate.language}" href="${escapeHtml(alternate.href)}">`),
  ].join('\n    ')
  const navigation = content.navigation.map(link =>
    `<a href="${link.href}"${link.page === page ? ' aria-current="page"' : ''}>${escapeHtml(link.label)}</a>`).join('\n')
  const languages = content.languages.map(link =>
    `<a href="${link.href}" hreflang="${link.language}" lang="${link.language}">${escapeHtml(link.label)}</a>`).join('\n')
  const shell = `<div id="app">
      <div class="static-landing">
        <header><h1>${escapeHtml(content.projectTitle)}</h1>
          <nav aria-label="${escapeHtml(content.navigationLabel)}">${navigation}</nav>
        </header>
        <main>
          ${page === 'home' ? '' : `<h2>${escapeHtml(content.heading)}</h2>`}
          <p>${escapeHtml(content.introduction)}</p>
          <noscript><p>${escapeHtml(content.interactiveNotice)}</p></noscript>
          <p id="startup-error" role="alert" hidden>${escapeHtml(content.startupError)}</p>
        </main>
        <footer>${languages}</footer>
      </div>
    </div>`

  if (!template.includes('<!--landing-head-->') || !template.includes('<div id="app"></div>')) {
    throw new Error('Landing document template is missing its head or app placeholder')
  }
  return template.replace(/<html lang="[^"]*">/, `<html lang="${locale}">`)
    .replace(/<title>[^<]*<\/title>/, '')
    .replace('<!--landing-head-->', head)
    .replace('<div id="app"></div>', shell)
}
