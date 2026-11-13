import type { Mode, PlayerView, ResultRow, WordView } from '@hajime/protocol';

/**
 * History of the finished games, kept only on this device (localStorage). There are no accounts, so nothing is
 * sent anywhere and nobody else can read it. Every access is guarded: storage can be missing or full.
 */

const KEY = 'hajime:history:v1';
/** Oldest games are dropped beyond this number. */
export const MAX_GAMES = 5;
/** A game longer than this keeps its first words only (a normal game has far fewer). */
export const MAX_WORDS = 400;

export interface SavedPlayer {
	id: string;
	name: string;
	avatar: number;
	bot: boolean;
	place: number;
	score: number;
	words: number;
}

export interface SavedGame {
	/** Same game, same id: reloading the results page never saves it twice. */
	id: string;
	/** When the game ended (ms since epoch). */
	at: number;
	room: string;
	/** The player's own id in that game, to find "my words". */
	you: string;
	mode: Mode;
	players: SavedPlayer[];
	words: WordView[];
}

/** What a finished game needs, as seen by the store. */
export interface FinishedGame {
	room: string;
	you: string;
	mode: Mode;
	players: PlayerView[];
	results: ResultRow[];
	words: WordView[];
}

function safe<T>(fn: () => T, fallback: T): T {
	try {
		return fn();
	} catch {
		return fallback;
	}
}

export function buildSavedGame(game: FinishedGame, at: number): SavedGame | null {
	if (game.results.length === 0) return null;
	const words = game.words.slice(0, MAX_WORDS);
	const players: SavedPlayer[] = [...game.results]
		.sort((a, b) => a.place - b.place)
		.map((row) => {
			const view = game.players.find((p) => p.id === row.player_id);
			return {
				id: row.player_id,
				name: view?.name ?? '?',
				avatar: view?.avatar ?? 0,
				bot: view?.bot ?? false,
				place: row.place,
				score: row.score,
				words: row.words
			};
		});
	const first = words[0]?.word ?? '';
	const last = words.at(-1)?.word ?? '';
	const scores = players.map((p) => `${p.id}${p.score}`).join('|');
	return {
		id: `${game.room}:${words.length}:${first}:${last}:${scores}`,
		at,
		room: game.room,
		you: game.you,
		mode: game.mode,
		players,
		words
	};
}

function isSavedGame(value: unknown): value is SavedGame {
	if (typeof value !== 'object' || value === null) return false;
	const g = value as Partial<SavedGame>;
	return (
		typeof g.id === 'string' &&
		typeof g.at === 'number' &&
		typeof g.room === 'string' &&
		typeof g.you === 'string' &&
		Array.isArray(g.players) &&
		Array.isArray(g.words)
	);
}

/** Saved games, newest first. */
export function loadHistory(): SavedGame[] {
	return safe(() => {
		const raw = localStorage.getItem(KEY);
		if (!raw) return [];
		const parsed: unknown = JSON.parse(raw);
		return Array.isArray(parsed) ? parsed.filter(isSavedGame) : [];
	}, []);
}

function write(games: SavedGame[]): boolean {
	return safe(() => {
		localStorage.setItem(KEY, JSON.stringify(games));
		return true;
	}, false);
}

/** Saves a game. Returns false when it was already saved or the browser refuses to store it. */
export function saveGame(game: SavedGame): boolean {
	const games = loadHistory();
	if (games.some((g) => g.id === game.id)) return false;
	let next = [game, ...games].slice(0, MAX_GAMES);
	// The storage can be full: drop the oldest games until it fits (the new one is always kept first).
	while (!write(next)) {
		if (next.length <= 1) return false;
		next = next.slice(0, -1);
	}
	return true;
}

export function deleteGame(id: string): void {
	write(loadHistory().filter((g) => g.id !== id));
}

export function clearHistory(): void {
	safe(() => localStorage.removeItem(KEY), undefined);
}
