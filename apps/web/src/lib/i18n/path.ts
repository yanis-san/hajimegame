/** Language in the URL: French lives at the root, other languages under a prefix (`/en`, `/ja`). */
export type Locale = 'fr' | 'en' | 'ja';

export const DEFAULT_LOCALE: Locale = 'fr';
export const PREFIXED: readonly Locale[] = ['en', 'ja'];
export const LANG_COOKIE = 'hajime_lang';

export function isLocale(value: unknown): value is Locale {
	return value === 'fr' || (PREFIXED as readonly unknown[]).includes(value);
}

/** The language a URL path is in (French when there is no prefix). */
export function localeFromPath(pathname: string): Locale {
	const first = pathname.split('/')[1];
	return (PREFIXED as readonly string[]).includes(first) ? (first as Locale) : DEFAULT_LOCALE;
}

/** The path without its language prefix: `/ja/r/ABC` -> `/r/ABC`, `/en` -> `/`. */
export function stripLocale(pathname: string): string {
	const first = pathname.split('/')[1];
	if (!(PREFIXED as readonly string[]).includes(first)) return pathname || '/';
	return pathname.slice(first.length + 1) || '/';
}

/** The same page in another language: `localizePath('/r/ABC', 'ja')` -> `/ja/r/ABC`. */
export function localizePath(path: string, locale: Locale): string {
	const bare = stripLocale(path);
	if (locale === DEFAULT_LOCALE) return bare;
	return bare === '/' ? `/${locale}` : `/${locale}${bare}`;
}

/** Best supported language for an `Accept-Language` header or a list of tags, French when none matches. */
export function detectLocale(preferred: readonly string[] | string | null | undefined): Locale {
	const tags =
		typeof preferred === 'string'
			? preferred.split(',').map((part) => part.split(';')[0].trim())
			: (preferred ?? []);
	for (const tag of tags) {
		const base = tag.toLowerCase().split('-')[0];
		if (isLocale(base)) return base;
	}
	return DEFAULT_LOCALE;
}
