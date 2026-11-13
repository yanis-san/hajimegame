import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { sfx } from './sfx';

/** The audio context must only be created after a real user gesture, or Chrome warns and keeps it asleep. */
describe('audio unlock', () => {
	let created = 0;
	class FakeContext {
		state = 'suspended';
		constructor() {
			created++;
			throw new Error('stop here: only the creation is being counted');
		}
	}

	beforeEach(() => {
		created = 0;
		vi.stubGlobal('window', { AudioContext: FakeContext });
		vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => undefined });
	});
	afterEach(() => vi.unstubAllGlobals());

	it('does not create the context while the page has had no real gesture (F12, Ctrl, a scroll)', () => {
		vi.stubGlobal('navigator', { userActivation: { isActive: false } });
		sfx.unlock();
		expect(created).toBe(0);
	});

	it('creates it on a real gesture', () => {
		vi.stubGlobal('navigator', { userActivation: { isActive: true } });
		sfx.unlock();
		expect(created).toBe(1);
	});

	it('still tries where the browser cannot say (Safari): there is no warning there', () => {
		vi.stubGlobal('navigator', {});
		sfx.unlock();
		expect(created).toBe(1);
	});
});
