import { expect, test } from '@playwright/test';
import { createRoom, newPlayer } from './helpers';

// The development server relaxes style-src for Vite's injected styles: the strict checks need the build.
const strict = Boolean(process.env.E2E_PREVIEW);

test('pages carry hardening headers and a strict Content-Security-Policy', async ({ request }) => {
	for (const path of ['/', '/en', '/ja/credits', '/history']) {
		const response = await request.get(path, { headers: { accept: 'text/html' } });
		expect(response.status(), path).toBe(200);
		const headers = response.headers();
		expect(headers['x-content-type-options'], path).toBe('nosniff');
		expect(headers['x-frame-options'], path).toBe('DENY');
		expect(headers['referrer-policy'], path).toBe('no-referrer');
		expect(headers['permissions-policy'], path).toContain('microphone=()');
		const csp = headers['content-security-policy'] ?? '';
		expect(csp, path).toContain("default-src 'none'");
		expect(csp, path).toContain("frame-ancestors 'none'");
		expect(csp, path).toMatch(/script-src 'self' 'nonce-[\w+/=-]+'/); // a nonce per response, never unsafe-inline
		expect(csp, path).not.toContain('unsafe-eval');
		if (strict) {
			expect(csp.replace(/style-src-attr[^;]*/, ''), path).not.toContain("'unsafe-inline'");
		}
	}
	// a different nonce each time, so it cannot be guessed
	const nonce = async (): Promise<string> =>
		((await request.get('/')).headers()['content-security-policy'] ?? '').match(
			/'nonce-([^']+)'/
		)?.[1] ?? '';
	expect(await nonce()).not.toBe(await nonce());
	expect(await (await request.get('/up')).text()).toBe('ok');
});

test('the whole app runs under the policy: no blocked script, style, font, image or WebSocket', async ({
	browser
}) => {
	const host = await newPlayer(browser, 'Yanis');
	const violations: string[] = [];
	await host.context.addInitScript(() => {
		const w = window as unknown as { __csp: string[] };
		w.__csp = [];
		document.addEventListener('securitypolicyviolation', (e) =>
			w.__csp.push(`${e.violatedDirective} blocked ${e.blockedURI}`)
		);
	});
	host.page.on(
		'console',
		(m) => m.text().includes('Content Security Policy') && violations.push(m.text())
	);

	await createRoom(host); // home page, then the lobby: the WebSocket to the game server
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeVisible();
	await host.page.goto('/en/credits');
	await host.page.goto('/ja/history');
	await host.page.waitForLoadState('networkidle');

	// the document is gone after navigation, so read what each page recorded as we go
	expect(violations).toEqual([]);
	await host.page.goto('/');
	await host.page.waitForLoadState('networkidle');
	const recorded = await host.page.evaluate(() => (window as unknown as { __csp: string[] }).__csp);
	expect(recorded).toEqual([]);
	await host.context.close();
});

test('an injected inline script is blocked (the policy really is enforced)', async ({ page }) => {
	test.skip(!strict, 'checked on the production build');
	await page.addInitScript(() => {
		const w = window as unknown as { __csp: string[]; __ran: boolean };
		w.__csp = [];
		document.addEventListener('securitypolicyviolation', (e) => w.__csp.push(e.violatedDirective));
	});
	await page.goto('/');
	await page.waitForLoadState('networkidle');
	await page.evaluate(() => {
		const script = document.createElement('script');
		script.textContent = 'window.__ran = true';
		document.body.append(script);
	});
	const result = await page.evaluate(() => {
		const w = window as unknown as { __csp: string[]; __ran?: boolean };
		return { ran: w.__ran === true, blocked: w.__csp };
	});
	expect(result.ran).toBe(false);
	expect(result.blocked.some((d) => d.startsWith('script-src'))).toBe(true);
});
