import { expect, test } from '@playwright/test';
import { answerFor, createRoom, joinRoom, newPlayer } from './helpers';

test('two players play a full game: refused word, accepted word, reload mid-game, rematch', async ({
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
	await expect(host.page.getByText('Aya').first()).toBeVisible();

	// the host cannot start until the guest is ready
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeDisabled();
	await guest.page.getByRole('button', { name: 'Pas prêt' }).click();
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeEnabled();
	await host.page.getByRole('button', { name: 'Lancer la partie' }).click();

	await expect(host.page.locator('.game')).toBeVisible({ timeout: 15_000 });
	await expect(guest.page.locator('.game')).toBeVisible();

	// the input placeholder says "À toi !" only for the active player
	const hostInput = host.page.getByLabel('Un mot avec');
	await expect(hostInput).toHaveAttribute('placeholder', /.+/);
	const active = (await hostInput.getAttribute('placeholder')) === 'À toi !' ? host : guest;
	const used = new Set<string>();
	const fragment = (await active.page.locator('.plaque .kana').innerText()).trim();

	// a nonsense word is refused with a reason in French, and the turn goes on
	const input = active.page.getByLabel('Un mot avec');
	await input.pressSequentially('zzzzzz');
	await input.press('Enter');
	await expect(active.page.getByRole('alert')).toContainText(/dictionnaire/);

	// a valid word is accepted: it appears in the list of played words
	await input.fill('');
	await input.pressSequentially(answerFor(fragment, used));
	await input.press('Enter');
	await expect(host.page.locator('.lastcard').first()).toBeVisible({ timeout: 5000 });

	// reload the guest's page: the session token brings them back into the same game
	await guest.page.reload();
	await expect(guest.page.locator('.game')).toBeVisible({ timeout: 15_000 });
	await expect(guest.page.getByText('Aya').first()).toBeVisible();

	// nobody answers any more: bombs eliminate players until one wins (1 life each)
	await expect(host.page.getByRole('heading', { name: /gagne|Tu gagnes/ })).toBeVisible({
		timeout: 60_000
	});
	await expect(guest.page.getByRole('heading', { name: /gagne|Tu gagnes/ })).toBeVisible();

	// rematch returns everybody to the lobby
	await host.page.getByRole('button', { name: 'Revanche' }).click();
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeVisible();
	await expect(guest.page.getByRole('button', { name: /prêt/i })).toBeVisible();

	expect(errors).toEqual([]);
	await host.context.close();
	await guest.context.close();
});

test('an unknown room shows a clear error', async ({ page }) => {
	await page.goto('/r/ZZZZZZ');
	await page.waitForLoadState('networkidle');
	await page.getByLabel('Ton pseudo').fill('Test');
	await page.getByRole('button', { name: 'Entrer' }).click();
	await expect(page.getByRole('heading', { name: 'Partie introuvable' })).toBeVisible();
	await page.getByRole('link', { name: /Retour à l.accueil/ }).click();
	await expect(page).toHaveURL('/');
});

test('a spectator can watch a running game', async ({ browser }) => {
	const host = await newPlayer(browser, 'Yanis');
	const guest = await newPlayer(browser, 'Aya');
	const watcher = await newPlayer(browser, 'Curieux');
	const code = await createRoom(host);
	await joinRoom(guest, code);
	await guest.page.getByRole('button', { name: 'Pas prêt' }).click();
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeEnabled();
	await host.page.getByRole('button', { name: 'Lancer la partie' }).click();
	await expect(host.page.locator('.game')).toBeVisible({ timeout: 15_000 });

	await watcher.page.goto(`/r/${code}`);
	await watcher.page.waitForLoadState('networkidle');
	await watcher.page.getByLabel('Ton pseudo').fill('Curieux');
	await watcher.page.getByRole('button', { name: 'Regarder seulement' }).click();
	await expect(watcher.page.locator('.game')).toBeVisible();
	await expect(watcher.page.getByText('Tu regardes la partie').first()).toBeVisible();
	for (const p of [host, guest, watcher]) await p.context.close();
});
