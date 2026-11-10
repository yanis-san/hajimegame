import { defineConfig, devices } from '@playwright/test';

const reuse = !process.env.CI;

export default defineConfig({
	testDir: 'e2e',
	testMatch: '**/*.e2e.ts',
	globalSetup: './e2e/global-setup.ts',
	timeout: 90_000,
	fullyParallel: false,
	workers: 1,
	reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
	use: { baseURL: 'http://localhost:5173', locale: 'fr-FR', trace: 'retain-on-failure' },
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
			command: 'uv run uvicorn app.main:create_app --factory --port 8000 --log-level warning',
			cwd: '../server',
			url: 'http://127.0.0.1:8000/readyz',
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
			command: 'pnpm exec vite dev --port 5173',
			url: 'http://localhost:5173',
			reuseExistingServer: reuse,
			timeout: 90_000
		}
	]
});
