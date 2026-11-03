import { getPageMetadata, PRODUCTION_LOCALES, SEARCH_PAGES, SITE_ORIGIN } from './metadata'

export function renderRobots() {
  return `User-agent: *\nAllow: /\n\nSitemap: ${SITE_ORIGIN}/sitemap.xml\n`
}

export function renderSitemap() {
  const entries = PRODUCTION_LOCALES.flatMap(locale => SEARCH_PAGES.map(page => {
    const metadata = getPageMetadata(page, locale)
    return `  <url>
    <loc>${metadata.canonical}</loc>
${metadata.alternates.map(alternate =>
    `    <xhtml:link rel="alternate" hreflang="${alternate.language}" href="${alternate.href}"/>`).join('\n')}
  </url>`
  }))
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
${entries.join('\n')}
</urlset>
`
}
