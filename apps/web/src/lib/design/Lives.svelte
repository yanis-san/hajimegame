<script lang="ts">
	import { t } from '#lib/i18n/index.ts';

	/** Lives as sakura petals. A lost life lets its petal fall (animation runs once, on the change). */
	let { lives, max = 3, size = 22 }: { lives: number; max?: number; size?: number } = $props();

	const slots = $derived(Math.max(max, lives));
	let falling = $state<number | null>(null);
	let previous = $state<number | null>(null);

	$effect(() => {
		const current = lives;
		if (previous !== null && current < previous) {
			falling = current; // index of the petal that was lost
			const timer = setTimeout(() => (falling = null), 700);
			previous = current;
			return () => clearTimeout(timer);
		}
		previous = current;
	});
</script>

<span class="lives" role="img" aria-label={t('game.lives', { n: lives })}>
	{#each { length: slots } as _, i (i)}
		<svg
			class="petal"
			class:lost={i >= lives}
			class:fall={falling === i}
			width={size}
			height={size}
			viewBox="0 0 24 24"
			aria-hidden="true"
		>
			<path
				d="M12 22C5.5 15 3.5 8 8.2 4.4c1.7-1.2 3.1-.7 3.8.9.7-1.6 2.1-2.1 3.8-.9C20.5 8 18.5 15 12 22z"
				stroke-width="2.2"
				stroke-linejoin="round"
			/>
		</svg>
	{/each}
</span>

<style>
	.lives {
		display: inline-flex;
		gap: 2px;
		align-items: center;
	}
	.petal path {
		fill: var(--sakura);
		stroke: var(--sumi);
	}
	.petal.lost path {
		fill: transparent;
		stroke: var(--text-mute);
		stroke-dasharray: 3 3;
	}
	.petal {
		overflow: visible;
		transform-origin: 50% 0;
	}
	.petal.fall {
		animation: fall 650ms cubic-bezier(0.4, 0, 0.9, 0.6) both;
	}
	.petal.fall path {
		fill: var(--sakura);
		stroke: var(--sumi);
		stroke-dasharray: none;
	}
	@keyframes fall {
		0% {
			transform: translate(0, 0) rotate(0);
			opacity: 1;
		}
		60% {
			opacity: 1;
		}
		100% {
			transform: translate(10px, 34px) rotate(110deg);
			opacity: 0;
		}
	}
</style>
