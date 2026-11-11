<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { t } from '#lib/i18n/index.ts';
	import { haptic } from '#lib/game/haptics.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import type { GameSession } from '#lib/game/session.svelte.ts';
	import Bomb from './Bomb.svelte';
	import type { Mood } from './Mascot.svelte';
	import Meanings from './Meanings.svelte';
	import Particles from './Particles.svelte';
	import PlayerCard from './PlayerCard.svelte';
	import WordInput from './WordInput.svelte';
	import WordsList from './WordsList.svelte';
	import { flyWord, shake } from './fly';

	let { session }: { session: GameSession } = $props();
	const store = $derived(session.store);

	let particles: Particles | undefined = $state();
	let root: HTMLElement | undefined = $state();
	let bombBox: HTMLElement | undefined = $state();
	let listBox: HTMLElement | undefined = $state();
	let lastBox: HTMLElement | undefined = $state();
	let input: WordInput | undefined = $state();
	// start from the real window size so the bomb never changes size after the first frame
	let width = $state(typeof window === 'undefined' ? 1000 : window.innerWidth);
	let height = $state(typeof window === 'undefined' ? 800 : window.innerHeight);
	let mood = $state<Mood | undefined>(undefined);
	let announcement = $state('');
	let rejection = $state('');
	let notice = $state('');
	let noticeTimer: ReturnType<typeof setTimeout> | undefined;
	let moodTimer: ReturnType<typeof setTimeout> | undefined;
	let rejectTimer: ReturnType<typeof setTimeout> | undefined;

	const desktop = $derived(width >= 900);
	const bombSize = $derived(
		desktop ? 230 : Math.max(130, Math.min(200, Math.round(height * 0.22)))
	);
	const lastWord = $derived(store.words.at(-1) ?? null);

	function setMood(next: Mood, ms: number): void {
		mood = next;
		clearTimeout(moodTimer);
		moodTimer = setTimeout(() => (mood = undefined), ms);
	}

	// A new turn: announce it, sound the cue, keep the keyboard up.
	let lastTurn = 0;
	$effect(() => {
		const turn = store.turn;
		if (!turn || turn.turn === lastTurn) return;
		lastTurn = turn.turn;
		rejection = '';
		const who = store.player(turn.player_id);
		announcement = t('a11y.turn', { name: who?.name ?? '', fragment: turn.fragment });
		if (store.isMyTurn) {
			sfx.play('turn');
			haptic('tap');
			void tick().then(() => input?.focus());
		}
	});

	let lastAccepted = 0;
	$effect(() => {
		const event = store.accepted;
		if (!event || event.id === lastAccepted) return;
		lastAccepted = event.id;
		sfx.play('accept');
		if (event.playerId === store.you) sfx.voice('nice');
		haptic('accept');
		setMood('relief', 700);
		const who = store.player(event.playerId);
		announcement = t('a11y.accepted', { name: who?.name ?? '', word: event.word });
		const target = desktop ? listBox : lastBox;
		if (bombBox && target) {
			flyWord(event.word, bombBox.getBoundingClientRect(), target.getBoundingClientRect());
		}
		if (event.playerId === store.you) {
			input?.clear();
			rejection = '';
		}
	});

	let lastRejected = 0;
	$effect(() => {
		const event = store.rejected;
		if (!event || event.id === lastRejected) return;
		lastRejected = event.id;
		sfx.play('reject');
		haptic('reject');
		input?.shake();
		const fragment = store.turn?.fragment ?? '';
		const key =
			event.reason === 'missing_fragment' && store.settings.mode === 'shiritori'
				? 'reject.missing_start'
				: (`reject.${event.reason}` as const);
		rejection = t(key, { fragment });
		clearTimeout(rejectTimer);
		rejectTimer = setTimeout(() => (rejection = ''), 3200);
	});

	let lastExplosion = 0;
	$effect(() => {
		const event = store.explosion;
		if (!event || event.id === lastExplosion) return;
		lastExplosion = event.id;
		sfx.play('boom');
		if (event.playerId === store.you) window.setTimeout(() => sfx.voice('boom'), 120);
		haptic('boom');
		setMood('boom', 800);
		shake(root);
		const box = bombBox?.getBoundingClientRect();
		if (box) particles?.explode(box.left + box.width / 2, box.top + box.height / 2);
		const who = store.player(event.playerId)?.name ?? '';
		announcement = t('a11y.explosion', { name: who });
		if (event.cause === 'n_ending') {
			notice = t('game.nPenalty', { name: who });
			clearTimeout(noticeTimer);
			noticeTimer = setTimeout(() => (notice = ''), 3500);
		}
	});

	let lastElimination = 0;
	$effect(() => {
		const event = store.elimination;
		if (!event || event.id === lastElimination) return;
		lastElimination = event.id;
		announcement = t('a11y.eliminated', { name: store.player(event.playerId)?.name ?? '' });
		window.setTimeout(() => sfx.play('out'), 450); // after the explosion has rung out
	});

	// The last three seconds of your own turn: a rising tick each second (the clock is the server-synced one).
	$effect(() => {
		const turn = store.turn;
		if (!turn || !store.isMyTurn) return;
		let last = Infinity;
		const id = setInterval(() => {
			const left = Math.ceil(session.client.clock.remaining(turn.deadline) / 1000);
			if (left === last || left > 3 || left < 1) return;
			last = left;
			sfx.play('warn', 3 - left);
		}, 100);
		return () => clearInterval(id);
	});

	// Keep the input above the on-screen keyboard (iOS does not resize the layout viewport).
	onMount(() => {
		const viewport = window.visualViewport;
		if (!viewport || !root) return;
		const update = (): void => {
			root?.style.setProperty('--vvh', `${viewport.height}px`);
			if (viewport.offsetTop > 0) window.scrollTo(0, 0);
		};
		update();
		viewport.addEventListener('resize', update);
		viewport.addEventListener('scroll', update);
		return () => {
			viewport.removeEventListener('resize', update);
			viewport.removeEventListener('scroll', update);
			clearTimeout(moodTimer);
			clearTimeout(rejectTimer);
			clearTimeout(noticeTimer);
		};
	});

	const activeName = $derived(store.activePlayer?.name ?? '');
	const placeholder = $derived(
		store.spectator
			? t('game.spectating')
			: store.isMyTurn
				? t('game.yourTurn')
				: t('game.turnOf', { name: activeName })
	);
