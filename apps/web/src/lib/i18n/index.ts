import { en } from './en.ts';
import { fr, type MessageKey } from './fr.ts';
import { ja } from './ja.ts';
import { active, LOCALES, type Locale } from './locale.svelte.ts';
import { localizePath } from './path.ts';

export type { MessageKey, Locale };
export { LOCALES };
export { detectLocale, isLocale, localeFromPath, localizePath, stripLocale } from './path.ts';

/** Keys that exist in a `.one` and a `.other` form, picked by `tn()` with the language's plural rules. */
export type PluralKey = 'lobby.spectators' | 'game.lives' | 'results.words';

type Dictionary = Record<MessageKey, string>;

// Adding a language: write `xx.ts` (TypeScript checks that every key is present), register it here and in
// LOCALES, and add its code to Locale. A missing key at runtime still falls back to French.
const dictionaries: Record<Locale, Partial<Dictionary>> = { fr, en, ja };

export function setLocale(next: Locale): void {
	active.locale = next;
}

/** An internal link in the current language: `href('/credits')` -> `/ja/credits` on a Japanese page. */
export function href(path: string): string {
	return localizePath(path, active.locale);
}

export function getLocale(): Locale {
	return active.locale;
}

function fill(template: string, params?: Record<string, string | number>): string {
	if (!params) return template;
	return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}

export function t(key: MessageKey, params?: Record<string, string | number>): string {
	return fill(dictionaries[active.locale][key] ?? fr[key], params);
}

/** Plural-aware lookup: `tn('game.lives', 2)` uses `game.lives.one` or `game.lives.other`. `{n}` is filled in. */
export function tn(
	key: PluralKey,
	n: number,
	params: Record<string, string | number> = {}
): string {
	const form = new Intl.PluralRules(active.locale).select(n) === 'one' ? 'one' : 'other';
	return t(`${key}.${form}` as MessageKey, { ...params, n });
}
