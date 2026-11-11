<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import AvatarPicker from '#lib/design/AvatarPicker.svelte';
	import Banner from '#lib/design/Banner.svelte';
	import Bomb from '#lib/design/Bomb.svelte';
	import Button from '#lib/design/Button.svelte';
	import ModePicker from '#lib/design/ModePicker.svelte';
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
	let mode = $state<'classic' | 'shiritori'>('classic');

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
			const room = await createRoom(mode);
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
			<!-- two sizes switched by CSS only, so nothing resizes after the page loads -->
			<span class="bomb-small"><Bomb fragment="はじ" {mood} size={120} showTimer={false} /></span>
			<span class="bomb-large"><Bomb fragment="はじ" {mood} size={230} showTimer={false} /></span>
			<span class="bomb-medium"><Bomb fragment="はじ" {mood} size={190} showTimer={false} /></span>
			<span class="bomb-xs"><Bomb fragment="はじ" {mood} size={140} showTimer={false} /></span>
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
			<legend>{t('home.mode')}</legend>
			<ModePicker value={mode} onchange={(m) => (mode = m)} />
		</fieldset>

		<fieldset>
			<legend>{t('home.avatar')}</legend>
			<AvatarPicker bind:value={avatar} />
		</fieldset>

		<div class="createbar">
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
		</div>

		<details class="codebox">
			<summary>{t('home.haveCode')}</summary>
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
		</details>

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
		max-width: 36rem;
		margin: 0 auto;
		padding: 0.2rem 1rem calc(1.5rem + env(safe-area-inset-bottom));
	}
	.hero {
		display: grid;
		justify-items: center;
		gap: 0.6rem;
		padding-top: 0;
	}
	/* the margin leaves room for the fuse above the bomb, so it counts when centring */
	.bomb-small {
		display: block;
		margin-top: 3rem;
	}
	.bomb-medium {
		display: none;
		margin-top: 4.4rem;
	}
	.bomb-xs {
		display: none;
		margin-top: 3.2rem;
	}
	.bomb-large {
		display: none;
		margin-top: 5.6rem;
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
		font-size: clamp(1.25rem, 5.5vw, 1.6rem);
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
	/* the main action stays on screen while the form scrolls (phones) */
	.createbar {
		position: sticky;
		bottom: 0.6rem;
		z-index: 10;
	}
	.codebox summary {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 48px;
		padding: 0.3rem 1rem;
		background: var(--surface-2);
		color: var(--text);
		border: var(--line) solid var(--sumi);
		border-radius: 14px;
		box-shadow:
			inset 0 -4px 0 rgb(0 0 0 / 0.22),
			0 4px 0 var(--sumi);
		font-weight: 700;
		cursor: pointer;
		list-style: none;
	}
	.codebox summary::-webkit-details-marker {
		display: none;
	}
	.codebox[open] summary {
		margin-bottom: 0.9rem;
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

	/* desktop: the bomb and the pitch on the left, the form on the right: no empty band at the top */
	@media (min-width: 900px) {
		.home {
			max-width: 68rem;
			grid-template-columns: 1fr 1.1fr;
			/* both columns share one height and their content is centred in it: bomb, title and form line up */
			align-items: stretch;
			align-content: center;
			gap: 3.5rem;
			min-height: calc(100dvh - var(--bar, 52px) - 1rem);
		}
		.hero {
			align-content: center;
			gap: 1.2rem;
			/* nudges the left block up a little (half of this value) */
			padding-bottom: 5rem;
		}
		.bomb-small {
			display: none;
		}
		.bomb-large {
			display: block;
		}
		h1 {
			max-width: 14ch;
			font-size: 2.3rem;
		}
		footer {
			grid-column: 1 / -1;
		}
	}

	/* medium windows (13 inch laptops with a browser toolbar): a little smaller, still comfortable */
	@media (min-width: 900px) and (max-height: 859px) {
		.home {
			gap: 3rem;
		}
		.bomb-large {
			display: none;
		}
		.bomb-medium {
			display: block;
		}
		.hero {
			padding-bottom: 0;
			gap: 0.9rem;
		}
		h1 {
			font-size: 2rem;
			max-width: 16ch;
		}
		.form {
			gap: 0.8rem;
			padding: 0.9rem 1.1rem 1.1rem;
		}
		footer {
			display: none;
		}
	}
	/* low windows: tighter, but everything (code button included) stays on screen */
	@media (min-width: 900px) and (max-height: 680px) {
		.bomb-medium {
			display: none;
		}
		.bomb-xs {
			display: block;
		}
		h1 {
			font-size: 1.6rem;
		}
		.form {
			gap: 0.6rem;
			padding: 0.7rem 1rem 0.9rem;
		}
	}
	@media (min-width: 900px) and (max-height: 590px) {
		.form {
			gap: 0.4rem;
			padding: 0.5rem 0.9rem 0.7rem;
		}
		h1 {
			font-size: 1.4rem;
		}
	}
</style>
