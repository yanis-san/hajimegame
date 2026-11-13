<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import Button from '#lib/design/Button.svelte';
	import { refreshAccount } from '#lib/game/account.svelte.ts';
	import { verifyEmail } from '#lib/game/auth.ts';
	import { href, t } from '#lib/i18n/index.ts';

	// the secret of the link is in the address: it is read once, here, and sent to the server
	type State = 'checking' | 'ok' | 'bad' | 'missing' | 'error';
	let state = $state<State>('checking');

	onMount(async () => {
		const token = page.url.searchParams.get('token')?.trim();
		if (!token) {
			state = 'missing';
			return;
		}
		try {
			state = (await verifyEmail(token)) ? 'ok' : 'bad';
			if (state === 'ok') await refreshAccount();
		} catch {
			state = 'error'; // the server did not answer: the link itself may be good, so say to try again
		}
	});
</script>

<svelte:head>
	<title>{t('verify.title')} · {t('app.name')}</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<article class="verify card" aria-live="polite">
	<h1>{t('verify.title')}</h1>
	{#if state === 'checking'}
		<p>{t('verify.checking')}</p>
	{:else if state === 'ok'}
		<p class="ok">{t('verify.ok')}</p>
		<Button href={href('/account')} icon="user">{t('verify.toAccount')}</Button>
	{:else if state === 'error'}
		<p>{t('verify.error')}</p>
		<Button variant="secondary" onclick={() => location.reload()}>{t('stats.retry')}</Button>
	{:else}
		<p>{state === 'missing' ? t('verify.missing') : t('verify.bad')}</p>
		<Button href={href('/account')} variant="secondary">{t('verify.toAccount')}</Button>
	{/if}
</article>

<style>
	.verify {
		display: grid;
		gap: 0.9rem;
		justify-items: start;
		max-width: 30rem;
		margin: 1.5rem auto 2rem;
		padding: 1.2rem 1.2rem 1.4rem;
		box-sizing: border-box;
	}
	h1 {
		font-size: clamp(1.5rem, 6vw, 2rem);
	}
	p {
		margin: 0;
	}
	.ok {
		font-weight: 700;
		color: var(--matcha);
	}
</style>
