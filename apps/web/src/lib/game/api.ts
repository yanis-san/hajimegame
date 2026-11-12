import type { StatsByGame } from '#lib/games/registry.ts';
import { apiUrl } from './config';
import { getGuestId } from './guest';

export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly detail: string
	) {
		super(detail);
	}
}

const HEADERS = { 'Content-Type': 'application/json', 'X-Hajime-Client': 'web' };

export async function createRoom(
	mode: 'classic' | 'shiritori' = 'classic',
	fetcher: typeof fetch = fetch
): Promise<{ code: string }> {
	const response = await fetcher(apiUrl('/api/rooms'), {
		method: 'POST',
		headers: HEADERS,
		body: JSON.stringify({ mode })
	});
	if (!response.ok) {
		const body = (await response.json().catch(() => ({}))) as { detail?: string };
		throw new ApiError(response.status, body.detail ?? 'error');
	}
	return (await response.json()) as { code: string };
}

/**
 * The statistics of this browser for one game. The guest identifier is the proof that those games are the
 * browser's own; it is sent in a header, never in the address. Each game has its own view type (`StatsByGame`).
 */
export async function getMyStats<G extends keyof StatsByGame>(
	game: G,
	mode = 'all',
	fetcher: typeof fetch = fetch
): Promise<StatsByGame[G]> {
	const response = await fetcher(apiUrl(`/api/me/stats/${game}?mode=${encodeURIComponent(mode)}`), {
		headers: { 'X-Hajime-Client': 'web', 'X-Hajime-Guest': getGuestId() }
	});
	if (!response.ok) {
		const body = (await response.json().catch(() => ({}))) as { detail?: string };
		throw new ApiError(response.status, body.detail ?? 'error');
	}
	return (await response.json()) as StatsByGame[G];
}

export async function roomExists(code: string, fetcher: typeof fetch = fetch): Promise<boolean> {
	const response = await fetcher(apiUrl(`/api/rooms/${encodeURIComponent(code)}`));
	if (response.status === 404) return false;
	if (!response.ok) throw new ApiError(response.status, 'error');
	return true;
}
