<script lang="ts">
	import { onMount } from 'svelte';
	import { flip } from 'svelte/animate';
	import { href, t, tn } from '#lib/i18n/index.ts';
	import { haptic } from '#lib/game/haptics.ts';
	import type { GameSession } from '#lib/game/session.svelte.ts';
	import { buildSavedGame, loadHistory, saveGame } from '#lib/game/history.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import Avatar from './Avatar.svelte';
	import Button from './Button.svelte';
	import Icon from './Icon.svelte';
	import Mascot from './Mascot.svelte';
	import Modal from './Modal.svelte';
	import Particles from './Particles.svelte';
	import WordReview from './WordReview.svelte';

	let { session }: { session: GameSession } = $props();
	const store = $derived(session.store);

	let particles: Particles | undefined = $state();
	let ordered = $state(false);
	let reviewOpen = $state(false);
	// true once this game is in the history of this device (a spectator's history is not kept)
	let saved = $state(false);

	const rows = $derived(store.results ?? []);
	// First show the seat order, then let the rows slide into their final places (animate:flip).
	const list = $derived(
		ordered
			? rows
			: [...rows].sort(
					(a, b) =>
						store.players.findIndex((p) => p.id === a.player_id) -
						store.players.findIndex((p) => p.id === b.player_id)
				)
	);
	const winner = $derived(store.player(store.winnerId ?? ''));
	const iWon = $derived(store.winnerId !== null && store.winnerId === store.you);

	onMount(() => {
		const game = store.spectator
			? null
			: buildSavedGame(
					{
						room: store.room,
						you: store.you,
						mode: store.settings.mode,
						players: store.players,
						results: store.results ?? [],
						words: store.words
					},
					Date.now()
				);
		if (game) saved = saveGame(game) || loadHistory().some((g) => g.id === game.id);
		const timer = setTimeout(() => (ordered = true), 700);
		const show = setTimeout(() => {
			sfx.play(iWon ? 'win' : 'lose');
			window.setTimeout(() => sfx.voice(iWon ? 'shouri' : 'zannen'), iWon ? 900 : 250);
			haptic('win');
			particles?.hanabi();
		}, 900);
		return () => {
			clearTimeout(timer);
			clearTimeout(show);
		};
	});
</script>

<Particles bind:this={particles} />

<section class="results" aria-label={t('results.title')}>
	<div class="hero card">
		<div class="mascot"><Mascot mood="relief" size={120} /></div>
		<div>
			<p class="eyebrow">{t('results.title')}</p>
			<h1 aria-live="polite">
				{#if iWon}{t('results.you')}{:else if winner}{t('results.winner', {
						name: winner.name
					})}{/if}
			</h1>
		</div>
	</div>

	<ol class="rank card">
		{#each list as row (row.player_id)}
			{@const p = store.player(row.player_id)}
			<li
				animate:flip={{ duration: 450 }}
				class:first={row.place === 1}
				class:you={row.player_id === store.you}
			>
				<span class="place">
					{#if row.place === 1}<Icon name="crown" size={22} />{:else}{row.place}{/if}
				</span>
				<Avatar id={p?.avatar ?? row.avatar} size={44} label={false} />
				<span class="who">
					<strong>{p?.name ?? row.name}</strong>
					<small
						>{row.longest
							? t('results.longest', { word: row.longest })
							: tn('results.words', row.words)}</small
					>
				</span>
				<span class="score">{t('results.score', { n: row.score })}</span>
			</li>
		{/each}
	</ol>

	<div class="cta">
		{#if store.isHost}
			<Button size="lg" full icon="refresh" onclick={() => session.rematch()}
				>{t('results.rematch')}</Button
			>
		{:else if !store.spectator}
			<p class="wait">{t('results.waitRematch')}</p>
		{/if}
		<div class="pair">
			<Button variant="secondary" full icon="book" onclick={() => (reviewOpen = true)}>
				{t('results.review')}
			</Button>
			<Button
				variant="ghost"
				full
				icon="home"
				onclick={() => {
					session.leave();
					location.assign(href('/'));
				}}
			>
				{t('results.leave')}
			</Button>
		</div>
		{#if saved}<p class="saved">{t('results.saved')}</p>{/if}
	</div>
</section>

<Modal bind:open={reviewOpen} title={t('review.title')}>
	<WordReview
		words={store.words}
		players={rows.map((r) => ({ id: r.player_id, name: r.name }))}
		you={store.you}
	/>
</Modal>

<style>
	.results {
		display: grid;
		gap: 0.9rem;
		max-width: 38rem;
		margin: 0 auto;
		padding: 0.5rem 0.9rem calc(1.5rem + env(safe-area-inset-bottom));
	}
	.hero {
		display: flex;
		align-items: center;
		gap: 0.9rem;
		padding: 0.8rem 1rem;
		background: var(--kinpaku);
		color: var(--sumi);
	}
	.eyebrow {
		margin: 0;
		font-weight: 700;
	}
	h1 {
		font-size: clamp(1.7rem, 7vw, 2.3rem);
	}
	.rank {
		list-style: none;
		margin: 0;
		padding: 0.6rem;
		display: grid;
		gap: 0.5rem;
	}
	li {
		display: grid;
		grid-template-columns: 2.2rem auto 1fr auto;
		align-items: center;
		gap: 0.7rem;
		padding: 0.4rem 0.7rem;
		background: var(--surface-2);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
	}
	li.first {
		background: var(--kinpaku);
		color: var(--sumi);
	}
	li.you:not(.first) {
		border-color: var(--washi);
	}
	.place {
		display: grid;
		place-items: center;
		font-family: var(--font-display);
		font-weight: 800;
		font-size: 1.5rem;
	}
	.who {
		display: grid;
		min-width: 0;
	}
	.who strong,
	.who small {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	small {
		opacity: 0.85;
		font-family: var(--font-kana);
	}
	.score {
		font-family: var(--font-mono);
		font-weight: 700;
	}
	.cta {
		display: grid;
		gap: 0.7rem;
	}
	.pair {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.7rem;
	}
	.saved {
		margin: 0;
		text-align: center;
		font-size: 0.85rem;
		color: var(--text-mute);
	}
	.wait {
		margin: 0;
		text-align: center;
		font-weight: 700;
		color: var(--text-mute);
	}
</style>
