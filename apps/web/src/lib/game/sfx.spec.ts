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

/** iPhone: the ring/silent switch mutes Web Audio unless the page says it plays media. */
describe('audio on iPhone', () => {
	class FailingContext {
		constructor() {
			throw new Error('stop here: only the audio session is being looked at');
		}
	}

	beforeEach(() => {
		vi.stubGlobal('window', { AudioContext: FailingContext });
		vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => undefined });
	});
	afterEach(() => vi.unstubAllGlobals());

	it('asks for the playback audio session where Safari offers it', () => {
		const audioSession = { type: 'auto' };
		vi.stubGlobal('navigator', { audioSession, userAgent: 'iPhone', maxTouchPoints: 5 });
		sfx.unlock();
		expect(audioSession.type).toBe('playback');
	});

	it('plays a silent loop on an older iPhone that has no audio session', () => {
		const play = vi.fn(() => Promise.resolve());
		const made: { loop?: boolean }[] = [];
		class FakeAudio {
			loop = false;
			constructor() {
				made.push(this);
			}
			setAttribute(): void {}
			play = play;
		}
		vi.stubGlobal('Audio', FakeAudio);
		vi.stubGlobal('URL', { createObjectURL: () => 'blob:silent' });
		vi.stubGlobal('navigator', {
			userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)',
			maxTouchPoints: 5
		});
		sfx.unlock();
		expect(play).toHaveBeenCalledTimes(1);
		expect(made[0].loop).toBe(true);
	});
});
