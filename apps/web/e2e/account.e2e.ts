import { expect, test, type Page } from '@playwright/test';

/** The account API, played by the test: the page is checked, not the server (the server has its own tests). */
async function fakeAccounts(page: Page, options: { taken?: boolean } = {}): Promise<void> {
	let user: { username: string; email: string | null; email_verified: boolean } | null = null;
	await page.route('**/api/auth/me', (route) => route.fulfill({ json: { user } }));
	await page.route('**/api/auth/register', async (route) => {
		if (options.taken) {
			return route.fulfill({ status: 409, json: { detail: 'username_taken' } });
		}
		const body = route.request().postDataJSON() as { username: string; email: string | null };
		user = { username: body.username, email: body.email, email_verified: false };
		return route.fulfill({ status: 201, json: user });
	});
	await page.route('**/api/auth/logout', (route) => {
		user = null;
		return route.fulfill({ json: { ok: true } });
	});
}

test('create an account, see it, sign out', async ({ page }) => {
	await fakeAccounts(page);
	await page.goto('/account');
	await page.getByLabel('Pseudo', { exact: true }).fill('Aya');
	await page.getByLabel('Mot de passe').fill('correct horse battery');
	await page.getByLabel('Email (facultatif)').fill('aya@example.com');
	await page.getByRole('button', { name: 'Créer mon compte' }).click();

	await expect(page.getByText('Connecté en tant que')).toBeVisible();
	await expect(page.getByText('Aya', { exact: true })).toBeVisible();
	await expect(page.getByText('aya@example.com')).toBeVisible();
	await expect(page.getByLabel('Mot de passe')).toHaveCount(0);

	await page.getByRole('button', { name: 'Me déconnecter' }).click();
	await expect(page.getByRole('button', { name: 'Créer mon compte' })).toBeVisible();
});

test('a taken username is explained in words, in the page language', async ({ page }) => {
	await fakeAccounts(page, { taken: true });
	await page.goto('/en/account');
	await page.getByLabel('Username', { exact: true }).fill('Aya');
	await page.getByLabel('Password').fill('correct horse battery');
	await page.getByRole('button', { name: 'Create my account' }).click();
	await expect(page.getByRole('alert')).toHaveText('That username is already taken.');
});

test('the Japanese page shows no French', async ({ page }) => {
	await fakeAccounts(page);
	await page.goto('/ja/account');
	await expect(page.getByRole('heading', { name: 'アカウント' })).toBeVisible();
	const text = await page.locator('body').innerText();
	expect(text).not.toMatch(/compte|connecter|Pseudo|Mot de passe|Retour/i);
});

test('the account page fits a phone without scrolling sideways', async ({ page }) => {
	await fakeAccounts(page);
	await page.setViewportSize({ width: 360, height: 740 });
	await page.goto('/account');
	const overflow = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	expect(overflow).toBeLessThanOrEqual(0);
	await expect(page.getByRole('button', { name: 'Créer mon compte' })).toBeInViewport();
});
