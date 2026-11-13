<script lang="ts">
	import { onMount } from 'svelte';
	import Avatar from '#lib/design/Avatar.svelte';
	import Button from '#lib/design/Button.svelte';
	import HistoryTabs from '#lib/design/HistoryTabs.svelte';
	import Modal from '#lib/design/Modal.svelte';
	import WordReview from '#lib/design/WordReview.svelte';
	import { clearHistory, deleteGame, loadHistory, type SavedGame } from '#lib/game/history.ts';
	import { getLocale, href, t, tn } from '#lib/i18n/index.ts';

	// null until the browser storage has been read, so the page never flashes "empty" for a saved history
	let games = $state<SavedGame[] | null>(null);
	let reviewing = $state<SavedGame | null>(null);
	let reviewOpen = $state(false);
	let confirmClear = $state(false);

	onMount(() => {
		games = loadHistory();
	});

	function review(game: SavedGame): void {
		reviewing = game;
		reviewOpen = true;
	}

	function remove(game: SavedGame): void {
		deleteGame(game.id);
		games = loadHistory();
	}

	function clearAll(): void {
		clearHistory();
		games = [];
		confirmClear = false;
	}

	const when = (at: number): string =>
		new Date(at).toLocaleString(getLocale(), { dateStyle: 'medium', timeStyle: 'short' });
</script>

<svelte:head><title>{t('history.title')} · {t('app.name')}</title></svelte:head>

<article class="history">
	<header class="top">
		<h1>{t('history.title')}</h1>
		<Button href={href('/')} variant="ghost" size="sm" icon="back">{t('history.back')}</Button>
	</header>
	<HistoryTabs current="games" />
	<p class="lead">{t('history.lead')}</p>

	{#if games === null}
		<div class="placeholder" aria-hidden="true"></div>
	{:else if games.length === 0}
		<div class="card empty">
			<p>{t('history.empty')}</p>
			<Button href={href('/')} icon="play">{t('history.play')}</Button>
		</div>
	{:else}
		<ul>
			{#each games as game (game.id)}
				{@const winner = game.players[0]}
				{@const me = game.players.find((p) => p.id === game.you)}
				<li class="card game">
					<div class="meta">
						<time datetime={new Date(game.at).toISOString()}>{when(game.at)}</time>
						<span class="mode">{t(`mode.${game.mode}.title` as const)}</span>
					</div>
					<div class="winner">
						{#if winner}<Avatar id={winner.avatar} size={40} label={false} />{/if}
						<div>
							<strong>{t('history.winner', { name: winner?.name ?? '?' })}</strong>
							<small>
								{#if me}{t('history.place', { place: me.place, n: game.players.length })} ·
								{/if}{tn('results.words', game.words.length)} · {tn(
									'history.players',
									game.players.length
								)}
							</small>
						</div>
					</div>
					<p class="ranking">
						{game.players.map((p) => `${p.name} ${p.score}`).join(' · ')}
					</p>
					<div class="actions">
						<Button size="sm" icon="book" onclick={() => review(game)}>{t('history.review')}</Button
						>
						<Button
							size="sm"
							variant="ghost"
							icon="close"
							iconOnly
							label={t('history.delete')}
							onclick={() => remove(game)}
						/>
					</div>
				</li>
			{/each}
		</ul>
		<Button variant="secondary" size="sm" onclick={() => (confirmClear = true)}>
			{t('history.clear')}
		</Button>
	{/if}
</article>

<Modal bind:open={reviewOpen} title={t('review.title')}>
	{#if reviewing}
		<WordReview words={reviewing.words} players={reviewing.players} you={reviewing.you} />
	{/if}
</Modal>

<Modal bind:open={confirmClear} title={t('history.clearTitle')}>
	<p class="confirm">{t('history.clearBody')}</p>
	<div class="confirm-actions">
		<Button variant="secondary" onclick={() => (confirmClear = false)}>{t('common.cancel')}</Button>
		<Button variant="danger" onclick={clearAll}>{t('history.clear')}</Button>
	</div>
</Modal>

<style>
	.history {
		display: grid;
		gap: 0.9rem;
		max-width: 40rem;
		margin: 0.5rem auto 2rem;
		padding: 0 1rem;
		box-sizing: border-box;
		justify-items: start;
	}
	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.8rem;
		width: 100%;
	}
	h1 {
		font-size: clamp(1.6rem, 6vw, 2.1rem);
	}
	.lead {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.95rem;
	}
	.placeholder {
		min-height: 8rem;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.8rem;
		width: 100%;
	}
	.card.game,
	.card.empty {
		display: grid;
		gap: 0.5rem;
		padding: 0.8rem 1rem;
	}
	.empty {
		width: 100%;
		box-sizing: border-box;
		justify-items: start;
	}
	.empty p {
		margin: 0;
	}
	.meta {
		display: flex;
		justify-content: space-between;
		gap: 0.6rem;
		font-size: 0.82rem;
		font-weight: 700;
		color: var(--text-mute);
	}
	.mode {
		color: var(--kinpaku);
	}
	.winner {
		display: flex;
		align-items: center;
		gap: 0.7rem;
	}
	.winner div {
		display: grid;
		min-width: 0;
	}
	.winner small {
		color: var(--text-mute);
	}
	.ranking {
		margin: 0;
		font-size: 0.85rem;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.actions {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.6rem;
	}
	.confirm {
		margin: 0 0 1rem;
	}
	.confirm-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.7rem;
		justify-content: flex-end;
	}
</style>
