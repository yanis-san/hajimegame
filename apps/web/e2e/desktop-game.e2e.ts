import { expect, test } from '@playwright/test';
import { answerFor, createRoom, newPlayer } from './helpers';

// A game on a computer: the page itself never scrolls, whatever the window height (laptops at 125% or 150% zoom
// have windows of 520 to 700 px), and only the list of words on the right scrolls, on its own.
test.skip(({ isMobile }) => isMobile, 'computer layout');

const WINDOWS: [number, number][] = [
	[1920, 1080],
	[1536, 730],
	[1366, 650],
	[1280, 600],
	[1100, 560],
	[1000, 520]
];

test('the game fits the window without scrolling, only the words on the right scroll', async ({
	browser
}) => {
	test.setTimeout(90_000);
	const host = await newPlayer(browser, 'Aya', { viewport: { width: 1280, height: 720 } });
	const { page } = host;
	await createRoom(host);
	await page.getByRole('button', { name: 'Ajouter un CPU' }).click();
	await page.getByRole('button', { name: 'Lancer la partie' }).click();
	await page.locator('.game').waitFor({ timeout: 15_000 });

	// play one word, so the card of the last word (meaning and example) is on screen: the tallest case
	await page.locator('input.field:not(.idle)').waitFor({ timeout: 40_000 });
	const fragment = (await page.locator('.kana').first().innerText()).trim();
	await page
		.locator('input.field')
		.pressSequentially(answerFor(fragment, new Set()), { delay: 10 });
	await page.keyboard.press('Enter');
	await page.locator('.lastcard').waitFor();
	if (process.env.E2E_SHOT) await page.waitForTimeout(900);
	if (process.env.E2E_SHOT) await page.screenshot({ path: process.env.E2E_SHOT });

	// the names of the players are readable, not just present
	for (const name of await page.locator('.slot .name').all()) {
		expect((await name.boundingBox())?.width ?? 0).toBeGreaterThan(30);
	}

	for (const [width, height] of WINDOWS) {
		await page.setViewportSize({ width, height });
		await page.waitForTimeout(300);
		const layout = await page.evaluate(() => {
			const field = document.querySelector('input.field')!.getBoundingClientRect();
			const card = document.querySelector('.lastcard')!.getBoundingClientRect();
			return {
				overflow: document.documentElement.scrollHeight - innerHeight,
				fieldBottom: field.bottom,
				cardTop: card.top,
				cardBottom: card.bottom,
				fieldTop: field.top,
				height: innerHeight
			};
		});
		const where = `${width}x${height}`;
		expect(layout.overflow, `the page scrolls at ${where}`).toBeLessThanOrEqual(0);
		expect(layout.fieldBottom, `the field is cut off at ${where}`).toBeLessThanOrEqual(
			layout.height
		);
		// the word just played is whole (only the word, no meaning), and sits above the field
		expect(layout.cardTop, `the word is cut off at ${where}`).toBeGreaterThanOrEqual(0);
		expect(layout.cardBottom, `the word touches the field at ${where}`).toBeLessThanOrEqual(
			layout.fieldTop
		);
		if (height >= 1000) {
			// room to spare: the field comes up with the bomb, it is not stuck to the bottom of the screen
			expect(layout.fieldBottom, `the field is at the very bottom at ${where}`).toBeLessThan(
				layout.height * 0.85
			);
		}
	}

	// many words: the list on the right scrolls by itself and the page still does not
	await page.setViewportSize({ width: 1366, height: 650 });
	await page.evaluate(() => {
		const list = document.querySelector('.history ol')!;
		const first = list.firstElementChild!;
		for (let i = 0; i < 40; i++) list.append(first.cloneNode(true));
	});
	const scroll = await page.evaluate(() => {
		const list = document.querySelector('.history ol') as HTMLElement;
		return {
			listScrolls: list.scrollHeight > list.clientHeight,
			listOverflow: getComputedStyle(list).overflowY,
			pageOverflow: document.documentElement.scrollHeight - innerHeight
		};
	});
	expect(scroll.listOverflow).toBe('auto');
	expect(scroll.listScrolls).toBe(true);
	expect(scroll.pageOverflow).toBeLessThanOrEqual(0);
	await host.context.close();
});
