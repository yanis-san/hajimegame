import { expect, test, type Page } from '@playwright/test';
import { answerFor, createRoom, newPlayer } from './helpers';

// The phone experience: no sideways scrolling, and a game that stays playable with the keyboard open.
test.skip(({ isMobile }) => !isMobile, 'phone layout');

const WIDTHS = [320, 360, 390, 412, 430, 480, 600];

/** How far the page is wider than the screen: on a phone this is what makes it scroll sideways. */
const overflow = (page: Page): Promise<number> =>
	page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

for (const width of WIDTHS) {
	test(`no sideways scrolling at ${width}px`, async ({ browser }) => {
		const player = await newPlayer(browser, 'Aya', {
			viewport: { width, height: 800 },
			isMobile: true,
			hasTouch: true
		});
		const { page } = player;
		for (const path of ['/', '/ja', '/en', '/history', '/stats/bomb', '/account', '/credits']) {
			await page.goto(path);
			await page.waitForLoadState('networkidle');
			expect(await overflow(page), `${path} at ${width}px`).toBeLessThanOrEqual(0);
		}
		await createRoom(player);
		expect(await overflow(page), `the lobby at ${width}px`).toBeLessThanOrEqual(0);
		await player.context.close();
	});
}

test('the countdown shows its last word inside the screen', async ({ browser }) => {
	const player = await newPlayer(browser, 'Aya', {
		viewport: { width: 360, height: 640 },
		isMobile: true,
		hasTouch: true
	});
	const { page } = player;
	await createRoom(player);
	await page.getByRole('button', { name: 'Ajouter un CPU' }).click();
	await page.getByRole('button', { name: 'Lancer la partie' }).click();
	await page.locator('.num').waitFor();
	// the word is on screen for a split second only: look at a copy of the number set to that word
	const box = await page.evaluate(() => {
		const source = document.querySelector('.num') as HTMLElement;
		const copy = source.cloneNode(true) as HTMLElement;
		copy.style.animation = 'none';
		copy.classList.add('word');
		copy.textContent = 'バカハツ';
		source.parentElement?.append(copy);
		const { left, right } = copy.getBoundingClientRect();
		copy.remove();
		return { left, right, width: document.documentElement.clientWidth };
	});
	expect(box.left).toBeGreaterThanOrEqual(0);
	expect(box.right).toBeLessThanOrEqual(box.width);
	expect(await overflow(page)).toBeLessThanOrEqual(0);
	await player.context.close();
});

test('with the keyboard open, the fragment stays visible and the keyboard stays open after sending', async ({
	browser
}) => {
	test.setTimeout(90_000);
	const player = await newPlayer(browser, 'Aya', {
		viewport: { width: 360, height: 640 },
		isMobile: true,
		hasTouch: true
	});
	const { page } = player;
	await createRoom(player);
	await page.getByRole('button', { name: 'Ajouter un CPU' }).click();
	await page.getByRole('button', { name: 'Lancer la partie' }).click();
	// the keyboard of a phone leaves little more than half of the screen
	await page.setViewportSize({ width: 360, height: 371 });
	const field = page.locator('input.field');
	await page.waitForFunction(() => !document.querySelector('input.field.idle'), null, {
		timeout: 30_000
	});
	const fragment = (await page.locator('.kana').first().innerText()).trim();
	await field.tap();
	await page.keyboard.type(answerFor(fragment, new Set()));

	// nothing covers the fragment: its tag is entirely above the field, inside the screen
	const layout = await page.evaluate(() => {
		const tag = document.querySelector('.plaque')!.getBoundingClientRect();
		const input = document.querySelector('input.field')!.getBoundingClientRect();
		return { tagTop: tag.top, tagBottom: tag.bottom, inputTop: input.top, height: innerHeight };
	});
	expect(layout.tagTop).toBeGreaterThanOrEqual(0);
	expect(layout.tagBottom).toBeLessThanOrEqual(layout.inputTop);
	expect(layout.inputTop + 56).toBeLessThanOrEqual(layout.height + 1);

	await page.keyboard.press('Enter');
	await expect(page.locator('.lastcard')).toBeVisible(); // the accepted word and its meaning
	// sending must not close the keyboard: the field still has the focus
	expect(await page.evaluate(() => document.activeElement?.classList.contains('field'))).toBe(true);
	expect(await overflow(page)).toBeLessThanOrEqual(0);
	await player.context.close();
});
