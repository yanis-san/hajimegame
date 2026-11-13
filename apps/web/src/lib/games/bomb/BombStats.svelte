<script lang="ts">
	import { onMount } from 'svelte';
	import type { BombStatsMode, BombStatsView } from '@hajime/protocol';
	import Button from '#lib/design/Button.svelte';
	import Example from '#lib/design/Example.svelte';
	import Meanings from '#lib/design/Meanings.svelte';
	import Segmented from '#lib/design/Segmented.svelte';
	import { ApiError, getMyStats } from '#lib/game/api.ts';
	import { toHiragana } from '#lib/game/kana.ts';
	import { getLocale, href, t, tn } from '#lib/i18n/index.ts';

	/** The bomb game's dashboard: totals, activity, the words played most, and the latest ones. */
	let mode = $state<BombStatsMode>('all');
	let status = $state<'loading' | 'ready' | 'unavailable' | 'error'>('loading');
	let data = $state<BombStatsView | null>(null);
	let requested = 0;

	async function load(next: BombStatsMode): Promise<void> {
		const ticket = ++requested; // only the latest request may update the page
		status = data ? 'ready' : 'loading';
		try {
			const view = await getMyStats('bomb', next);
			if (ticket !== requested) return;
			data = view;
			status = 'ready';
		} catch (error) {
			if (ticket !== requested) return;
			status = error instanceof ApiError && error.status === 503 ? 'unavailable' : 'error';
		}
	}

	onMount(() => void load(mode));

	function choose(next: BombStatsMode): void {
		mode = next;
		void load(next);
	}

	const seconds = (ms: number | null): string =>
		ms === null
			? '-'
			: t('stats.seconds', {
					n: (ms / 1000).toLocaleString(getLocale(), {
						minimumFractionDigits: 1,
						maximumFractionDigits: 1
					})
				});
	// played_at is a UTC time without a zone marker
	const day = (iso: string): string =>
		new Date(iso.length > 10 ? `${iso}Z` : iso).toLocaleDateString(getLocale(), {
			day: 'numeric',
			month: 'short'
		});

	const summary = $derived(data?.summary);
	const winRate = $derived(
		summary && summary.games ? Math.round((100 * summary.wins) / summary.games) : 0
	);
	const peak = $derived(Math.max(1, ...(data?.activity.map((d) => d.games) ?? [1])));
	const totalGames = $derived(data?.activity.reduce((sum, d) => sum + d.games, 0) ?? 0);
</script>

<Segmented
	label={t('stats.mode')}
	value={mode}
	options={[
		{ value: 'all', label: t('stats.mode.all') },
		{ value: 'classic', label: t('mode.classic.title') },
		{ value: 'shiritori', label: t('mode.shiritori.title') }
	]}
	onchange={choose}
/>

