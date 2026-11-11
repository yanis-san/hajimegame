// Screenshots of the home page (full page height) and the lobby.   node scripts/home.mjs
import { chromium, devices } from '@playwright/test';

const b = await chromium.launch();
const profiles = [
	['mobile', { ...devices['iPhone 13'], locale: 'fr-FR' }],
	['desktop', { viewport: { width: 1600, height: 900 }, locale: 'fr-FR' }]
];
const out = (n) => new URL(`../.shots/${n}.png`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
for (const [name, options] of profiles) {
	const p = await (await b.newContext(options)).newPage();
	await p.goto('http://localhost:5173/');
	await p.waitForLoadState('networkidle');
	await p.waitForTimeout(600);
	await p.screenshot({ path: out(`${name}-01-home`), fullPage: true });
	await p.getByLabel('Ton pseudo').fill('Yanis');
	await p.getByRole('button', { name: 'Créer une partie' }).click();
	await p.waitForURL(/\/r\//);
	await p.getByRole('button', { name: 'Lancer la partie' }).waitFor();
	await p.waitForTimeout(600);
	await p.screenshot({ path: out(`${name}-02-lobby`) });
}
await b.close();
