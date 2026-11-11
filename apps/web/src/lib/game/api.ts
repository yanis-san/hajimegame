import { apiUrl } from './config';

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

export async function roomExists(code: string, fetcher: typeof fetch = fetch): Promise<boolean> {
	const response = await fetcher(apiUrl(`/api/rooms/${encodeURIComponent(code)}`));
	if (response.status === 404) return false;
	if (!response.ok) throw new ApiError(response.status, 'error');
	return true;
}
