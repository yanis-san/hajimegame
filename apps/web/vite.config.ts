import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';

// In development the game server runs on :8000. The proxy makes it same-origin for the browser, so no CORS setup
// is needed and WebSockets just work. In production set PUBLIC_API_URL (or put both behind one domain).
const API = process.env.HAJIME_API_TARGET ?? 'http://127.0.0.1:8000';
// Same origin unless the interface is built with VITE_API_URL: then that origin is allowed to be called too.
const apiOrigin = (
	process.env.VITE_API_URL ? [new URL(process.env.VITE_API_URL).origin] : []
) as `${string}://${string}.${string}`[];

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter(),
			// Strict by default: only our own files run. SvelteKit adds nonces for the inline scripts it renders.
			csp: {
				mode: 'auto',
				directives: {
					'default-src': ['none'],
					'script-src': ['self'],
					'style-src': ['self'],
					// inline style="..." attributes (a style attribute cannot run code)
					'style-src-attr': ['unsafe-inline'],
					'img-src': ['self', 'data:'],
					'font-src': ['self'],
					'media-src': ['self', 'blob:'],
					'manifest-src': ['self'],
					// the game server over a WebSocket (ws: only matters for local development)
					'connect-src': ['self', 'ws:', 'wss:', ...apiOrigin],
					'object-src': ['none'],
					'base-uri': ['self'],
					'form-action': ['self'],
					'frame-ancestors': ['none']
				}
			}
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
