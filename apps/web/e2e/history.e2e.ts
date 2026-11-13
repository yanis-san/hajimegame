import { expect, test } from '@playwright/test';
import { answerFor, asShown, createRoom, joinRoom, newPlayer } from './helpers';

test('a finished game can be reviewed with all its words, then found again in the history', async ({
	browser
}) => {
	const host = await newPlayer(browser, 'Yanis');
	const guest = await newPlayer(browser, 'Aya');
	const errors: string[] = [];
	for (const p of [host, guest]) {
		p.page.on('pageerror', (e) => errors.push(e.message));
		p.page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
	}
	const code = await createRoom(host);
	await host.page.getByRole('radio', { name: '1', exact: true }).first().click();
	await host.page.getByRole('radio', { name: '5 s', exact: true }).click();
	await joinRoom(guest, code);
	await guest.page.getByRole('button', { name: 'Je suis prêt' }).click();
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeEnabled();
	await host.page.getByRole('button', { name: 'Lancer la partie' }).click();
	await expect(host.page.locator('.game')).toBeVisible({ timeout: 15_000 });

	// whoever has the turn plays one word, then nobody answers and a bomb ends the game
	const hostInput = host.page.getByLabel('Un mot avec');
	await expect(hostInput).toHaveAttribute('placeholder', /.+/);
	const active = (await hostInput.getAttribute('placeholder')) === 'À toi !' ? host : guest;
	const fragment = (await active.page.locator('.plaque .kana').innerText()).trim();
	const word = answerFor(fragment, new Set());
	const input = active.page.getByLabel('Un mot avec');
	await input.pressSequentially(word);
	await input.press('Enter');
	await expect(host.page.locator('.lastcard').first()).toBeVisible({ timeout: 5000 });

	await expect
		.poll(
			() =>
				errors.length > 0 || host.page.getByRole('heading', { name: /gagne|Tu gagnes/ }).count(),
			{
				timeout: 60_000
			}
		)
		.toBeTruthy();
	expect(errors).toEqual([]);
	expect(errors).toEqual([]);
	await expect(host.page.getByText('Partie enregistrée dans ton historique')).toBeVisible();

	// "Revoir la partie" lists every word of the game with who played it
	await host.page.getByRole('button', { name: 'Revoir la partie' }).click();
	const dialog = host.page.getByRole('dialog');
	await expect(dialog.getByRole('heading', { name: 'Les mots de la partie' })).toBeVisible();
	await expect(dialog.getByText(asShown(word)).first()).toBeVisible();
	await expect(dialog.getByText(active.name)).toBeVisible();
	await host.page.keyboard.press('Escape');

	// reloading the results does not save the game a second time
	await host.page.reload();
	await expect(host.page.getByRole('heading', { name: /gagne|Tu gagnes/ })).toBeVisible();

	// the history page, reached from the home page, has that one game and reopens it
	await host.page.goto('/');
	await host.page.waitForLoadState('networkidle');
	await host.page.getByRole('link', { name: 'Historique des parties' }).click();
	await expect(host.page.getByRole('heading', { name: 'Historique' })).toBeVisible();
	await expect(host.page.locator('li.game')).toHaveCount(1);
	await expect(host.page.locator('li.game')).toContainText('1 mot');
	await host.page.getByRole('button', { name: 'Revoir', exact: true }).click();
	await expect(host.page.getByRole('dialog').getByText(asShown(word)).first()).toBeVisible();
	await host.page.keyboard.press('Escape');

	// deleting the game empties the page
	await host.page.getByRole('button', { name: 'Supprimer cette partie' }).click();
	await expect(host.page.getByText('Aucune partie pour l’instant', { exact: false })).toBeVisible();
	await host.context.close();
	await guest.context.close();
});

test('the history page speaks the language of its URL', async ({ page }) => {
	await page.goto('/ja/history');
	await expect(page.getByRole('heading', { name: '履歴' })).toBeVisible();
	await expect(page.getByText('まだ試合がありません', { exact: false })).toBeVisible();
	await expect(page.locator('body')).not.toContainText(/Historique|Aucune partie/);
	await page.goto('/en/history');
	await expect(page.getByRole('heading', { name: 'History' })).toBeVisible();
	await expect(page.getByText('No games yet', { exact: false })).toBeVisible();
});

test('clearing the whole history asks for confirmation first', async ({ page }) => {
	await page.goto('/');
	await page.evaluate(() => {
		const game = {
			id: 'ABCDEF:1:さくら:さくら:a5|b1',
			at: Date.now(),
			room: 'ABCDEF',
			you: 'a',
			mode: 'classic',
			players: [
				{ id: 'a', name: 'Yanis', avatar: 1, bot: false, place: 1, score: 5, words: 1 },
				{ id: 'b', name: 'Aya', avatar: 2, bot: false, place: 2, score: 1, words: 0 }
			],
			words: [
				{
					player_id: 'a',
					word: 'さくら',
					reading: 'さくら',
					turn: 1,
					meaning_fr: 'cerisier',
					meaning_en: 'cherry tree',
					example_ja: '桜が咲いた。',
					example_en: 'The cherry blossoms bloomed.',
					example_fr: 'Les cerisiers ont fleuri.'
				}
			]
		};
		localStorage.setItem('hajime:history:v1', JSON.stringify([game]));
	});
	await page.goto('/history');
	await expect(page.locator('li.game')).toHaveCount(1);
	await page.getByRole('button', { name: 'Revoir', exact: true }).click();
	const dialog = page.getByRole('dialog');
	await expect(dialog.getByText('cherry tree')).toBeVisible();
	await expect(dialog.getByText('桜が咲いた。')).toBeVisible();
	await expect(dialog.getByText('Les cerisiers ont fleuri.')).toBeVisible();
	await page.keyboard.press('Escape');

	await page.getByRole('button', { name: 'Tout effacer' }).click();
	await expect(
		page.getByRole('dialog').getByText('C’est définitif', { exact: false })
	).toBeVisible();
	await page.getByRole('button', { name: 'Annuler' }).click();
	await expect(page.locator('li.game')).toHaveCount(1);
	await page.getByRole('button', { name: 'Tout effacer' }).click();
	await page.getByRole('dialog').getByRole('button', { name: 'Tout effacer' }).click();
	await expect(page.locator('li.game')).toHaveCount(0);
	expect(await page.evaluate(() => localStorage.getItem('hajime:history:v1'))).toBeNull();
});
