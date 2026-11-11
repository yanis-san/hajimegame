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
		fixed = false,
		label = ''
	}: {
		value: Mode;
		onchange?: (mode: Mode) => void;
		disabled?: boolean;
		/** show the chosen mode as plain information, without any way to change it */
		fixed?: boolean;
		label?: string;
	} = $props();

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
		onchange?.(modes[next]);
		(event.currentTarget as HTMLElement).parentElement
			?.querySelectorAll<HTMLElement>('[role=radio]')
			[next]?.focus();
	}
</script>

{#snippet card(mode: Mode, showCheck: boolean)}
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
	<span class="head">
		<span class="title">{t(`mode.${mode}.title` as const)}</span>
		{#if showCheck}
			<span class="check"><Icon name="check" size={16} /></span>
		{/if}
	</span>
	<span class="desc">{t(`mode.${mode}.desc` as const)}</span>
{/snippet}

{#if fixed}
	<div class="picker one">
		<div class="opt on fixed">{@render card(value, false)}</div>
	</div>
{:else}
	<div class="picker" role="radiogroup" aria-label={label || t('mode.label')}>
		{#each modes as mode, i (mode)}
			<button
				type="button"
				role="radio"
				class="opt"
				class:on={value === mode}
				aria-checked={value === mode}
				tabindex={value === mode ? 0 : -1}
				{disabled}
				onclick={() => onchange?.(mode)}
				onkeydown={(e) => onkey(e, i)}
			>
				{@render card(mode, value === mode)}
			</button>
		{/each}
	</div>
{/if}

<style>
	.picker.one {
		grid-template-columns: 1fr;
	}
	.opt.fixed {
		cursor: default;
		transform: none;
		box-shadow:
			inset 0 -3px 0 var(--kinpaku-dark),
			0 3px 0 var(--sumi);
	}
	.picker {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr));
		gap: 0.8rem;
	}
	.opt {
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
	.opt.on {
		background: var(--kinpaku);
		color: var(--sumi);
		transform: translateY(3px);
		box-shadow:
			inset 0 -3px 0 var(--kinpaku-dark),
			0 2px 0 var(--sumi);
	}
	.opt:disabled:not(.on) {
		opacity: 0.55;
		cursor: not-allowed;
	}
	.opt:disabled.on {
		cursor: default;
	}
	@media (hover: hover) {
		.opt:not(.on):not(:disabled):hover {
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
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}
	.check {
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		flex: none;
		background: var(--sumi);
		color: var(--kinpaku);
		border-radius: 50%;
	}

	/* phones: two compact cards side by side instead of two tall ones */
	@media (max-width: 639px) {
		.picker {
			grid-template-columns: 1fr 1fr;
			gap: 0.5rem;
		}
		.art {
			flex-wrap: wrap;
		}
		.opt {
			padding: 0.55rem 0.6rem 0.65rem;
			gap: 0.25rem;
		}
		.art {
			min-height: 2rem;
			gap: 0.15rem;
		}
		.tile {
			font-size: 0.95rem;
			padding: 0 0.22rem 0.05rem;
			border-width: 2px;
			border-radius: 6px;
		}
		.link {
			margin: 0;
		}
		.link :global(svg) {
			width: 14px;
			height: 14px;
		}
		.title {
			font-size: 1.15rem;
		}
		.desc {
			font-size: 0.78rem;
			line-height: 1.3;
		}
		.check {
			width: 22px;
			height: 22px;
		}
	}

	@media (min-width: 900px) and (max-height: 680px) {
		.opt {
			padding: 0.5rem 0.7rem 0.6rem;
			gap: 0.15rem;
		}
		.art {
			min-height: 2rem;
		}
		.tile {
			font-size: 1rem;
		}
		.title {
			font-size: 1.2rem;
		}
		.desc {
			font-size: 0.8rem;
			line-height: 1.25;
		}
	}

	/* the read-only card on wide screens: tiles, title and sentence on one line */
	@media (min-width: 820px) {
		.picker.one .opt.fixed {
			display: flex;
			align-items: center;
			gap: 1.4rem;
		}
		.picker.one .head {
			flex: none;
		}
		.picker.one .desc {
			flex: 1;
		}
	}
</style>
