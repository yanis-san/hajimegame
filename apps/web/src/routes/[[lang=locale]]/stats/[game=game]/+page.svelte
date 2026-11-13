<script lang="ts">
	import { page } from '$app/state';
	import Button from '#lib/design/Button.svelte';
	import HistoryTabs from '#lib/design/HistoryTabs.svelte';
	import { account } from '#lib/game/account.svelte.ts';
	import { GAME_IDS, isGameId } from '#lib/games/registry.ts';
	import { GAME_NAMES, STATS_VIEWS } from '#lib/games/stats.ts';
	import { href, t } from '#lib/i18n/index.ts';

	// the route only matches known games (see src/params.ts)
	const game = $derived(
		isGameId(page.params.game ?? '') ? (page.params.game as 'bomb') : GAME_IDS[0]
	);
	const View = $derived(STATS_VIEWS[game]);
</script>

<svelte:head><title>{t('stats.title')} · {t('app.name')}</title></svelte:head>

<article class="stats">
	<header class="top">
		<h1>{t('stats.title')}</h1>
		<Button href={href('/')} variant="ghost" size="sm" icon="back">{t('history.back')}</Button>
	</header>
	<HistoryTabs current="stats" />
	{#if GAME_IDS.length > 1}
		<nav class="games" aria-label={t('stats.games.label')}>
			{#each GAME_IDS as id (id)}
				<a href={href(`/stats/${id}`)} aria-current={id === game ? 'page' : undefined}>
					{t(GAME_NAMES[id])}
				</a>
			{/each}
		</nav>
	{/if}
	{#if account.user}<p class="lead">{t('stats.leadAccount')}</p>{/if}
	{#if account.user === undefined}
		<div class="placeholder" aria-hidden="true"></div>
	{:else if account.user === null}
		<div class="card guest">
			<h2>{t('stats.guest.title')}</h2>
			<p>{t('stats.guest.body')}</p>
			<Button href={href('/signup')} icon="user">{t('stats.guest.cta')}</Button>
		</div>
	{:else}
		<!-- keyed by game, so switching game starts from a clean view -->
		{#key game}
			<View />
		{/key}
	{/if}
</article>

<style>
	.placeholder {
		min-height: 8rem;
	}
	.guest {
		display: grid;
		gap: 0.7rem;
		justify-items: start;
		padding: 1rem;
	}
	.guest h2,
	.guest p {
		margin: 0;
	}
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
	.lead {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.92rem;
	}
	.games {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.games a {
		padding: 0.3rem 0.9rem;
		border: var(--line) solid var(--sumi);
		border-radius: 999px;
		font-weight: 700;
		text-decoration: none;
		color: var(--text);
		background: var(--surface-2);
	}
	.games a[aria-current='page'] {
		background: var(--kinpaku);
		color: var(--sumi);
	}
</style>
