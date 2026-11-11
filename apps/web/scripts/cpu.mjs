// Lobby with CPU players and the game against them.   BASE_URL=http://localhost:5273 node scripts/cpu.mjs
import { chromium, devices } from '@playwright/test';

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const b = await chromium.launch();
const out = (n) =>
	new URL(`../.shots/${n}.png`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
for (const [name, o] of [
	['desktop', { viewport: { width: 1440, height: 780 }, locale: 'fr-FR' }],
	['mobile', { ...devices['iPhone 13'], locale: 'fr-FR' }]
]) {
	const p = await (await b.newContext(o)).newPage();
	await p.goto(BASE + '/');
	await p.waitForLoadState('networkidle');
	await p.getByLabel('Ton pseudo').fill('Yanis');
	await p.getByRole('button', { name: 'Créer une partie' }).click();
	await p.waitForURL(/\/r\//);
	await p.getByRole('button', { name: 'Lancer la partie' }).waitFor();
	await p.getByRole('radio', { name: 'Difficile' }).click();
	for (let i = 0; i < 20; i++) {
		await p.getByRole('button', { name: 'Ajouter un CPU' }).click();
		if (await p.locator('.tag.cpu').count()) break;
		await p.waitForTimeout(1000);
	}
	await p.getByRole('radio', { name: 'Facile' }).click();
	await p.getByRole('button', { name: 'Ajouter un CPU' }).click();
	await p.waitForTimeout(500);
	await p.screenshot({ path: out(`${name}-20-lobby-cpu`), fullPage: name === 'mobile' });
	await p.getByRole('button', { name: 'Lancer la partie' }).click();
	await p.locator('.game').waitFor({ timeout: 15000 });
	await p.locator('.lastcard').waitFor({ timeout: 60000 });
	await p.waitForTimeout(800);
	await p.screenshot({ path: out(`${name}-21-game-cpu`) });
}
await b.close();
