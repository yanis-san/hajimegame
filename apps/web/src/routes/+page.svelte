<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import AvatarPicker from '#lib/design/AvatarPicker.svelte';
	import Banner from '#lib/design/Banner.svelte';
	import Bomb from '#lib/design/Bomb.svelte';
	import Button from '#lib/design/Button.svelte';
	import TextField from '#lib/design/TextField.svelte';
	import { ApiError, createRoom, roomExists } from '#lib/game/api.ts';
	import { loadProfile, saveProfile } from '#lib/game/session.ts';
	import { t } from '#lib/i18n/index.ts';
	import type { Mood } from '#lib/design/Mascot.svelte';

	let name = $state('');
	let avatar = $state(0);
	let code = $state('');
	let busy = $state<'create' | 'join' | null>(null);
	let error = $state('');
	let nameError = $state('');
	let mood = $state<Mood | undefined>(undefined);

	onMount(() => {
		const profile = loadProfile();
		name = profile.name;
		avatar = profile.avatar;
	});

	function remember(): boolean {
		const clean = name.trim().slice(0, 20);
		if (!clean) {
			nameError = t('home.nickname');
			return false;
		}
		nameError = '';
		saveProfile({ name: clean, avatar });
		return true;
	}

	async function create(): Promise<void> {
		error = '';
		if (!remember()) return;
		busy = 'create';
		try {
			const room = await createRoom();
			sessionStorage.setItem(`hajime:autojoin:${room.code}`, '1');
			await goto(`/r/${room.code}`);
		} catch (e) {
			error =
				e instanceof ApiError && e.status === 429 ? t('home.errorRate') : t('home.errorCreate');
			busy = null;
		}
	}

	async function join(event: Event): Promise<void> {
		event.preventDefault();
		error = '';
		const clean = code.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
		if (clean.length < 4 || !remember()) return;
		busy = 'join';
		try {
			if (!(await roomExists(clean))) {
				error = t('home.errorNotFound');
				busy = null;
				return;
			}
			sessionStorage.setItem(`hajime:autojoin:${clean}`, '1');
			await goto(`/r/${clean}`);
		} catch {
			error = t('home.errorCreate');
			busy = null;
		}
	}

	function poke(): void {
		mood = 'boom';
		setTimeout(() => (mood = undefined), 650);
	}
</script>

<svelte:head>
	<title>Hajime · {t('app.tagline')}</title>
	<meta name="description" content={t('app.tagline')} />
</svelte:head>

<div class="home">
	<section class="hero">
		<button class="bomb-btn" type="button" onclick={poke} aria-label="Bakuro">
			<Bomb fragment="はじ" {mood} size={170} showTimer={false} />
		</button>
		<h1>{t('app.tagline')}</h1>
	</section>

	<section class="card form" aria-label={t('home.create')}>
		<TextField
			label={t('home.nickname')}
			placeholder={t('home.nicknamePlaceholder')}
			bind:value={name}
			maxlength={20}
			error={nameError}
			enterkeyhint="go"
		/>
		<fieldset>
			<legend>{t('home.avatar')}</legend>
			<AvatarPicker bind:value={avatar} />
		</fieldset>

		<Button
			size="lg"
			full
			icon="play"
			loading={busy === 'create'}
			disabled={busy !== null}
			onclick={create}
		>
			{busy === 'create' ? t('home.creating') : t('home.create')}
		</Button>

		<p class="or"><span>{t('home.or')}</span></p>

		<form class="join" onsubmit={join}>
			<TextField
				label={t('home.codeLabel')}
				placeholder={t('home.codePlaceholder')}
				bind:value={code}
				maxlength={8}
				uppercase
				inputmode="text"
			/>
			<Button
				type="submit"
				variant="gold"
				disabled={busy !== null || code.trim().length < 4}
				loading={busy === 'join'}
			>
				{t('home.join')}
			</Button>
		</form>

		{#if error}
			<Banner tone="error" icon="bolt" live="assertive">{error}</Banner>
		{/if}
	</section>

	<footer>
		<a href="/credits">{t('footer.credits')}</a>
		<a href="/design">{t('footer.design')}</a>
	</footer>
</div>

<style>
	.home {
		display: grid;
		gap: 1.1rem;
		max-width: 28rem;
		margin: 0 auto;
		padding: 0.5rem 1rem calc(1.5rem + env(safe-area-inset-bottom));
	}
	.hero {
		display: grid;
		justify-items: center;
		gap: 0.9rem;
		padding-top: 0.5rem;
	}
	.bomb-btn {
		display: block;
		padding: 0 0 0.5rem;
		border: none;
		background: none;
		color: inherit;
		cursor: pointer;
	}
	h1 {
		max-width: 18ch;
		text-align: center;
		font-size: clamp(1.5rem, 6.5vw, 1.9rem);
		line-height: 1.25;
	}
	.form {
		display: grid;
		gap: 1rem;
		padding: 1.1rem;
	}
	fieldset {
		margin: 0;
		padding: 0;
		border: none;
		display: grid;
		gap: 0.4rem;
	}
	legend {
		padding: 0;
		margin-bottom: 0.4rem;
		font-weight: 700;
		font-size: 0.95rem;
	}
	.or {
		display: flex;
		align-items: center;
		gap: 0.8rem;
		margin: 0;
		color: var(--text-mute);
		font-weight: 700;
	}
	.or::before,
	.or::after {
		content: '';
		flex: 1;
		border-top: var(--line) dashed var(--text-mute);
		opacity: 0.5;
	}
	.join {
		display: grid;
		grid-template-columns: 1fr auto;
		align-items: end;
		gap: 0.6rem;
	}
	footer {
		display: flex;
		justify-content: center;
		gap: 1.4rem;
		font-size: 0.9rem;
	}
	footer a {
		color: var(--text-mute);
		font-weight: 700;
		padding: 0.6rem 0.2rem;
	}
</style>
