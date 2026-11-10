// Visual check of an accepted word with its meaning. Needs the game running and e2e/.cache/answers.json
// (created by `pnpm e2e`).  node scripts/accepted.mjs
import { chromium, devices } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const answers = JSON.parse(
	readFileSync(new URL('../e2e/.cache/answers.json', import.meta.url), 'utf8')
);
const out = new URL('../.shots/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
mkdirSync(out, { recursive: true });

const profiles = {
	mobile: { ...devices['iPhone 13'], locale: 'fr-FR' },
	desktop: { viewport: { width: 1280, height: 800 }, locale: 'fr-FR' }
};
const browser = await chromium.launch();
for (const [name, options] of Object.entries(profiles)) {
	const a = await (await browser.newContext(options)).newPage();
	const b = await (await browser.newContext(options)).newPage();
	await a.goto(BASE);
	await a.waitForLoadState('networkidle');
	await a.getByLabel('Ton pseudo').fill('Yanis');
	await a.getByRole('button', { name: 'Créer une partie' }).click();
	await a.waitForURL(/\/r\//);
	await a.getByRole('radio', { name: '5', exact: true }).first().click();
	const code = a.url().split('/r/')[1];
	await b.goto(`${BASE}/r/${code}`);
	await b.waitForLoadState('networkidle');
	await b.getByLabel('Ton pseudo').fill('Aya');
	await b.getByRole('button', { name: 'Entrer' }).click();
	await b.getByRole('button', { name: 'Pas prêt' }).click();
	await a.waitForTimeout(600);
	await a.getByRole('button', { name: 'Lancer la partie' }).click();
	await a.locator('.game').waitFor({ timeout: 15000 });
	const used = new Set();
	for (let round = 0; round < 3; round++) {
		await a.waitForTimeout(700);
		const active =
			(await a.getByLabel('Un mot avec').getAttribute('placeholder')) === 'À toi !' ? a : b;
		const fragment = (await active.locator('.plaque .kana').innerText()).trim();
		const word = (answers[fragment] ?? []).find((w) => !used.has(w));
		used.add(word);
		const input = active.getByLabel('Un mot avec');
		await input.pressSequentially(word, { delay: 20 });
		await input.press('Enter');
		await a.locator('.lastcard').first().waitFor();
		await a.waitForTimeout(900);
	}
	await a.screenshot({ path: `${out}${name}-14-accepted.png` });
	console.log('shot', name);
}
await browser.close();
