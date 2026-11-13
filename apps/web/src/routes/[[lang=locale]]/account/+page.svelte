<script lang="ts">
	import Button from '#lib/design/Button.svelte';
	import Modal from '#lib/design/Modal.svelte';
	import TextField from '#lib/design/TextField.svelte';
	import { account, refreshAccount } from '#lib/game/account.svelte.ts';
	import { ApiError } from '#lib/game/api.ts';
	import { deleteAccount, resendVerification, signOut } from '#lib/game/auth.ts';
	import { href, t, type MessageKey } from '#lib/i18n/index.ts';

	let busy = $state(false);
	let problem = $state('');
	let confirmOpen = $state(false);
	let confirmPassword = $state('');

	const KNOWN = ['bad_credentials', 'email_unavailable', 'rate_limited'] as const;

	/** The server answers with a short code; the words come from the interface language. */
	function explain(error: unknown): string {
		if (error instanceof ApiError && (KNOWN as readonly string[]).includes(error.detail)) {
			return t(`err.${error.detail}` as MessageKey);
		}
		return t('err.account_generic');
	}

	let resending = $state(false);
	let resent = $state(false);

	async function sendAgain(): Promise<void> {
		if (resending) return;
		resending = true;
		resent = false;
		problem = '';
		try {
			await resendVerification();
			resent = true;
		} catch (e) {
			problem = explain(e);
		} finally {
			resending = false;
		}
	}

	async function leave(): Promise<void> {
		busy = true;
		try {
			await signOut();
		} finally {
			await refreshAccount();
			busy = false;
		}
	}

	async function remove(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		busy = true;
		problem = '';
		try {
			await deleteAccount(confirmPassword);
			confirmOpen = false;
			confirmPassword = '';
			await refreshAccount();
		} catch (e) {
			problem = explain(e);
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>{t('account.title')} · {t('app.name')}</title></svelte:head>

<article class="account">
	<header class="top">
		<h1>{t('account.title')}</h1>
		<Button href={href('/')} variant="ghost" size="sm" icon="back">{t('account.back')}</Button>
	</header>

	{#if account.user === undefined}
		<div class="placeholder" aria-hidden="true"></div>
	{:else if account.user}
		<section class="card">
			<p class="who">{t('account.signedIn')} <strong>{account.user.username}</strong></p>
			<p class="mail">
				{#if account.user.email}
					{account.user.email}{#if !account.user.email_verified}
						· {t('account.emailPending')}{/if}
				{:else}
					{t('account.emailNone')}
				{/if}
			</p>
			{#if account.user.email && !account.user.email_verified}
				<div class="confirm-mail">
					<p>
						{resent
							? t('account.emailSent', { email: account.user.email })
							: t('account.emailToConfirm')}
					</p>
					<Button
						size="sm"
						variant="secondary"
						loading={resending}
						disabled={resending}
						onclick={sendAgain}
					>
						{t('account.resend')}
					</Button>
					{#if problem}<p class="problem" role="alert">{problem}</p>{/if}
				</div>
			{/if}
			<div class="actions">
				<Button href={href('/stats')} icon="trophy">{t('account.stats')}</Button>
				<Button variant="secondary" disabled={busy} onclick={leave}>{t('account.signOut')}</Button>
			</div>
		</section>
		<Button
			variant="danger"
			size="sm"
			onclick={() => {
				problem = '';
				confirmOpen = true;
			}}>{t('account.delete')}</Button
		>
	{:else}
		<p class="lead">{t('account.lead')}</p>
		<div class="choices">
			<Button href={href('/signup')} icon="user">{t('account.tab.up')}</Button>
			<Button href={href('/login')} variant="secondary">{t('account.tab.in')}</Button>
		</div>
	{/if}
</article>

<Modal bind:open={confirmOpen} title={t('account.deleteTitle')}>
	{#if confirmOpen}
		<form class="delete" onsubmit={remove}>
			<p>{t('account.deleteBody')}</p>
			<TextField
				label={t('account.password')}
				bind:value={confirmPassword}
				type="password"
				autocomplete="current-password"
				required
			/>
			{#if problem}<p class="problem" role="alert">{problem}</p>{/if}
			<div class="confirm-actions">
				<Button variant="secondary" onclick={() => (confirmOpen = false)}
					>{t('common.cancel')}</Button
				>
				<Button type="submit" variant="danger" loading={busy} disabled={busy}>
					{t('account.deleteConfirm')}
				</Button>
			</div>
		</form>
	{/if}
</Modal>

<style>
	.account {
		display: grid;
		gap: 0.9rem;
		max-width: 30rem;
		margin: 0.5rem auto 2rem;
		padding: 0 1rem;
		box-sizing: border-box;
		justify-items: start;
	}
	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.8rem;
		width: 100%;
	}
	h1 {
		font-size: clamp(1.6rem, 6vw, 2.1rem);
	}
	.lead {
		margin: 0;
		color: var(--text-mute);
		font-size: 0.95rem;
	}
	.placeholder {
		min-height: 8rem;
	}
	.account > :global(.seg),
	.card {
		width: 100%;
		box-sizing: border-box;
	}
	.card {
		display: grid;
		gap: 0.7rem;
		padding: 1rem;
	}
	.who,
	.mail {
		margin: 0;
	}
	.mail {
		color: var(--text-mute);
		font-size: 0.9rem;
	}
	.confirm-mail {
		display: grid;
		justify-items: start;
		gap: 0.5rem;
		padding: 0.7rem 0.8rem;
		border: var(--line) dashed var(--text-mute);
		border-radius: var(--radius-sm);
	}
	.confirm-mail p {
		margin: 0;
		font-size: 0.92rem;
	}
	.choices {
		display: flex;
		flex-wrap: wrap;
		gap: 0.7rem;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.7rem;
	}
	.problem {
		margin: 0;
		color: var(--shu);
		font-weight: 700;
		font-size: 0.9rem;
	}
	.delete {
		display: grid;
		gap: 0.9rem;
	}
	.delete p {
		margin: 0;
	}
	.confirm-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.7rem;
		justify-content: flex-end;
	}
</style>
