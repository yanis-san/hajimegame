<script lang="ts">
	import type { PlayerView, WordView } from '@hajime/protocol';
	import { t } from '#lib/i18n/index.ts';

	let { words, players }: { words: WordView[]; players: PlayerView[] } = $props();

	const recent = $derived([...words].reverse().slice(0, 14));
	const nameOf = (id: string): string => players.find((p) => p.id === id)?.name ?? '';
</script>

<section class="words" aria-label={t('game.words')}>
	<h2>{t('game.words')}</h2>
	{#if recent.length === 0}
		<p class="empty">{t('game.wordsEmpty')}</p>
	{:else}
		<ol>
			{#each recent as word, i (word.turn + word.word)}
				<li class:latest={i === 0} title={nameOf(word.player_id)}>
					<span class="w">{word.word}</span>
					<span class="by">{nameOf(word.player_id)}</span>
				</li>
			{/each}
		</ol>
	{/if}
</section>

<style>
	.words {
		min-width: 0;
	}
	h2 {
		display: none;
		font-size: 1.1rem;
		margin-bottom: 0.5rem;
	}
	.empty {
		display: none;
		margin: 0;
		color: var(--text-mute);
		font-size: 0.9rem;
		text-align: center;
	}
	@media (min-width: 900px) {
		.empty {
			display: block;
		}
	}
	ol {
		list-style: none;
		margin: 0;
		padding: 0.1rem 0.1rem 0.4rem;
		display: flex;
		gap: 0.45rem;
		overflow-x: auto;
		scrollbar-width: none;
	}
	li {
		flex: none;
		display: grid;
		padding: 0.1rem 0.7rem 0.25rem;
		background: var(--surface);
		border: var(--line) solid var(--sumi);
		border-radius: 11px;
		box-shadow: var(--shadow-sm);
	}
	li.latest {
		background: var(--matcha);
		color: var(--sumi);
	}
	.w {
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.15rem;
		line-height: 1.25;
	}
	.by {
		font-size: 0.7rem;
		opacity: 0.8;
	}
	@media (min-width: 900px) {
		h2 {
			display: block;
		}
		ol {
			flex-direction: column;
			overflow: auto;
			max-height: calc(var(--vvh, 100dvh) - 11rem);
		}
		li {
			grid-template-columns: 1fr auto;
			align-items: baseline;
			gap: 0.6rem;
		}
	}
</style>
