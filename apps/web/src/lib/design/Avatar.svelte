<script lang="ts" module>
	export const AVATAR_COUNT = 12;
	const COLORS = ['#f4a6b8', '#e7b94a', '#8fb8e8'];
	const BLUSH = '#e27b94';
</script>

<script lang="ts">
	import { t } from '#lib/i18n/index.ts';

	let {
		id,
		size = 56,
		out = false,
		label = true
	}: { id: number; size?: number; out?: boolean; label?: boolean } = $props();

	const style = $derived(((id % 4) + 4) % 4);
	const fill = $derived(COLORS[Math.floor((((id % 12) + 12) % 12) / 4)]);
</script>

<svg
	class="avatar"
	class:out
	width={size}
	height={size}
	viewBox="0 0 64 64"
	role={label ? 'img' : undefined}
	aria-label={label ? t('a11y.avatar', { n: id + 1 }) : undefined}
	aria-hidden={label ? undefined : 'true'}
	stroke="#14110f"
	stroke-width="3"
	stroke-linejoin="round"
	stroke-linecap="round"
>
	{#if style === 0}
		<!-- neko: round ears -->
		<polygon points="11,28 13,7 29,17" {fill} />
		<polygon points="53,28 51,7 35,17" {fill} />
		<circle cx="32" cy="37" r="23" {fill} />
	{:else if style === 1}
		<!-- kitsune: tall ears, pale muzzle -->
		<polygon points="9,30 15,3 30,17" {fill} />
		<polygon points="55,30 49,3 34,17" {fill} />
		<circle cx="32" cy="37" r="23" {fill} />
		<path d="M18 46 L32 58 L46 46 Q32 40 18 46z" fill="#f5efe3" stroke-width="2.5" />
	{:else if style === 2}
		<!-- onigiri: rice triangle with nori band -->
		<path d="M32 7 L57 52 Q59 58 52 58 H12 Q5 58 7 52 Z" {fill} />
		<path d="M17 44 H47 L52 54 Q53 58 49 58 H15 Q11 58 12 54 Z" fill="#14110f" stroke-width="2" />
	{:else}
		<!-- daruma: round body, pale face -->
		<circle cx="32" cy="34" r="25" {fill} />
		<ellipse cx="32" cy="35" rx="17" ry="14" fill="#f5efe3" stroke-width="2.5" />
	{/if}

	<g stroke="none">
		{#if out}
			<g stroke="#14110f" stroke-width="3">
				<path d="M20 31l8 8M28 31l-8 8M36 31l8 8M44 31l-8 8" />
			</g>
			<path d="M26 48q6-4 12 0" stroke="#14110f" stroke-width="2.5" fill="none" />
		{:else}
			<ellipse cx="24" cy="35" rx="3.6" ry="4.6" fill="#14110f" />
			<ellipse cx="40" cy="35" rx="3.6" ry="4.6" fill="#14110f" />
			<circle cx="25.2" cy="33.4" r="1.2" fill="#f5efe3" />
			<circle cx="41.2" cy="33.4" r="1.2" fill="#f5efe3" />
			<path d="M27 45q5 5 10 0" stroke="#14110f" stroke-width="2.6" fill="none" />
			{#if style !== 3}
				<circle cx="17" cy="43" r="3.2" fill={BLUSH} />
				<circle cx="47" cy="43" r="3.2" fill={BLUSH} />
			{/if}
		{/if}
	</g>
</svg>

<style>
	.avatar {
		display: block;
		flex: none;
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
