<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from './Button.svelte';
	import Captcha from './Captcha.svelte';
	import TextField from './TextField.svelte';
	import { account, refreshAccount } from '#lib/game/account.svelte.ts';
	import { ApiError } from '#lib/game/api.ts';
	import { signIn, signUp } from '#lib/game/auth.ts';
	import { href, t, type MessageKey } from '#lib/i18n/index.ts';

	/** Creating an account (`up`) or signing in (`in`): two pages, one form. */
	let { mode }: { mode: 'up' | 'in' } = $props();

	let username = $state('');
	let password = $state('');
	let email = $state('');
	let birthDate = $state('');
	let captcha = $state('');
	let busy = $state(false);
	let problem = $state('');
	let captchaBox: { reset(): void } | undefined = $state();

	// a date field refuses what cannot exist: no future date, nobody older than 120 (the server checks again)
	const today = new Date().toISOString().slice(0, 10);
	const oldest = `${new Date().getFullYear() - 120}-01-01`;

	const KNOWN = [
		'username_taken',
		'bad_username',
		'bad_password',
		'bad_email',
		'bad_birth_date',
		'bad_credentials',
		'captcha_failed',
		'accounts_unavailable',
		'rate_limited'
	] as const;

	/** The server answers with a short code; the words come from the interface language. */
	function explain(error: unknown): string {
		if (error instanceof ApiError && (KNOWN as readonly string[]).includes(error.detail)) {
			return t(`err.${error.detail}` as MessageKey);
		}
		return t('err.account_generic');
	}

	// Signed in (just now, or already): the account page is the place to be.
	$effect(() => {
		if (account.user) void goto(href('/account'), { replaceState: true });
	});

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		busy = true;
		problem = '';
		try {
			if (mode === 'up') await signUp({ username, password, email, birthDate, captcha });
			else await signIn({ username, password });
			password = '';
			await refreshAccount();
		} catch (e) {
			problem = explain(e);
			captchaBox?.reset(); // a captcha answer is good for one try only
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>{mode === 'up' ? t('account.tab.up') : t('account.tab.in')} · {t('app.name')}</title>
</svelte:head>

<article class="auth">
	<header class="top">
		<h1>{mode === 'up' ? t('account.tab.up') : t('account.tab.in')}</h1>
		<Button href={href('/')} variant="ghost" size="sm" icon="back">{t('account.back')}</Button>
	</header>

	<form class="card form" onsubmit={submit}>
		<div class="grid" class:two={mode === 'up'}>
			<TextField
				label={t('account.username')}
				bind:value={username}
				placeholder={mode === 'up' ? t('account.username.placeholder') : ''}
				maxlength={20}
				autocomplete="username"
				required
			/>
			<TextField
				label={t('account.password')}
				bind:value={password}
				type="password"
				placeholder={mode === 'up' ? t('account.password.placeholder') : ''}
				minlength={mode === 'up' ? 8 : undefined}
				autocomplete={mode === 'up' ? 'new-password' : 'current-password'}
				required
			/>
			{#if mode === 'up'}
				<TextField
					label={t('account.email')}
					bind:value={email}
					type="email"
					autocomplete="email"
					required
				/>
				<TextField
					label={t('account.birth')}
					bind:value={birthDate}
					type="date"
					min={oldest}
					max={today}
					autocomplete="bday"
					required
				/>
			{/if}
		</div>
		{#if mode === 'up'}
			<p class="note">{t('signup.note')}</p>
			<Captcha bind:this={captchaBox} bind:token={captcha} />
		{/if}
		{#if problem}<p class="problem" role="alert">{problem}</p>{/if}
		<Button type="submit" loading={busy} disabled={busy} full>
			{mode === 'up' ? t('account.signUp') : t('account.signIn')}
		</Button>
	</form>

	<p class="switch">
		{mode === 'up' ? t('signup.haveAccount') : t('login.noAccount')}
		<a href={href(mode === 'up' ? '/login' : '/signup')}
			>{mode === 'up' ? t('account.tab.in') : t('account.tab.up')}</a
		>
	</p>
</article>

<style>
	.auth {
		display: grid;
		gap: 0.7rem;
		max-width: 36rem;
		margin: 0 auto;
		padding: 0.4rem 1rem 1rem;
		box-sizing: border-box;
	}
	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.8rem;
	}
	h1 {
		font-size: clamp(1.5rem, 5.5vw, 2rem);
	}
	.card {
		display: grid;
		gap: 0.8rem;
		padding: 1rem;
	}
	.grid {
		display: grid;
		gap: 0.7rem 0.9rem;
		grid-template-columns: minmax(0, 1fr);
	}
	/* wide enough: the fields side by side, so the form is two rows instead of four */
	@media (min-width: 560px) {
		.grid.two {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.note {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.85rem;
	}
	.problem {
		margin: 0;
		color: var(--shu);
		font-weight: 700;
		font-size: 0.9rem;
	}
	.switch {
		margin: 0;
		text-align: center;
		color: var(--text-mute);
		font-size: 0.95rem;
	}
	.switch a {
		color: var(--kinpaku);
		font-weight: 700;
	}
</style>
