<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { t } from '#lib/i18n/index.ts';
	import { toHiragana } from '#lib/game/script.ts';
	import { haptic } from '#lib/game/haptics.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import type { GameSession } from '#lib/game/session.svelte.ts';
	import Bomb from './Bomb.svelte';
	import type { Mood } from './Mascot.svelte';
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
	// What is really visible: on phones the keyboard covers part of the page without resizing it.
	let visualHeight = $state(0);
	const visible = $derived(visualHeight > 0 ? visualHeight : height);
	let mood = $state<Mood | undefined>(undefined);
	let announcement = $state('');
	let rejection = $state('');
	let notice = $state('');
	let noticeTimer: ReturnType<typeof setTimeout> | undefined;
	let moodTimer: ReturnType<typeof setTimeout> | undefined;
	let rejectTimer: ReturnType<typeof setTimeout> | undefined;

	const desktop = $derived(width >= 900);
	// Phones: what is left once the players, the turn line, the last word and the field have their room goes to the
	// bomb, with its fuse above and its tag below (about 1.75 times its size).
	// A short window (a phone with its keyboard open, a laptop at 125% zoom): the last word and the preview shrink
	// to a line, and the bomb takes only what is left. The page never scrolls during a game.
	const compact = $derived(visible < 620);
	// Many players on a phone: smaller tiles (avatar and name), so that eight still fit in a row.
	const crowded = $derived(!desktop && store.players.length > 5);
	const chrome = $derived(desktop ? (compact ? 310 : 355) : compact ? 278 : 330);
	const bombSize = $derived(
		desktop
			? Math.max(110, Math.min(260, Math.floor((visible - chrome) / 1.74)))
			: Math.max(76, Math.min(200, Math.floor((visible - chrome) / 1.75)))
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
				: event.reason === 'missing_fragment' && store.settings.mode === 'kanji'
					? 'reject.missing_kanji'
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

	// A timed game: the time left, from the end time the server sends with every turn.
	let gameLeft = $state<number | null>(null);
	$effect(() => {
		const ends = store.turn?.ends_at ?? null;
		if (ends === null) {
			gameLeft = null;
			return;
		}
		const tick = (): void => {
			gameLeft = Math.max(0, Math.ceil(session.client.clock.remaining(ends) / 1000));
		};
		tick();
		const id = setInterval(tick, 250);
		return () => clearInterval(id);
	});
	const gameClock = $derived(
		gameLeft === null
			? ''
			: `${Math.floor(gameLeft / 60)}:${String(gameLeft % 60).padStart(2, '0')}`
	);

	// While a game is on, phones hide the site bar: every pixel goes to the game.
	onMount(() => {
		document.documentElement.dataset.playing = '';
		return () => delete document.documentElement.dataset.playing;
	});

	// Keep the input above the on-screen keyboard (iOS does not resize the layout viewport).
	onMount(() => {
		const viewport = window.visualViewport;
		if (!viewport || !root) return;
		const update = (): void => {
			visualHeight = viewport.height;
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
					timed={store.settings.duration > 0}
					typing={store.typing}
					compact={compact || crowded}
				/>
			</div>
		{/each}
	</div>

	<div class="main">
		<!-- tapping the stage brings the keyboard back if it was closed -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="stage" onpointerdown={() => input?.focus()}>
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

			{#if gameClock}
				<p
					class="gameclock"
					class:low={(gameLeft ?? 99) <= 10}
					role="timer"
					aria-label={t('game.timeLeft')}
				>
					{gameClock}
				</p>
			{/if}

			{#if notice}<p class="notice" role="status">{notice}</p>{/if}

			<p class="turnline" class:mine={store.isMyTurn} aria-hidden="true">
				{#if store.turn}
					{#if store.isMyTurn}
						<strong>{t('game.yourTurn')}</strong>
						{store.settings.mode === 'shiritori'
							? t('game.typeStart')
							: store.settings.mode === 'kanji'
								? t('game.typeKanji')
								: t('game.typeHere')}
						<span class="frag">{store.turn.fragment}</span>
					{:else}
						{t('game.turnOf', { name: activeName })}
						{#if store.typing}<span class="typed">{store.typing}</span>{/if}
					{/if}
				{/if}
			</p>
		</div>

		<!-- the word just played, shown cleanly: meanings and examples are in the list -->
		<div class="last" bind:this={lastBox}>
			{#if lastWord}
				{#key lastWord.turn + lastWord.word}
					<div class="lastcard" class:compact lang="ja">
						<span class="w">{lastWord.word}</span>
						{#if toHiragana(lastWord.reading) !== toHiragana(lastWord.word)}<span class="r"
								>{lastWord.reading}</span
							>{/if}
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
					{compact}
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
		padding: calc(0.6rem + env(safe-area-inset-top)) 0.7rem
			calc(0.6rem + env(safe-area-inset-bottom));
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
	/* The bomb and its tag come first and never shrink; the last word's card takes what is left and gives way. */
	.main {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-height: 0;
	}
	.gameclock {
		position: absolute;
		top: 0;
		right: 0;
		margin: 0;
		padding: 0.1rem 0.6rem 0.15rem;
		background: var(--washi);
		color: var(--sumi);
		border: var(--line) solid var(--sumi);
		border-radius: 10px;
		box-shadow: 0 3px 0 var(--sumi);
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: 1.2rem;
		line-height: 1.3;
	}
	.gameclock.low {
		background: var(--shu-btn);
		color: #fff8ef;
	}
	.stage {
		position: relative;
		flex: 1 0 auto;
		display: grid;
		align-content: center;
		justify-items: center;
		gap: 0.6rem;
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
		flex: none;
		display: grid;
		justify-items: center;
		align-items: center;
		min-height: 2.6rem;
	}
	.foot {
		flex: none;
	}
	.lastcard {
		display: flex;
		align-items: baseline;
		justify-content: center;
		gap: 0.2rem 0.7rem;
		flex-wrap: wrap;
		padding: 0.3rem 1rem 0.4rem;
		background: var(--matcha);
		color: var(--sumi);
		border: var(--line) solid var(--sumi);
		border-radius: 14px;
		box-shadow: var(--shadow-sm);
		animation: card-pop var(--t-mid) var(--ease-pop) both;
	}
	.lastcard .w {
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.7rem;
		line-height: 1.25;
	}
	.lastcard .r {
		font-family: var(--font-kana);
		font-size: 1rem;
		opacity: 0.8;
	}
	/* short screens (a phone with its keyboard open): the word on a slimmer line */
	.last:has(.compact) {
		min-height: 0;
	}
	.lastcard.compact {
		padding: 0.15rem 0.8rem 0.2rem;
	}
	.lastcard.compact .w {
		font-size: 1.2rem;
	}
	.lastcard.compact .r {
		display: none;
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
	/* phones: the tag already shows the fragment, and an empty list needs no sentence */
	@media (max-width: 899px) {
		.turnline.mine,
		.hint {
			display: none;
		}
		.turnline {
			min-height: 0;
			font-size: 0.95rem;
		}
		.lastcard .w {
			font-size: 1.4rem;
		}
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
		/* the bomb, the word and the field sit together in the middle, not the field at the foot of the screen */
		.main {
			justify-content: center;
			gap: 0.9rem;
		}
		.stage {
			flex: none;
		}
	}
</style>
