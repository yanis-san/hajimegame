/**
 * Base URL of the game server, fixed at build time from VITE_API_URL.
 * Empty means same origin (the Vite dev proxy, or one domain behind a reverse proxy).
 */
const raw: string = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
export const API_URL = raw.replace(/\/$/, '');

export function apiUrl(path: string): string {
	return `${API_URL}${path}`;
}

export function wsUrl(code: string): string {
	const base = API_URL || (typeof location === 'undefined' ? '' : location.origin);
	return `${base.replace(/^http/, 'ws')}/ws/${encodeURIComponent(code)}`;
}
