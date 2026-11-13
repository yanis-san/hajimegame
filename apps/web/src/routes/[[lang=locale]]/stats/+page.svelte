<script lang="ts">
	import Button from '#lib/design/Button.svelte';
	import HistoryTabs from '#lib/design/HistoryTabs.svelte';
	import { GAME_IDS } from '#lib/games/registry.ts';
	import { GAME_NAMES } from '#lib/games/stats.ts';
	import { href, t } from '#lib/i18n/index.ts';
</script>

<svelte:head><title>{t('stats.title')} · {t('app.name')}</title></svelte:head>

<article class="stats">
	<header class="top">
		<h1>{t('stats.title')}</h1>
		<Button href={href('/')} variant="ghost" size="sm" icon="back">{t('history.back')}</Button>
	</header>
	<HistoryTabs current="stats" />
	<ul>
		{#each GAME_IDS as id (id)}
			<li>
				<Button href={href(`/stats/${id}`)} variant="secondary" full>{t(GAME_NAMES[id])}</Button>
			</li>
		{/each}
	</ul>
</article>

<style>
	.stats {
		display: grid;
		gap: 0.9rem;
		max-width: 40rem;
		margin: 0.5rem auto 2rem;
		padding: 0 1rem;
		box-sizing: border-box;
	}
	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.8rem;
	}
	h1 {
		font-size: clamp(1.6rem, 6vw, 2.1rem);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.6rem;
	}
</style>
