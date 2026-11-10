import { fr, type MessageKey } from './fr';

export type { MessageKey };
export type Locale = 'fr' | 'en' | 'ja';

type Dictionary = Partial<Record<MessageKey, string>>;

// English and Japanese dictionaries plug in here; missing keys fall back to French.
const dictionaries: Record<Locale, Dictionary> = { fr, en: {}, ja: {} };

let locale: Locale = 'fr';

export function setLocale(next: Locale): void {
	locale = next;
}

export function getLocale(): Locale {
	return locale;
}

export function t(key: MessageKey, params?: Record<string, string | number>): string {
	const template = dictionaries[locale][key] ?? fr[key];
	if (!params) return template;
	return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
