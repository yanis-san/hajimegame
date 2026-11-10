<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon, { type IconName } from './Icon.svelte';

	let {
		tone = 'info',
		icon,
		live = 'polite',
		children,
		action
	}: {
		tone?: 'info' | 'warn' | 'error' | 'success';
		icon?: IconName;
		live?: 'polite' | 'assertive' | 'off';
		children: Snippet;
		action?: Snippet;
	} = $props();
</script>

<div class="banner {tone}" role={live === 'assertive' ? 'alert' : 'status'} aria-live={live}>
	{#if icon}<Icon name={icon} size={22} />{/if}
	<div class="text">{@render children()}</div>
	{#if action}<div class="action">{@render action()}</div>{/if}
</div>

<style>
	.banner {
		display: flex;
		align-items: center;
		gap: 0.7rem;
		padding: 0.6rem 0.9rem;
		border: var(--line) solid var(--sumi);
		border-radius: var(--radius-sm);
		box-shadow: var(--shadow-sm);
		font-weight: 700;
		color: var(--sumi);
		background: var(--washi);
	}
	.info {
		background: var(--washi);
	}
	.warn {
		background: var(--kinpaku);
	}
	.error {
		background: #ffb3a8;
	}
	.success {
		background: var(--matcha);
	}
	.text {
		flex: 1;
		min-width: 0;
	}
	.action {
		flex: none;
	}
</style>
