import { mkdtemp, rm, writeFile } from 'node:fs/promises'
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
      const output = await build({
        configFile: false, root, plugins: [landingPages()], logLevel: 'silent',
        build: { write: true },
      })
      if (Array.isArray(output) || !('output' in output)) throw new Error('Expected one build output')
      expect(output.output.map(asset => asset.fileName).sort()).toEqual([
        'en-GB/about.html', 'en-GB/events.html', 'en-GB/index.html',
        'en-US/about.html', 'en-US/events.html', 'en-US/index.html', 'index.html',
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
