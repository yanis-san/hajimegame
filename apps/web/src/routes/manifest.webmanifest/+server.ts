import { json, type RequestHandler } from '@sveltejs/kit';
import { en } from '#lib/i18n/en.ts';
import { fr } from '#lib/i18n/fr.ts';
import { ja } from '#lib/i18n/ja.ts';
import { isLocale, localizePath } from '#lib/i18n/path.ts';

const TAGLINES = { fr: fr['app.tagline'], en: en['app.tagline'], ja: ja['app.tagline'] };

/** The web app manifest in the visitor's language, so an installed app is not French by accident. */
export const GET: RequestHandler = ({ url }) => {
	const asked = url.searchParams.get('lang');
	const lang = isLocale(asked) ? asked : 'fr';
	return json(
		{
			name: 'Bakahatsu',
			short_name: 'Bakahatsu',
			description: TAGLINES[lang],
			lang,
			start_url: localizePath('/', lang),
			scope: '/',
			display: 'standalone',
			orientation: 'portrait',
			background_color: '#0f1b2d',
			theme_color: '#0f1b2d',
			icons: [
				{ src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
				{ src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
				{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'maskable' }
			]
		},
		{ headers: { 'content-type': 'application/manifest+json' } }
	);
};
