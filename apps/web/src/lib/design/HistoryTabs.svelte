<script lang="ts">
	import { ACCOUNTS } from '#lib/game/config.ts';
	import { href, t } from '#lib/i18n/index.ts';

	/** Switches between the two pages about past games: the games themselves, and the statistics. */
	let { current }: { current: 'games' | 'stats' } = $props();
</script>

{#if ACCOUNTS}
	<nav class="tabs" aria-label={t('stats.tabs')}>
		<a href={href('/history')} aria-current={current === 'games' ? 'page' : undefined}>
			{t('stats.tab.games')}
		</a>
		<a href={href('/stats')} aria-current={current === 'stats' ? 'page' : undefined}>
			{t('stats.tab.stats')}
		</a>
	</nav>
{/if}

<style>
	.tabs {
		display: flex;
		gap: 0.5rem;
		width: 100%;
	}
	a {
		flex: 1;
		display: grid;
		place-items: center;
		min-height: 44px;
		padding: 0.3rem 1rem;
		color: var(--text);
		text-decoration: none;
		font-weight: 700;
		background: var(--surface-2);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
	}
	a[aria-current='page'] {
		background: var(--kinpaku);
		color: var(--sumi);
	}
	a:focus-visible {
		outline: 3px solid var(--kinpaku);
		outline-offset: 2px;
	}
</style>
