<script lang="ts" module>
	export type Mood = 'calm' | 'worried' | 'boom' | 'relief';
</script>

<script lang="ts">
	import { t } from '#lib/i18n/index.ts';
	/**
	 * Exupulojon, the bomb. Original character: a round ink-black bomb with a washi highlight and expressive face.
	 * The mood changes only in response to game events; there is no idle loop.
	 */
	let { mood = 'calm', size = 200 }: { mood?: Mood; size?: number } = $props();
</script>

<svg
	class="mascot"
	width={size}
	height={size}
	viewBox="0 0 200 200"
	role="img"
	aria-label={t('mascot.label')}
	stroke-linejoin="round"
	stroke-linecap="round"
>
	{#key mood}
		<g class="squash" data-mood={mood}>
			{#if mood === 'boom'}
				<!-- impact star behind the body -->
				<polygon
					points="100,0 118,38 160,14 150,58 196,60 160,88 190,126 144,122 150,170 112,148 100,196 88,148 50,170 56,122 10,126 40,88 4,60 50,58 40,14 82,38"
					fill="#e7b94a"
					stroke="#14110f"
					stroke-width="5"
				/>
				<polygon
					points="100,34 112,62 142,50 134,80 164,92 134,106 150,134 118,128 100,156 82,128 50,134 66,106 36,92 66,80 58,50 88,62"
					fill="#e8412d"
				/>
			{:else}
				<!-- neck cap -->
				<path d="M76 44h48v20H76z" fill="#e4dbc8" stroke="#14110f" stroke-width="5" />
				<!-- body -->
				<circle cx="100" cy="116" r="72" fill="#23212b" stroke="#14110f" stroke-width="6" />
				<!-- washi highlight: flat crescent -->
				<path d="M52 98a50 50 0 0 1 34-40 42 42 0 0 0-26 44z" fill="#f5efe3" />
				<circle cx="64" cy="62" r="5" fill="#f5efe3" />
			{/if}

			<!-- face -->
			{#if mood === 'boom'}
				<g stroke="#14110f" stroke-width="7" fill="none">
					<path d="M74 84l20 20M94 84l-20 20M110 84l20 20M130 84l-20 20" />
					<path d="M80 124q20-18 40 0q-20 30-40 0z" fill="#14110f" />
				</g>
			{:else}
				<ellipse cx="78" cy="112" rx="15" ry="19" fill="#f5efe3" />
				<ellipse cx="122" cy="112" rx="15" ry="19" fill="#f5efe3" />
				{#if mood === 'relief'}
					<path
						d="M62 112q16-16 32 0M106 112q16-16 32 0"
						fill="none"
						stroke="#14110f"
						stroke-width="6"
					/>
					<path d="M86 138q14 12 28 0" fill="none" stroke="#f5efe3" stroke-width="6" />
					<path d="M158 96q8 14 0 22q-8-8 0-22z" fill="#8fb8e8" stroke="#14110f" stroke-width="3" />
				{:else if mood === 'worried'}
					<circle cx="80" cy="106" r="8" fill="#14110f" />
					<circle cx="124" cy="106" r="8" fill="#14110f" />
					<path d="M58 84l26 8M142 84l-26 8" fill="none" stroke="#f5efe3" stroke-width="6" />
					<path d="M82 142q9-9 18 0t18 0" fill="none" stroke="#f5efe3" stroke-width="6" />
					<path d="M160 92q9 15 0 24q-9-9 0-24z" fill="#8fb8e8" stroke="#14110f" stroke-width="3" />
				{:else}
					<circle cx="80" cy="112" r="8" fill="#14110f" />
					<circle cx="122" cy="112" r="8" fill="#14110f" />
					<circle cx="83" cy="108" r="2.6" fill="#f5efe3" />
					<circle cx="125" cy="108" r="2.6" fill="#f5efe3" />
					<path d="M84 140q16 14 32 0" fill="none" stroke="#f5efe3" stroke-width="6" />
				{/if}
			{/if}
		</g>
	{/key}
</svg>

<style>
	.mascot {
		display: block;
		overflow: visible;
		max-width: 100%;
		height: auto;
	}
	.squash {
		transform-box: fill-box;
		transform-origin: 50% 100%;
		animation: squash var(--t-slow) var(--ease-pop) both;
	}
	/* squash and stretch with a little overshoot, once per mood change */
	@keyframes squash {
		0% {
			transform: scale(1.14, 0.84);
		}
		45% {
			transform: scale(0.94, 1.1);
		}
		100% {
			transform: scale(1, 1);
		}
	}
</style>
