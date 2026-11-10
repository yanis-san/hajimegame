<script lang="ts" module>
	export const AVATAR_COUNT = 12;
	/** Badge colours behind each character. */
	const BADGE = [
		'#f4a6b8',
		'#e7b94a',
		'#8fb8e8',
		'#f4a6b8',
		'#7fb069',
		'#8fb8e8',
		'#e8a07a',
		'#7fb069',
		'#e7b94a',
		'#8fb8e8',
		'#e7b94a',
		'#f4a6b8'
	];
	/** Names are only used for the accessible label. */
	export const AVATAR_NAMES = [
		'chat',
		'renard',
		'tanuki',
		'lapin',
		'ours',
		'chien',
		'oiseau',
		'panda',
		'poulpe',
		'onigiri',
		'daruma',
		'kappa'
	];
</script>

<script lang="ts">
	let {
		id,
		size = 56,
		out = false,
		label = true
	}: { id: number; size?: number; out?: boolean; label?: boolean } = $props();

	const i = $derived(((id % 12) + 12) % 12);
	const name = $derived(AVATAR_NAMES[i]);
	const mouthY = $derived(i === 6 || i === 8 || i === 11 ? 52 : 48);
</script>

<svg
	class="avatar"
	class:out
	width={size}
	height={size}
	viewBox="0 0 64 64"
	role={label ? 'img' : undefined}
	aria-label={label ? `Avatar : ${name}` : undefined}
	aria-hidden={label ? undefined : 'true'}
	stroke="#14110f"
	stroke-width="2.6"
	stroke-linejoin="round"
	stroke-linecap="round"
