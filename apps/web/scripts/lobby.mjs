// Lobby of a Shiritori room, desktop and mobile.   node scripts/lobby.mjs
import { chromium, devices } from '@playwright/test';
const b = await chromium.launch();
for (const [name, o] of [
	['desktop', { viewport: { width: 1440, height: 780 }, locale: 'fr-FR' }],
	['mobile', { ...devices['iPhone 13'], locale: 'fr-FR' }]
]) {
	const p = await (await b.newContext(o)).newPage();
	await p.goto('http://localhost:5173/');
	await p.waitForLoadState('networkidle');
	await p.getByLabel('Ton pseudo').fill('Yanis');
	await p.getByRole('radio', { name: /Shiritori/ }).click();
	await p.getByRole('button', { name: 'Créer une partie' }).click();
	await p.waitForURL(/\/r\//);
	await p.getByRole('button', { name: 'Lancer la partie' }).waitFor();
	await p.waitForTimeout(600);
	await p.screenshot({
		path: new URL(`../.shots/${name}-02-lobby-shiritori.png`, import.meta.url).pathname.replace(
			/^\/([A-Za-z]:)/,
			'$1'
		)
	});
}
await b.close();
