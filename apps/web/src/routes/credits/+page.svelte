<script lang="ts">
	import Button from '#lib/design/Button.svelte';
	import { t } from '#lib/i18n/index.ts';
</script>

<svelte:head><title>{t('credits.title')} · Hajime</title></svelte:head>

<article class="credits card">
	<h1>{t('credits.title')}</h1>

	<section>
		<h2>Dictionnaire</h2>
		<p>
			Les mots et leurs sens (anglais, et français quand JMdict le fournit) viennent du fichier <strong
				>JMdict</strong
			>, © Electronic Dictionary Research and Development Group (EDRDG), utilisé conformément à la
			<a href="https://www.edrdg.org/edrdg/licence.html" rel="noreferrer">licence du groupe</a>
			(<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noreferrer">CC BY-SA 4.0</a>).
			Le dictionnaire de jeu est une version filtrée et reformatée de ce fichier ; ses règles de
			filtrage sont documentées dans le dépôt.
		</p>
		<p>
			Les niveaux N5 à N1 sont une estimation fondée sur la fréquence des mots dans JMdict. Ce n’est
			pas la liste officielle du JLPT, qui n’est plus publiée.
		</p>
	</section>

	<section>
		<h2>Polices</h2>
		<p>
			Shippori Mincho, Zen Maru Gothic, Zen Kaku Gothic New et JetBrains Mono, sous licence SIL Open
			Font License 1.1, auto-hébergées via Fontsource.
		</p>
	</section>

	<section>
		<h2>Logiciels</h2>
		<p>
			Svelte et SvelteKit (MIT), WanaKana (MIT) pour la conversion romaji vers kana, FastAPI,
			msgspec et jaconv.
		</p>
	</section>

	<section>
		<h2>Illustrations et sons</h2>
		<p>
			La mascotte Bakuro, les avatars et les icônes sont dessinés pour Hajime. Les sons sont
			synthétisés dans le navigateur : aucun fichier audio tiers.
		</p>
	</section>

	<Button href="/" variant="secondary" icon="back">{t('credits.back')}</Button>
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