{#if status === 'loading'}
	<div class="placeholder" aria-hidden="true"></div>
{:else if status === 'unavailable'}
	<div class="card note"><p>{t('stats.unavailable')}</p></div>
{:else if status === 'error'}
	<div class="card note">
		<p>{t('stats.error')}</p>
		<Button size="sm" variant="secondary" icon="refresh" onclick={() => void load(mode)}>
			{t('stats.retry')}
		</Button>
	</div>
{:else if data && summary}
	{#if summary.games === 0}
		<div class="card note">
			<p>{t('stats.empty')}</p>
			<Button href={href('/')} icon="play">{t('history.play')}</Button>
		</div>
	{:else}
		<dl class="cards">
			<div class="stat">
				<dt>{t('stats.games')}</dt>
				<dd>{summary.games}</dd>
			</div>
			<div class="stat">
				<dt>{t('stats.wins')}</dt>
				<dd>{summary.wins}<small>{winRate} %</small></dd>
			</div>
			<div class="stat">
				<dt>{t('stats.words')}</dt>
				<dd>{summary.words}</dd>
			</div>
			<div class="stat">
				<dt>{t('stats.distinct')}</dt>
				<dd>{summary.distinct_words}</dd>
			</div>
			<div class="stat">
				<dt>{t('stats.avg')}</dt>
				<dd>{seconds(summary.avg_response_ms)}</dd>
			</div>
			<div class="stat">
				<dt>{t('stats.fastest')}</dt>
				<dd>{seconds(summary.fastest_ms)}</dd>
			</div>
			<div class="stat">
				<dt>{t('stats.explosions')}</dt>
				<dd>{summary.explosions}</dd>
			</div>
			<div class="stat">
				<dt>{t('stats.longest')}</dt>
				<dd class="kana" lang="ja">{summary.longest_word || '-'}</dd>
			</div>
		</dl>

		<section class="card block">
			<h2>{t('stats.activity')}</h2>
			<svg
				class="bars"
				viewBox="0 0 300 64"
				role="img"
				aria-label={t('stats.activity.total', { n: totalGames })}
				preserveAspectRatio="none"
			>
				{#each data.activity as d, i (i)}
					{@const h = d.games ? Math.max(5, (54 * d.games) / peak) : 2}
					<rect class:zero={!d.games} x={i * 10 + 1} y={60 - h} width="8" height={h} rx="1.5">
						<title>{day(d.day)} · {d.games}</title>
					</rect>
				{/each}
			</svg>
		</section>

		<section class="card block">
			<h2>{t('stats.top')}</h2>
			<p class="hint">{t('stats.top.hint')}</p>
			{#if data.top_words.length === 0}
				<p class="none">{t('stats.noWords')}</p>
			{:else}
				<ol>
					{#each data.top_words as word (word.word)}
						<li>
							<div class="head">
								<span class="w" lang="ja">{word.word}</span>
								{#if toHiragana(word.reading) !== toHiragana(word.word)}<span class="r" lang="ja"
										>{word.reading}</span
									>{/if}
								<span class="count">{tn('stats.times', word.count)}</span>
							</div>
							<Meanings fr={word.meaning_fr} en={word.meaning_en} />
							<Example ja={word.example_ja} fr={word.example_fr} en={word.example_en} compact />
						</li>
					{/each}
				</ol>
			{/if}
		</section>

		<section class="card block">
			<h2>{t('stats.recent')}</h2>
			{#if data.recent_words.length === 0}
				<p class="none">{t('stats.noWords')}</p>
			{:else}
				<ol>
					{#each data.recent_words as word, i (i)}
						<li>
							<div class="head">
								<span class="w" lang="ja">{word.word}</span>
								{#if toHiragana(word.reading) !== toHiragana(word.word)}<span class="r" lang="ja"
										>{word.reading}</span
									>{/if}
								<span class="when"
									>{day(word.played_at)} · {t(`mode.${word.mode}.title` as const)}</span
								>
							</div>
							<Meanings fr={word.meaning_fr} en={word.meaning_en} />
							<Example ja={word.example_ja} fr={word.example_fr} en={word.example_en} compact />
						</li>
					{/each}
				</ol>
			{/if}
		</section>
	{/if}
{/if}

<style>
	h2 {
		font-size: 1.2rem;
		margin-bottom: 0.4rem;
	}
	.hint {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.92rem;
	}
	.placeholder {
		min-height: 12rem;
	}
	.note {
		display: grid;
		gap: 0.7rem;
		justify-items: start;
		padding: 0.9rem 1rem;
	}
	.note p,
	.none {
		margin: 0;
	}
	.cards {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.6rem;
		margin: 0;
	}
	@media (min-width: 560px) {
		.cards {
			grid-template-columns: repeat(4, 1fr);
		}
	}
	.stat {
		display: flex;
		flex-direction: column-reverse; /* the value above its label, while the DOM keeps term then value */
		gap: 0.1rem;
		padding: 0.6rem 0.7rem;
		background: var(--surface);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
	}
	dd {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.45rem;
		font-weight: 800;
		line-height: 1.15;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	dd small {
		margin-left: 0.4rem;
		font-family: var(--font-body, inherit);
		font-size: 0.75rem;
		color: var(--text-mute);
	}
	dd.kana {
		font-family: var(--font-kana);
	}
	dt {
		font-size: 0.78rem;
		font-weight: 700;
		color: var(--text-mute);
	}
	.block {
		padding: 0.8rem 1rem 1rem;
	}
	.bars {
		display: block;
		width: 100%;
		height: 4.5rem;
	}
	.bars rect {
		fill: var(--kinpaku);
		stroke: var(--sumi);
		stroke-width: 1;
		vector-effect: non-scaling-stroke;
	}
	.bars rect.zero {
		fill: var(--text-mute);
		stroke: none;
		opacity: 0.35;
	}
	ol {
		list-style: none;
		margin: 0.5rem 0 0;
		padding: 0;
		display: grid;
		gap: 0.55rem;
	}
	li {
		display: grid;
		gap: 0.15rem;
		padding: 0.45rem 0.8rem 0.55rem;
		background: var(--surface-2);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
	}
	.head {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.2rem 0.6rem;
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
	.count,
	.when {
		margin-left: auto;
		font-size: 0.78rem;
		font-weight: 700;
		color: var(--text-mute);
	}
</style>
