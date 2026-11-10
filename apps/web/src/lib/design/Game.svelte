<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { t } from '#lib/i18n/index.ts';
	import { haptic } from '#lib/game/haptics.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import type { GameSession } from '#lib/game/session.svelte.ts';
	import Bomb from './Bomb.svelte';
	import type { Mood } from './Mascot.svelte';
	import Particles from './Particles.svelte';
	import PlayerChip from './PlayerChip.svelte';
	import WordInput from './WordInput.svelte';
	import WordsList from './WordsList.svelte';
	import { flyWord, shake } from './fly';

	let { session }: { session: GameSession } = $props();
	const store = $derived(session.store);

	let particles: Particles | undefined = $state();
	let root: HTMLElement | undefined = $state();
	let bombBox: HTMLElement | undefined = $state();
	let listBox: HTMLElement | undefined = $state();
	let input: WordInput | undefined = $state();
	let width = $state(1000);
	let height = $state(800);
	let mood = $state<Mood | undefined>(undefined);
	let announcement = $state('');
	let rejection = $state('');
	let moodTimer: ReturnType<typeof setTimeout> | undefined;
	let rejectTimer: ReturnType<typeof setTimeout> | undefined;

	const desktop = $derived(width >= 900);
	const bombSize = $derived(desktop ? 165 : Math.max(120, Math.min(180, Math.round(height * 0.2))));
	const mySeat = $derived(
		Math.max(
			0,
			store.players.findIndex((p) => p.id === store.you)
		)
	);

	/** Seats on a ring (desktop), with the local player at the bottom. */
	const seats = $derived(
		store.players.map((p, i) => {
			const n = store.players.length;
			const angle = Math.PI / 2 + ((i - mySeat) / n) * Math.PI * 2;
			return { player: p, x: 50 + 44 * Math.cos(angle), y: 50 + 43 * Math.sin(angle) };
		})
	);

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
		haptic('accept');
		setMood('relief', 700);
		const who = store.player(event.playerId);
		announcement = t('a11y.accepted', { name: who?.name ?? '', word: event.word });
		if (bombBox && listBox)
			flyWord(event.word, bombBox.getBoundingClientRect(), listBox.getBoundingClientRect());
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
		rejection = t(`reject.${event.reason}` as const, { fragment });
		clearTimeout(rejectTimer);
		rejectTimer = setTimeout(() => (rejection = ''), 3200);
	});

	let lastExplosion = 0;
	$effect(() => {
		const event = store.explosion;
		if (!event || event.id === lastExplosion) return;
		lastExplosion = event.id;
		sfx.play('boom');
		haptic('boom');
		setMood('boom', 800);
		shake(root);
		const box = bombBox?.getBoundingClientRect();
		if (box) particles?.explode(box.left + box.width / 2, box.top + box.height / 2);
		announcement = t('a11y.explosion', { name: store.player(event.playerId)?.name ?? '' });
	});

	let lastElimination = 0;
	$effect(() => {
		const event = store.elimination;
		if (!event || event.id === lastElimination) return;
		lastElimination = event.id;
		announcement = t('a11y.eliminated', { name: store.player(event.playerId)?.name ?? '' });
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

<section class="game" bind:this={root} aria-label="Partie">
	<div class="sr-only" aria-live="polite" aria-atomic="true">{announcement}</div>

	<div class="stage">
		<div class="arena" class:arena-on={desktop}>
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
				<p class="live" aria-hidden="true" class:mine={store.isMyTurn}>
					{#if store.turn}
						<span class="who">{store.isMyTurn ? t('game.yourTurn') : activeName}</span>
					{/if}
					<span class="typed">{store.isMyTurn ? '' : store.typing}</span>
				</p>
			</div>

			{#each seats as seat (seat.player.id)}
				<div class="seat" style="--x:{seat.x}%; --y:{seat.y}%">
					<PlayerChip
						player={seat.player}
						you={seat.player.id === store.you}
						active={seat.player.id === store.turn?.player_id && store.phase === 'playing'}
						maxLives={store.settings.lives}
						typing={store.typing}
						size={desktop ? 'lg' : 'md'}
						compact={!desktop}
					/>
				</div>
			{/each}
		</div>

		<aside class="words" bind:this={listBox}>
			<WordsList words={store.words} players={store.players} />
		</aside>
	</div>

	<footer class="foot">
		{#if store.spectator}
			<p class="watching">{t('game.spectating')}</p>
		{:else}
			<WordInput
				bind:this={input}
				fragment={store.turn?.fragment ?? ''}
				active={store.isMyTurn && (store.me?.alive ?? false)}
				{placeholder}
				error={rejection}
				onsubmit={(text) => session.submit(text)}
				ontyping={(text) => session.typing(text)}
			/>
		{/if}
	</footer>
</section>

<style>
	.game {
		display: flex;
		flex-direction: column;
		height: calc(var(--vvh, 100dvh) - var(--bar, 52px));
		box-sizing: border-box;
		padding: 0.5rem 0.75rem calc(0.6rem + env(safe-area-inset-bottom));
		gap: 0.4rem;
		max-width: 1180px;
		margin-inline: auto;
	}
	.stage {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.arena {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.6rem;
	}
	.center {
		order: 1;
		display: grid;
		justify-items: center;
		padding-top: 0.2rem;
		z-index: 2;
	}
	/* mobile: players in a compact grid under the bomb */
	.seat {
		order: 2;
	}
	.arena:not(.arena-on) {
		flex-direction: row;
		flex-wrap: wrap;
		justify-content: center;
		align-content: flex-start;
		gap: 0.45rem;
	}
	.arena:not(.arena-on) .center {
		flex: 0 0 100%;
	}
	.arena:not(.arena-on) .seat {
		flex: 0 0 calc(25% - 0.4rem);
		max-width: 6.5rem;
	}
	.live {
		margin: 0.1rem 0 0;
		min-height: 2.2rem;
		display: grid;
		justify-items: center;
		font-family: var(--font-kana);
		text-align: center;
	}
	.who {
		font-size: 0.9rem;
		font-weight: 700;
		color: var(--text-mute);
		font-family: var(--font-ui);
	}
	.mine .who {
		color: var(--kinpaku);
		font-size: 1.1rem;
	}
	.typed {
		font-size: 1.7rem;
		font-weight: 700;
		min-height: 2rem;
	}
	.words {
		min-width: 0;
	}
	.foot {
		flex: none;
	}
	.watching {
		margin: 0;
		padding: 0.9rem;
		text-align: center;
		font-weight: 700;
		color: var(--text-mute);
	}

	@media (min-width: 900px) {
		.stage {
			flex-direction: row;
			justify-content: center;
			align-items: stretch;
			gap: 1.2rem;
		}
		.arena.arena-on {
			position: relative;
			display: block;
			flex: none;
			width: min(100%, calc(var(--vvh, 100dvh) - var(--bar, 52px) - 8rem));
			aspect-ratio: 1;
			margin: auto;
		}
		.arena.arena-on .center {
			position: absolute;
			left: 50%;
			top: 50%;
			transform: translate(-50%, -50%);
		}
		.arena.arena-on .seat {
			position: absolute;
			left: var(--x);
			top: var(--y);
			transform: translate(-50%, -50%);
			width: 8.5rem;
			z-index: 3;
		}
		.words {
			flex: none;
			width: 15rem;
		}
		.typed {
			display: none; /* desktop shows the text beside the active avatar */
		}
	}
</style>
