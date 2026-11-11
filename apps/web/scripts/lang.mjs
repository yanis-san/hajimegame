// Home and lobby in English and Japanese.   BASE_URL=http://localhost:5273 node scripts/lang.mjs
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
	for (const [code, label] of [
		['en', 'Create a game'],
		['ja', 'ゲームを作る']
	]) {
		await p.locator('select').selectOption(code);
		await p.getByRole('button', { name: label }).waitFor();
		await p.screenshot({ path: out(`${name}-30-home-${code}`) });
	}
	await p.getByLabel('ニックネーム').fill('Yanis');
	await p.getByRole('button', { name: 'ゲームを作る' }).click();
	await p.waitForURL(/\/r\//);
	await p.getByRole('button', { name: 'ゲーム開始' }).waitFor();
	await p.getByRole('button', { name: 'CPUを追加' }).click();
	await p.waitForTimeout(600);
	await p.screenshot({ path: out(`${name}-31-lobby-ja`), fullPage: name === 'mobile' });
}
await b.close();
