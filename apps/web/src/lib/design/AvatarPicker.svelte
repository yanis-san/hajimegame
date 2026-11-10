<script lang="ts">
	import { t } from '#lib/i18n/index.ts';
	import Avatar, { AVATAR_COUNT } from './Avatar.svelte';

	let { value = $bindable(0) }: { value?: number } = $props();
</script>

<div class="picker" role="radiogroup" aria-label={t('home.avatar')}>
	{#each { length: AVATAR_COUNT } as _, i (i)}
		<button
			type="button"
			role="radio"
			class:on={value === i}
			aria-checked={value === i}
			aria-label={t('a11y.avatar', { n: i + 1 })}
			onclick={() => (value = i)}
		>
			<Avatar id={i} size={42} label={false} />
		</button>
	{/each}
</div>

<style>
	.picker {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 0.4rem;
	}
	button {
		display: grid;
		place-items: center;
		min-width: 44px;
		min-height: 52px;
		padding: 0.15rem;
		border: var(--line) solid transparent;
		border-radius: 12px;
		background: var(--surface-2);
		cursor: pointer;
		transition: transform var(--t-fast) var(--ease-pop);
	}
	button.on {
		background: var(--kinpaku);
		border-color: var(--sumi);
		transform: translateY(-2px);
		box-shadow: 0 4px 0 var(--sumi);
	}
	@media (hover: hover) {
		button:not(.on):hover {
			transform: translateY(-2px);
		}
	}
</style>
