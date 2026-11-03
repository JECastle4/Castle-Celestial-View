import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { build, preview } from 'vite'
import { describe, expect, it } from 'vitest'
import { landingPages } from './landingPages'
import type { AddressInfo } from 'node:net'

const template = '<html lang="en-GB"><head><title>Old title</title><!--landing-head--></head><body><div id="app"></div></body></html>'

describe('landing build integration', () => {
  it('builds six localized documents plus the default, and serves clean preview URLs', async () => {
    const root = await mkdtemp(join(tmpdir(), 'castle-landing-'))
    try {
      await writeFile(join(root, 'index.html'), template)
      await mkdir(join(root, 'public/social'), { recursive: true })
      await writeFile(join(root, 'public/social/home-v1.png'),
        await readFile(join(process.cwd(), 'public/social/home-v1.png')))
      const output = await build({
        configFile: false, root, plugins: [landingPages()], logLevel: 'silent',
        build: { write: true },
      })
      if (Array.isArray(output) || !('output' in output)) throw new Error('Expected one build output')
      expect(output.output.map(asset => asset.fileName).sort()).toEqual([
        'en-GB/about.html', 'en-GB/events.html', 'en-GB/index.html',
        'en-US/about.html', 'en-US/events.html', 'en-US/index.html', 'index.html', 'robots.txt', 'sitemap.xml',
      ])
      const server = await preview({
        configFile: false, root, plugins: [landingPages()], logLevel: 'silent',
        preview: { host: '127.0.0.1', port: 0 },
      })
      try {
        const { port } = server.httpServer.address() as AddressInfo
        for (const locale of ['en-GB', 'en-US']) {
          for (const route of ['/', '/events', '/about']) {
            const response = await fetch(`http://127.0.0.1:${port}/${locale}${route}?source=search`)
            expect(response.status).toBe(200)
            expect(response.headers.get('content-type')).toContain('text/html')
            const html = await response.text()
            expect(html).toContain(`<html lang="${locale}">`)
            expect(html).toContain(`href="https://castlecelestialview.net/${locale}${route}"`)
            expect(html).toContain('class="static-landing"')
          }
        }
        const rootResponse = await fetch(`http://127.0.0.1:${port}/`)
        expect(await rootResponse.text()).toContain('href="https://castlecelestialview.net/en-GB/"')
        for (const [file, type, content] of [
          ['robots.txt', 'text/plain', 'Sitemap: https://castlecelestialview.net/sitemap.xml'],
          ['sitemap.xml', 'xml', '<loc>https://castlecelestialview.net/en-US/events</loc>'],
        ]) {
          const response = await fetch(`http://127.0.0.1:${port}/${file}`)
          expect(response.status).toBe(200)
          expect(response.headers.get('content-type')).toContain(type)
          expect(await response.text()).toContain(content)
        }
        const image = await fetch(`http://127.0.0.1:${port}/social/home-v1.png`)
        expect(image.headers.get('content-type')).toContain('image/png')
        const bytes = Buffer.from(await image.arrayBuffer())
        expect(bytes.subarray(1, 4).toString()).toBe('PNG')
        expect([bytes.readUInt32BE(16), bytes.readUInt32BE(20)]).toEqual([1200, 630])
        await rm(join(root, 'dist/robots.txt'))
        await rm(join(root, 'dist/sitemap.xml'))
        for (const path of ['/robots.txt', '/sitemap.xml', '/social/missing.png', '/social/subdir/missing.png']) {
          const missing = await fetch(`http://127.0.0.1:${port}${path}`)
          expect(missing.status).toBe(404)
          expect(await missing.text()).not.toContain('static-landing')
        }
      } finally {
        await new Promise<void>((resolve, reject) => {
          server.httpServer.close(error => error ? reject(error) : resolve())
        })
      }
    } finally {
      await rm(root, { recursive: true, force: true })
    }
  })

  it('fails the build explicitly when index.html is missing from the bundle', async () => {
    const root = await mkdtemp(join(tmpdir(), 'castle-landing-'))
    try {
      await writeFile(join(root, 'index.html'), template)
      await expect(build({
        configFile: false, root, logLevel: 'silent',
        plugins: [{
          name: 'remove-index-fixture',
          generateBundle: {
            order: 'post',
            handler(_options, bundle) { delete bundle['index.html'] },
          },
        }, landingPages()],
        build: { write: false },
      })).rejects.toThrow('Cannot generate landing pages: built index.html is missing')
    } finally {
      await rm(root, { recursive: true, force: true })
    }
  })
})
