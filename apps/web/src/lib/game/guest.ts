/**
 * A random identifier that names this browser as a player, without an account. It is created once, kept in
 * localStorage, and sent to the server when joining a game so that games can be linked to an account later
 * (when someone signs up, the games played with this identifier become theirs). It is never shown to other
 * players. Clearing the site's data creates a new one.
 */

const KEY = 'hajime:guest';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** A version 4 UUID. `crypto.randomUUID` only exists on secure pages, and the game is also opened over plain http
 * on a local network, so there is a fallback on `getRandomValues`, which is available everywhere. */
export function randomUuid(): string {
	if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
	const bytes = crypto.getRandomValues(new Uint8Array(16));
	bytes[6] = (bytes[6] & 0x0f) | 0x40;
	bytes[8] = (bytes[8] & 0x3f) | 0x80;
	const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
	return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

// Used when the browser refuses to store anything: stable for the life of the page at least.
let fallback: string | null = null;

export function getGuestId(): string {
	try {
		const stored = localStorage.getItem(KEY);
		if (stored && UUID.test(stored)) return stored;
		const created = randomUuid();
		localStorage.setItem(KEY, created);
		return created;
	} catch {
		fallback ??= randomUuid();
		return fallback;
	}
}
