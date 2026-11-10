import { toKana } from 'wanakana';

/**
 * Display and input helpers for kana. These are cosmetic: the server normalizes and validates everything again.
 */

/** Romaji to hiragana while typing. A trailing lone "n" stays as typed until the next letter arrives. */
export function liveKana(raw: string): string {
	return toKana(lowerAscii(raw), { IMEMode: true });
}

/** Final conversion when the word is sent: a trailing "n" becomes ん. */
export function finalKana(raw: string): string {
	return toKana(lowerAscii(raw));
}

/**
 * Prepare typed text for wanakana: lower-case ASCII (so it produces hiragana, not katakana) and make "nn" before a
 * vowel mean ん + n-syllable ("konnichiwa" is こんにちわ), like the server's romaji table. A real IME would read it
 * as こんいちわ, which surprises learners.
 */
function lowerAscii(raw: string): string {
	return raw.replace(/[A-Z]+/g, (s) => s.toLowerCase()).replace(/nn(?=[aiueoy])/g, "n'n");
}

/** Katakana to hiragana (display only). */
export function toHiragana(text: string): string {
	return text.replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

export interface Highlight {
	before: string;
	match: string;
	after: string;
}

const TRAILING_SMALL = 'ゃゅょぁぃぅぇぉゎっ';

/** Split ``text`` around the first occurrence of ``fragment`` that does not cut a kana from its small kana. */
export function highlightFragment(text: string, fragment: string): Highlight | null {
	if (!fragment) return null;
	const hay = toHiragana(text);
	let from = 0;
	for (;;) {
		const index = hay.indexOf(fragment, from);
		if (index < 0) return null;
		const end = index + fragment.length;
		if (end >= hay.length || !TRAILING_SMALL.includes(hay[end])) {
			return {
				before: text.slice(0, index),
				match: text.slice(index, end),
				after: text.slice(end)
			};
		}
		from = index + 1;
	}
}

/**
 * IME safety. While a composition is active (Japanese keyboard), the input must neither be converted nor sent.
 * Safari fires ``compositionend`` before the Enter keydown that confirmed the composition, so an Enter arriving right
 * after a composition ended is the confirmation key, not a submit.
 */
export class CompositionGuard {
	composing = false;
	#endedAt = -Infinity;
	readonly #now: () => number;
	readonly #window: number;

	constructor(now: () => number = () => performance.now(), safariWindowMs = 80) {
		this.#now = now;
		this.#window = safariWindowMs;
	}

	start(): void {
		this.composing = true;
	}

	end(): void {
		this.composing = false;
		this.#endedAt = this.#now();
	}

	/** True when an Enter keydown should submit the word. */
	canSubmit(event: { isComposing?: boolean; keyCode?: number }): boolean {
		if (this.composing || event.isComposing || event.keyCode === 229) return false;
		return this.#now() - this.#endedAt > this.#window;
	}
}
