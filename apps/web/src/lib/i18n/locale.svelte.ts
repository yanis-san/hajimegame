/** The active interface language. Kept in a rune module so every `t()` call re-renders when it changes. */
import type { Locale } from './path.ts';

export type { Locale };

/** Languages offered in the picker, each named in its own language (never translated). */
export const LOCALES: readonly { code: Locale; name: string }[] = [
	{ code: 'fr', name: 'Français' },
	{ code: 'en', name: 'English' },
	{ code: 'ja', name: '日本語' }
];

export const active = $state<{ locale: Locale }>({ locale: 'fr' });
