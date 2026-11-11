<script lang="ts">
	import { t } from '#lib/i18n/index.ts';
	import { CompositionGuard, finalKana, highlightFragment, liveKana } from '#lib/game/kana.ts';
	import Icon from './Icon.svelte';

	let {
		fragment = '',
		mode = 'classic',
		active = false,
		placeholder = '',
		onsubmit,
		ontyping,
		error = ''
	}: {
		fragment?: string;
		mode?: 'classic' | 'shiritori';
		/** true when it is this player's turn */
		active?: boolean;
		placeholder?: string;
		onsubmit: (text: string) => void;
		ontyping: (text: string) => void;
		error?: string;
	} = $props();

	let value = $state('');
	let input: HTMLInputElement | undefined = $state();
	let wrap: HTMLDivElement | undefined = $state();
	const guard = new CompositionGuard();
	let lastTyped = 0;
	let pendingTyped: ReturnType<typeof setTimeout> | null = null;

	const parts = $derived(highlightFragment(value, fragment, mode === 'shiritori'));

	/** Keep the keyboard open between turns: focus is never released, only the content is cleared. */
	export function focus(): void {
		input?.focus({ preventScroll: true });
	}

	export function clear(): void {
		value = '';
	}

	export function shake(): void {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		wrap?.animate(
			[
				{ transform: 'translateX(0)' },
				{ transform: 'translateX(-10px)' },
				{ transform: 'translateX(9px)' },
				{ transform: 'translateX(-6px)' },
				{ transform: 'translateX(3px)' },
				{ transform: 'translateX(0)' }
			],
			{ duration: 220, easing: 'ease-out' }
		);
	}

	$effect(() => {
		// a new turn starts with an empty field
		void fragment;
		value = '';
	});

	function relay(text: string): void {
		const now = performance.now();
		if (now - lastTyped >= 100) {
			lastTyped = now;
			ontyping(text);
		} else if (!pendingTyped) {
			pendingTyped = setTimeout(
				() => {
					pendingTyped = null;
					lastTyped = performance.now();
					ontyping(value);
				},
				100 - (now - lastTyped)
			);
		}
	}

	function handleInput(event: Event): void {
		const el = event.target as HTMLInputElement;
		if (!active) {
			el.value = '';
			value = '';
			return;
		}
		// While an IME composition is active, the browser owns the text: neither convert nor relay it.
		if (guard.composing || (event as InputEvent).isComposing) {
			value = el.value;
			return;
		}
		const converted = liveKana(el.value);
		value = converted;
		el.value = converted;
		relay(converted);
	}

	function handleCompositionEnd(event: CompositionEvent): void {
		guard.end();
		const el = event.target as HTMLInputElement;
		value = el.value;
		relay(value);
	}

	function submit(): void {
		const text = finalKana(value).trim();
		if (!active || !text) return;
		onsubmit(text);
	}

	function handleKeydown(event: KeyboardEvent): void {
		if (event.key !== 'Enter') return;
		event.preventDefault();
		if (guard.canSubmit(event)) submit();
	}
</script>

<div class="dock" bind:this={wrap}>
	<div class="preview" class:empty={!value} aria-hidden="true">
		{#if !value}
			<span class="hint">{t('game.kanaInput')}</span>
		{:else if parts}
			{parts.before}<mark>{parts.match}</mark>{parts.after}
		{:else}
			{value}
		{/if}
	</div>
	<form
		class="row"
		onsubmit={(e) => {
			e.preventDefault();
			submit();
		}}
	>
		<input
			bind:this={input}
			class="field"
			type="text"
			inputmode="text"
			lang="ja"
			enterkeyhint="send"
			autocapitalize="off"
			autocorrect="off"
			autocomplete="off"
			spellcheck="false"
			maxlength="32"
			aria-label={mode === 'shiritori' ? t('game.typeStart') : t('game.typeHere')}
			{placeholder}
			{value}
			class:idle={!active}
			oninput={handleInput}
			oncompositionstart={() => guard.start()}
			oncompositionend={handleCompositionEnd}
			onkeydown={handleKeydown}
		/>
		<button class="send" type="submit" aria-label={t('game.send')} disabled={!active || !value}>
			<Icon name="send" size={24} />
		</button>
	</form>
	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
</div>

<style>
	.dock {
		display: grid;
		gap: 0.4rem;
	}
	.preview {
		min-height: 2.6rem;
		padding: 0.2rem 0.9rem 0.3rem;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: clamp(1.7rem, 7vw, 2.4rem);
		color: var(--text);
		text-align: center;
		overflow: hidden;
		white-space: nowrap;
	}
	@media (max-width: 899px) {
		.preview.empty {
			display: none;
		}
	}
	.preview.empty {
		font-size: 1rem;
		font-family: var(--font-ui);
		font-weight: 500;
		color: var(--text-mute);
	}
	mark {
		background: var(--kinpaku);
		color: var(--sumi);
		padding: 0 0.12em;
		border-radius: 6px;
		box-shadow: 0 3px 0 var(--sumi);
	}
	.row {
		display: flex;
		gap: 0.6rem;
	}
	.field {
		flex: 1;
		min-width: 0;
		min-height: 56px;
		box-sizing: border-box;
		padding: 0.5rem 1rem;
		border: var(--line) solid var(--sumi);
		border-radius: var(--radius-sm);
		background: var(--washi);
		color: var(--sumi);
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: max(16px, 1.3rem);
		box-shadow: inset 0 4px 0 rgb(20 17 15 / 0.14);
	}
	.field:focus {
		outline: var(--line) solid var(--kinpaku);
		outline-offset: 2px;
	}
	.field.idle {
		background: var(--washi-dim);
	}
	.send {
		display: grid;
		place-items: center;
		width: 60px;
		min-height: 56px;
		border: var(--line) solid var(--sumi);
		border-radius: var(--radius-sm);
		background: var(--shu-btn);
		color: #fff8ef;
		cursor: pointer;
		box-shadow:
			inset 0 -5px 0 var(--shu-dark),
			0 4px 0 var(--sumi);
		transition: transform var(--t-fast) var(--ease-pop);
	}
	.send:active:not(:disabled) {
		transform: translateY(3px);
		box-shadow:
			inset 0 -1px 0 var(--shu-dark),
			0 1px 0 var(--sumi);
	}
	.send:disabled {
		background: #5a6479;
		box-shadow:
			inset 0 -3px 0 #48516a,
			0 3px 0 var(--sumi);
		color: #c4cbd8;
	}
	.error {
		margin: 0;
		text-align: center;
		font-weight: 700;
		color: #ffb3a8;
	}
</style>
