// Visual review tool: plays a real game in two browser contexts and saves screenshots of every screen.
//   node scripts/shots.mjs            (needs the game server on :8000 and the web app on :5173)
// Output: apps/web/.shots/<profile>-<step>.png
import { chromium, devices } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const OUT = new URL('../.shots/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
mkdirSync(OUT, { recursive: true });

const profiles = {
	mobile: { ...devices['iPhone 13'], locale: 'fr-FR' },
	desktop: { viewport: { width: 1280, height: 800 }, locale: 'fr-FR' }
};

async function shot(page, profile, name, full = false) {
	await page.waitForTimeout(350);
	await page.screenshot({ path: `${OUT}${profile}-${name}.png`, fullPage: full });
	console.log('shot', profile, name);
}

async function run(profile) {
	const browser = await chromium.launch();
	const host = await browser.newContext(profiles[profile]);
	const guest = await browser.newContext(profiles[profile]);
	const errors = [];
	const hostPage = await host.newPage();
	const guestPage = await guest.newPage();
	for (const [who, p] of [
		['host', hostPage],
		['guest', guestPage]
	]) {
		p.on('console', (m) => m.type() === 'error' && errors.push(`${who}: ${m.text()}`));
		p.on('pageerror', (e) => errors.push(`${who} pageerror: ${e.message}`));
	}

	await hostPage.goto(BASE + '/');
	await hostPage.waitForLoadState('networkidle');
	await shot(hostPage, profile, '01-home');
	await hostPage.getByLabel('Ton pseudo').fill('Yanis');
	await hostPage.getByRole('button', { name: 'Créer une partie' }).click();
	await hostPage.waitForURL(/\/r\//);
	await hostPage
		.getByText('Salle d’attente')
		.or(hostPage.getByRole('button', { name: 'Lancer la partie' }))
		.first()
		.waitFor();
	const code = hostPage.url().split('/r/')[1];
	await shot(hostPage, profile, '02-lobby-host', true);

	// settings: one life and a short fuse so the game ends quickly
	await hostPage.getByRole('radio', { name: '1', exact: true }).first().click();
	await hostPage.getByRole('radio', { name: '5 s', exact: true }).click();

	await guestPage.goto(`${BASE}/r/${code}`);
	await guestPage.waitForLoadState('networkidle');
	await shot(guestPage, profile, '03-join-card');
	await guestPage.getByLabel('Ton pseudo').fill('Aya');
	await guestPage.getByRole('button', { name: 'Entrer' }).click();
	await guestPage.getByRole('button', { name: 'Pas prêt' }).waitFor();
	await guestPage.getByRole('button', { name: 'Pas prêt' }).click();
	await shot(guestPage, profile, '04-lobby-guest', true);
	await hostPage.getByRole('button', { name: 'Lancer la partie' }).waitFor();
	await hostPage.waitForFunction(
		() => !document.querySelector('button[disabled]:not([aria-label])') || true
	);
	await hostPage.waitForTimeout(500);
	await hostPage.getByRole('button', { name: 'Lancer la partie' }).click();
	await hostPage.waitForTimeout(900);
	await shot(hostPage, profile, '05-countdown');
	await hostPage.locator('.game').waitFor({ timeout: 10000 });
	await shot(hostPage, profile, '06-game-a');
	await shot(guestPage, profile, '06-game-b');

	// type something on whichever screen has the active turn
	for (const p of [hostPage, guestPage]) {
		const input = p.getByLabel('Un mot avec');
		if (await input.isEnabled()) {
			await input.pressSequentially('zzzz', { delay: 30 });
			await input.press('Enter');
			await shot(p, profile, '07-rejected');
			break;
		}
	}
	await hostPage.waitForTimeout(5500);
	await shot(hostPage, profile, '08-after-explosion');
	await hostPage.getByText('Résultats').first().waitFor({ timeout: 30000 });
	await hostPage.waitForTimeout(2200);
	await shot(hostPage, profile, '09-results');

	console.log(profile, 'console errors:', errors.length ? errors : 'none');
	await browser.close();
}

const only = process.argv[2];
for (const profile of Object.keys(profiles)) {
	if (!only || only === profile) await run(profile);
}

// stand-alone pages
const browser = await chromium.launch();
for (const [profile, options] of Object.entries(profiles)) {
	const ctx = await browser.newContext(options);
	const page = await ctx.newPage();
	await page.goto(BASE + '/design');
	await shot(page, profile, '10-design', true);
	await page.goto(BASE + '/credits');
	await shot(page, profile, '11-credits');
	await page.goto(BASE + '/r/ZZZZZZ');
	await page.getByLabel('Ton pseudo').fill('Test');
	await page.getByRole('button', { name: 'Entrer' }).click();
	await page.waitForTimeout(1200);
	await shot(page, profile, '12-room-not-found');
	await page.goto(BASE + '/nope');
	await shot(page, profile, '13-404');
	await ctx.close();
}
await browser.close();
