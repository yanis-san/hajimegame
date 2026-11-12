import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getGuestId, randomUuid } from './guest';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

class MemoryStorage {
	data = new Map<string, string>();
	getItem = (key: string): string | null => this.data.get(key) ?? null;
	setItem = (key: string, value: string): void => void this.data.set(key, value);
}

describe('guest identifier', () => {
	beforeEach(() => vi.stubGlobal('localStorage', new MemoryStorage()));
	afterEach(() => vi.unstubAllGlobals());

	it('is a version 4 UUID, created once and then kept', () => {
		const first = getGuestId();
		expect(first).toMatch(UUID);
		expect(getGuestId()).toBe(first);
		expect(localStorage.getItem('hajime:guest')).toBe(first);
	});

	it('replaces a stored value that is not a UUID', () => {
		localStorage.setItem('hajime:guest', 'hello');
		const id = getGuestId();
		expect(id).toMatch(UUID);
		expect(id).not.toBe('hello');
	});

	it('still works, and stays stable, when the browser refuses to store anything', () => {
		vi.stubGlobal('localStorage', {
			getItem: () => {
				throw new Error('blocked');
			},
			setItem: () => {
				throw new Error('blocked');
			}
		});
		const id = getGuestId();
		expect(id).toMatch(UUID);
		expect(getGuestId()).toBe(id);
	});

	it('generates a valid UUID without crypto.randomUUID (plain http pages)', () => {
		const real = globalThis.crypto;
		vi.stubGlobal('crypto', { getRandomValues: real.getRandomValues.bind(real) });
		expect(randomUuid()).toMatch(UUID);
		expect(randomUuid()).not.toBe(randomUuid());
	});
});
