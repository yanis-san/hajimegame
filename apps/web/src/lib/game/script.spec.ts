import { describe, expect, it } from 'vitest';
import { sameKana, toHiragana } from './script';

describe('script', () => {
	it('folds katakana to hiragana and leaves the rest', () => {
		expect(toHiragana('コーヒー')).toBe('こーひー');
		expect(toHiragana('学校ガッコウabc')).toBe('学校がっこうabc');
	});
	it('compares spellings of the same kana', () => {
		expect(sameKana('コーヒー', 'こーひー')).toBe(true);
		expect(sameKana('ねこ', '猫')).toBe(false);
	});
});
