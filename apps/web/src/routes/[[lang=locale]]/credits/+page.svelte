<script lang="ts">
	import Button from '#lib/design/Button.svelte';
	import { href, t } from '#lib/i18n/index.ts';
</script>

<svelte:head><title>{t('credits.title')} · Hajime</title></svelte:head>

<article class="credits card">
	<h1>{t('credits.title')}</h1>

	<section>
		<h2>{t('credits.dictionary.title')}</h2>
		<p>{t('credits.dictionary.body')}</p>
		<p>
			<a href="https://www.edrdg.org/edrdg/licence.html" rel="noreferrer"
				>{t('credits.dictionary.licence')}</a
			>
			·
			<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noreferrer">CC BY-SA 4.0</a>
		</p>
	</section>

	<section>
		<h2>{t('credits.fonts.title')}</h2>
		<p>{t('credits.fonts.body')}</p>
	</section>

	<section>
		<h2>{t('credits.software.title')}</h2>
		<p>{t('credits.software.body')}</p>
	</section>

	<section>
		<h2>{t('credits.art.title')}</h2>
		<p>{t('credits.art.body')}</p>
	</section>

	<Button href={href('/')} variant="secondary" icon="back">{t('credits.back')}</Button>
</article>

<style>
	.credits {
		display: grid;
		gap: 1rem;
		max-width: 40rem;
		margin: 0.5rem auto 2rem;
		padding: 1.3rem;
		width: calc(100% - 2rem);
		box-sizing: border-box;
	}
	h2 {
		font-size: 1.2rem;
		margin-bottom: 0.3rem;
	}
	p {
		margin: 0 0 0.6rem;
	}
	a {
		color: var(--kinpaku);
		font-weight: 700;
	}
</style>
