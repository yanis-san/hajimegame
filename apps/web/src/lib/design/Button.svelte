<script lang="ts">
	import type { Snippet } from 'svelte';
	import { sfx } from '#lib/game/sfx.ts';
	import { haptic } from '#lib/game/haptics.ts';
	import Icon, { type IconName } from './Icon.svelte';

	type Variant = 'primary' | 'secondary' | 'gold' | 'ghost' | 'danger';

	let {
		variant = 'primary',
		size = 'md',
		icon,
		iconOnly = false,
		label,
		disabled = false,
		loading = false,
		full = false,
		href,
		type = 'button',
		pressed,
		onclick,
		children
	}: {
		variant?: Variant;
		size?: 'sm' | 'md' | 'lg';
		icon?: IconName;
		iconOnly?: boolean;
		/** accessible name when the button only shows an icon */
		label?: string;
		disabled?: boolean;
		loading?: boolean;
		full?: boolean;
		href?: string;
		type?: 'button' | 'submit';
		pressed?: boolean;
		onclick?: (event: MouseEvent) => void;
		children?: Snippet;
	} = $props();

	function feedback(): void {
		if (disabled || loading) return;
		sfx.unlock();
		sfx.play('click');
		haptic('tap');
	}
</script>

{#if href && !disabled}
	<a
		class="btn {variant} {size}"
		class:full
		class:icon-only={iconOnly}
		{href}
		aria-label={label}
		onpointerdown={feedback}
	>
		{#if icon}<Icon name={icon} size={size === 'lg' ? 26 : 22} />{/if}
		{#if !iconOnly}<span>{@render children?.()}</span>{/if}
	</a>
{:else}
	<button
		class="btn {variant} {size}"
		class:full
		class:icon-only={iconOnly}
		class:loading
		{type}
		disabled={disabled || loading}
		aria-label={label}
		aria-pressed={pressed}
		aria-busy={loading || undefined}
		onpointerdown={feedback}
		{onclick}
	>
		{#if icon}<Icon name={icon} size={size === 'lg' ? 26 : 22} />{/if}
		{#if !iconOnly}<span>{@render children?.()}</span>{/if}
	</button>
{/if}

<style>
	.btn {
		--face: var(--shu);
		--lip: var(--shu-dark);
		--fg: var(--washi);
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.55rem;
		min-height: 48px;
		min-width: 48px;
		padding: 0.55rem 1.25rem 0.7rem;
		border: var(--line) solid var(--sumi);
		border-radius: 14px;
		background: var(--face);
		color: var(--fg);
		font-family: var(--font-ui);
		font-weight: 700;
		font-size: 1.05rem;
		line-height: 1.1;
		text-decoration: none;
		cursor: pointer;
		user-select: none;
		-webkit-user-select: none;
		/* hard bottom lip inside, hard ink shadow outside: no blur anywhere */
		box-shadow:
			inset 0 -5px 0 var(--lip),
			0 5px 0 var(--sumi);
		transform: translateY(0);
		transition:
			transform var(--t-fast) var(--ease-pop),
			box-shadow var(--t-fast) var(--ease-snap);
	}

	.primary {
		--face: var(--shu-btn);
		--lip: var(--shu-dark);
		--fg: #fff8ef;
	}
	.secondary {
		--face: var(--washi);
		--lip: var(--washi-dim);
		--fg: var(--sumi);
	}
	.gold {
		--face: var(--kinpaku);
		--lip: var(--kinpaku-dark);
		--fg: var(--sumi);
	}
	.danger {
		--face: var(--sumi);
		--lip: #000;
		--fg: var(--washi);
	}
	.ghost {
		--face: var(--surface-2);
		--lip: var(--surface);
		--fg: var(--text);
	}

	.sm {
		min-height: 40px;
		padding: 0.35rem 0.85rem 0.5rem;
		font-size: 0.95rem;
		border-radius: 11px;
	}
	.lg {
		min-height: 60px;
		padding: 0.75rem 1.9rem 0.95rem;
		font-size: 1.3rem;
		border-radius: 16px;
	}
	/* narrow phones: less padding, so a label such as "Créer une partie" keeps two lines at most */
	@media (max-width: 380px) {
		.lg {
			padding-inline: 1rem;
			font-size: 1.15rem;
		}
	}
	.full {
		width: 100%;
	}
	.icon-only {
		padding: 0.5rem;
	}

	@media (hover: hover) {
		.btn:hover:not(:disabled) {
			transform: translateY(-2px);
			box-shadow:
				inset 0 -5px 0 var(--lip),
				0 7px 0 var(--sumi);
		}
	}

	.btn:active:not(:disabled),
	.btn[aria-pressed='true'] {
		transform: translateY(4px);
		box-shadow:
			inset 0 -1px 0 var(--lip),
			0 1px 0 var(--sumi);
		transition-duration: 60ms;
	}

	.btn:disabled {
		--face: #5a6479;
		--lip: #48516a;
		--fg: #c4cbd8;
		cursor: not-allowed;
		transform: translateY(2px);
		box-shadow:
			inset 0 -3px 0 var(--lip),
			0 3px 0 var(--sumi);
	}

	.loading span {
		opacity: 0.7;
	}

	.btn:focus-visible {
		outline: var(--line) solid var(--kinpaku);
		outline-offset: 4px;
	}
</style>
