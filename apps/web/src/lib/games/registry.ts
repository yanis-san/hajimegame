import type { BombStatsView } from '@hajime/protocol';

/**
 * The games the site offers. A game lives in its own folder under `src/lib/games/<game>/` and is registered here and
 * in `stats.ts`; nothing outside its folder and these two files needs to know it exists. The server has the same
 * list (`app/api/games`).
 */
export const GAME_IDS = ['bomb'] as const;
export type GameId = (typeof GAME_IDS)[number];

export const isGameId = (value: string): value is GameId =>
	(GAME_IDS as readonly string[]).includes(value);

/** What each game's statistics endpoint returns (`GET /api/me/stats/{game}`). */
export interface StatsByGame {
	bomb: BombStatsView;
}
