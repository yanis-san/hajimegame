<script lang="ts">
	import { t } from '#lib/i18n/index.ts';

	/** Meaning in French and in English. French is listed first and only shown when JMdict has it. */
	let { fr, en }: { fr: string; en: string } = $props();
</script>

<div class="meanings">
	{#if fr}
		<p><span class="lang fr" title={t('game.meaningFr')}>FR</span>{fr}</p>
	{/if}
	{#if en}
		<p><span class="lang" title={t('game.meaningEn')}>EN</span>{en}</p>
	{/if}
	{#if !fr && !en}
		<p class="none">{t('game.noMeaning')}</p>
	{/if}
</div>

<style>
	.meanings {
		display: grid;
		gap: 0.1rem;
	}
	p {
		margin: 0;
		font-size: 0.92rem;
		line-height: 1.3;
	}
	.lang {
		display: inline-block;
		margin-right: 0.4rem;
		padding: 0 0.35rem;
		border: 2px solid currentcolor;
		border-radius: 6px;
		font-size: 0.66rem;
		font-weight: 700;
		vertical-align: 1px;
	}
	.lang.fr {
		background: var(--sumi);
		color: var(--washi);
		border-color: var(--sumi);
	}
	.none {
		opacity: 0.8;
	}
</style>
