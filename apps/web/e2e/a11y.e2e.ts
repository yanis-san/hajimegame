import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { createRoom, joinRoom, newPlayer } from './helpers';

async function serious(page: Page) {
	const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
	return result.violations
		.filter((v) => v.impact === 'critical' || v.impact === 'serious')
		.map((v) => ({
			id: v.id,
			impact: v.impact,
			nodes: v.nodes.map((n) => n.target.join(' ')).slice(0, 4)
		}));
}

for (const path of ['/', '/credits', '/design']) {
	test(`no serious accessibility violation on ${path}`, async ({ page }) => {
		await page.goto(path);
		await page.waitForLoadState('networkidle');
		expect(await serious(page)).toEqual([]);
	});
}

test('no serious accessibility violation in the lobby and in a game', async ({ browser }) => {
	const host = await newPlayer(browser, 'Yanis');
	const guest = await newPlayer(browser, 'Aya');
	const code = await createRoom(host);
	expect(await serious(host.page)).toEqual([]);
	await joinRoom(guest, code);
	await guest.page.getByRole('button', { name: 'Je suis prêt' }).click();
	await host.page.getByRole('button', { name: 'Lancer la partie' }).click();
	await expect(host.page.locator('.game')).toBeVisible({ timeout: 15_000 });
	expect(await serious(host.page)).toEqual([]);
	await host.context.close();
	await guest.context.close();
});
