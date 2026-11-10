// Renders static/icon.svg to the PNG sizes a PWA and iOS need.
import { chromium } from '@playwright/test';
import { readFileSync } from 'node:fs';
const svg = readFileSync(new URL('../static/icon.svg', import.meta.url), 'utf8');
const browser = await chromium.launch();
for (const [name, size] of [
	['icon-192.png', 192],
	['icon-512.png', 512],
	['apple-touch-icon.png', 180]
]) {
	const page = await browser.newPage({ viewport: { width: size, height: size } });
	await page.setContent(
		`<body style="margin:0">${svg.replace('<svg ', `<svg width="${size}" height="${size}" `)}</body>`
	);
	await page.screenshot({
		path: new URL(`../static/${name}`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')
	});
	console.log('wrote', name);
}
await browser.close();
