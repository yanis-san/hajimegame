<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import Button from '#lib/design/Button.svelte';
	import Icon from '#lib/design/Icon.svelte';
	import LanguagePicker from '#lib/design/LanguagePicker.svelte';
	import Sky from '#lib/design/Sky.svelte';
	import { loadAccount } from '#lib/game/account.svelte.ts';
	import { loadPref, savePref } from '#lib/game/session.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		LOCALES,
		href,
		localeFromPath,
		localizePath,
		setLocale,
		t,
		type Locale
	} from '#lib/i18n/index.ts';
	import { LANG_COOKIE } from '#lib/i18n/path.ts';

	let { children } = $props();

	// The language comes from the URL. It is set while this component initialises, before any child renders, so the
	// server-rendered HTML and the first client render are already in the right language (no flash, no French).
	setLocale(localeFromPath(page.url.pathname));
	$effect.pre(() => setLocale(localeFromPath(page.url.pathname)));
	// The server sets <html lang>; this keeps it right after an in-page language change.
	$effect(() => {
		document.documentElement.lang = localeFromPath(page.url.pathname);
	});

	/** Same page, other language: the URL changes and the choice is remembered for the bare root URL. */
	function chooseLocale(next: Locale): void {
		document.cookie = `${LANG_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
		const { pathname, search, hash } = page.url;
		void goto(localizePath(pathname, next) + search + hash, {
			replace: true,
			reset: false
		});
	}

	let theme = $state<'dark' | 'light'>('dark');
	let muted = $state(false);

	function applyTheme(next: 'dark' | 'light'): void {
		theme = next;
		document.documentElement.dataset.theme = next;
		savePref('theme', next);
		document
			.querySelector('meta[name="theme-color"]')
			?.setAttribute('content', next === 'dark' ? '#0f1b2d' : '#f5efe3');
	}

	onMount(() => {
		void loadAccount();
		applyTheme(loadPref<'dark' | 'light'>('theme', 'dark'));
		muted = sfx.muted;
		// Audio can only start from a user gesture: try on each tap, click and key press until it is awake. (A touch
		// counts as a gesture when it ends, a key such as F12 does not count at all: hence several events.)
		const events = ['pointerdown', 'pointerup', 'click', 'keydown'] as const;
		const unlock = (): void => {
			sfx.unlock();
			if (sfx.running) for (const name of events) window.removeEventListener(name, unlock);
		};
		for (const name of events) window.addEventListener(name, unlock);
		return () => {
			for (const name of events) window.removeEventListener(name, unlock);
		};
	});

	function toggleSound(): void {
		sfx.unlock();
		muted = !muted;
		sfx.setMuted(muted);
	}
</script>

<svelte:head>
	{#each LOCALES as option (option.code)}
		<link
			rel="alternate"
			hreflang={option.code}
			href={page.url.origin + localizePath(page.url.pathname, option.code)}
		/>
	{/each}
</svelte:head>

<Sky />

<header class="bar">
	<a class="logo" href={href('/')} aria-label={t('app.name')}>
		<span class="mark" aria-hidden="true"><Icon name="bomb" size={22} /></span>
		<span class="word">{t('app.name')}</span>
	</a>
	<div class="tools">
		<LanguagePicker onchange={chooseLocale} />
		<Button
			size="sm"
			variant="ghost"
			iconOnly
			icon="user"
			label={t('account.open')}
			href={href('/account')}
		/>
		<Button
			size="sm"
			variant="ghost"
			iconOnly
			icon={muted ? 'mute' : 'volume'}
			label={muted ? t('sound.off') : t('sound.on')}
			pressed={muted}
			onclick={toggleSound}
		/>
		<Button
			size="sm"
			variant="ghost"
			iconOnly
			icon={theme === 'dark' ? 'sun' : 'moon'}
			label={theme === 'dark' ? t('theme.light') : t('theme.dark')}
			onclick={() => applyTheme(theme === 'dark' ? 'light' : 'dark')}
		/>
	</div>
</header>

<main>
	{@render children()}
</main>

<style>
	:global(:root) {
		--bar: 52px;
	}
	.bar {
		position: sticky;
		top: 0;
		z-index: 40;
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: var(--bar);
		box-sizing: border-box;
		padding: 0 0.75rem;
		padding-top: env(safe-area-inset-top);
		/* solid band so scrolled content never runs behind the logo and buttons */
		background: var(--bg);
		border-bottom: var(--line) solid var(--sumi);
	}
	.logo {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		color: var(--text);
		font-family: var(--font-display);
		font-weight: 800;
		font-size: 1.35rem;
	}
	.mark {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		background: var(--shu-btn);
		color: #fff8ef;
		border: var(--line) solid var(--sumi);
		border-radius: 8px;
		box-shadow: 2px 3px 0 var(--sumi);
		transform: rotate(-4deg);
	}
	.tools {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-width: 0;
	}
	/* narrow phones: tighter bar so the logo, the language picker and the two buttons never widen the page */
	/* during a game the page itself never scrolls: only the list of words does */
	:global(html[data-playing]) {
		overflow: hidden;
	}
	/* a game on a phone: no bar, the whole screen is the game */
	@media (max-width: 899px) {
		:global(html[data-playing]) {
			--bar: 0px;
		}
		:global(html[data-playing]) .bar {
			display: none;
		}
	}
	@media (max-width: 480px) {
		.bar {
			padding-inline: 0.5rem;
		}
		.tools {
			gap: 0.4rem;
		}
		.logo {
			gap: 0.4rem;
			font-size: 1.2rem;
		}
	}
	@media (max-width: 380px) {
		.bar {
			padding-inline: 0.4rem;
		}
		.tools {
			gap: 0.25rem;
		}
	}
	/* the seal alone is the logo on phones: the account button needs the room */
	@media (max-width: 560px) {
		.word {
			display: none;
		}
	}
	main {
		min-height: calc(100dvh - var(--bar));
	}
</style>
