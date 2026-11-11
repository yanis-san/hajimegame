<script lang="ts">
	import { t } from '#lib/i18n/index.ts';

	/**
	 * An example sentence for a word: Japanese first, then its translations. Only a part of the words have one
	 * (JMdict examples from Tatoeba), and only some of those have a French translation. Nothing is shown otherwise.
	 * `compact` keeps one line of Japanese and one translation (French when there is one) so it never grows a card.
	 */
	let {
		ja,
		fr,
		en,
		compact = false
	}: { ja: string; fr: string; en: string; compact?: boolean } = $props();
</script>

{#if ja}
	<div class="example" class:compact aria-label={t('game.example')}>
		<p class="ja" lang="ja">{ja}</p>
		{#if fr}
			<p class="tr"><span class="lang fr" title={t('game.exampleFr')}>FR</span>{fr}</p>
		{/if}
		{#if en && !(compact && fr)}
			<p class="tr"><span class="lang" title={t('game.exampleEn')}>EN</span>{en}</p>
		{/if}
	</div>
{/if}

<style>
	.example {
		display: grid;
		gap: 0.1rem;
		margin-top: 0.2rem;
		padding-top: 0.3rem;
		border-top: 2px dashed currentcolor;
	}
	p {
		margin: 0;
		font-size: 0.86rem;
		line-height: 1.3;
	}
	.ja {
		font-family: var(--font-kana);
		font-size: 0.98rem;
		font-weight: 700;
	}
	.tr {
		opacity: 0.9;
	}
	.compact p {
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.lang {
		display: inline-block;
		margin-right: 0.4rem;
		padding: 0 0.3rem;
		border: 2px solid currentcolor;
		border-radius: 6px;
		font-size: 0.62rem;
		font-weight: 700;
		vertical-align: 1px;
	}
	.lang.fr {
		background: var(--sumi);
		color: var(--washi);
		border-color: var(--sumi);
	}
</style>
