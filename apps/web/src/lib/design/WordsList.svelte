<script lang="ts">
	import type { PlayerView, WordView } from '@hajime/protocol';
	import { t } from '#lib/i18n/index.ts';
	import Example from './Example.svelte';
	import Meanings from './Meanings.svelte';

	let { words, players }: { words: WordView[]; players: PlayerView[] } = $props();

	const recent = $derived([...words].reverse().slice(0, 30));
	const nameOf = (id: string): string => players.find((p) => p.id === id)?.name ?? '';
</script>

<section class="words" aria-label={t('game.words')}>
	<h2>{t('game.words')}</h2>
	{#if recent.length === 0}
		<p class="empty">{t('game.wordsEmpty')}</p>
	{:else}
		<ol>
			{#each recent as word, i (word.turn + word.word)}
				<li class:latest={i === 0}>
					<div class="head">
						<span class="w">{word.word}</span>
						{#if word.reading !== word.word}<span class="r">{word.reading}</span>{/if}
					</div>
					<Meanings fr={word.meaning_fr} en={word.meaning_en} />
					<Example ja={word.example_ja} fr={word.example_fr} en={word.example_en} />
					<span class="by">{nameOf(word.player_id)}</span>
				</li>
			{/each}
		</ol>
	{/if}
</section>

<style>
	.words {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
	}
	h2 {
		font-size: 1.15rem;
		margin-bottom: 0.6rem;
	}
	.empty {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.95rem;
	}
	ol {
		list-style: none;
		margin: 0;
		padding: 0 0.3rem 0.5rem 0;
		display: grid;
		gap: 0.55rem;
		align-content: start;
		overflow-y: auto;
		min-height: 0;
	}
	li {
		display: grid;
		gap: 0.15rem;
		padding: 0.45rem 0.8rem 0.5rem;
		background: var(--surface);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
	}
	li.latest {
		background: var(--matcha);
		color: var(--sumi);
	}
	.head {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	.w {
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.4rem;
		line-height: 1.25;
	}
	.r {
		font-family: var(--font-kana);
		font-size: 0.9rem;
		opacity: 0.8;
	}
	.by {
		font-size: 0.72rem;
		opacity: 0.75;
	}
</style>
