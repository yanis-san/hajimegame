import type {
	PlayerView,
	RejectCode,
	ResultRow,
	RoomPhase,
	ServerMessage,
	SettingsView,
	TurnView,
	WordView
} from '@hajime/protocol';
import type { ConnectionStatus } from './client';

export interface GameEvent {
	/** Monotonic id so components can react to each event exactly once. */
	id: number;
}

export interface AcceptedEvent extends GameEvent {
	playerId: string;
	word: string;
	reading: string;
	gain: number;
	meaning_fr: string;
	meaning_en: string;
	example_ja: string;
	example_en: string;
	example_fr: string;
}
export interface RejectedEvent extends GameEvent {
	reason: RejectCode;
	text: string;
}
export interface ExplosionEvent extends GameEvent {
	playerId: string;
	lives: number;
	cause: 'timeout' | 'n_ending';
}
export interface EliminationEvent extends GameEvent {
	playerId: string;
	place: number;
}
export interface ChatLine {
	id: number;
	playerId: string;
	name: string;
	text: string;
}

const DEFAULT_SETTINGS: SettingsView = {
	lives: 3,
	fuse_seconds: 10,
	mode: 'classic',
	max_players: 8,
	bonus_kana: false,
	n_penalty: false,
	levels: [5, 4]
};

/** Reactive game state. The server is authoritative: this class only mirrors what it sends. */
export class GameStore {
	status = $state<ConnectionStatus>('idle');
	reconnectIn = $state(0);
	fatal = $state<string | null>(null);

	room = $state('');
	you = $state('');
	spectator = $state(false);
	host = $state('');
	phase = $state<RoomPhase>('lobby');
	settings = $state<SettingsView>({ ...DEFAULT_SETTINGS });
	players = $state<PlayerView[]>([]);
	spectators = $state(0);
	turn = $state<TurnView | null>(null);
	typing = $state('');
	words = $state<WordView[]>([]);
	results = $state<ResultRow[] | null>(null);
	countdownEnds = $state<number | null>(null);
	chat = $state<ChatLine[]>([]);
	loaded = $state(false);
	lastError = $state<{ code: string; id: number } | null>(null);

	accepted = $state<AcceptedEvent | null>(null);
	rejected = $state<RejectedEvent | null>(null);
	explosion = $state<ExplosionEvent | null>(null);
	elimination = $state<EliminationEvent | null>(null);
	winnerId = $state<string | null>(null);

	#eventId = 0;

	me = $derived(this.players.find((p) => p.id === this.you) ?? null);
	isHost = $derived(this.host === this.you && !this.spectator);
	activePlayer = $derived(this.players.find((p) => p.id === this.turn?.player_id) ?? null);
	isMyTurn = $derived(this.phase === 'playing' && this.turn?.player_id === this.you);
	alivePlayers = $derived(this.players.filter((p) => p.alive));
	canStart = $derived(
		this.isHost &&
			this.players.filter((p) => p.connected).length >= 2 &&
			this.players.every((p) => p.host || !p.connected || p.ready)
	);

