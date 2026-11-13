import { expect, test } from '@playwright/test';
import { answerFor, createRoom, joinRoom, newPlayer } from './helpers';

test('timed game: choose a duration, see the clock, an explosion takes points and keeps everyone in', async ({
	browser
}) => {
	test.setTimeout(90_000);
	const host = await newPlayer(browser, 'Yanis');
	const guest = await newPlayer(browser, 'Aya');
	const code = await createRoom(host);

	// no clock by default: lives are offered; with a duration they are not (nobody is eliminated)
	const lives = host.page.getByRole('radiogroup', { name: 'Vies' });
	await expect(lives).toBeVisible();
	await host.page.getByRole('radio', { name: '2 min' }).click();
	await expect(lives).toHaveCount(0);
	await expect(host.page.getByText('une explosion fait perdre 10 points')).toBeVisible();
	await host.page.getByRole('radio', { name: '8 s' }).click(); // a short fuse: an explosion comes quickly

	await joinRoom(guest, code);
	await guest.page.getByRole('button', { name: 'Je suis prêt' }).click();
	await host.page.getByRole('button', { name: 'Lancer la partie' }).click();
	await expect(host.page.locator('.game')).toBeVisible({ timeout: 15_000 });
	await expect(guest.page.locator('.game')).toBeVisible();

	// the clock: about two minutes, counting down, for both players
	const clock = host.page.getByRole('timer', { name: 'Temps restant' });
	await expect(clock).toHaveText(/^(2:00|1:5\d)$/);
	const first = await clock.innerText();
	await expect(clock).not.toHaveText(first, { timeout: 5000 });
	await expect(guest.page.getByRole('timer', { name: 'Temps restant' })).toBeVisible();

	// nobody answers: the bomb explodes, nobody is eliminated, no hearts anywhere
	await expect(host.page.locator('.slot [data-player]')).toHaveCount(2);
	await host.page.waitForTimeout(9500);
	await expect(host.page.locator('.slot .gone')).toHaveCount(0);
	await expect(host.page.locator('.slot .lives')).toHaveCount(0);

	// a word still scores
	await host.page.waitForTimeout(300);
	const hostInput = host.page.getByLabel('Un mot avec');
	const active = (await hostInput.getAttribute('placeholder')) === 'À toi !' ? host : guest;
	const fragment = (await active.page.locator('.plaque .kana').innerText()).trim();
	const input = active.page.getByLabel('Un mot avec');
	await input.pressSequentially(answerFor(fragment, new Set()));
	await input.press('Enter');
	await expect(host.page.locator('.lastcard').first()).toBeVisible({ timeout: 5000 });
	await host.context.close();
	await guest.context.close();
});
