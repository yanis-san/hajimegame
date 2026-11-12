import type { ServerMessage } from '@hajime/protocol';
import { PROTOCOL_VERSION } from '@hajime/protocol';
import { ClockSync } from './clock';
import type { Outgoing } from './types';

export type ConnectionStatus = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed';

export interface SocketLike {
	readyState: number;
	onopen: ((ev: unknown) => void) | null;
	onmessage: ((ev: { data: unknown }) => void) | null;
	onclose: ((ev: { code: number; reason: string }) => void) | null;
	onerror: ((ev: unknown) => void) | null;
	send(data: string): void;
	close(code?: number, reason?: string): void;
}

export interface JoinInfo {
	name: string;
	avatar: number;
	spectator: boolean;
	/** Private identifier of this browser (see guest.ts); sent so finished games can be linked to an account later. */
	guest_id?: string;
	/** Interface language, for statistics. */
	lang?: 'fr' | 'en' | 'ja';
}

export interface SessionStore {
	load(room: string): string | null;
	save(room: string, token: string): void;
	clear(room: string): void;
}

export interface ClientOptions {
	url: (room: string) => string;
	createSocket?: (url: string) => SocketLike;
	session?: SessionStore;
	now?: () => number;
	setTimer?: (fn: () => void, ms: number) => unknown;
	clearTimer?: (id: unknown) => void;
	random?: () => number;
	onMessage: (msg: ServerMessage) => void;
	onStatus: (status: ConnectionStatus, detail?: { attempt: number; delay: number }) => void;
	onFatal: (code: string) => void;
}

const OPEN = 1;
/** Errors after which retrying is pointless, wherever they happen. */
const FATAL = new Set(['room_not_found', 'kicked', 'bad_version']);
/** Errors that end the attempt only while joining (afterwards they are ordinary refusals). */
const FATAL_WHILE_JOINING = new Set(['room_full', 'wrong_phase', 'name_invalid']);
/** Broadcast events advance the room sequence; private and ephemeral messages repeat it. */
const SEQUENCED = new Set([
	'patch',
	'countdown',
	'turn',
	'accepted',
	'explosion',
	'elimination',
	'life',
	'bonus',
	'game_over',
	'chat'
]);

export function backoffDelay(
	attempt: number,
	random: () => number,
	base = 500,
	cap = 8000
): number {
	const exp = Math.min(cap, base * 2 ** attempt);
	return Math.round(exp * (0.7 + random() * 0.3)); // 70-100%: exponential with jitter
}

export class GameClient {
	readonly clock = new ClockSync();
	status: ConnectionStatus = 'idle';
	readonly #opts: ClientOptions;
	#socket: SocketLike | null = null;
	#room = '';
	#join: JoinInfo | null = null;
	#attempt = 0;
	#lastSeq = -1;
	#pending = new Map<number, number>();
	#pingN = 0;
	#timers = new Set<unknown>();
	#stopped = false;
	#gotSnapshot = false;
	#visibilityHandler: (() => void) | null = null;

	constructor(opts: ClientOptions) {
		this.#opts = opts;
	}

	get #now(): number {
		return (this.#opts.now ?? (() => performance.now()))();
	}

