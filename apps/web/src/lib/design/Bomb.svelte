<script lang="ts">
	import { onMount } from 'svelte';
	import type { ClockSync } from '#lib/game/clock.ts';
	import Mascot, { type Mood } from './Mascot.svelte';

	let {
		fragment = '',
		turn = 0,
		deadline = 0,
		fuseMs = 10_000,
		running = false,
		clock,
		mood,
		size = 190,
		showTimer = true,
		onspark
	}: {
		fragment?: string;
		turn?: number;
		/** server time (ms) at which the bomb explodes */
		deadline?: number;
		fuseMs?: number;
		running?: boolean;
		clock?: ClockSync;
		/** forces the mascot mood (explosion, relief); otherwise it follows the fuse */
		mood?: Mood;
		size?: number;
		showTimer?: boolean;
		onspark?: (x: number, y: number, intensity: number) => void;
	} = $props();

	const FUSE_PATH = 'M100 46 C100 8 142 14 136 -40';
	const uid = $props.id();

	let maskPath: SVGPathElement | undefined = $state();
	let ropePath: SVGPathElement | undefined = $state();
	let sparkEl: SVGGElement | undefined = $state();
	let fraction = $state(1);
	let tenths = $state(0);
	let reduced = false;

	const auto = $derived<Mood>(running && fraction < 0.35 ? 'worried' : 'calm');
	const shown = $derived(mood ?? auto);
	const seconds = $derived((tenths / 10).toFixed(1));

	onMount(() => {
		reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	});

	$effect(() => {
		const el = maskPath;
		const path = ropePath;
		if (!el || !path) return;
		void turn; // restart on every new turn, even with the same deadline
		if (!running || !clock) {
			fraction = 1;
			tenths = fuseMs / 100;
			placeSpark(1);
			return;
		}

		const animation = el.animate([{ strokeDasharray: '100 200' }, { strokeDasharray: '0 200' }], {
			duration: fuseMs,
			easing: 'linear',
			fill: 'forwards'
		});
		const sync = (): void => {
			const elapsed = fuseMs - clock.remaining(deadline);
			const target = Math.min(fuseMs, Math.max(0, elapsed));
			const current = Number(animation.currentTime ?? 0);
			if (Math.abs(current - target) > 60) animation.currentTime = target; // clock estimate improved
		};
		animation.currentTime = Math.min(fuseMs, Math.max(0, fuseMs - clock.remaining(deadline)));

		let raf = 0;
		let lastSpark = 0;
		let lastText = -1;
		const frame = (now: number): void => {
			const progress = Math.min(1, Number(animation.currentTime ?? 0) / fuseMs);
			fraction = 1 - progress;
			placeSpark(fraction);
			const left = Math.max(0, Math.round((fuseMs * fraction) / 100));
			if (left !== lastText) {
				lastText = left;
				tenths = left;
			}
			// sparks fly faster and more often as the fuse gets short
			const interval = 140 - 110 * progress;
			if (!reduced && onspark && sparkEl && now - lastSpark > interval && fraction > 0) {
				lastSpark = now;
				const box = sparkEl.getBoundingClientRect();
				onspark(box.left + box.width / 2, box.top + box.height / 2, 0.6 + progress * 1.6);
			}
			if (progress < 1) raf = requestAnimationFrame(frame);
		};
		raf = requestAnimationFrame(frame);
		const resync = setInterval(sync, 500);

		return () => {
			cancelAnimationFrame(raf);
			clearInterval(resync);
			animation.cancel();
		};
	});

	function placeSpark(frac: number): void {
		if (!ropePath || !sparkEl) return;
		const length = ropePath.getTotalLength();
		const point = ropePath.getPointAtLength(length * Math.max(0, Math.min(1, frac)));
		sparkEl.setAttribute('transform', `translate(${point.x} ${point.y})`);
	}
</script>

