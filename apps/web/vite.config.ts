import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';

// In development the game server runs on :8000. The proxy makes it same-origin for the browser, so no CORS setup
// is needed and WebSockets just work. In production set PUBLIC_API_URL (or put both behind one domain).
const API = process.env.HAJIME_API_TARGET ?? 'http://127.0.0.1:8000';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter()
		})
	],
	server: {
		host: true,
		port: 5173,
		proxy: {
			'/api': { target: API, changeOrigin: false },
			'/ws': { target: API.replace(/^http/, 'ws'), ws: true, changeOrigin: false }
		}
	},
	preview: {
		port: 4173,
		proxy: {
			'/api': { target: API, changeOrigin: false },
			'/ws': { target: API.replace(/^http/, 'ws'), ws: true, changeOrigin: false }
		}
	},
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'client',
					browser: {
						enabled: true,
						provider: playwright(),
						instances: [{ browser: 'chromium', headless: true }]
					},
					include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
					exclude: ['src/lib/server/**']
				}
			},

			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
