import type { BombStatsView } from '@hajime/protocol';
import { expect, test, type Page } from '@playwright/test';

const activity = Array.from({ length: 30 }, (_, i) => ({
	day: new Date(Date.UTC(2026, 10, 12 - (29 - i))).toISOString().slice(0, 10),
	games: i === 29 ? 2 : i === 27 ? 1 : 0
}));

const view = (mode: BombStatsView['mode'] = 'all'): BombStatsView => ({
	mode,
	summary: {
		games: 3,
		wins: 2,
		words: 7,
		distinct_words: 3,
		explosions: 1,
		avg_response_ms: 1533,
		fastest_ms: 500,
		longest_word: 'さくら'
	},
	top_words: [
		{
			word: '桜',
			reading: 'さくら',
			count: 4,
			last_played: '2026-11-12',
			meaning_fr: 'cerisier',
			meaning_en: 'cherry tree',
			example_ja: '桜が咲いた。',
			example_en: 'The cherry blossoms bloomed.',
			example_fr: 'Les cerisiers ont fleuri.'
		},
		{
			word: 'ねこ',
			reading: 'ねこ',
			count: 2,
			last_played: '2026-11-11',
			meaning_fr: '',
			meaning_en: 'cat',
			example_ja: '',
			example_en: '',
			example_fr: ''
		}
	],
	recent_words: [
		{
			word: 'らくだ',
			reading: 'らくだ',
			played_at: '2026-11-12T10:00:00',
			mode: 'shiritori',
			response_ms: 1200,
			meaning_fr: '',
			meaning_en: 'camel',
			example_ja: '',
			example_en: '',
			example_fr: ''
		}
	],
	activity
});

async function mockStats(page: Page, status = 200, requests: string[] = []): Promise<void> {
	// statistics are for accounts: these tests are played by a signed-in player
	await page.route('**/api/auth/me', (route) =>
		route.fulfill({ json: { user: { username: 'Aya', email: null, email_verified: false } } })
	);
	await page.route('**/api/me/stats/bomb*', async (route) => {
		const url = new URL(route.request().url());
		requests.push(`${url.search}|${route.request().headers()['x-hajime-guest'] ?? ''}`);
		if (status !== 200) {
			await route.fulfill({ status, json: { detail: 'stats_unavailable' } });
			return;
		}
		await route.fulfill({ json: view(url.searchParams.get('mode') as BombStatsView['mode']) });
	});
}

test('the statistics page shows the totals, the most used words and the last ones', async ({
	page
}) => {
	const requests: string[] = [];
	await mockStats(page, 200, requests);
	await page.goto('/stats'); // with one game it goes straight to that game
	await expect(page).toHaveURL(/\/stats\/bomb$/);
	await expect(page.getByRole('heading', { name: 'Mes statistiques' })).toBeVisible();

	await expect(page.getByText('Parties', { exact: true }).first()).toBeVisible();
	await expect(page.getByText('1,5 s')).toBeVisible(); // 1533 ms
	await expect(page.getByRole('heading', { name: 'Les mots que tu joues le plus' })).toBeVisible();
	await expect(page.getByText('桜', { exact: true })).toBeVisible();
	await expect(page.getByText('4 fois')).toBeVisible();
	await expect(page.getByText('cherry tree')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Tes 10 derniers mots' })).toBeVisible();
	await expect(page.getByText('らくだ', { exact: true })).toBeVisible();
	await expect(
		page.getByRole('img', { name: /3 parties sur les 30 derniers jours/ })
	).toBeVisible();

	// the browser proves who it is with its private guest id, in a header
	const guest = await page.evaluate(() => localStorage.getItem('hajime:guest'));
	expect(guest).toMatch(/^[0-9a-f-]{36}$/);
	expect(requests[0]).toBe(`?mode=all|${guest}`);

	// the mode filter asks the server again, for that mode only
	await page.getByRole('radio', { name: 'Shiritori' }).click();
	await expect.poll(() => requests.some((r) => r.startsWith('?mode=shiritori'))).toBe(true);
});

test('an empty history and an unavailable database each say so', async ({ page }) => {
	await page.route('**/api/auth/me', (route) =>
		route.fulfill({ json: { user: { username: 'Aya', email: null, email_verified: false } } })
	);
	await page.route('**/api/me/stats/bomb*', (route) =>
		route.fulfill({
			json: { ...view(), summary: { ...view().summary, games: 0, words: 0 }, top_words: [] }
		})
	);
	await page.goto('/stats/bomb');
	await expect(page.getByText('Pas encore de statistiques')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Jouer' })).toBeVisible();

	await page.unroute('**/api/me/stats/bomb*');
	await page.unroute('**/api/auth/me');
	await mockStats(page, 503);
	await page.reload();
	await expect(page.getByText('Les statistiques ne sont pas disponibles')).toBeVisible();
});

test('the two pages are linked, and the page speaks the language of its URL', async ({ page }) => {
	await mockStats(page);
	await page.goto('/history');
	await page.getByRole('link', { name: 'Statistiques' }).click();
	await expect(page).toHaveURL(/\/stats\/bomb$/);
	await page.getByRole('link', { name: 'Parties' }).click();
	await expect(page).toHaveURL(/\/history$/);

	await page.goto('/ja/stats');
	await expect(page).toHaveURL(/\/ja\/stats\/bomb$/);
	await expect(page.getByRole('heading', { name: '自分の統計' })).toBeVisible();
	await expect(page.getByText('よく使う単語')).toBeVisible();
	await expect(page.locator('main')).not.toContainText(/Statistiques|parties|Parties/);

	await page.goto('/en/stats/bomb');
	await expect(page.getByRole('heading', { name: 'My statistics' })).toBeVisible();
	await expect(page.getByText('4 times')).toBeVisible();
});

test('only games the site offers have a statistics page', async ({ request }) => {
	expect((await request.get('/stats/chess', { headers: { accept: 'text/html' } })).status()).toBe(
		404
	);
});

test('a guest is invited to create an account instead of seeing statistics', async ({ page }) => {
	const requests: string[] = [];
	await page.route('**/api/auth/me', (route) => route.fulfill({ json: { user: null } }));
	await page.route('**/api/me/stats/bomb*', (route) => {
		requests.push(route.request().url());
		return route.fulfill({ status: 401, json: { detail: 'guest_required' } });
	});
	await page.goto('/stats/bomb');
	await expect(
		page.getByRole('heading', { name: 'Les statistiques sont réservées aux comptes' })
	).toBeVisible();
	await page.getByRole('link', { name: 'Créer un compte' }).click();
	await expect(page).toHaveURL(/\/account$/);
	expect(requests).toEqual([]); // a guest's page never asks the server for statistics

	await page.goto('/ja/stats/bomb');
	await expect(page.getByRole('heading', { name: '統計はアカウント専用です' })).toBeVisible();
	await expect(page.locator('main')).not.toContainText(/compte|statistiques|invité/i);
});
