import type { ServerMessage } from '@hajime/protocol';
import { beforeEach, describe, expect, it } from 'vitest';
import { backoffDelay, GameClient, type ConnectionStatus, type SocketLike } from './client';

class FakeSocket implements SocketLike {
	readyState = 0;
	onopen: SocketLike['onopen'] = null;
	onmessage: SocketLike['onmessage'] = null;
	onclose: SocketLike['onclose'] = null;
	onerror: SocketLike['onerror'] = null;
	sent: Record<string, unknown>[] = [];
	constructor(readonly url: string) {}
	send(data: string): void {
		this.sent.push(JSON.parse(data) as Record<string, unknown>);
	}
	close(): void {
		this.readyState = 3;
	}
	open(): void {
		this.readyState = 1;
		this.onopen?.({});
	}
	receive(msg: Record<string, unknown>): void {
		this.onmessage?.({ data: JSON.stringify({ v: 1, ...msg }) });
	}
	drop(code = 1006): void {
		this.readyState = 3;
		this.onclose?.({ code, reason: '' });
	}
}

interface Harness {
	client: GameClient;
	sockets: FakeSocket[];
	messages: ServerMessage[];
	statuses: ConnectionStatus[];
	fatals: string[];
	timers: { fn: () => void; ms: number; id: number }[];
	tokens: Map<string, string>;
	fireNextTimer(): void;
	advance(ms: number): void;
}

function harness(): Harness {
	const sockets: FakeSocket[] = [];
	const messages: ServerMessage[] = [];
	const statuses: ConnectionStatus[] = [];
	const fatals: string[] = [];
	const timers: Harness['timers'] = [];
	const tokens = new Map<string, string>();
	let nextTimer = 1;
	let now = 1000;
	const client = new GameClient({
		url: (room) => `ws://test/ws/${room}`,
		createSocket: (url) => {
			const socket = new FakeSocket(url);
			sockets.push(socket);
			return socket;
		},
		session: {
			load: (room) => tokens.get(room) ?? null,
			save: (room, token) => void tokens.set(room, token),
			clear: (room) => void tokens.delete(room)
		},
		now: () => now,
		setTimer: (fn, ms) => {
			const id = nextTimer++;
			timers.push({ fn, ms, id });
			return id;
		},
		clearTimer: (id) => {
			const index = timers.findIndex((t) => t.id === id);
			if (index >= 0) timers.splice(index, 1);
		},
		random: () => 0.5,
		onMessage: (m) => messages.push(m),
		onStatus: (s) => statuses.push(s),
		onFatal: (c) => fatals.push(c)
	});
	return {
		client,
		sockets,
		messages,
		statuses,
		fatals,
		timers,
		tokens,
		fireNextTimer: () => {
			const next = timers.shift();
			next?.fn();
		},
		advance: (ms) => {
			now += ms;
		}
	};
}

const JOIN = { name: 'Aya', avatar: 3, spectator: false };

describe('backoffDelay', () => {
	it('grows exponentially, is capped and jittered', () => {
		const delays = [0, 1, 2, 3, 4, 5, 10].map((n) => backoffDelay(n, () => 1));
		expect(delays).toEqual([500, 1000, 2000, 4000, 8000, 8000, 8000]);
		expect(backoffDelay(2, () => 0)).toBe(1400);
		expect(backoffDelay(2, () => 0.5)).toBeGreaterThan(1400);
		expect(backoffDelay(2, () => 0.5)).toBeLessThan(2000);
	});
});

