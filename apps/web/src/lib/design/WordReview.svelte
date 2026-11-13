<script lang="ts">
	import type { WordView } from '@hajime/protocol';
	import { toHiragana } from '#lib/game/kana.ts';
	import { t, tn } from '#lib/i18n/index.ts';
	import Example from './Example.svelte';
	import Meanings from './Meanings.svelte';
	import Segmented from './Segmented.svelte';

	/**
	 * Every word of one game, in the order they were played, with meanings and example sentences.
	 * Used by the end-of-game screen and by the history page.
	 */
	let {
		words,
		players,
		you
	}: { words: WordView[]; players: { id: string; name: string }[]; you: string } = $props();

	let filter = $state<'all' | 'mine'>('all');

	const mine = $derived(words.filter((w) => w.player_id === you));
	const shown = $derived(filter === 'mine' ? mine : words);
	const nameOf = (id: string): string => players.find((p) => p.id === id)?.name ?? '?';
</script>

<div class="review">
	{#if mine.length > 0 && mine.length < words.length}
		<Segmented
			label={t('review.filter')}
			value={filter}
			options={[
				{ value: 'all', label: `${t('review.all')} · ${words.length}` },
				{ value: 'mine', label: `${t('review.mine')} · ${mine.length}` }
			]}
			onchange={(v) => (filter = v)}
		/>
	{/if}

	{#if shown.length === 0}
		<p class="empty">{t('review.empty')}</p>
	{:else}
		<p class="count">{tn('results.words', shown.length)}</p>
		<ol>
			{#each shown as word, i (word.turn + word.word)}
				<li class:mine={word.player_id === you}>
					<div class="head">
						<span class="n">{i + 1}</span>
						<span class="w" lang="ja">{word.word}</span>
						{#if toHiragana(word.reading) !== toHiragana(word.word)}<span class="r" lang="ja"
								>{word.reading}</span
							>{/if}
						<span class="by">{nameOf(word.player_id)}</span>
					</div>
					<Meanings fr={word.meaning_fr} en={word.meaning_en} />
					<Example ja={word.example_ja} fr={word.example_fr} en={word.example_en} />
				</li>
			{/each}
		</ol>
	{/if}
</div>

<style>
	.review {
		display: grid;
		gap: 0.7rem;
	}
	.count {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.9rem;
		font-weight: 700;
	}
	.empty {
		margin: 0;
		color: var(--text-mute);
	}
	ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.55rem;
	}
	li {
		display: grid;
		gap: 0.15rem;
		padding: 0.45rem 0.8rem 0.55rem;
		background: var(--surface);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
	}
	li.mine {
		background: var(--matcha);
		color: var(--sumi);
	}
	.head {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.2rem 0.6rem;
	}
	.n {
		min-width: 1.5rem;
		font-size: 0.78rem;
		font-weight: 700;
		opacity: 0.7;
	}
	.w {
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.35rem;
		line-height: 1.25;
	}
	.r {
		font-family: var(--font-kana);
		font-size: 0.9rem;
		opacity: 0.8;
	}
	.by {
		margin-left: auto;
		font-size: 0.74rem;
		font-weight: 700;
		opacity: 0.75;
	}
</style>
