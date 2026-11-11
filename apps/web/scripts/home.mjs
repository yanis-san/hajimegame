import { chromium, devices } from '@playwright/test';
const b = await chromium.launch();
for (const [name, o] of [
	['mobile', { ...devices['iPhone 13'], locale: 'fr-FR' }],
	['desktop', { viewport: { width: 1280, height: 800 }, locale: 'fr-FR' }]
]) {
	const p = await (await b.newContext(o)).newPage();
	await p.goto('http://localhost:5173/');
	await p.waitForLoadState('networkidle');
	await p.waitForTimeout(800);
	await p.screenshot({
		path: new URL(`../.shots/${name}-01-home.png`, import.meta.url).pathname.replace(
			/^\/([A-Za-z]:)/,
			'$1'
		),
		fullPage: true
	});
}
await b.close();
