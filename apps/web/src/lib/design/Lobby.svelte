<script lang="ts">
	import { onMount } from 'svelte';
	import { href, t, tn, type MessageKey } from '#lib/i18n/index.ts';
	import { haptic } from '#lib/game/haptics.ts';
	import type { GameSession } from '#lib/game/session.svelte.ts';
	import { sfx } from '#lib/game/sfx.ts';
	import Button from './Button.svelte';
	import Icon from './Icon.svelte';
	import PlayerChip from './PlayerChip.svelte';
	import Segmented from './Segmented.svelte';
	import TextField from './TextField.svelte';
	import Toggle from './Toggle.svelte';
	import Mascot from './Mascot.svelte';
	import Banner from './Banner.svelte';

	let { session }: { session: GameSession } = $props();
	const store = $derived(session.store);

	let copied = $state(false);
	let cpuLevel = $state<'easy' | 'normal' | 'hard'>('normal');
	let chatText = $state('');
	let seconds = $state(0);
	let notice = $state('');
	let copyTimer: ReturnType<typeof setTimeout> | undefined;
	let chatEl: HTMLElement | undefined = $state();

	const link = $derived(
		typeof location === 'undefined' ? '' : `${location.origin}${href(`/r/${store.room}`)}`
	);
	const canShare = $derived(
		typeof navigator !== 'undefined' && typeof navigator.share === 'function'
	);
	const counting = $derived(store.phase === 'countdown');
	const isHost = $derived(store.isHost);
	const canAddCpu = $derived(isHost && store.players.length < store.settings.max_players);
	const meReady = $derived(store.me?.ready ?? false);

	// Countdown: derived from the server deadline and our clock estimate, so every screen reads the same number.
	$effect(() => {
		if (!counting || store.countdownEnds === null) {
			seconds = 0;
			return;
		}
		let last = -1;
		const ends = store.countdownEnds;
		const update = (): void => {
			const left = Math.max(0, Math.ceil(session.client.clock.remaining(ends) / 1000));
			if (left !== last) {
				last = left;
				seconds = left;
				if (left > 0) {
					sfx.play('tick');
					sfx.voice(left === 3 ? 'san' : left === 2 ? 'ni' : left === 1 ? 'ichi' : 'hajime');
					haptic('tap');
				} else {
					sfx.play('go');
					sfx.voice('hajime');
					haptic('boom');
				}
			}
		};
		update();
		const id = setInterval(update, 80);
		return () => clearInterval(id);
	});

	// Show server refusals (not host, not ready...) in plain French.
	let lastError = 0;
	$effect(() => {
		const err = store.lastError;
		if (!err || err.id === lastError) return;
		lastError = err.id;
		const key = `err.${err.code}` as MessageKey;
		notice = t(key) === key ? '' : t(key);
		if (notice) setTimeout(() => (notice = ''), 3500);
	});

	$effect(() => {
		void store.chat.length;
		queueMicrotask(() => chatEl?.scrollTo({ top: chatEl.scrollHeight }));
	});

	onMount(() => () => clearTimeout(copyTimer));

	async function copyLink(): Promise<void> {
		try {
			await navigator.clipboard.writeText(link);
		} catch {
			// clipboard API unavailable (http, old Safari): fall back to a temporary textarea
			const area = document.createElement('textarea');
			area.value = link;
			document.body.appendChild(area);
			area.select();
			document.execCommand('copy');
			area.remove();
		}
		copied = true;
		clearTimeout(copyTimer);
		copyTimer = setTimeout(() => (copied = false), 1800);
	}

	async function share(): Promise<void> {
		try {
			await navigator.share({ title: t('app.name'), text: t('app.tagline'), url: link });
		} catch {
			/* cancelled */
		}
	}

	function sendChat(event: Event): void {
		event.preventDefault();
		const text = chatText.trim();
		if (!text) return;
		session.chat(text);
		chatText = '';
	}
</script>

