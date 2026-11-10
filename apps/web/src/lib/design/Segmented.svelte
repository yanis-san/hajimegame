<script lang="ts" generics="T extends string | number">
	let {
		options,
		value,
		label,
		disabled = false,
		onchange
	}: {
		options: { value: T; label: string }[];
		value: T;
		label: string;
		disabled?: boolean;
		onchange: (value: T) => void;
	} = $props();

	function onkey(event: KeyboardEvent, index: number): void {
		if (disabled) return;
		const step =
			event.key === 'ArrowRight' || event.key === 'ArrowDown'
				? 1
				: event.key === 'ArrowLeft' || event.key === 'ArrowUp'
					? -1
					: 0;
		if (!step) return;
		event.preventDefault();
		const next = options[(index + step + options.length) % options.length];
		onchange(next.value);
		(event.currentTarget as HTMLElement).parentElement
			?.querySelectorAll<HTMLElement>('[role=radio]')
			[(index + step + options.length) % options.length]?.focus();
	}
</script>

<div class="seg" role="radiogroup" aria-label={label}>
	{#each options as option, i (option.value)}
		<button
			type="button"
			role="radio"
			class:on={option.value === value}
			aria-checked={option.value === value}
			tabindex={option.value === value ? 0 : -1}
			{disabled}
			onclick={() => onchange(option.value)}
			onkeydown={(e) => onkey(e, i)}
		>
			{option.label}
		</button>
	{/each}
</div>

<style>
	.seg {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	button {
		min-width: 44px;
		min-height: 44px;
		padding: 0.25rem 0.7rem 0.4rem;
		border: var(--line) solid var(--sumi);
		border-radius: 11px;
		background: var(--surface-2);
		color: var(--text);
		font-family: var(--font-ui);
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		box-shadow:
			inset 0 -4px 0 rgb(0 0 0 / 0.25),
			0 3px 0 var(--sumi);
		transition: transform var(--t-fast) var(--ease-pop);
	}
	button:active:not(:disabled) {
		transform: translateY(3px);
		box-shadow:
			inset 0 -1px 0 rgb(0 0 0 / 0.25),
			0 0 0 var(--sumi);
	}
	button.on {
		background: var(--kinpaku);
		color: var(--sumi);
		transform: translateY(2px);
		box-shadow:
			inset 0 -2px 0 var(--kinpaku-dark),
			0 1px 0 var(--sumi);
	}
	button:disabled {
		cursor: not-allowed;
		opacity: 0.6;
	}
</style>
