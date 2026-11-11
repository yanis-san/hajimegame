/** The active interface language. Kept in a rune module so every `t()` call re-renders when it changes. */
export type Locale = 'fr' | 'en' | 'ja';

/** Languages offered in the picker, each named in its own language (never translated). */
export const LOCALES: readonly { code: Locale; name: string }[] = [
	{ code: 'fr', name: 'Français' },
	{ code: 'en', name: 'English' },
	{ code: 'ja', name: '日本語' }
];

export const active = $state<{ locale: Locale }>({ locale: 'fr' });