<div class="bomb" style:--size="{size}px">
	{#if fragment}
		{#key `${turn}:${fragment}`}
			<div class="plaque" aria-hidden="true">
				<span class="kana">{fragment}</span>
			</div>
		{/key}
	{/if}

	<div class="body">
		<svg
			class="fuse"
			viewBox="-20 -70 240 270"
			aria-hidden="true"
			focusable="false"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<defs>
				<mask id="burn-{uid}" maskUnits="userSpaceOnUse" x="-20" y="-70" width="240" height="270">
					<path
						bind:this={maskPath}
						d={FUSE_PATH}
						pathLength="100"
						fill="none"
						stroke="#fff"
						stroke-width="30"
						stroke-dasharray="100 200"
					/>
				</mask>
			</defs>
			<g mask="url(#burn-{uid})">
				<path d={FUSE_PATH} fill="none" stroke="#14110f" stroke-width="13" />
				<path d={FUSE_PATH} fill="none" stroke="#e4c88f" stroke-width="7" />
				<path d={FUSE_PATH} fill="none" stroke="#a8884a" stroke-width="7" stroke-dasharray="3 7" />
			</g>
			<!-- the same path, hidden, used to measure where the spark is -->
			<path bind:this={ropePath} d={FUSE_PATH} fill="none" stroke="none" />
			<g bind:this={sparkEl}>
				<polygon
					points="0,-13 4,-4 13,0 4,4 0,13 -4,4 -13,0 -4,-4"
					fill="#e7b94a"
					stroke="#14110f"
					stroke-width="3"
				/>
				<circle r="4" fill="#e8412d" />
			</g>
		</svg>
		<Mascot mood={shown} {size} />
	</div>

	{#if showTimer}
		<div class="seconds" aria-hidden="true">
			<span class="digits" class:hot={running && fraction < 0.3}>{running ? seconds : '--.-'}</span>
		</div>
	{/if}
</div>

<style>
	.bomb {
		display: grid;
		justify-items: center;
		gap: 0.2rem;
		width: var(--size);
		margin-inline: auto;
	}
	.plaque {
		display: grid;
		place-items: center;
		min-width: calc(var(--size) * 0.8);
		padding: 0.1rem 1.1rem 0.35rem;
		background: var(--washi);
		color: var(--sumi);
		border: var(--line-thick) solid var(--sumi);
		border-radius: 18px 18px 8px 8px;
		box-shadow: 4px 6px 0 var(--sumi);
		margin-bottom: calc(var(--size) * 0.3);
		animation: plaque-pop var(--t-mid) var(--ease-pop) both;
	}
	.kana {
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: clamp(3rem, 14vw, 4.6rem);
		line-height: 1.15;
		letter-spacing: 0.04em;
	}
	.body {
		position: relative;
		width: var(--size);
		height: var(--size);
	}
	.fuse {
		position: absolute;
		left: calc(var(--size) * -0.1);
		top: calc(var(--size) * -0.35);
		width: calc(var(--size) * 1.2);
		height: calc(var(--size) * 1.35);
		overflow: visible;
		z-index: 2;
		pointer-events: none;
	}
	.seconds {
		margin-top: 0.25rem;
	}
	.digits {
		display: inline-block;
		min-width: 4.2ch;
		padding: 0.05rem 0.6rem 0.15rem;
		text-align: center;
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: 1.4rem;
		background: var(--sumi);
		color: var(--washi);
		border: var(--line) solid var(--washi);
		border-radius: 10px;
		font-variant-numeric: tabular-nums;
	}
	.digits.hot {
		background: var(--shu);
		color: #fff8ef;
		border-color: var(--sumi);
	}
	@keyframes plaque-pop {
		0% {
			transform: scale(0.6) translateY(10px);
			opacity: 0;
		}
		60% {
			transform: scale(1.1);
			opacity: 1;
		}
		100% {
			transform: scale(1);
		}
	}
</style>
