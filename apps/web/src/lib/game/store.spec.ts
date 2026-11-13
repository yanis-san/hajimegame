import type { PlayerView, ServerMessage, SettingsView } from '@hajime/protocol';
import { describe, expect, it } from 'vitest';
import { GameStore } from './store.svelte';

const settings: SettingsView = {
	lives: 3,
	fuse_seconds: 10,
	mode: 'classic',
	max_players: 8,
	bonus_kana: false,
	n_penalty: false,
	levels: [5, 4]
};

function player(id: string, extra: Partial<PlayerView> = {}): PlayerView {
	return {
		id,
		name: id.toUpperCase(),
		avatar: 0,
		ready: false,
		connected: true,
		host: false,
		alive: true,
		lives: 3,
		score: 0,
		bonus: [],
		bot: false,
		difficulty: null,
		...extra
	};
}

function snapshot(extra: Record<string, unknown> = {}): ServerMessage {
	return {
		t: 'snapshot',
		room: 'ABCDEF',
		phase: 'lobby',
		host: 'a',
		you: 'a',
		spectator: false,
		settings,
		players: [player('a', { host: true }), player('b')],
		spectators: 0,
		turn: null,
		typing: '',
		words: [],
		countdown_ends: null,
		results: null,
		server_time: 1000,
		seq: 1,
		v: 1,
		...extra
	} as ServerMessage;
}

describe('GameStore', () => {
	it('mirrors a snapshot', () => {
		const store = new GameStore();
		store.apply(snapshot());
		expect(store.loaded).toBe(true);
		expect(store.room).toBe('ABCDEF');
		expect(store.players.map((p) => p.id)).toEqual(['a', 'b']);
		expect(store.isHost).toBe(true);
		expect(store.me?.id).toBe('a');
	});

	it('merges player patches: update, add and remove', () => {
		const store = new GameStore();
		store.apply(snapshot());
		store.apply({
			t: 'patch',
			players: { b: player('b', { ready: true }), c: player('c'), a: null },
			host: 'b',
			seq: 2,
			v: 1
		} as ServerMessage);
		expect(store.players.map((p) => p.id)).toEqual(['b', 'c']);
		expect(store.players[0].ready).toBe(true);
		expect(store.host).toBe('b');
		expect(store.isHost).toBe(false);
	});

	it('knows when the host can start', () => {
		const store = new GameStore();
		store.apply(snapshot());
		expect(store.canStart).toBe(false);
		store.apply({
			t: 'patch',
			players: { b: player('b', { ready: true }) },
			seq: 2,
			v: 1
		} as ServerMessage);
		expect(store.canStart).toBe(true);
	});

	it('tracks turns, typing and accepted words', () => {
		const store = new GameStore();
		store.apply(snapshot({ phase: 'playing' }));
		store.apply({
			t: 'turn',
			turn: 1,
			player_id: 'b',
			fragment: 'く',
			deadline: 5000,
			fuse_ms: 10_000,
			seq: 2,
			v: 1
		} as ServerMessage);
		expect(store.turn?.fragment).toBe('く');
		expect(store.isMyTurn).toBe(false);
		store.apply({ t: 'typing', player_id: 'b', text: 'くる', seq: 2, v: 1 } as ServerMessage);
		expect(store.typing).toBe('くる');
		store.apply({
			t: 'accepted',
			turn: 1,
			player_id: 'b',
			word: 'くるま',
			reading: 'くるま',
			score_gain: 3,
			score: 3,
			seq: 3,
			v: 1
		} as ServerMessage);
		expect(store.words.at(-1)?.word).toBe('くるま');
		expect(store.player('b')?.score).toBe(3);
		expect(store.accepted?.gain).toBe(3);
		store.apply({
			t: 'turn',
			turn: 2,
			player_id: 'a',
			fragment: 'さ',
			deadline: 9000,
			fuse_ms: 10_000,
			seq: 4,
			v: 1
		} as ServerMessage);
		expect(store.typing).toBe('');
		expect(store.isMyTurn).toBe(true);
	});

	it('handles explosion, elimination and game over', () => {
		const store = new GameStore();
		store.apply(snapshot({ phase: 'playing' }));
		store.apply({
			t: 'explosion',
			turn: 1,
			player_id: 'b',
			lives: 2,
			seq: 2,
			v: 1
		} as ServerMessage);
		expect(store.player('b')?.lives).toBe(2);
		expect(store.explosion?.playerId).toBe('b');
		store.apply({
			t: 'elimination',
			player_id: 'b',
			place: 2,
			reason: 'explosion',
			seq: 3,
			v: 1
		} as ServerMessage);
		expect(store.player('b')?.alive).toBe(false);
		store.apply({
			t: 'game_over',
			winner_id: 'a',
			results: [
				{ player_id: 'a', place: 1, score: 5, words: 2, longest: 'さくら' },
				{ player_id: 'b', place: 2, score: 1, words: 1, longest: 'ねこ' }
			],
			words: [
				{ player_id: 'a', word: 'さくら', reading: 'さくら', turn: 1 },
				{ player_id: 'b', word: 'ねこ', reading: 'ねこ', turn: 2 }
			],
			seq: 4,
			v: 1
		} as ServerMessage);
		expect(store.winnerId).toBe('a');
		expect(store.results).toHaveLength(2);
		expect(store.words.map((w) => w.word)).toEqual(['さくら', 'ねこ']); // all of them, not the last few
	});

	it('clears the game when the room goes back to the lobby', () => {
		const store = new GameStore();
		store.apply(
			snapshot({
				phase: 'finished',
				results: [{ player_id: 'a', place: 1, score: 1, words: 1, longest: 'x' }]
			})
		);
		expect(store.winnerId).toBe('a');
		store.apply({ t: 'patch', phase: 'lobby', seq: 2, v: 1 } as ServerMessage);
		expect(store.results).toBeNull();
		expect(store.winnerId).toBeNull();
		expect(store.phase).toBe('lobby');
	});

	it('keeps chat bounded and records errors', () => {
		const store = new GameStore();
		store.apply(snapshot());
		for (let i = 0; i < 60; i++) {
			store.apply({
				t: 'chat',
				player_id: 'a',
				name: 'A',
				text: `m${i}`,
				seq: 2 + i,
				v: 1
			} as ServerMessage);
		}
		expect(store.chat).toHaveLength(50);
		expect(store.chat.at(-1)?.text).toBe('m59');
		store.apply({ t: 'error', code: 'not_host', message: '', seq: 0, v: 1 } as ServerMessage);
		expect(store.lastError?.code).toBe('not_host');
	});
});
