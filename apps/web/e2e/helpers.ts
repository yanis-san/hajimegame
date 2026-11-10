import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Browser, BrowserContext, Page } from '@playwright/test';

const answers: Record<string, string[]> = JSON.parse(
	readFileSync(path.resolve(import.meta.dirname, '.cache/answers.json'), 'utf8')
);

export function answerFor(fragment: string, used: Set<string>): string {
	const word = (answers[fragment] ?? []).find((w) => !used.has(w));
	if (!word) throw new Error(`no answer for ${fragment}`);
	used.add(word);
	return word;
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
	await player.page.getByRole('button', { name: 'Pas prêt' }).waitFor();
}
