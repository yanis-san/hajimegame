<script lang="ts">
	import type { PlayerView } from '@hajime/protocol';
	import { t } from '#lib/i18n/index.ts';
	import Avatar from './Avatar.svelte';
	import Icon from './Icon.svelte';
	import Lives from './Lives.svelte';

	/**
	 * A player in the game. On phones it is a compact tile in a row above the bomb; on desktop it becomes a row of
	 * the player column (avatar, name, lives, score, and what they are typing right now).
	 */
	let {
		player,
		you = false,
		active = false,
		maxLives = 3,
		typing = ''
	}: {
		player: PlayerView;
		you?: boolean;
		active?: boolean;
		maxLives?: number;
		typing?: string;
	} = $props();

	const out = $derived(!player.alive);
</script>

<div class="card" class:active class:out class:you data-player={player.id}>
	<div class="face">
		<Avatar id={player.avatar} size={48} {out} label={false} />
		{#if !player.connected}
			<span class="off" title={t('lobby.disconnected')}><Icon name="wifiOff" size={12} /></span>
		{/if}
	</div>
	<div class="info">
		<span class="name"
			>{player.name}{#if you}<small>{t('game.you')}</small>{/if}</span
		>
		{#if out}
			<span class="gone">{t('game.eliminated')}</span>
		{:else}
			<Lives lives={player.lives} max={maxLives} size={15} />
		{/if}
		{#if active && typing}
			<span class="typing" aria-hidden="true">{typing}</span>
		{/if}
	</div>
	<span class="score" aria-label="{player.score} points">{player.score}</span>
</div>

<style>
	.card {
		position: relative;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: 0.2rem 0.7rem;
		padding: 0.4rem 0.7rem 0.45rem 0.45rem;
		background: var(--surface);
		border: var(--line) solid var(--sumi);
		border-radius: 14px;
		box-shadow: var(--shadow-sm);
		transition:
			transform var(--t-mid) var(--ease-pop),
			background-color var(--t-mid) var(--ease-snap);
	}
	.card.active {
		background: var(--kinpaku);
		color: var(--sumi);
		transform: translateX(6px);
		box-shadow: 3px 5px 0 var(--sumi);
	}
	/* ink arrow pointing at the player whose turn it is */
	.card.active::before {
		content: '';
		position: absolute;
		left: -15px;
		top: 50%;
		width: 0;
		height: 0;
		transform: translateY(-50%);
		border: 9px solid transparent;
		border-left: 11px solid var(--shu-btn);
		filter: drop-shadow(2px 0 0 var(--sumi));
	}
	.card.out {
		opacity: 0.7;
		box-shadow: none;
	}
	.card.you:not(.active) {
		border-color: var(--washi);
	}
	.face {
		position: relative;
	}
	.off {
		position: absolute;
		right: -4px;
		bottom: -2px;
		display: grid;
		place-items: center;
		width: 20px;
		height: 20px;
		border: 2px solid var(--sumi);
		border-radius: 50%;
		background: #ffb3a8;
		color: var(--sumi);
	}
	.info {
		display: grid;
		gap: 0.1rem;
		min-width: 0;
	}
	.name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-weight: 700;
		font-size: 1rem;
	}
	.name small {
		margin-left: 0.4rem;
		font-size: 0.72rem;
		opacity: 0.8;
	}
	.gone {
		font-size: 0.8rem;
		font-weight: 700;
		color: var(--text-mute);
	}
	.typing {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: var(--font-kana);
		font-weight: 700;
		font-size: 1.15rem;
		padding: 0 0.5rem 0.1rem;
		background: var(--washi);
		border: 2px solid var(--sumi);
		border-radius: 8px;
	}
	.score {
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: 1.15rem;
		min-width: 1.6ch;
		text-align: right;
	}

	/* phones: a vertical tile, many fit in one row */
	@media (max-width: 899px) {
		.card {
			grid-template-columns: 1fr;
			justify-items: center;
			gap: 0.1rem;
			padding: 0.35rem 0.2rem 0.3rem;
			text-align: center;
		}
		.card.active {
			transform: translateY(-3px) scale(1.07);
		}
		.card.active::before {
			display: none;
		}
		.face :global(svg) {
			width: 40px;
			height: 40px;
		}
		.info {
			justify-items: center;
		}
		.name {
			max-width: 100%;
			font-size: 0.72rem;
		}
		.info :global(.lives) {
			gap: 0;
		}
		.info :global(.petal) {
			width: 11px;
			height: 11px;
		}
		.name small,
		.typing {
			display: none;
		}
		.score {
			font-size: 0.8rem;
			color: var(--text-mute);
		}
		.active .score {
			color: var(--sumi);
		}
	}
</style>
