/**
 * Katakana to hiragana, with no dependency: pages that are rendered on the server use it (the kana library of the
 * input field is only loaded in the browser).
 */
export function toHiragana(text: string): string {
	return [...text]
		.map((c) => (c >= 'ァ' && c <= 'ヶ' ? String.fromCharCode(c.charCodeAt(0) - 0x60) : c))
		.join('');
}

/** The same word in two spellings of the same kana (コーヒー and こーひー). */
export function sameKana(a: string, b: string): boolean {
	return toHiragana(a) === toHiragana(b);
}
