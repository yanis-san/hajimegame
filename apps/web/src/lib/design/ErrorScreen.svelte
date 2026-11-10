<script lang="ts">
	import type { Snippet } from 'svelte';
	import Button from './Button.svelte';
	import Mascot from './Mascot.svelte';
	import { t } from '#lib/i18n/index.ts';

	let {
		title,
		body,
		actions,
		mood = 'boom'
	}: {
		title: string;
		body: string;
		actions?: Snippet;
		mood?: 'boom' | 'worried' | 'calm';
	} = $props();
</script>

<section class="error" role="alert">
	<div class="art"><Mascot {mood} size={170} /></div>
	<h1>{title}</h1>
	<p>{body}</p>
	<div class="actions">
		{#if actions}
			{@render actions()}
		{:else}
			<Button href="/" icon="home" size="lg">{t('error.home')}</Button>
		{/if}
	</div>
</section>

<style>
	.error {
		display: grid;
		justify-items: center;
		gap: 0.8rem;
		max-width: 26rem;
		margin: 0 auto;
		padding: 2rem 1.2rem;
		text-align: center;
	}
	h1 {
		font-size: 1.9rem;
	}
	p {
		margin: 0;
		color: var(--text-mute);
		font-size: 1.05rem;
	}
	.actions {
		display: grid;
		gap: 0.7rem;
		width: 100%;
		margin-top: 0.6rem;
	}
</style>
