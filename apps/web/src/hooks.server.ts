import type { Handle } from '@sveltejs/kit/hooks';
import {
	DEFAULT_LOCALE,
	LANG_COOKIE,
	detectLocale,
	isLocale,
	localeFromPath
} from '#lib/i18n/path.ts';

function redirect(location: string, status: 301 | 302): Response {
	return new Response(null, {
		status,
		headers: { location, 'cache-control': 'private, no-store', vary: 'Accept-Language, Cookie' }
	});
}

/**
 * The language is part of the URL: `/` is French, `/en/...` and `/ja/...` are served already translated (the
 * server renders the right language and `<html lang>`), so a shared link always opens in its own language.
 * Only the bare root adapts: a visitor without a saved choice is sent to the language of their browser.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const { pathname, search } = event.url;

	if (pathname === '/fr' || pathname.startsWith('/fr/')) {
		return redirect((pathname.slice(3) || '/') + search, 301); // French has no prefix
	}
	if (pathname === '/') {
		const saved = event.cookies.get(LANG_COOKIE);
		const wanted = isLocale(saved)
			? saved
			: detectLocale(event.request.headers.get('accept-language'));
		if (wanted !== DEFAULT_LOCALE) return redirect(`/${wanted}${search}`, 302);
	}

	const locale = localeFromPath(pathname);
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replaceAll('%lang%', locale)
	});
};
