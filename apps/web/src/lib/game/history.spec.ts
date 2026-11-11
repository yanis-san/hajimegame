import type { PlayerView, ResultRow, WordView } from '@hajime/protocol';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
	MAX_GAMES,
	MAX_WORDS,
	buildSavedGame,
	clearHistory,
	deleteGame,
	loadHistory,
	saveGame,
	type FinishedGame
} from './history';

/** Minimal localStorage, with an optional size limit to simulate a full disk. */
class MemoryStorage {
	#data = new Map<string, string>();
	limit = Infinity;
	getItem(key: string): string | null {
		return this.#data.get(key) ?? null;
	}
	setItem(key: string, value: string): void {
		if (value.length > this.limit) throw new DOMException('full', 'QuotaExceededError');
		this.#data.set(key, value);
	}
	removeItem(key: string): void {
		this.#data.delete(key);
	}
}

const player = (id: string, name: string): PlayerView => ({
	id,
	name,
	avatar: 3,
	ready: true,
	connected: true,
	host: false,
	alive: true,
	lives: 1,
	score: 0,
	bonus: [],
	bot: false,
	difficulty: null
});
const word = (id: string, text: string, turn: number): WordView => ({
	player_id: id,
	word: text,
	reading: text,
	turn,
	meaning_fr: '',
	meaning_en: 'x',
	example_ja: '',
	example_en: '',
	example_fr: ''
});
const results: ResultRow[] = [
	{ player_id: 'b', place: 2, score: 1, words: 1, longest: 'ねこ' },
	{ player_id: 'a', place: 1, score: 5, words: 2, longest: 'さくら' }
];

function finished(extra: Partial<FinishedGame> = {}): FinishedGame {
	return {
		room: 'ABCDEF',
		you: 'a',
		mode: 'classic',
		players: [player('a', 'Aya'), player('b', 'Ben')],
		results,
		words: [word('a', 'さくら', 1), word('b', 'ねこ', 2)],
		...extra
	};
}

let storage: MemoryStorage;
beforeEach(() => {
	storage = new MemoryStorage();
	(globalThis as { localStorage?: unknown }).localStorage = storage;
});
afterEach(() => {
	delete (globalThis as { localStorage?: unknown }).localStorage;
});

describe('history', () => {
	it('builds a game ordered by place, with the names and every word', () => {
		const game = buildSavedGame(finished(), 1000);
		expect(game?.players.map((p) => [p.name, p.place])).toEqual([
			['Aya', 1],
			['Ben', 2]
		]);
		expect(game?.words.map((w) => w.word)).toEqual(['さくら', 'ねこ']);
		expect(game?.at).toBe(1000);
		expect(buildSavedGame(finished({ results: [] }), 1)).toBeNull();
	});

	it('saves, lists newest first, and never saves the same game twice', () => {
		const first = buildSavedGame(finished(), 1)!;
		const second = buildSavedGame(finished({ room: 'ZZZZZZ' }), 2)!;
		expect(saveGame(first)).toBe(true);
		expect(saveGame(first)).toBe(false);
		expect(saveGame(second)).toBe(true);
		expect(loadHistory().map((g) => g.room)).toEqual(['ZZZZZZ', 'ABCDEF']);
	});

	it('deletes one game or all of them', () => {
		const a = buildSavedGame(finished(), 1)!;
		const b = buildSavedGame(finished({ room: 'ZZZZZZ' }), 2)!;
		saveGame(a);
		saveGame(b);
		deleteGame(a.id);
		expect(loadHistory().map((g) => g.id)).toEqual([b.id]);
		clearHistory();
		expect(loadHistory()).toEqual([]);
	});

	it('keeps only the most recent games and the first words of a very long game', () => {
		for (let i = 0; i < MAX_GAMES + 5; i++) {
			saveGame(buildSavedGame(finished({ room: `R${i}` }), i)!);
		}
		const games = loadHistory();
		expect(games).toHaveLength(MAX_GAMES);
		expect(games[0].room).toBe(`R${MAX_GAMES + 4}`);
		const long = buildSavedGame(
			finished({ words: Array.from({ length: MAX_WORDS + 50 }, (_, i) => word('a', `w${i}`, i)) }),
			1
		)!;
		expect(long.words).toHaveLength(MAX_WORDS);
	});

	it('drops the oldest games when the storage is full instead of failing', () => {
		const games = [1, 2, 3].map((i) => buildSavedGame(finished({ room: `R${i}` }), i)!);
		saveGame(games[0]);
		saveGame(games[1]);
		storage.limit = JSON.stringify([games[2], games[1]]).length + 5;
		expect(saveGame(games[2])).toBe(true);
		expect(loadHistory().map((g) => g.room)).toEqual(['R3', 'R2']);
	});

	it('survives missing or broken storage', () => {
		storage.setItem('hajime:history:v1', '{not json');
		expect(loadHistory()).toEqual([]);
		storage.setItem('hajime:history:v1', JSON.stringify([{ nope: 1 }, 7]));
		expect(loadHistory()).toEqual([]);
		delete (globalThis as { localStorage?: unknown }).localStorage;
		expect(loadHistory()).toEqual([]);
		expect(saveGame(buildSavedGame(finished(), 1)!)).toBe(false);
	});
});
