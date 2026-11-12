<script lang="ts">
	import { onMount } from 'svelte';
	import { getLocale } from '#lib/i18n/index.ts';

	/**
	 * The captcha on sign-up (Cloudflare Turnstile). It only appears when the site was built with a key
	 * (`VITE_TURNSTILE_SITE_KEY`); without one the server skips the check too, in development.
	 */
	let { token = $bindable('') }: { token?: string } = $props();

	interface Turnstile {
		render(el: HTMLElement, options: Record<string, unknown>): string;
		reset(id?: string): void;
		remove(id?: string): void;
	}
	const SITE_KEY = (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined) ?? '';
	const SCRIPT = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

	let host: HTMLElement | undefined = $state();
	let widget: string | undefined;

	function load(): Promise<Turnstile> {
		const w = window as unknown as { turnstile?: Turnstile };
		if (w.turnstile) return Promise.resolve(w.turnstile);
		return new Promise((resolve, reject) => {
			const script = document.createElement('script');
			script.src = SCRIPT;
			script.async = true;
			script.onload = () => (w.turnstile ? resolve(w.turnstile) : reject(new Error('turnstile')));
			script.onerror = () => reject(new Error('turnstile'));
			document.head.append(script);
		});
	}

	onMount(() => {
		if (!SITE_KEY || !host) return;
		let gone = false;
		const el = host;
		load()
			.then((turnstile) => {
				if (gone) return;
				widget = turnstile.render(el, {
					sitekey: SITE_KEY,
					language: getLocale(),
					callback: (value: string) => (token = value),
					'expired-callback': () => (token = ''),
					'error-callback': () => (token = '')
				});
			})
			.catch(() => (token = ''));
		return () => {
			gone = true;
			if (widget) (window as unknown as { turnstile?: Turnstile }).turnstile?.remove(widget);
		};
	});
</script>

{#if SITE_KEY}
	<div bind:this={host} class="captcha"></div>
{/if}

<style>
	.captcha {
		min-height: 65px;
	}
</style>
