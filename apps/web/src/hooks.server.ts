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

const NOT_PAGES = ['/api/', '/ws/', '/_app/', '/manifest.webmanifest', '/healthz', '/readyz'];

/** A browser navigation to a page without a language prefix (not an asset, API call or data request). */
function isUnprefixedPage(request: Request, pathname: string): boolean {
	if (request.method !== 'GET' || localeFromPath(pathname) !== DEFAULT_LOCALE) return false;
	if (NOT_PAGES.some((p) => pathname === p || pathname.startsWith(p))) return false;
	return (request.headers.get('accept') ?? '').includes('text/html');
}

/**
 * The language is part of the URL: `/` is French, `/en/...` and `/ja/...` are served already translated (the
 * server renders the right language and `<html lang>`), so a shared link always opens in its own language.
 * A page opened without a prefix adapts: a visitor without a saved choice is sent to the language of their browser
 * (a prefixed link is never touched, and a saved choice always wins).
 */
export const handle: Handle = async ({ event, resolve }) => {
	const { pathname, search } = event.url;

	if (pathname === '/fr' || pathname.startsWith('/fr/')) {
		return redirect((pathname.slice(3) || '/') + search, 301); // French has no prefix
	}
	if (isUnprefixedPage(event.request, pathname)) {
		const saved = event.cookies.get(LANG_COOKIE);
		const wanted = isLocale(saved)
			? saved
			: detectLocale(event.request.headers.get('accept-language'));
		if (wanted !== DEFAULT_LOCALE)
			return redirect(`/${wanted}${pathname === '/' ? '' : pathname}${search}`, 302);
	}

	const locale = localeFromPath(pathname);
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replaceAll('%lang%', locale)
	});
};