describe('GameClient', () => {
	let h: Harness;
	beforeEach(() => {
		h = harness();
	});

	it('joins when there is no saved session and saves the token it receives', () => {
		h.client.connect('abcdef', JOIN);
		expect(h.sockets[0].url).toBe('ws://test/ws/ABCDEF');
		h.sockets[0].open();
		expect(h.sockets[0].sent[0]).toMatchObject({
			t: 'join',
			room: 'ABCDEF',
			name: 'Aya',
			avatar: 3,
			v: 1
		});
		h.sockets[0].receive({
			t: 'welcome',
			player_id: 'p1',
			token: 'tok'.repeat(6),
			spectator: false,
			seq: 0
		});
		expect(h.tokens.get('ABCDEF')).toBe('tok'.repeat(6));
		expect(h.statuses).toContain('open');
	});

	it('rejoins with the saved token after a drop, using backoff', () => {
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		h.sockets[0].receive({
			t: 'welcome',
			player_id: 'p1',
			token: 'x'.repeat(22),
			spectator: false,
			seq: 0
		});
		h.sockets[0].drop();
		expect(h.client.status).toBe('reconnecting');
		expect(h.timers.at(-1)?.ms).toBe(backoffDelay(0, () => 0.5));
		h.timers.splice(0, h.timers.length - 1); // keep only the retry timer
		h.fireNextTimer();
		expect(h.sockets).toHaveLength(2);
		h.sockets[1].open();
		expect(h.sockets[1].sent[0]).toMatchObject({
			t: 'rejoin',
			room: 'ABCDEF',
			token: 'x'.repeat(22)
		});
	});

	it('increases the delay on consecutive failures and resets after success', () => {
		h.client.connect('ABCDEF', JOIN);
		const delays: number[] = [];
		for (let i = 0; i < 4; i++) {
			h.sockets[i].drop();
			delays.push(h.timers.at(-1)?.ms ?? -1);
			h.timers.pop()?.fn(); // the retry opens the next socket
		}
		expect(delays).toEqual([0, 1, 2, 3].map((n) => backoffDelay(n, () => 0.5)));
		h.sockets[4].open(); // success resets the counter
		h.sockets[4].drop();
		expect(h.timers.at(-1)?.ms).toBe(backoffDelay(0, () => 0.5));
	});

	it('estimates the clock from pongs', () => {
		h.client.connect('ABCDEF', JOIN);
		const socket = h.sockets[0];
		socket.open();
		const pings = socket.sent.filter((m) => m.t === 'ping');
		expect(pings).toHaveLength(1);
		h.advance(40);
		socket.receive({ t: 'pong', n: pings[0].n, t0: pings[0].t0, server_time: 51_020, seq: 0 });
		expect(h.client.clock.sampleCount).toBe(1);
		expect(h.client.clock.offset).toBeCloseTo(51_020 + 20 - 1040, 5);
		expect(h.messages).toHaveLength(0); // pongs are internal
	});

	it('pings in a burst of 8 then every 5 seconds', () => {
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		for (let i = 0; i < 7; i++) h.fireNextTimer();
		expect(h.sockets[0].sent.filter((m) => m.t === 'ping')).toHaveLength(8);
		expect(h.timers[h.timers.length - 1].ms).toBe(5000);
	});

	it('resynchronises when a broadcast event is missed', () => {
		h.client.connect('ABCDEF', JOIN);
		const first = h.sockets[0];
		first.open();
		first.receive({ t: 'snapshot', seq: 10, room: 'ABCDEF' });
		first.receive({ t: 'turn', seq: 11, turn: 1 });
		expect(h.messages.map((m) => m.t)).toEqual(['snapshot', 'turn']);
		first.receive({ t: 'accepted', seq: 13 }); // 12 was lost
		expect(h.messages).toHaveLength(2); // dropped, not applied
		expect(h.sockets).toHaveLength(2); // a new socket is opening to get a fresh snapshot
	});

	it('does not treat private or ephemeral messages as gaps', () => {
		h.client.connect('ABCDEF', JOIN);
		const socket = h.sockets[0];
		socket.open();
		socket.receive({ t: 'snapshot', seq: 5 });
		socket.receive({ t: 'rejected', seq: 5, reason: 'too_late', text: 'x' });
		socket.receive({ t: 'typing', seq: 5, player_id: 'p', text: 'あ' });
		socket.receive({ t: 'patch', seq: 6 });
		expect(h.messages.map((m) => m.t)).toEqual(['snapshot', 'rejected', 'typing', 'patch']);
		expect(h.sockets).toHaveLength(1);
	});

	it('stops retrying on fatal errors', () => {
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		h.sockets[0].receive({ t: 'error', code: 'room_not_found', message: 'x', seq: 0 });
		expect(h.fatals).toEqual(['room_not_found']);
		h.sockets[0].drop(4404);
		expect(h.sockets).toHaveLength(1);
	});

	it('treats room_full as fatal only while joining', () => {
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		h.sockets[0].receive({ t: 'snapshot', seq: 1 });
		h.sockets[0].receive({ t: 'error', code: 'wrong_phase', message: '', seq: 1 });
		expect(h.fatals).toEqual([]);
		expect(h.messages.at(-1)?.t).toBe('error');
	});

	it('forgets an expired session token and joins again', () => {
		h.tokens.set('ABCDEF', 'old'.repeat(8));
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		expect(h.sockets[0].sent[0].t).toBe('rejoin');
		h.sockets[0].receive({ t: 'error', code: 'bad_token', message: '', seq: 0 });
		expect(h.tokens.has('ABCDEF')).toBe(false);
		expect(h.sockets[0].sent.at(-1)).toMatchObject({ t: 'join', name: 'Aya' });
	});

	it('waits longer after a server restart notice', () => {
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		h.sockets[0].drop(1012);
		expect(h.timers.at(-1)?.ms).toBeGreaterThanOrEqual(1500);
	});

	it('refuses to send while disconnected and stops cleanly', () => {
		h.client.connect('ABCDEF', JOIN);
		expect(h.client.send({ t: 'ready', ready: true })).toBe(false);
		h.sockets[0].open();
		expect(h.client.send({ t: 'ready', ready: true })).toBe(true);
		expect(h.sockets[0].sent.at(-1)).toMatchObject({ t: 'ready', ready: true, v: 1 });
		h.client.close();
		expect(h.client.status).toBe('closed');
		h.sockets[0].drop();
		expect(h.sockets).toHaveLength(1);
	});

	it('ignores malformed frames', () => {
		h.client.connect('ABCDEF', JOIN);
		h.sockets[0].open();
		h.sockets[0].onmessage?.({ data: 'not json' });
		expect(h.messages).toHaveLength(0);
	});
});
