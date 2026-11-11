<script lang="ts">
	import type { Mode } from '@hajime/protocol';
	import { t } from '#lib/i18n/index.ts';
	import Icon from './Icon.svelte';

	/**
	 * Two big cards to choose how to play. Each one shows the rule with kana tiles and explains it in one sentence.
	 */
	let {
		value,
		onchange,
		disabled = false,
		label = ''
	}: { value: Mode; onchange: (mode: Mode) => void; disabled?: boolean; label?: string } = $props();

	const modes: Mode[] = ['classic', 'shiritori'];

	function onkey(event: KeyboardEvent, index: number): void {
		if (disabled) return;
		const step = ['ArrowRight', 'ArrowDown'].includes(event.key)
			? 1
			: ['ArrowLeft', 'ArrowUp'].includes(event.key)
				? -1
				: 0;
		if (!step) return;
		event.preventDefault();
		const next = (index + step + modes.length) % modes.length;
		onchange(modes[next]);
		(event.currentTarget as HTMLElement).parentElement
			?.querySelectorAll<HTMLElement>('[role=radio]')
			[next]?.focus();
	}
</script>

<div class="picker" role="radiogroup" aria-label={label || t('mode.label')}>
	{#each modes as mode, i (mode)}
		<button
			type="button"
			role="radio"
			class:on={value === mode}
			aria-checked={value === mode}
			tabindex={value === mode ? 0 : -1}
			{disabled}
			onclick={() => onchange(mode)}
			onkeydown={(e) => onkey(e, i)}
		>
			<!-- the rule, drawn with kana tiles -->
			<span class="art" aria-hidden="true">
				{#if mode === 'classic'}
					<span class="tile">た</span><span class="tile hot">べ</span><span class="tile">もの</span>
				{:else}
					<span class="tile">くる</span><span class="tile hot">ま</span>
					<span class="link"><Icon name="back" size={20} /></span>
					<span class="tile hot">ま</span><span class="tile">くら</span>
				{/if}
			</span>
			<span class="title">{t(`mode.${mode}.title` as const)}</span>
			<span class="desc">{t(`mode.${mode}.desc` as const)}</span>
			{#if value === mode}
				<span class="check"><Icon name="check" size={16} /></span>
			{/if}
		</button>
	{/each}
</div>

<style>
	.picker {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
		gap: 0.8rem;
	}
	button {
		position: relative;
		display: grid;
		gap: 0.35rem;
		padding: 0.8rem 0.9rem 0.9rem;
		text-align: left;
		background: var(--surface-2);
		color: var(--text);
		border: var(--line) solid var(--sumi);
		border-radius: var(--radius);
		box-shadow:
			inset 0 -5px 0 rgb(0 0 0 / 0.22),
			0 5px 0 var(--sumi);
		cursor: pointer;
		transition: transform var(--t-fast) var(--ease-pop);
	}
	button.on {
		background: var(--kinpaku);
		color: var(--sumi);
		transform: translateY(3px);
		box-shadow:
			inset 0 -3px 0 var(--kinpaku-dark),
			0 2px 0 var(--sumi);
	}
	button:disabled:not(.on) {
		opacity: 0.55;
		cursor: not-allowed;
	}
	button:disabled.on {
		cursor: default;
	}
	@media (hover: hover) {
		button:not(.on):not(:disabled):hover {
			transform: translateY(-2px);
		}
	}
	.art {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		min-height: 2.6rem;
	}
	.tile {
		padding: 0 0.35rem 0.1rem;
		background: var(--washi);
		color: var(--sumi);
		border: 2.5px solid var(--sumi);
		border-radius: 8px;
		box-shadow: 0 2px 0 var(--sumi);
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.2rem;
		line-height: 1.35;
		white-space: nowrap;
	}
	.on .tile.hot,
	.tile.hot {
		background: var(--shu-btn);
		color: #fff8ef;
	}
	.link {
		display: grid;
		place-items: center;
		margin: 0 0.15rem;
		opacity: 0.8;
		transform: rotate(180deg);
	}
	.title {
		font-family: var(--font-display);
		font-weight: 800;
		font-size: 1.45rem;
		line-height: 1.1;
	}
	.desc {
		font-size: 0.95rem;
		line-height: 1.35;
		font-weight: 500;
	}
	.check {
		position: absolute;
		top: 0.7rem;
		right: 0.7rem;
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		background: var(--sumi);
		color: var(--kinpaku);
		border-radius: 50%;
	}
</style>
