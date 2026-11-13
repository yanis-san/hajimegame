import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Browser, BrowserContext, Page } from '@playwright/test';

const tables: {
	contains: Record<string, string[]>;
	starts: Record<string, string[]>;
	nends: Record<string, string[]>;
	kanji: Record<string, string[]>;
} = JSON.parse(readFileSync(path.resolve(import.meta.dirname, '.cache/answers.json'), 'utf8'));

/** A word (in hiragana) written with the kanji, for the kanji mode. */
export function wordWithKanji(kanji: string): string {
	const word = tables.kanji[kanji]?.[0];
	if (!word) throw new Error(`no word for the kanji ${kanji}`);
	return word;
}

export function answerFor(fragment: string, used: Set<string>, shiritori = false): string {
	const table = shiritori ? tables.starts : tables.contains;
	const word = (table[fragment] ?? []).find((w) => !used.has(w));
	if (!word) throw new Error(`no answer for ${fragment}`);
	used.add(word);
	return word;
}

/**
 * A word as it can appear on screen: the game compares kana as hiragana but shows a word that the dictionary writes
 * in katakana (フィッシュ) in katakana, so a test that typed ふぃっしゅ looks for either spelling.
 */
export function asShown(word: string): RegExp {
	const katakana = [...word]
		.map((c) => (c >= 'ぁ' && c <= 'ゖ' ? String.fromCharCode(c.charCodeAt(0) + 0x60) : c))
		.join('');
	return new RegExp(`^(${word}|${katakana})$`);
}

export interface Player {
	page: Page;
	context: BrowserContext;
	name: string;
}

export async function newPlayer(
	browser: Browser,
	name: string,
	options: object = {}
): Promise<Player> {
	const context = await browser.newContext({ locale: 'fr-FR', ...options });
	const page = await context.newPage();
	return { page, context, name };
}

/** Create a room as the host. Waiting for network idle makes sure the page is hydrated before we click. */
export async function createRoom(host: Player): Promise<string> {
	await host.page.goto('/');
	await host.page.waitForLoadState('networkidle');
	await host.page.getByLabel('Ton pseudo').fill(host.name);
	await host.page.getByRole('button', { name: 'Créer une partie' }).click();
	await host.page.waitForURL(/\/r\/[A-Z0-9]{6}/);
	await host.page.getByRole('button', { name: 'Lancer la partie' }).waitFor();
	return host.page.url().split('/r/')[1];
}

export async function joinRoom(player: Player, code: string): Promise<void> {
	await player.page.goto(`/r/${code}`);
	await player.page.waitForLoadState('networkidle');
	await player.page.getByLabel('Ton pseudo').fill(player.name);
	await player.page.getByRole('button', { name: 'Entrer' }).click();
	await player.page.getByRole('button', { name: 'Je suis prêt' }).waitFor();
}

/** A word starting with `first` and ending in ん (for the shiritori penalty option). */
export function wordEndingInN(first: string): string {
	const word = tables.nends[first]?.[0];
	if (!word) throw new Error(`no word starting with ${first} and ending in n`);
	return word;
}