	connect(room: string, join: JoinInfo): void {
		this.#room = room.toUpperCase();
		this.#join = join;
		this.#stopped = false;
		this.#attempt = 0;
		this.#open();
		if (typeof document !== 'undefined' && !this.#visibilityHandler) {
			// Safari kills sockets in the background: reconnect right away when the tab comes back.
			this.#visibilityHandler = () => {
				if (document.visibilityState === 'visible' && !this.#stopped && !this.isOpen)
					this.reconnectNow();
			};
			document.addEventListener('visibilitychange', this.#visibilityHandler);
			window.addEventListener('online', this.#visibilityHandler);
		}
	}

	get isOpen(): boolean {
		return this.#socket?.readyState === OPEN;
	}

	send(msg: Outgoing): boolean {
		if (!this.isOpen) return false;
		this.#socket?.send(JSON.stringify({ ...msg, v: PROTOCOL_VERSION }));
		return true;
	}

	leave(): void {
		this.send({ t: 'leave' });
		this.close();
		this.#opts.session?.clear(this.#room);
	}

	close(): void {
		this.#stopped = true;
		this.#clearTimers();
		if (this.#visibilityHandler) {
			document.removeEventListener('visibilitychange', this.#visibilityHandler);
			window.removeEventListener('online', this.#visibilityHandler);
			this.#visibilityHandler = null;
		}
		const socket = this.#socket;
		this.#socket = null;
		if (socket) {
			socket.onclose = socket.onmessage = socket.onerror = socket.onopen = null;
			socket.close(1000);
		}
		this.#setStatus('closed');
	}

	/** Drop the current socket and reconnect without waiting for the backoff. */
	reconnectNow(): void {
		if (this.#stopped) return;
		this.#clearTimers();
		const socket = this.#socket;
		this.#socket = null;
		if (socket) {
			socket.onclose = socket.onmessage = socket.onerror = socket.onopen = null;
			try {
				socket.close();
			} catch {
				/* already dead */
			}
		}
		this.#attempt = 0;
		this.#open();
	}

	// ------------------------------------------------------------------ internals

	#setStatus(status: ConnectionStatus, delay = 0): void {
		this.status = status;
		this.#opts.onStatus(status, { attempt: this.#attempt, delay });
	}

	#timer(fn: () => void, ms: number): unknown {
		const set = this.#opts.setTimer ?? ((f, t) => setTimeout(f, t));
		const id = set(fn, ms);
		this.#timers.add(id);
		return id;
	}

	#clearTimers(): void {
		const clear = this.#opts.clearTimer ?? ((id) => clearTimeout(id as number));
		for (const id of this.#timers) clear(id);
		this.#timers.clear();
	}

	#open(): void {
		this.#setStatus(this.#attempt === 0 && this.status === 'idle' ? 'connecting' : 'reconnecting');
		const create =
			this.#opts.createSocket ?? ((url) => new WebSocket(url) as unknown as SocketLike);
		const socket = create(this.#opts.url(this.#room));
		this.#socket = socket;
		this.#gotSnapshot = false;
		socket.onopen = () => {
			if (this.#socket !== socket) return;
			this.#attempt = 0;
			this.#lastSeq = -1;
			this.clock.reset();
			this.#pending.clear();
			const token = this.#opts.session?.load(this.#room);
			if (token) {
				this.#raw({ t: 'rejoin', room: this.#room, token });
			} else if (this.#join) {
				this.#raw({ t: 'join', room: this.#room, ...this.#join });
			}
			this.#setStatus('open');
			this.#startPings();
		};
		socket.onmessage = (ev) => {
			if (this.#socket !== socket) return;
			this.#onFrame(String(ev.data));
		};
		socket.onclose = (ev) => {
			if (this.#socket !== socket) return;
			this.#socket = null;
			this.#onClosed(ev.code);
		};
		socket.onerror = () => {
			/* onclose follows */
		};
	}

	#raw(msg: Record<string, unknown>): void {
		this.#socket?.send(JSON.stringify({ ...msg, v: PROTOCOL_VERSION }));
	}

	#onFrame(raw: string): void {
		let msg: ServerMessage;
		try {
			msg = JSON.parse(raw) as ServerMessage;
		} catch {
			return;
		}
		if (msg.t === 'pong') {
			const sentAt = this.#pending.get(msg.n);
			if (sentAt !== undefined) {
				this.#pending.delete(msg.n);
				this.clock.addPong(sentAt, this.#now, msg.server_time);
			}
			return;
		}
		if (msg.t === 'welcome') {
			this.#opts.session?.save(this.#room, msg.token);
		}
		if (msg.t === 'snapshot') {
			this.#lastSeq = msg.seq;
			this.#gotSnapshot = true;
		} else if (SEQUENCED.has(msg.t) && this.#gotSnapshot) {
			const seq = (msg as { seq: number }).seq;
			if (seq > this.#lastSeq + 1) {
				// We missed at least one event: resynchronise from a fresh snapshot.
				this.reconnectNow();
				return;
			}
			this.#lastSeq = Math.max(this.#lastSeq, seq);
		}
		if (msg.t === 'error') {
			if (msg.code === 'bad_token') {
				// Session expired: forget it and join again as a new player.
				this.#opts.session?.clear(this.#room);
				if (this.#join) this.#raw({ t: 'join', room: this.#room, ...this.#join });
				return;
			}
			if (FATAL.has(msg.code) || (!this.#gotSnapshot && FATAL_WHILE_JOINING.has(msg.code))) {
				this.#stopped = true;
				this.#opts.onMessage(msg);
				this.#opts.onFatal(msg.code);
				return;
			}
		}
		this.#opts.onMessage(msg);
	}

	#onClosed(code: number): void {
		this.#clearTimers();
		if (this.#stopped) {
			this.#setStatus('closed');
			return;
		}
		if (code === 4404 || code === 4403 || code === 4401) {
			if (code === 4401) this.#opts.session?.clear(this.#room);
			else {
				this.#stopped = true;
				this.#opts.onFatal(code === 4404 ? 'room_not_found' : 'kicked');
				this.#setStatus('closed');
				return;
			}
		}
		const random = this.#opts.random ?? Math.random;
		const delay =
			code === 1012 ? 1500 + Math.round(random() * 1500) : backoffDelay(this.#attempt, random);
		this.#attempt += 1;
		this.#setStatus('reconnecting', delay);
		this.#timer(() => {
			this.#open();
		}, delay);
	}

	#startPings(): void {
		// 8 quick pings to estimate the clock, then one every 5 s (also keeps the server heartbeat happy).
		let burst = 0;
		const tick = () => {
			if (!this.isOpen) return;
			this.#sendPing();
			burst += 1;
			this.#timer(tick, burst < 8 ? 120 : 5000);
		};
		tick();
	}

	#sendPing(): void {
		const n = ++this.#pingN;
		const t0 = this.#now;
		this.#pending.set(n, t0);
		if (this.#pending.size > 20) this.#pending.delete(this.#pending.keys().next().value as number);
		this.#raw({ t: 'ping', n, t0 });
	}
}
