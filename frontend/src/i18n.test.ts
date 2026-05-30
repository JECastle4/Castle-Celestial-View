import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('i18n module', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetModules();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('creates an i18n instance with en as default locale', async () => {
    const { getCurrentLocale } = await import('@/i18n');
    expect(getCurrentLocale()).toBe('en-UK');
  });

  it
  ('creates an i18n instance with en as en-US locale', async () => {
    const { getCurrentLocale } = await import('@/i18n');
    const { setCurrentLocale } = await import('@/i18n');
    setCurrentLocale('en-US');
    expect(getCurrentLocale()).toBe('en-US');
  });

  it('includes xx-reverse messages in dev mode', async () => {
    // import.meta.env.DEV is true in vitest
    const { i18n } = await import('@/i18n');
    const messages = i18n.global.getLocaleMessage('xx-reverse') as Record<string, unknown>;
    expect(Object.keys(messages).length).toBeGreaterThan(0);
  });

  it('can switch locale to xx-reverse', async () => {
    const { getCurrentLocale, setCurrentLocale } = await import('@/i18n');
    setCurrentLocale('xx-reverse');
    expect(getCurrentLocale()).toBe('xx-reverse');
  });

  it('translates a key correctly in en', async () => {
    const { i18n, setCurrentLocale } = await import('@/i18n');
    setCurrentLocale('en');
    expect(i18n.global.t('astronomy.dayNames.sunday')).toBe('Sunday');
  });

  it('translates a key correctly in xx-reverse', async () => {
    const { i18n, setCurrentLocale } = await import('@/i18n');
    setCurrentLocale('xx-reverse');
    expect(i18n.global.t('astronomy.dayNames.sunday')).toBe('yadnuS');
  });

  it('translates the animationReset toast label in en', async () => {
    const { i18n, setCurrentLocale } = await import('@/i18n');
    setCurrentLocale('en');
    expect(i18n.global.t('ui.status.animationReset')).toBe('Animation reset to initial state.');
  });

  it('translates the animationReset toast label in xx-reverse', async () => {
    const { i18n, setCurrentLocale } = await import('@/i18n');
    setCurrentLocale('xx-reverse');
    expect(i18n.global.t('ui.status.animationReset')).toBe('.etats laitini ot teser noitaminA');
  });

    it('does not include xx-reverse messages in prod mode', async () => {
      // Simulate production mode by patching import.meta.env.DEV
      const originalDev = import.meta.env.DEV;
      import.meta.env.DEV = false;
      // Re-import the module to get prod config
      const { i18n } = await import('@/i18n');
      expect(i18n.global.getLocaleMessage('xx-reverse')).toStrictEqual({});
      import.meta.env.DEV = originalDev;
    });
});
