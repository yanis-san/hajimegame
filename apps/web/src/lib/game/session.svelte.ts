import type { SetSettingsPatch } from './types';
import { GameClient, type JoinInfo } from './client';
import { sessionTokens } from './session';
import { GameStore } from './store.svelte';
import { wsUrl } from './config';
import { getGuestId } from './guest';
import { getLocale } from '#lib/i18n/index.ts';

/** Wires the websocket client to the reactive store and exposes the intents a player can send. */
export class GameSession {
	readonly store = new GameStore();
	readonly client: GameClient;
	readonly code: string;

	constructor(code: string) {
		this.code = code.toUpperCase();
		this.client = new GameClient({
			url: wsUrl,
			session: sessionTokens,
			onMessage: (msg) => this.store.apply(msg),
			onStatus: (status, detail) => {
				this.store.status = status;
				this.store.reconnectIn = detail?.delay ? Math.ceil(detail.delay / 1000) : 0;
			},
			onFatal: (code) => {
				this.store.fatal = code;
			}
		});
	}

	connect(join: JoinInfo): void {
		this.store.reset();
		// A spectator is not recorded, so nothing identifying is sent for one.
		const identity = join.spectator ? {} : { guest_id: getGuestId(), lang: getLocale() };
		this.client.connect(this.code, { ...join, ...identity });
	}

	ready(ready: boolean): void {
		this.client.send({ t: 'ready', ready });
	}

	start(): void {
		this.client.send({ t: 'start' });
	}

	settings(patch: SetSettingsPatch): void {
		this.client.send({ t: 'settings', ...patch });
	}

	submit(text: string): void {
		this.client.send({ t: 'submit', text });
	}

	typing(text: string): void {
		this.client.send({ t: 'typing', text });
	}

	addBot(difficulty: 'easy' | 'normal' | 'hard'): void {
		this.client.send({ t: 'add_bot', difficulty });
	}

	removeBot(playerId: string): void {
		this.client.send({ t: 'remove_bot', player_id: playerId });
	}

	kick(playerId: string): void {
		this.client.send({ t: 'kick', player_id: playerId });
	}

	chat(text: string): void {
		this.client.send({ t: 'chat', text });
	}

	rematch(): void {
		this.client.send({ t: 'rematch' });
	}

	leave(): void {
		this.client.leave();
	}

	destroy(): void {
		this.client.close();
	}
}