	#id(): number {
		return ++this.#eventId;
	}

	player(id: string): PlayerView | undefined {
		return this.players.find((p) => p.id === id);
	}

	reset(): void {
		this.loaded = false;
		this.fatal = null;
		this.players = [];
		this.turn = null;
		this.typing = '';
		this.words = [];
		this.results = null;
		this.chat = [];
		this.phase = 'lobby';
		this.countdownEnds = null;
		this.winnerId = null;
	}

	apply(msg: ServerMessage): void {
		switch (msg.t) {
			case 'welcome':
				this.you = msg.player_id;
				this.spectator = msg.spectator;
				break;
			case 'snapshot':
				this.room = msg.room;
				this.you = msg.you;
				this.spectator = msg.spectator;
				this.host = msg.host;
				this.phase = msg.phase;
				this.settings = msg.settings;
				this.players = msg.players;
				this.spectators = msg.spectators;
				this.turn = msg.turn;
				this.typing = msg.typing;
				this.words = msg.words;
				this.results = msg.results;
				this.countdownEnds = msg.countdown_ends;
				this.winnerId = msg.results?.find((r) => r.place === 1)?.player_id ?? null;
				this.loaded = true;
				break;
			case 'patch':
				if (msg.players) this.#mergePlayers(msg.players);
				if (msg.host !== undefined) this.host = msg.host;
				if (msg.phase !== undefined) this.#setPhase(msg.phase);
				if (msg.settings) this.settings = msg.settings;
				if (msg.spectators !== undefined) this.spectators = msg.spectators;
				if (msg.countdown_ends !== undefined) this.countdownEnds = msg.countdown_ends;
				break;
			case 'countdown':
				this.countdownEnds = msg.ends_at;
				break;
			case 'turn':
				this.turn = {
					turn: msg.turn,
					player_id: msg.player_id,
					fragment: msg.fragment,
					deadline: msg.deadline,
					fuse_ms: msg.fuse_ms
				};
				this.typing = '';
				break;
			case 'typing':
				if (msg.player_id === this.turn?.player_id) this.typing = msg.text;
				break;
			case 'accepted':
				this.#patchPlayer(msg.player_id, { score: msg.score });
				this.words = [
					...this.words.slice(-39),
					{
						player_id: msg.player_id,
						word: msg.word,
						reading: msg.reading,
						turn: msg.turn,
						meaning_fr: msg.meaning_fr,
						meaning_en: msg.meaning_en,
						example_ja: msg.example_ja,
						example_en: msg.example_en,
						example_fr: msg.example_fr
					}
				];
				this.accepted = {
					id: this.#id(),
					playerId: msg.player_id,
					word: msg.word,
					reading: msg.reading,
					gain: msg.score_gain,
					meaning_fr: msg.meaning_fr,
					meaning_en: msg.meaning_en,
					example_ja: msg.example_ja,
					example_en: msg.example_en,
					example_fr: msg.example_fr
				};
				break;
			case 'rejected':
				this.rejected = { id: this.#id(), reason: msg.reason, text: msg.text };
				break;
			case 'explosion':
				this.#patchPlayer(msg.player_id, { lives: msg.lives });
				this.explosion = {
					id: this.#id(),
					playerId: msg.player_id,
					lives: msg.lives,
					cause: msg.cause
				};
				break;
			case 'elimination':
				this.#patchPlayer(msg.player_id, { alive: false, lives: 0 });
				this.elimination = { id: this.#id(), playerId: msg.player_id, place: msg.place };
				break;
			case 'life':
				this.#patchPlayer(msg.player_id, { lives: msg.lives });
				break;
			case 'bonus':
				this.#patchPlayer(msg.player_id, { bonus: msg.remaining });
				break;
			case 'game_over':
				this.results = msg.results;
				this.words = msg.words; // the whole game, for the review
				this.winnerId = msg.winner_id;
				this.turn = null;
				break;
			case 'chat':
				this.chat = [
					...this.chat.slice(-49),
					{ id: this.#id(), playerId: msg.player_id, name: msg.name, text: msg.text }
				];
				break;
			case 'error':
				this.lastError = { code: msg.code, id: this.#id() };
				break;
			case 'pong':
				break;
		}
	}

	#setPhase(phase: RoomPhase): void {
		if (phase === 'lobby') {
			this.results = null;
			this.turn = null;
			this.words = [];
			this.winnerId = null;
			this.typing = '';
		}
		this.phase = phase;
	}

	#mergePlayers(changes: Record<string, PlayerView | null>): void {
		let next = this.players;
		for (const [id, view] of Object.entries(changes)) {
			if (view === null) {
				next = next.filter((p) => p.id !== id);
			} else if (next.some((p) => p.id === id)) {
				next = next.map((p) => (p.id === id ? view : p));
			} else {
				next = [...next, view];
			}
		}
		this.players = next;
	}

	#patchPlayer(id: string, change: Partial<PlayerView>): void {
		this.players = this.players.map((p) => (p.id === id ? { ...p, ...change } : p));
	}
}
