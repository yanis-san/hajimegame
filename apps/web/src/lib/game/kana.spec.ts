import { describe, expect, it } from 'vitest';
import { CompositionGuard, finalKana, highlightFragment, liveKana, toHiragana } from './kana';

describe('romaji to kana', () => {
	it('converts as you type and keeps a pending n', () => {
		expect(liveKana('konnichiwa')).toBe('こんにちわ');
		expect(liveKana('hon')).toBe('ほn');
		expect(finalKana('hon')).toBe('ほん');
		expect(finalKana('SHOKUJI')).toBe('しょくじ');
	});

	it('leaves kana and kanji untouched', () => {
		expect(liveKana('さくら')).toBe('さくら');
		expect(finalKana('学校')).toBe('学校');
	});

	it('folds katakana for display', () => {
		expect(toHiragana('コーヒー')).toBe('こーひー');
	});
});

describe('highlightFragment', () => {
	it('splits around the fragment', () => {
		expect(highlightFragment('たべもの', 'べ')).toEqual({
			before: 'た',
			match: 'べ',
			after: 'もの'
		});
	});

	it('never cuts a kana from its small kana', () => {
		expect(highlightFragment('しょくじ', 'し')).toBeNull();
		expect(highlightFragment('しょくじ', 'しょ')).toEqual({
			before: '',
			match: 'しょ',
			after: 'くじ'
		});
		expect(highlightFragment('ひしょし', 'し')).toEqual({
			before: 'ひしょ',
			match: 'し',
			after: ''
		});
	});

	it('handles missing fragments and empty input', () => {
		expect(highlightFragment('ねこ', 'く')).toBeNull();
		expect(highlightFragment('ねこ', '')).toBeNull();
	});
});

describe('CompositionGuard (IME)', () => {
	it('blocks submit while composing', () => {
		const guard = new CompositionGuard(() => 1000);
		guard.start();
		expect(guard.canSubmit({})).toBe(false);
		expect(guard.canSubmit({ isComposing: true })).toBe(false);
	});

	it('blocks the Enter that confirms a composition on Safari (compositionend fires first)', () => {
		let now = 1000;
		const guard = new CompositionGuard(() => now, 80);
		guard.start();
		guard.end();
		now += 10;
		expect(guard.canSubmit({ isComposing: false })).toBe(false);
		now += 200;
		expect(guard.canSubmit({ isComposing: false })).toBe(true);
	});

	it('blocks keyCode 229 and allows a plain Enter', () => {
		const guard = new CompositionGuard(() => 5000);
		expect(guard.canSubmit({ keyCode: 229 })).toBe(false);
		expect(guard.canSubmit({ keyCode: 13 })).toBe(true);
	});
});
