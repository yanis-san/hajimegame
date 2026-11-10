<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import Button from '#lib/design/Button.svelte';
	import Sky from '#lib/design/Sky.svelte';
	import { loadPref, savePref } from '#lib/game/session.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import { t } from '#lib/i18n/index.ts';

	let { children } = $props();

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
		applyTheme(loadPref<'dark' | 'light'>('theme', 'dark'));
		muted = sfx.muted;
		// Audio can only start from a user gesture (iOS): unlock on the first tap or key press.
		const unlock = (): void => {
			sfx.unlock();
			window.removeEventListener('pointerdown', unlock);
			window.removeEventListener('keydown', unlock);
		};
		window.addEventListener('pointerdown', unlock);
		window.addEventListener('keydown', unlock);
		return () => {
			window.removeEventListener('pointerdown', unlock);
			window.removeEventListener('keydown', unlock);
		};
	});

	function toggleSound(): void {
		sfx.unlock();
		muted = !muted;
		sfx.setMuted(muted);
	}
</script>

<Sky />

<header class="bar">
	<a class="logo" href="/" aria-label={t('app.name')}>
		<span class="mark" aria-hidden="true">始</span>
		<span class="word">{t('app.name')}</span>
	</a>
	<div class="tools">
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
		background: var(--shu);
		color: #fff8ef;
		border: var(--line) solid var(--sumi);
		border-radius: 8px;
		box-shadow: 2px 3px 0 var(--sumi);
		font-size: 1.2rem;
		transform: rotate(-4deg);
	}
	.tools {
		display: flex;
		gap: 0.5rem;
	}
	main {
		min-height: calc(100dvh - var(--bar));
	}
</style>
