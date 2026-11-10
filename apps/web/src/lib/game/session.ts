import type { SessionStore } from './client';

/** localStorage/sessionStorage can throw (private mode, blocked cookies): every access is guarded. */
function safe<T>(fn: () => T, fallback: T): T {
	try {
		return fn();
	} catch {
		return fallback;
	}
}

export const sessionTokens: SessionStore = {
	load: (room) => safe(() => sessionStorage.getItem(`hajime:session:${room}`), null),
	save: (room, token) =>
		safe(() => sessionStorage.setItem(`hajime:session:${room}`, token), undefined),
	clear: (room) => safe(() => sessionStorage.removeItem(`hajime:session:${room}`), undefined)
};

export interface Profile {
	name: string;
	avatar: number;
}

export function loadProfile(): Profile {
	return safe<Profile>(
		() => {
			const raw = localStorage.getItem('hajime:profile');
			if (!raw) return { name: '', avatar: Math.floor(Math.random() * 12) };
			const parsed = JSON.parse(raw) as Partial<Profile>;
			const avatar =
				typeof parsed.avatar === 'number' && Number.isInteger(parsed.avatar) ? parsed.avatar : 0;
			return {
				name: typeof parsed.name === 'string' ? parsed.name.slice(0, 20) : '',
				avatar: Math.min(11, Math.max(0, avatar))
			};
		},
		{ name: '', avatar: 0 }
	);
}

export function saveProfile(profile: Profile): void {
	safe(() => localStorage.setItem('hajime:profile', JSON.stringify(profile)), undefined);
}

export function loadPref<T extends string | number | boolean>(key: string, fallback: T): T {
	return safe(() => {
		const raw = localStorage.getItem(`hajime:pref:${key}`);
		return raw === null ? fallback : (JSON.parse(raw) as T);
	}, fallback);
}

export function savePref(key: string, value: string | number | boolean): void {
	safe(() => localStorage.setItem(`hajime:pref:${key}`, JSON.stringify(value)), undefined);
}
