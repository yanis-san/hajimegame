// Home page on short desktop windows (13 inch laptops).   node scripts/laptop.mjs
import { chromium } from '@playwright/test';
const b = await chromium.launch();
for (const [w, h] of [[1280, 560], [1280, 600], [1366, 650], [1440, 720], [1440, 780], [1536, 864]]) {
	const p = await (await b.newContext({ viewport: { width: w, height: h }, locale: 'fr-FR' })).newPage();
	await p.goto('http://localhost:5173/');
	await p.waitForLoadState('networkidle');
	await p.waitForTimeout(500);
	const overflow = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight);
	console.log(`${w}x${h}: page taller than the window by ${overflow}px`);
	await p.screenshot({ path: new URL(`../.shots/laptop-${w}x${h}.png`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1') });
}
await b.close();
