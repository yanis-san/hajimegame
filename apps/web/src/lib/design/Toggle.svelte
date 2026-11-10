<script lang="ts">
	import Icon from './Icon.svelte';

	let {
		checked,
		label,
		disabled = false,
		onchange
	}: {
		checked: boolean;
		label: string;
		disabled?: boolean;
		onchange: (checked: boolean) => void;
	} = $props();
</script>

<button
	type="button"
	class="toggle"
	class:on={checked}
	role="switch"
	aria-checked={checked}
	{disabled}
	onclick={() => onchange(!checked)}
>
	<span class="box" aria-hidden="true">
		{#if checked}<Icon name="check" size={18} />{/if}
	</span>
	<span class="label">{label}</span>
</button>

<style>
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.7rem;
		min-height: 44px;
		padding: 0.2rem 0.3rem;
		border: none;
		background: none;
		color: var(--text);
		font-family: var(--font-ui);
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		text-align: left;
	}
	.box {
		display: grid;
		place-items: center;
		width: 32px;
		height: 32px;
		flex: none;
		border: var(--line) solid var(--sumi);
		border-radius: 9px;
		background: var(--washi);
		color: var(--sumi);
		box-shadow: 0 3px 0 var(--sumi);
		transition: transform var(--t-fast) var(--ease-pop);
	}
	.on .box {
		background: var(--matcha);
		transform: translateY(2px);
		box-shadow: 0 1px 0 var(--sumi);
	}
	.toggle:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
