import { defineConfig, devices } from '@playwright/test';

const reuse = !process.env.CI;
// Ports can be changed when the defaults are taken: E2E_API_PORT=8100 E2E_WEB_PORT=5273 pnpm e2e
const apiPort = process.env.E2E_API_PORT ?? '8000';
const webPort = process.env.E2E_WEB_PORT ?? '5173';
// E2E_PREVIEW=1 tests the production build (run `pnpm build` first): same code and headers as a deployment.
const webCommand = process.env.E2E_PREVIEW
	? `pnpm exec vite preview --port ${webPort} --strictPort`
	: `pnpm exec vite dev --port ${webPort}`;

export default defineConfig({
	testDir: 'e2e',
	testMatch: '**/*.e2e.ts',
	globalSetup: './e2e/global-setup.ts',
	timeout: 90_000,
	fullyParallel: false,
	workers: 1,
	reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
	use: { baseURL: `http://localhost:${webPort}`, locale: 'fr-FR', trace: 'retain-on-failure' },
	projects: [
		{
			name: 'desktop',
			use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } }
		},
		{ name: 'mobile', use: { ...devices['Pixel 7'] } },
		...(process.env.E2E_WEBKIT
			? [
					{
						name: 'iphone',
						use: { ...devices['iPhone 13'], defaultBrowserType: 'webkit' as const }
					}
				]
			: [])
	],
	webServer: [
		{
			command: `uv run uvicorn app.main:create_app --factory --port ${apiPort} --log-level warning`,
			cwd: '../server',
			url: `http://127.0.0.1:${apiPort}/readyz`,
			reuseExistingServer: reuse,
			timeout: 90_000,
			env: {
				PYTHONUTF8: '1',
				HAJIME_MAX_ROOMS_PER_IP: '500',
				HAJIME_JOIN_ATTEMPTS_PER_MINUTE: '10000',
				HAJIME_ROOM_CREATIONS_PER_MINUTE: '10000'
			}
		},
		{
			command: webCommand,
			url: `http://localhost:${webPort}`,
			env: { HAJIME_API_TARGET: `http://127.0.0.1:${apiPort}` },
			reuseExistingServer: reuse,
			timeout: 90_000
		}
	]
});