<section class="lobby" aria-label={t('lobby.title')}>
	<div class="card invite">
		<div class="code-row">
			<div>
				<p class="eyebrow">{t('lobby.code')}</p>
				<p class="code" aria-label="{t('lobby.code')} {store.room.split('').join(' ')}">
					{store.room}
				</p>
			</div>
			<div class="actions">
				<Button variant="gold" icon={copied ? 'check' : 'copy'} onclick={copyLink}>
					{copied ? t('lobby.copied') : t('lobby.copy')}
				</Button>
				{#if canShare}
					<Button
						variant="secondary"
						icon="share"
						iconOnly
						label={t('lobby.share')}
						onclick={share}
					/>
				{/if}
			</div>
		</div>
		<!-- the mode was chosen on the home page: a title here, not something to pick -->
		<p class="modeline">
			<span class="tag-mode">{t('lobby.mode')}</span>
			<strong>{t(`mode.${store.settings.mode}.title` as const)}</strong>
			<span class="why">{t(`mode.${store.settings.mode}.desc` as const)}</span>
		</p>
	</div>

	<div class="cols">
		<div class="card players">
			<h2><Icon name="users" size={22} /> {store.players.length}/{store.settings.max_players}</h2>
			<ul>
				{#each store.players as player (player.id)}
					<li>
						<div class="chip-wrap">
							<PlayerChip
								{player}
								you={player.id === store.you}
								maxLives={store.settings.lives}
								showScore={false}
							/>
						</div>
						<div class="state">
							{#if player.bot}
								<span class="tag cpu">
									{t('cpu.tag')} · {t(`cpu.${player.difficulty ?? 'normal'}` as const)}
								</span>
							{:else if player.host}
								<span class="tag host">{t('lobby.host')}</span>
							{:else if !player.connected}
								<span class="tag off">{t('lobby.disconnected')}</span>
							{:else if player.ready}
								<span class="tag ready"><Icon name="check" size={16} /> {t('lobby.ready')}</span>
							{:else}
								<span class="tag">{t('lobby.notReady')}</span>
							{/if}
							{#if isHost && player.id !== store.you}
								<Button
									size="sm"
									variant="ghost"
									iconOnly
									icon={player.bot ? 'close' : 'kick'}
									label="{player.bot ? t('cpu.remove') : t('lobby.kick')} {player.name}"
									onclick={() =>
										player.bot ? session.removeBot(player.id) : session.kick(player.id)}
								/>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
			{#if isHost}
				<div class="cpu-panel">
					<h3><Icon name="bolt" size={20} /> {t('cpu.title')}</h3>
					<Segmented
						label={t('cpu.title')}
						value={cpuLevel}
						options={[
							{ value: 'easy', label: t('cpu.easy') },
							{ value: 'normal', label: t('cpu.normal') },
							{ value: 'hard', label: t('cpu.hard') }
						]}
						onchange={(level) => (cpuLevel = level)}
					/>
					<p class="cpu-desc">{t(`cpu.${cpuLevel}.desc` as const)}</p>
					<Button
						variant="secondary"
						icon="play"
						disabled={!canAddCpu}
						onclick={() => session.addBot(cpuLevel)}
					>
						{t('cpu.add')}
					</Button>
				</div>
			{/if}
			{#if store.spectators > 0}
				<p class="spectators">
					<Icon name="eye" size={18} />
					{tn('lobby.spectators', store.spectators)}
				</p>
			{/if}
		</div>

		<div class="card settings">
			<h2><Icon name="gear" size={22} /> {t('lobby.settings')}</h2>
			<div class="setting">
				<span class="lbl">{t('lobby.lives')}</span>
				<Segmented
					label={t('lobby.lives')}
					disabled={!isHost}
					value={store.settings.lives}
					options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
					onchange={(lives) => session.settings({ lives })}
				/>
			</div>
			<div class="setting">
				<span class="lbl">{t('lobby.fuse')}</span>
				<Segmented
					label={t('lobby.fuse')}
					disabled={!isHost}
					value={store.settings.fuse_seconds}
					options={[5, 8, 10, 15, 20].map((n) => ({ value: n, label: t('lobby.seconds', { n }) }))}
					onchange={(fuse_seconds) => session.settings({ fuse_seconds })}
				/>
			</div>
			<div class="setting toggles">
				{#if store.settings.mode === 'shiritori'}
					<Toggle
						label={t('lobby.nPenalty')}
						disabled={!isHost}
						checked={store.settings.n_penalty}
						onchange={(n_penalty) => session.settings({ n_penalty })}
					/>
				{/if}
				<Toggle
					label={t('lobby.bonus')}
					disabled={!isHost}
					checked={store.settings.bonus_kana}
					onchange={(bonus_kana) => session.settings({ bonus_kana })}
				/>
			</div>
		</div>
	</div>

	<div class="cta">
		{#if notice}
			<Banner tone="warn" icon="bolt" live="assertive">{notice}</Banner>
		{/if}
		{#if store.spectator}
			<p class="wait">{t('game.spectating')}</p>
		{:else if isHost}
			<Button
				size="lg"
				full
				icon="play"
				disabled={!store.canStart || counting}
				onclick={() => session.start()}
			>
				{t('lobby.start')}
			</Button>
			{#if !store.canStart}
				<p class="hint">
					{store.players.filter((p) => p.connected).length < 2
						? t('lobby.needPlayers')
						: t('lobby.needReady')}
				</p>
			{/if}
		{:else}
			<Button
				size="lg"
				full
				variant={meReady ? 'secondary' : 'primary'}
				icon={meReady ? 'check' : undefined}
				pressed={meReady}
				onclick={() => session.ready(!meReady)}
			>
				{meReady ? t('lobby.ready') : t('lobby.notReady')}
			</Button>
			<p class="hint">{t('lobby.waitHost')}</p>
		{/if}
	</div>

	<div class="card chat">
		<h2><Icon name="chat" size={22} /> {t('lobby.chat')}</h2>
		<ul class="lines" bind:this={chatEl} aria-live="polite">
			{#each store.chat as line (line.id)}
				<li><strong>{line.name}</strong> <span>{line.text}</span></li>
			{/each}
		</ul>
		<form onsubmit={sendChat}>
			<TextField
				label={t('lobby.chat')}
				placeholder={t('lobby.chatPlaceholder')}
				bind:value={chatText}
				maxlength={200}
			/>
			<Button type="submit" variant="secondary" icon="send" iconOnly label={t('lobby.send')} />
		</form>
	</div>
</section>

{#if counting}
	<div class="countdown" role="status" aria-live="assertive">
		<div class="mascot"><Mascot mood="worried" size={150} /></div>
		<p class="lead">{t('lobby.countdown')}</p>
		{#key seconds}
			<p class="num" class:word={seconds === 0}>{seconds > 0 ? seconds : 'バカハツ'}</p>
		{/key}
	</div>
{/if}

<style>
	.lobby {
		display: grid;
		gap: 0.9rem;
		max-width: 62rem;
		margin: 0 auto;
		padding: 0.5rem 0.9rem calc(1.5rem + env(safe-area-inset-bottom));
	}
	.card {
		padding: 0.9rem 1rem;
	}
	h2 {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1.2rem;
		margin-bottom: 0.7rem;
	}
	.code-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.8rem;
	}
	.eyebrow {
		margin: 0;
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--text-mute);
	}
	.code {
		margin: 0;
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: clamp(2rem, 9vw, 2.8rem);
		letter-spacing: 0.2em;
		line-height: 1.1;
		color: var(--kinpaku);
	}
	.modeline {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.3rem 0.8rem;
		margin: 0.8rem 0 0;
		padding-top: 0.7rem;
		border-top: var(--line) dashed var(--text-mute);
	}
	.tag-mode {
		padding: 0 0.5rem;
		background: var(--shu-btn);
		color: #fff8ef;
		border: 2px solid var(--sumi);
		border-radius: 6px;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}
	.modeline strong {
		font-family: var(--font-display);
		font-weight: 800;
		font-size: 1.5rem;
		color: var(--kinpaku);
	}
	.why {
		flex: 1 1 18rem;
		font-size: 0.95rem;
		color: var(--text-mute);
	}
	.actions {
		display: flex;
		gap: 0.6rem;
	}
	.cols {
		display: grid;
		gap: 0.9rem;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.players ul {
		display: grid;
		gap: 0.6rem;
	}
	.players li {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.6rem;
	}
	.chip-wrap {
		width: 9rem;
		flex: none;
	}
	.state {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.tag {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.15rem 0.6rem 0.25rem;
		border: var(--line) solid var(--sumi);
		border-radius: 999px;
		background: var(--surface-2);
		font-weight: 700;
		font-size: 0.85rem;
	}
	.tag.ready {
		background: var(--matcha);
		color: var(--sumi);
	}
	.tag.host {
		background: var(--kinpaku);
		color: var(--sumi);
	}
	.tag.cpu {
		background: var(--ai-raised);
		color: var(--text);
	}
	.cpu-panel {
		display: grid;
		gap: 0.5rem;
		margin-top: 0.9rem;
		padding-top: 0.8rem;
		border-top: var(--line) dashed var(--text-mute);
	}
	.cpu-panel h3 {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 1.05rem;
	}
	.cpu-desc {
		margin: 0;
		font-size: 0.9rem;
		color: var(--text-mute);
	}
	.tag.off {
		background: #ffb3a8;
		color: var(--sumi);
	}
	.spectators {
		display: flex;
		gap: 0.4rem;
		align-items: center;
		margin: 0.7rem 0 0;
		color: var(--text-mute);
		font-weight: 700;
	}
	.setting {
		display: grid;
		gap: 0.35rem;
		margin-bottom: 0.9rem;
	}
	.lbl {
		font-weight: 700;
	}
	.toggles {
		gap: 0.1rem;
		margin-bottom: 0;
	}
	/* the start / ready button stays reachable without scrolling */
	.cta {
		display: grid;
		gap: 0.6rem;
		position: sticky;
		bottom: 0;
		z-index: 20;
		margin: 0 -0.9rem;
		padding: 0.6rem 0.9rem calc(0.6rem + env(safe-area-inset-bottom));
		background: var(--bg);
		border-top: var(--line) solid var(--sumi);
	}
	.hint,
	.wait {
		margin: 0;
		text-align: center;
		color: var(--text-mute);
		font-weight: 700;
	}
	.lines {
		max-height: 9rem;
		overflow: auto;
		margin-bottom: 0.6rem;
		display: grid;
		gap: 0.2rem;
		font-size: 0.95rem;
		overflow-wrap: anywhere;
	}
	.lines strong {
		color: var(--kinpaku);
	}
	.chat form {
		display: grid;
		grid-template-columns: 1fr auto;
		align-items: end;
		gap: 0.5rem;
	}
	.countdown {
		position: fixed;
		inset: 0;
		z-index: 65;
		display: grid;
		place-content: center;
		justify-items: center;
		gap: 0.3rem;
		background: rgb(10 19 32 / 0.9);
		overflow: hidden; /* the number pops in scaled up: it must never widen the page */
		touch-action: none;
	}
	.lead {
		margin: 0;
		font-weight: 700;
		font-size: 1.2rem;
		color: var(--text-mute);
	}
	.num {
		margin: 0;
		font-family: var(--font-display);
		font-weight: 800;
		font-size: clamp(6rem, 30vw, 11rem);
		line-height: 1;
		color: var(--kinpaku);
		-webkit-text-stroke: 4px var(--sumi);
		paint-order: stroke fill;
		text-shadow: 6px 8px 0 var(--sumi);
		animation: count-pop var(--t-slow) var(--ease-pop) both;
	}
	/* the final word is four kana wide: sized to the screen instead of to a digit */
	.num.word {
		font-size: clamp(2.4rem, 15vw, 6.5rem);
		white-space: nowrap;
		-webkit-text-stroke-width: 3px;
		text-shadow: 4px 6px 0 var(--sumi);
	}
	@keyframes count-pop {
		0% {
			transform: scale(1.7);
			opacity: 0;
		}
		60% {
			transform: scale(0.94);
			opacity: 1;
		}
		100% {
			transform: scale(1);
		}
	}

	@media (min-width: 820px) {
		.cols {
			grid-template-columns: 1fr 1.2fr;
			align-items: start;
		}
		/* difficulty settings in two columns so nothing hides behind the action bar */
		.settings {
			display: grid;
			grid-template-columns: 1fr 1fr;
			column-gap: 1.6rem;
			align-items: start;
		}
		.settings h2,
		.settings .toggles {
			grid-column: 1 / -1;
		}
	}
</style>