</script>

<svelte:window bind:innerWidth={width} bind:innerHeight={height} />
<Particles bind:this={particles} />

<section class="game" bind:this={root} aria-label={t('game.region')} style="--bomb:{bombSize}px">
	<div class="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>

	<!-- players: a row of tiles on phones, a column on desktop -->
	<div class="players" role="list">
		{#each store.players as player (player.id)}
			<div role="listitem" class="slot">
				<PlayerCard
					{player}
					you={player.id === store.you}
					active={player.id === store.turn?.player_id && store.phase === 'playing'}
					maxLives={store.settings.lives}
					typing={store.typing}
				/>
			</div>
		{/each}
	</div>

	<div class="main">
		<div class="stage">
			<div class="center" bind:this={bombBox}>
				<Bomb
					fragment={store.turn?.fragment ?? ''}
					turn={store.turn?.turn ?? 0}
					deadline={store.turn?.deadline ?? 0}
					fuseMs={store.turn?.fuse_ms ?? 10_000}
					running={store.phase === 'playing' && !!store.turn}
					clock={session.client.clock}
					{mood}
					size={bombSize}
					onspark={(x, y, k) => particles?.spark(x, y, k)}
				/>
			</div>

			{#if notice}<p class="notice" role="status">{notice}</p>{/if}

			<p class="turnline" class:mine={store.isMyTurn} aria-hidden="true">
				{#if store.turn}
					{#if store.isMyTurn}
						<strong>{t('game.yourTurn')}</strong>
						{store.settings.mode === 'shiritori' ? t('game.typeStart') : t('game.typeHere')}
						<span class="frag">{store.turn.fragment}</span>
					{:else}
						{t('game.turnOf', { name: activeName })}
						{#if store.typing}<span class="typed">{store.typing}</span>{/if}
					{/if}
				{/if}
			</p>
		</div>

		<!-- last accepted word with its meaning (French first, English otherwise) -->
		<div class="last" bind:this={lastBox}>
			{#if lastWord}
				{#key lastWord.turn + lastWord.word}
					<div class="lastcard">
						<div class="lead">
							<span class="w">{lastWord.word}</span>
							{#if lastWord.reading !== lastWord.word}<span class="r">{lastWord.reading}</span>{/if}
						</div>
						<Meanings fr={lastWord.meaning_fr} en={lastWord.meaning_en} />
					</div>
				{/key}
			{:else}
				<p class="hint">{t('game.wordsEmpty')}</p>
			{/if}
		</div>

		<footer class="foot">
			{#if store.spectator}
				<p class="watching">{t('game.spectating')}</p>
			{:else}
				<WordInput
					bind:this={input}
					fragment={store.turn?.fragment ?? ''}
					mode={store.settings.mode}
					active={store.isMyTurn && (store.me?.alive ?? false)}
					{placeholder}
					error={rejection}
					onsubmit={(text) => session.submit(text)}
					ontyping={(text) => session.typing(text)}
				/>
			{/if}
		</footer>
	</div>

	<aside class="history" bind:this={listBox}>
		<WordsList words={store.words} players={store.players} />
	</aside>
</section>

<style>
	.game {
		display: grid;
		grid-template-rows: auto minmax(0, 1fr);
		height: calc(var(--vvh, 100dvh) - var(--bar, 52px));
		box-sizing: border-box;
		padding: 0.3rem 0.7rem calc(0.6rem + env(safe-area-inset-bottom));
		gap: 0.5rem;
		max-width: 1240px;
		margin-inline: auto;
	}
	.players {
		display: flex;
		gap: 0.35rem;
		justify-content: center;
	}
	.slot {
		flex: 1 1 0;
		min-width: 0;
		max-width: 5.4rem;
	}
	.main {
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto auto;
		gap: 0.5rem;
		min-height: 0;
	}
	.stage {
		display: grid;
		align-content: center;
		justify-items: center;
		gap: 0.6rem;
		min-height: 0;
		padding-top: calc(var(--bomb) * 0.4); /* room for the fuse above the bomb */
	}
	.center {
		display: grid;
		justify-items: center;
	}
	.turnline {
		margin: 0;
		min-height: 2.2rem;
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: baseline;
		gap: 0.5rem;
		font-weight: 700;
		font-size: 1.05rem;
		text-align: center;
		color: var(--text-mute);
	}
	.turnline.mine {
		color: var(--text);
	}
	.turnline strong {
		color: var(--kinpaku);
		font-size: 1.25rem;
	}
	.notice {
		margin: 0;
		padding: 0.25rem 0.9rem 0.35rem;
		background: var(--shu-btn);
		color: #fff8ef;
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: 0 3px 0 var(--sumi);
		font-weight: 700;
		animation: card-pop var(--t-mid) var(--ease-pop) both;
	}
	.frag {
		padding: 0 0.6rem 0.1rem;
		background: var(--kinpaku);
		color: var(--sumi);
		border: var(--line) solid var(--sumi);
		border-radius: 10px;
		box-shadow: 0 3px 0 var(--sumi);
		font-family: var(--font-kana);
		font-size: 1.5rem;
	}
	.typed {
		padding: 0 0.7rem 0.1rem;
		background: var(--washi);
		color: var(--sumi);
		border: var(--line) solid var(--sumi);
		border-radius: 10px;
		font-family: var(--font-kana);
		font-size: 1.4rem;
	}
	.last {
		min-height: 3.8rem;
		display: grid;
		align-items: center;
	}
	.lastcard {
		display: grid;
		gap: 0.1rem;
		padding: 0.45rem 0.9rem 0.55rem;
		background: var(--matcha);
		color: var(--sumi);
		border: var(--line) solid var(--sumi);
		border-radius: 14px;
		box-shadow: var(--shadow-sm);
		animation: card-pop var(--t-mid) var(--ease-pop) both;
	}
	.lead {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	.lastcard .w {
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.7rem;
		line-height: 1.2;
	}
	.lastcard .r {
		font-family: var(--font-kana);
		font-size: 1rem;
		opacity: 0.8;
	}
	.hint {
		margin: 0;
		text-align: center;
		color: var(--text-mute);
		font-size: 0.95rem;
	}
	.history {
		display: none;
	}
	.watching {
		margin: 0;
		padding: 0.9rem;
		text-align: center;
		font-weight: 700;
		color: var(--text-mute);
	}
	@keyframes card-pop {
		0% {
			transform: scale(0.92) translateY(8px);
			opacity: 0;
		}
		100% {
			transform: scale(1);
			opacity: 1;
		}
	}

	/* desktop: players | stage and input | words with meanings */
	@media (min-width: 900px) {
		.game {
			grid-template-columns: 17rem minmax(0, 1fr) 21rem;
			grid-template-rows: minmax(0, 1fr);
			gap: 1.4rem;
			padding-top: 0.6rem;
		}
		.players {
			flex-direction: column;
			justify-content: flex-start;
			gap: 0.6rem;
			overflow-y: auto;
			padding: 0.3rem 0.7rem 0.5rem 0.9rem;
		}
		.slot {
			flex: none;
			max-width: none;
		}
		.history {
			display: block;
			min-height: 0;
		}
		.hint {
			display: none;
		}
		.last {
			min-height: 5.4rem;
		}
	}
</style>
