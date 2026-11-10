<script lang="ts">
	import type { PlayerView } from '@hajime/protocol';
	import { t } from '#lib/i18n/index.ts';
	import Avatar from './Avatar.svelte';
	import Icon from './Icon.svelte';
	import Lives from './Lives.svelte';

	let {
		player,
		you = false,
		active = false,
		maxLives = 3,
		typing = '',
		showScore = true,
		size = 'md',
		compact = false
	}: {
		player: PlayerView;
		you?: boolean;
		active?: boolean;
		maxLives?: number;
		typing?: string;
		showScore?: boolean;
		size?: 'md' | 'lg';
		compact?: boolean;
	} = $props();

	const out = $derived(!player.alive);
</script>

<div
	class="chip"
	class:active
	class:out
	class:you
	class:lg={size === 'lg'}
	class:compact
	data-player={player.id}
>
	{#if active}
		<span class="pointer" aria-hidden="true"></span>
	{/if}
	<div class="face">
		<Avatar id={player.avatar} size={size === 'lg' ? 64 : compact ? 38 : 48} {out} label={false} />
		{#if player.host}
			<span class="badge host" title={t('lobby.host')}><Icon name="crown" size={13} /></span>
		{/if}
		{#if !player.connected}
			<span class="badge off" title={t('lobby.disconnected')}
				><Icon name="wifiOff" size={13} /></span
			>
		{/if}
	</div>
	<span class="name">{player.name}</span>
	{#if !out}
		<Lives lives={player.lives} max={maxLives} size={compact ? 14 : 17} />
	{:else}
		<span class="out-label">{t('game.eliminated')}</span>
	{/if}
	{#if showScore}
		<span class="score">{player.score}</span>
	{/if}
	{#if active && typing}
		<span class="bubble" aria-hidden="true">{typing}</span>
	{/if}
</div>

<style>
	.chip {
		position: relative;
		display: grid;
		justify-items: center;
		gap: 0.12rem;
		padding: 0.4rem 0.35rem 0.35rem;
		min-width: 0;
		background: var(--surface);
		border: var(--line) solid var(--sumi);
		border-radius: 14px;
		box-shadow: var(--shadow-sm);
		transition:
			transform var(--t-mid) var(--ease-pop),
			background-color var(--t-mid) var(--ease-snap),
			border-color var(--t-mid) var(--ease-snap);
	}
	.chip.active {
		background: var(--kinpaku);
		color: var(--sumi);
		transform: translateY(-3px) scale(1.06);
		box-shadow: 3px 6px 0 var(--sumi);
	}
	.chip.out {
		background: var(--surface);
		opacity: 0.8;
		box-shadow: none;
	}
	.chip.you:not(.active) {
		border-color: var(--washi);
	}
	.face {
		position: relative;
	}
	.name {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-weight: 700;
		font-size: 0.85rem;
	}
	.chip.lg .name {
		font-size: 1rem;
	}
	.score {
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: 0.8rem;
		color: var(--text-mute);
	}
	.active .score {
		color: var(--sumi);
	}
	.out-label {
		font-size: 0.75rem;
		color: var(--text-mute);
		font-weight: 700;
	}
	.badge {
		position: absolute;
		display: grid;
		place-items: center;
		width: 20px;
		height: 20px;
		border: 2px solid var(--sumi);
		border-radius: 50%;
		color: var(--sumi);
	}
	.badge.host {
		top: -6px;
		right: -8px;
		background: var(--kinpaku);
	}
	.badge.off {
		bottom: -4px;
		right: -8px;
		background: #ffb3a8;
	}
	/* a small ink pointer above the player whose turn it is */
	.pointer {
		position: absolute;
		top: -13px;
		left: 50%;
		width: 16px;
		height: 16px;
		background: var(--shu);
		border: var(--line) solid var(--sumi);
		transform: translateX(-50%) rotate(45deg);
		border-right: none;
		border-bottom: none;
		clip-path: none;
		display: none;
	}
	.bubble {
		display: none;
		position: absolute;
		left: calc(100% + 10px);
		top: 50%;
		transform: translateY(-50%);
		max-width: 11rem;
		padding: 0.25rem 0.7rem 0.35rem;
		background: var(--washi);
		color: var(--sumi);
		border: var(--line) solid var(--sumi);
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.3rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		z-index: 5;
	}
	@media (min-width: 900px) {
		.bubble {
			display: block;
		}
	}
	.compact {
		padding: 0.3rem 0.2rem;
	}
	.compact .name {
		font-size: 0.75rem;
	}
</style>
