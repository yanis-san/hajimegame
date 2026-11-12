import type { Component } from 'svelte';
import type { MessageKey } from '#lib/i18n/index.ts';
import BombStats from './bomb/BombStats.svelte';
import type { GameId } from './registry.ts';

/** Each game's statistics dashboard, and its name as shown in a game picker. A new game adds its entry here. */
export const STATS_VIEWS: Record<GameId, Component> = { bomb: BombStats };
export const GAME_NAMES: Record<GameId, MessageKey> = { bomb: 'games.bomb.name' };
