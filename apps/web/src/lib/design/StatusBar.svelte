<script lang="ts">
	import { t } from '#lib/i18n/index.ts';
	import type { ConnectionStatus } from '#lib/game/client.ts';
	import Banner from './Banner.svelte';
	import Button from './Button.svelte';

	let {
		status,
		reconnectIn = 0,
		onretry
	}: { status: ConnectionStatus; reconnectIn?: number; onretry?: () => void } = $props();

	let online = $state(true);

	$effect(() => {
		online = navigator.onLine;
		const on = (): void => void (online = true);
		const off = (): void => void (online = false);
		window.addEventListener('online', on);
		window.addEventListener('offline', off);
		return () => {
			window.removeEventListener('online', on);
			window.removeEventListener('offline', off);
		};
	});
</script>

{#if !online}
	<div class="bar">
		<Banner tone="error" icon="wifiOff" live="assertive">{t('status.offline')}</Banner>
	</div>
{:else if status === 'reconnecting'}
	<div class="bar">
		<Banner tone="warn" icon="refresh">
			{t('status.reconnecting')}
			{#if reconnectIn > 1}<span class="n">{t('status.reconnectingIn', { n: reconnectIn })}</span
				>{/if}
			{#snippet action()}
				{#if onretry}<Button size="sm" variant="secondary" onclick={onretry}
						>{t('status.retry')}</Button
					>{/if}
			{/snippet}
		</Banner>
	</div>
{/if}

<style>
	.bar {
		position: fixed;
		z-index: 70;
		top: calc(var(--bar, 44px) + 0.4rem);
		left: 50%;
		transform: translateX(-50%);
		width: min(94vw, 30rem);
		animation: drop var(--t-mid) var(--ease-pop) both;
	}
	.n {
		display: block;
		font-weight: 500;
		font-size: 0.85rem;
	}
	@keyframes drop {
		from {
			transform: translate(-50%, -16px);
			opacity: 0;
		}
	}
</style>
