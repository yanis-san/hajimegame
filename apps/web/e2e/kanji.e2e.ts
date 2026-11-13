import { expect, test } from '@playwright/test';
import { joinRoom, newPlayer, wordWithKanji } from './helpers';

test('kanji mode: choose the levels, get a kanji, a word written with it is accepted', async ({
	browser
}) => {
	test.setTimeout(90_000);
	const host = await newPlayer(browser, 'Yanis');
	const guest = await newPlayer(browser, 'Aya');
	await host.page.goto('/');
	await host.page.waitForLoadState('networkidle');
	await host.page.getByLabel('Ton pseudo').fill('Yanis');
	await host.page.getByRole('radio', { name: /Kanji Bombe/ }).click();
	await host.page.getByRole('button', { name: 'Créer une partie' }).click();
	await host.page.waitForURL(/\/r\/[A-Z0-9]{6}/);
	await host.page.getByRole('button', { name: 'Lancer la partie' }).waitFor();
	const code = host.page.url().split('/r/')[1];
	await expect(host.page.locator('.modeline')).toContainText('Kanji Bombe');

	// the levels: N5 and N4 by default; only N5 once N4 is off; the last one cannot be switched off
	const levels = host.page.getByRole('group', { name: 'Niveaux JLPT' });
	await expect(levels.getByRole('switch', { name: 'N5' })).toHaveAttribute('aria-checked', 'true');
	await expect(levels.getByRole('switch', { name: 'N4' })).toHaveAttribute('aria-checked', 'true');
	await expect(levels.getByRole('switch', { name: 'N1' })).toHaveAttribute('aria-checked', 'false');
	await levels.getByRole('switch', { name: 'N4' }).click();
	await expect(levels.getByRole('switch', { name: 'N4' })).toHaveAttribute('aria-checked', 'false');
	await levels.getByRole('switch', { name: 'N5' }).click(); // refused: it is the last one
	await expect(levels.getByRole('switch', { name: 'N5' })).toHaveAttribute('aria-checked', 'true');
	await expect(host.page.getByText('Vie bonus')).toHaveCount(0); // a kana bonus makes no sense here

	await joinRoom(guest, code);
	await expect(guest.page.locator('.modeline')).toContainText('Kanji Bombe');
	await guest.page.getByRole('button', { name: 'Pas prêt' }).click();
	await host.page.getByRole('button', { name: 'Lancer la partie' }).click();
	await expect(host.page.locator('.game')).toBeVisible({ timeout: 15_000 });

	for (let round = 0; round < 2; round++) {
		await host.page.waitForTimeout(700);
		const hostInput = host.page.getByLabel('Un mot avec le kanji');
		const active = (await hostInput.getAttribute('placeholder')) === 'À toi !' ? host : guest;
		const kanji = (await active.page.locator('.plaque .kana').innerText()).trim();
		expect(kanji).toMatch(/^\p{Script=Han}$/u); // one kanji on the tag
		const input = active.page.getByLabel('Un mot avec le kanji');
		if (round === 0) {
			// a word that exists but is not written with this kanji is refused, with the kanji named
			await input.pressSequentially('ねこ');
			await input.press('Enter');
			await expect(active.page.getByRole('alert')).toContainText(`« ${kanji} »`);
			await input.fill('');
		}
		await input.pressSequentially(wordWithKanji(kanji));
		await input.press('Enter');
		await expect(host.page.locator('.lastcard').first()).toBeVisible({ timeout: 5000 });
		// the other player now has a different turn
		await expect(host.page.locator('.plaque .kana')).not.toHaveText(kanji, { timeout: 5000 });
	}
	await host.context.close();
	await guest.context.close();
});
