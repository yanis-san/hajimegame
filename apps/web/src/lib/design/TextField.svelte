<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	let {
		value = $bindable(''),
		label,
		error,
		hint,
		id,
		uppercase = false,
		...rest
	}: {
		value?: string;
		label: string;
		error?: string;
		hint?: string;
		id?: string;
		uppercase?: boolean;
	} & Omit<HTMLInputAttributes, 'value' | 'id'> = $props();

	const uid = $props.id();
	const fieldId = $derived(id ?? `field-${uid}`);
</script>

<div class="field" class:invalid={!!error}>
	<label for={fieldId}>{label}</label>
	<input
		id={fieldId}
		bind:value
		class:uppercase
		aria-invalid={error ? 'true' : undefined}
		aria-describedby={error ? `${fieldId}-msg` : hint ? `${fieldId}-hint` : undefined}
		autocomplete="off"
		autocapitalize="off"
		autocorrect="off"
		spellcheck="false"
		{...rest}
	/>
	{#if error}
		<p class="msg error" id="{fieldId}-msg" role="alert">{error}</p>
	{:else if hint}
		<p class="msg" id="{fieldId}-hint">{hint}</p>
	{/if}
</div>

<style>
	.field {
		display: grid;
		gap: 0.4rem;
	}
	label {
		font-weight: 700;
		font-size: 0.95rem;
		color: var(--text);
	}
	input {
		box-sizing: border-box;
		width: 100%;
		min-height: 52px;
		padding: 0.6rem 0.9rem;
		border: var(--line) solid var(--sumi);
		border-radius: var(--radius-sm);
		background: var(--washi);
		color: var(--sumi);
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: max(16px, 1.15rem);
		/* hard inset edge, like a recessed slot */
		box-shadow: inset 0 4px 0 rgb(20 17 15 / 0.14);
		transition: transform var(--t-fast) var(--ease-snap);
	}
	input::placeholder {
		color: #7a7266;
		font-weight: 500;
	}
	input:focus {
		outline: var(--line) solid var(--kinpaku);
		outline-offset: 2px;
	}
	.uppercase {
		text-transform: uppercase;
		letter-spacing: 0.18em;
		font-family: var(--font-mono);
	}
	.invalid input {
		border-color: var(--shu);
	}
	.msg {
		margin: 0;
		font-size: 0.9rem;
		color: var(--text-mute);
	}
	.msg.error {
		color: #ffb3a8;
		font-weight: 700;
	}
</style>
