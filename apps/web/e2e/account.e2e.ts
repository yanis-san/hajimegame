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

test('create an account from the header, see it, sign out', async ({ page }) => {
	await fakeAccounts(page);
	await page.setViewportSize({ width: 1280, height: 720 });
	await page.goto('/');
	await expect(page.getByRole('link', { name: 'Se connecter' })).toBeVisible();
	await page.getByRole('link', { name: 'Créer un compte' }).click();
	await expect(page).toHaveURL(/\/signup$/);
	await page.getByLabel('Pseudo', { exact: true }).fill('Aya');
	await page.getByLabel('Mot de passe').fill('correct horse battery');
	await page.getByLabel('Email', { exact: true }).fill('aya@example.com');
	await page.getByLabel('Date de naissance').fill('1995-06-15');
	await page.getByRole('button', { name: 'Créer mon compte' }).click();

	await expect(page).toHaveURL(/\/account$/);
	await expect(page.getByText('Connecté en tant que')).toBeVisible();
	await expect(page.getByText('aya@example.com')).toBeVisible();

	await page.getByRole('button', { name: 'Me déconnecter' }).click();
	await expect(page.getByRole('link', { name: 'Créer un compte' }).first()).toBeVisible();
});

test('the sign-up form needs no scrolling on a desktop screen', async ({ page }) => {
	await fakeAccounts(page);
	await page.setViewportSize({ width: 1280, height: 720 });
	await page.goto('/signup');
	const button = page.getByRole('button', { name: 'Créer mon compte' });
	await expect(button).toBeInViewport({ ratio: 1 });
	const extra = await page.evaluate(
		() => document.documentElement.scrollHeight - document.documentElement.clientHeight
	);
	expect(extra).toBeLessThanOrEqual(0);
});

test('a taken username is explained in words, in the page language', async ({ page }) => {
	await fakeAccounts(page, { taken: true });
	await page.goto('/en/signup');
	await page.getByLabel('Username', { exact: true }).fill('Aya');
	await page.getByLabel('Password').fill('correct horse battery');
	await page.getByLabel('Email', { exact: true }).fill('aya@example.com');
	await page.getByLabel('Date of birth').fill('1995-06-15');
	await page.getByRole('button', { name: 'Create my account' }).click();
	await expect(page.getByRole('alert')).toHaveText('That username is already taken.');
});

test('the Japanese pages show no French', async ({ page }) => {
	await fakeAccounts(page);
	for (const path of ['/ja/signup', '/ja/login', '/ja/account']) {
		await page.goto(path);
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		const text = await page.locator('body').innerText();
		expect(text).not.toMatch(/compte|connecter|Pseudo|Mot de passe|Retour|Déjà/i);
	}
});

test('the sign-in and sign-up pages fit a phone without scrolling sideways', async ({ page }) => {
	await fakeAccounts(page);
	await page.setViewportSize({ width: 360, height: 740 });
	for (const path of ['/login', '/signup', '/account']) {
		await page.goto(path);
		const overflow = await page.evaluate(
			() => document.documentElement.scrollWidth - document.documentElement.clientWidth
		);
		expect(overflow).toBeLessThanOrEqual(0);
	}
	await page.goto('/signup');
	const button = page.getByRole('button', { name: 'Créer mon compte' });
	await button.scrollIntoViewIfNeeded();
	await expect(button).toBeInViewport();
});

test('the page behind the link of the message confirms the address, or says the link is no good', async ({
	page
}) => {
	let answer = 200;
	let sent: string | undefined;
	await page.route('**/api/auth/me', (route) => route.fulfill({ json: { user: null } }));
	await page.route('**/api/auth/verify', (route) => {
		sent = (route.request().postDataJSON() as { token: string }).token;
		return route.fulfill({
			status: answer,
			json: answer === 200 ? { verified: true } : { detail: 'bad_token' }
		});
	});
	await page.goto('/verify?token=abc-123');
	await expect(page.getByText('C’est confirmé')).toBeVisible();
	expect(sent).toBe('abc-123');
	await expect(page.getByRole('link', { name: 'Aller à mon compte' })).toBeVisible();

	answer = 400; // used or expired
	await page.goto('/en/verify?token=old');
	await expect(page.getByText('This link no longer works')).toBeVisible();

	await page.goto('/ja/verify'); // no code in the address
	await expect(page.getByText('このリンクにはコードがありません')).toBeVisible();
	const text = await page.locator('main').innerText();
	expect(text).not.toMatch(/lien|confirmé|compte/i); // the Japanese page shows no French
});

test('an address that is not confirmed offers to send the message again', async ({ page }) => {
	let asked = 0;
	await page.route('**/api/auth/me', (route) =>
		route.fulfill({
			json: { user: { username: 'Aya', email: 'aya@example.com', email_verified: false } }
		})
	);
	await page.route('**/api/auth/verify/resend', (route) => {
		asked += 1;
		return route.fulfill({ status: 202, json: { sent: true } });
	});
	await page.goto('/account');
	await expect(page.getByText('Ton email n’est pas encore confirmé')).toBeVisible();
	await page.getByRole('button', { name: 'Renvoyer l’email' }).click();
	await expect(page.getByText('Message envoyé à aya@example.com')).toBeVisible();
	expect(asked).toBe(1);
});
