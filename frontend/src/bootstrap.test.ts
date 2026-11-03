import { describe, expect, it, vi } from 'vitest'
import { mountWhenReady } from './bootstrap'

describe('static to interactive handoff', () => {
  it('keeps content until routing is ready, then mounts exactly once', async () => {
    let finish!: () => void
    const ready = new Promise<void>(resolve => { finish = resolve })
    const mount = vi.fn()
    const report = vi.fn()
    const result = mountWhenReady(ready, mount, report)
    expect(mount).not.toHaveBeenCalled()
    finish()
    await result
    expect(mount).toHaveBeenCalledOnce()
    expect(report).not.toHaveBeenCalled()
  })

  it('reports routing failure without replacing static content', async () => {
    const error = new Error('Route chunk failed to load')
    const mount = vi.fn()
    const report = vi.fn()
    await mountWhenReady(Promise.reject(error), mount, report)
    expect(mount).not.toHaveBeenCalled()
    expect(report).toHaveBeenCalledExactlyOnceWith(error)
  })

  it('reports a synchronous mount failure', async () => {
    const error = new Error('Cannot mount application')
    const report = vi.fn()
    await mountWhenReady(Promise.resolve(), () => { throw error }, report)
    expect(report).toHaveBeenCalledExactlyOnceWith(error)
  })
})
