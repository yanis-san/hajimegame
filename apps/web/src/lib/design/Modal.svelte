<script lang="ts">
	import { t } from '#lib/i18n/index.ts';
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		open = $bindable(false),
		title,
		onclose,
		children
	}: { open?: boolean; title: string; onclose?: () => void; children: Snippet } = $props();

	let dialog: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});

	function handleClose(): void {
		open = false;
		onclose?.();
	}
</script>

<!-- the native dialog gives us focus trapping, Escape to close and inert background for free -->
<dialog bind:this={dialog} class="modal" onclose={handleClose} aria-labelledby="modal-title">
	<div class="panel">
		<header>
			<h2 id="modal-title">{title}</h2>
			<button
				class="x"
				type="button"
				aria-label={t('common.close')}
				onclick={() => dialog?.close()}
			>
				<Icon name="close" />
			</button>
		</header>
		<div class="body">{@render children()}</div>
	</div>
</dialog>

<style>
	.modal {
		padding: 0;
		border: none;
		background: transparent;
		color: var(--text);
		max-width: min(92vw, 30rem);
		width: 100%;
	}
	.modal::backdrop {
		background: rgb(10 19 32 / 0.82);
	}
	.modal[open] .panel {
		animation: pop var(--t-mid) var(--ease-pop) both;
	}
	.panel {
		background: var(--surface);
		border: var(--line-thick) solid var(--sumi);
		border-radius: var(--radius);
		box-shadow: 6px 8px 0 var(--sumi);
		overflow: hidden;
	}
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.8rem 1rem;
		background: var(--washi);
		color: var(--sumi);
		border-bottom: var(--line) solid var(--sumi);
	}
	h2 {
		font-size: 1.35rem;
	}
	.x {
		display: grid;
		place-items: center;
		width: 44px;
		height: 44px;
		border: var(--line) solid var(--sumi);
		border-radius: 10px;
		background: var(--shu-btn);
		color: #fff8ef;
		cursor: pointer;
	}
	.body {
		padding: 1rem;
		max-height: 70dvh;
		overflow: auto;
	}
	@keyframes pop {
		from {
			transform: scale(0.9) translateY(10px);
			opacity: 0;
		}
		to {
			transform: scale(1) translateY(0);
			opacity: 1;
		}
	}
</style>
