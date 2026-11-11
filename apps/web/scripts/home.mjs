// Screenshots of the home page with Shiritori selected.   node scripts/home.mjs
import { chromium, devices } from '@playwright/test';

const b = await chromium.launch();
const profiles = [
	['mobile', { ...devices['iPhone 13'], locale: 'fr-FR' }],
	['desktop', { viewport: { width: 1280, height: 800 }, locale: 'fr-FR' }]
];
for (const [name, options] of profiles) {
	const p = await (await b.newContext(options)).newPage();
	await p.goto('http://localhost:5173/');
	await p.waitForLoadState('networkidle');
	await p.getByRole('radio', { name: /Shiritori/ }).click();
	await p.waitForTimeout(500);
	const target = new URL(`../.shots/${name}-01-home-shiritori.png`, import.meta.url);
	await p.getByRole('radio', { name: /Shiritori/ }).scrollIntoViewIfNeeded();
	await p.screenshot({ path: target.pathname.replace(/^\/([A-Za-z]:)/, '$1') });
}
await b.close();
