/**
 * Normalize app locales to valid BCP-47/Intl locale tags.
 * Some app locales use non-standard tags that toLocaleString() cannot handle.
 * @param locale - The app locale string (e.g., 'en-UK', 'xx-reverse')
 * @returns A valid BCP-47 locale tag for use with Intl APIs
 */
export function normalizeLocaleForIntl(locale: string): string {
  // Map non-standard app locales to valid BCP-47 tags
  const localeMap: Record<string, string> = {
    'en-UK': 'en-GB', // en-UK is not a valid tag; use en-GB instead
    'xx-reverse': 'en-GB', // dev-only locale; fallback to en-GB for Intl formatting
  };

  return localeMap[locale] || locale;
}
