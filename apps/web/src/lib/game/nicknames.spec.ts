import { describe, expect, it } from 'vitest';
import { NICKNAMES, randomNickname } from './nicknames';

describe('nickname examples', () => {
	it('are romaji, short enough for the field, and all different', () => {
		expect(new Set(NICKNAMES).size).toBe(NICKNAMES.length);
		for (const name of NICKNAMES) {
			expect(name.length).toBeLessThanOrEqual(20); // the limit of a nickname
			expect(name).toMatch(/^[A-Za-z -]+$/);
		}
	});

	it('are picked from the whole list, whatever the random number', () => {
		expect(randomNickname(0)).toBe(NICKNAMES[0]);
		expect(randomNickname(0.999999)).toBe(NICKNAMES[NICKNAMES.length - 1]);
		expect(randomNickname(1)).toBe(NICKNAMES[NICKNAMES.length - 1]); // never out of range
	});
});
