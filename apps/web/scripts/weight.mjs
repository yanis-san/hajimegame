// Measures the compressed JavaScript the browser downloads for a page (target: home < 150 KB).
import { chromium } from '@playwright/test';
import { gzipSync } from 'node:zlib';
const url = process.argv[2] ?? 'http://localhost:4173/';
const browser = await chromium.launch();
const page = await browser.newPage();
let total = 0;
page.on('response', async (r) => {
	if ((r.headers()['content-type'] ?? '').includes('javascript'))
		total += gzipSync(await r.body()).length;
});
await page.goto(url, { waitUntil: 'networkidle' });
console.log(`${url} JS gzip: ${(total / 1024).toFixed(1)} KiB`);
await browser.close();