>
	<!-- sticker badge -->
	<circle cx="32" cy="33" r="28.5" fill={BADGE[i]} stroke-width="3" />

	{#if i === 0}
		<polygon points="12,30 13,9 28,19" fill="#f6e6c8" />
		<polygon points="52,30 51,9 36,19" fill="#f6e6c8" />
		<polygon points="15,26 16,14 24,19" fill="#f4a6b8" stroke="none" />
		<polygon points="49,26 48,14 40,19" fill="#f4a6b8" stroke="none" />
		<circle cx="32" cy="38" r="20" fill="#f6e6c8" />
		<path d="M10 40h8M10 46l8-2M54 40h-8M54 46l-8-2" fill="none" stroke-width="2" />
		<path d="M29 43l3 3 3-3z" fill="#e27b94" stroke-width="2" />
	{:else if i === 1}
		<polygon points="10,32 16,3 30,19" fill="#f08a3c" />
		<polygon points="54,32 48,3 34,19" fill="#f08a3c" />
		<polygon points="15,25 17,11 25,19" fill="#14110f" stroke="none" />
		<polygon points="49,25 47,11 39,19" fill="#14110f" stroke="none" />
		<circle cx="32" cy="38" r="20" fill="#f08a3c" />
		<path d="M12 44q20 6 40 0l-8 12q-12 4-24 0z" fill="#fff8ef" stroke-width="2.2" />
		<circle cx="32" cy="48" r="2.6" fill="#14110f" stroke="none" />
	{:else if i === 2}
		<circle cx="15" cy="21" r="6.5" fill="#7a5233" />
		<circle cx="49" cy="21" r="6.5" fill="#7a5233" />
		<circle cx="32" cy="38" r="20" fill="#a87a50" />
		<ellipse cx="23" cy="35" rx="6.5" ry="8" fill="#3b2a1d" stroke="none" />
		<ellipse cx="41" cy="35" rx="6.5" ry="8" fill="#3b2a1d" stroke="none" />
		<ellipse cx="32" cy="47" rx="9" ry="6.5" fill="#f1dfc0" stroke-width="2" />
		<ellipse cx="32" cy="44" rx="3" ry="2.2" fill="#14110f" stroke="none" />
	{:else if i === 3}
		<ellipse cx="23" cy="13" rx="6" ry="14" fill="#fffaf0" />
		<ellipse cx="41" cy="13" rx="6" ry="14" fill="#fffaf0" />
		<ellipse cx="23" cy="14" rx="2.6" ry="9" fill="#f4a6b8" stroke="none" />
		<ellipse cx="41" cy="14" rx="2.6" ry="9" fill="#f4a6b8" stroke="none" />
		<circle cx="32" cy="38" r="19" fill="#fffaf0" />
		<path d="M29 44l3 3 3-3z" fill="#e27b94" stroke-width="2" />
	{:else if i === 4}
		<circle cx="16" cy="20" r="7.5" fill="#8a5a36" />
		<circle cx="48" cy="20" r="7.5" fill="#8a5a36" />
		<circle cx="16" cy="20" r="3.2" fill="#d9a77a" stroke="none" />
		<circle cx="48" cy="20" r="3.2" fill="#d9a77a" stroke="none" />
		<circle cx="32" cy="38" r="20" fill="#a8703f" />
		<ellipse cx="32" cy="46" rx="9.5" ry="7" fill="#e9cba0" stroke-width="2" />
		<ellipse cx="32" cy="43" rx="3.4" ry="2.6" fill="#14110f" stroke="none" />
	{:else if i === 5}
		<ellipse cx="14" cy="36" rx="7" ry="13" fill="#7a5233" transform="rotate(12 14 36)" />
		<ellipse cx="50" cy="36" rx="7" ry="13" fill="#7a5233" transform="rotate(-12 50 36)" />
		<circle cx="32" cy="37" r="19" fill="#e0b074" />
		<ellipse cx="32" cy="46" rx="8" ry="6" fill="#f6e6c8" stroke-width="2" />
		<ellipse cx="32" cy="43" rx="4" ry="3" fill="#14110f" stroke="none" />
		<path d="M29 50q3 4 6 0v3q-3 3-6 0z" fill="#e27b94" stroke-width="1.8" />
	{:else if i === 6}
		<path d="M28 15q4-9 8 0M32 14q8-6 10 2" fill="none" stroke-width="2.4" />
		<circle cx="32" cy="38" r="20" fill="#f7d154" />
		<polygon points="26,43 38,43 32,52" fill="#f08a3c" />
	{:else if i === 7}
		<circle cx="16" cy="20" r="7.5" fill="#14110f" />
		<circle cx="48" cy="20" r="7.5" fill="#14110f" />
		<circle cx="32" cy="38" r="20" fill="#fffaf0" />
		<ellipse cx="23" cy="35" rx="6" ry="8" fill="#14110f" transform="rotate(-18 23 35)" />
		<ellipse cx="41" cy="35" rx="6" ry="8" fill="#14110f" transform="rotate(18 41 35)" />
		<ellipse cx="32" cy="44" rx="3.2" ry="2.4" fill="#14110f" stroke="none" />
	{:else if i === 8}
		<ellipse cx="32" cy="30" rx="20" ry="19" fill="#f2677a" />
		<circle cx="17" cy="52" r="6.5" fill="#f2677a" />
		<circle cx="27" cy="55" r="6.5" fill="#f2677a" />
		<circle cx="37" cy="55" r="6.5" fill="#f2677a" />
		<circle cx="47" cy="52" r="6.5" fill="#f2677a" />
		<ellipse cx="32" cy="42" rx="19" ry="11" fill="#f2677a" stroke="none" />
		<circle cx="42" cy="22" r="2.4" fill="#fff8ef" stroke="none" />
	{:else if i === 9}
		<path d="M32 8L57 52Q59 58 52 58H12Q5 58 7 52Z" fill="#fffaf0" />
		<path d="M17 45h30l5 9q1 4-3 4H15q-4 0-3-4z" fill="#14110f" stroke-width="2" />
	{:else if i === 10}
		<circle cx="32" cy="34" r="22" fill="#e8412d" />
		<ellipse cx="32" cy="36" rx="15" ry="13" fill="#fff8ef" stroke-width="2.2" />
		<path d="M18 24q6-6 12-2M46 24q-6-6-12-2" fill="none" stroke-width="3.2" />
	{:else}
		<ellipse cx="32" cy="14" rx="9" ry="4.5" fill="#fff8ef" stroke-width="2.2" />
		<circle cx="32" cy="38" r="20" fill="#7fb069" />
		<ellipse cx="32" cy="47" rx="8" ry="4.4" fill="#f7d154" stroke-width="2" />
	{/if}

	<g stroke="none">
		{#if out}
			<g stroke="#14110f" stroke-width="2.8">
				<path d="M19 31l8 8M27 31l-8 8M37 31l8 8M45 31l-8 8" />
			</g>
		{:else if i === 9}
			<ellipse cx="25" cy="33" rx="3" ry="4" fill="#14110f" />
			<ellipse cx="39" cy="33" rx="3" ry="4" fill="#14110f" />
		{:else if i === 10}
			<ellipse cx="26" cy="35" rx="2.8" ry="3.6" fill="#14110f" />
			<ellipse cx="38" cy="35" rx="2.8" ry="3.6" fill="#14110f" />
		{:else if i === 7}
			<circle cx="24" cy="35" r="1.8" fill="#fff8ef" />
			<circle cx="40" cy="35" r="1.8" fill="#fff8ef" />
		{:else}
			<ellipse cx="24" cy="35" rx="3.2" ry="4.2" fill="#14110f" />
			<ellipse cx="40" cy="35" rx="3.2" ry="4.2" fill="#14110f" />
			<circle cx="25.2" cy="33.4" r="1.2" fill="#fff8ef" />
			<circle cx="41.2" cy="33.4" r="1.2" fill="#fff8ef" />
		{/if}
	</g>
	{#if !out && i !== 5 && i !== 9 && i !== 10}
		<path d="M28 {mouthY}q4 3 8 0" fill="none" stroke-width="2.2" />
	{:else if !out && i === 9}
		<path d="M28 39q4 3 8 0" fill="none" stroke="#14110f" stroke-width="2.2" />
	{/if}
</svg>

<style>
	.avatar {
		display: block;
		flex: none;
		overflow: visible;
		transition:
			filter var(--t-slow) var(--ease-snap),
			opacity var(--t-slow) var(--ease-snap),
			transform var(--t-slow) var(--ease-snap);
	}
	.out {
		filter: grayscale(1) contrast(0.85);
		opacity: 0.55;
		transform: scale(0.94);
	}
</style>
