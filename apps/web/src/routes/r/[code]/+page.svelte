<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import AvatarPicker from '#lib/design/AvatarPicker.svelte';
	import Button from '#lib/design/Button.svelte';
	import ErrorScreen from '#lib/design/ErrorScreen.svelte';
	import Game from '#lib/design/Game.svelte';
	import Lobby from '#lib/design/Lobby.svelte';
	import Mascot from '#lib/design/Mascot.svelte';
	import Results from '#lib/design/Results.svelte';
	import StatusBar from '#lib/design/StatusBar.svelte';
	import TextField from '#lib/design/TextField.svelte';
	import { GameSession } from '#lib/game/session.svelte.ts';
	import { loadProfile, saveProfile, sessionTokens } from '#lib/game/session.ts';
	import { t, type MessageKey } from '#lib/i18n/index.ts';

	const code = $derived(page.params.code?.toUpperCase() ?? '');

	let session = $state<GameSession | null>(null);
	let name = $state('');
	let avatar = $state(0);
	let nameError = $state('');

	const store = $derived(session?.store);
	const fatal = $derived(store?.fatal ?? null);

	onMount(() => {
		const profile = loadProfile();
		name = profile.name;
		avatar = profile.avatar;
		// The creator (and anybody reloading the page) goes straight in; invited friends confirm their pseudo first.
		const auto =
			sessionStorage.getItem(`hajime:autojoin:${code}`) === '1' ||
			sessionTokens.load(code) !== null;
		if (auto && profile.name) enter(false);
		return () => session?.destroy();
	});

	function enter(spectator: boolean): void {
		const clean = name.trim().slice(0, 20);
		if (!clean) {
			nameError = t('home.nickname');
			return;
		}
		nameError = '';
		saveProfile({ name: clean, avatar });
		session?.destroy();
		const next = new GameSession(code);
		session = next;
		next.connect({ name: clean, avatar, spectator });
	}

	function errorText(key: string, part: 'title' | 'body'): string {
		const full = `error.${key}.${part}` as MessageKey;
		const text = t(full);
		return text === full ? t(`error.generic.${part}` as MessageKey) : text;
	}

	const title = $derived(
		store?.phase === 'playing' ? `${store.turn?.fragment ?? ''} · Hajime` : `${code} · Hajime`
	);
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="robots" content="noindex" />
</svelte:head>

{#if fatal && session}
	<ErrorScreen title={errorText(fatal, 'title')} body={errorText(fatal, 'body')}>
		{#snippet actions()}
			{#if fatal === 'room_full' || fatal === 'wrong_phase'}
				<Button size="lg" icon="eye" onclick={() => enter(true)}>{t('error.watch')}</Button>
			{/if}
			{#if fatal === 'name_invalid'}
				<Button size="lg" onclick={() => (session = null)}>{t('join.enter')}</Button>
			{/if}
			<Button variant="secondary" href="/" icon="home">{t('error.home')}</Button>
		{/snippet}
	</ErrorScreen>
{:else if !session}
	<section class="join card" aria-label={t('join.title')}>
		<div class="art"><Mascot mood="calm" size={120} /></div>
		<h1>{t('join.title')}</h1>
		<p class="code">{code}</p>
		<form
			onsubmit={(e) => {
				e.preventDefault();
				enter(false);
			}}
		>
			<TextField
				label={t('home.nickname')}
				placeholder={t('home.nicknamePlaceholder')}
				bind:value={name}
				maxlength={20}
				error={nameError}
			/>
			<AvatarPicker bind:value={avatar} />
			<Button type="submit" size="lg" full icon="play">{t('join.enter')}</Button>
			<Button variant="ghost" full icon="eye" onclick={() => enter(true)}>{t('join.watch')}</Button>
		</form>
	</section>
{:else if !store?.loaded}
	<section class="loading" role="status">
		<Mascot mood="worried" size={110} />
		<p>{t('join.connecting')}</p>
	</section>
	<StatusBar
		status={store?.status ?? 'connecting'}
		reconnectIn={store?.reconnectIn}
		onretry={() => session?.client.reconnectNow()}
	/>
{:else}
	<StatusBar
		status={store.status}
		reconnectIn={store.reconnectIn}
		onretry={() => session?.client.reconnectNow()}
	/>
	{#if store.phase === 'playing'}
		<Game {session} />
	{:else if store.phase === 'finished' && store.results}
		<Results {session} />
	{:else}
		<Lobby {session} />
	{/if}
{/if}

<style>
	.join {
		display: grid;
		gap: 0.9rem;
		justify-items: center;
		max-width: 26rem;
		margin: 0.5rem auto;
		padding: 1.2rem;
		width: calc(100% - 2rem);
		box-sizing: border-box;
	}
	.join form {
		display: grid;
		gap: 0.9rem;
		width: 100%;
	}
	h1 {
		font-size: 1.7rem;
	}
	.code {
		margin: -0.4rem 0 0;
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: 1.6rem;
		letter-spacing: 0.2em;
		color: var(--kinpaku);
	}
	.loading {
		display: grid;
		justify-items: center;
		gap: 0.5rem;
		padding-top: 4rem;
		font-weight: 700;
	}
</style>
