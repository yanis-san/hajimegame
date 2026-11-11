<script lang="ts">
	import Avatar, { AVATAR_COUNT } from '#lib/design/Avatar.svelte';
	import AvatarPicker from '#lib/design/AvatarPicker.svelte';
	import Banner from '#lib/design/Banner.svelte';
	import Bomb from '#lib/design/Bomb.svelte';
	import Button from '#lib/design/Button.svelte';
	import Icon, { ICONS, type IconName } from '#lib/design/Icon.svelte';
	import Lives from '#lib/design/Lives.svelte';
	import Mascot from '#lib/design/Mascot.svelte';
	import Modal from '#lib/design/Modal.svelte';
	import Particles from '#lib/design/Particles.svelte';
	import PlayerChip from '#lib/design/PlayerChip.svelte';
	import Segmented from '#lib/design/Segmented.svelte';
	import TextField from '#lib/design/TextField.svelte';
	import Toggle from '#lib/design/Toggle.svelte';
	import WordInput from '#lib/design/WordInput.svelte';
	import { ClockSync } from '#lib/game/clock.ts';
	import { sfx, type SfxName } from '#lib/game/sfx.ts';
	import type { PlayerView } from '@hajime/protocol';

	const clock = new ClockSync();
	let deadline = $state(0);
	let turn = $state(1);
	let running = $state(false);
	let particles: Particles | undefined = $state();
	let modal = $state(false);
	let nick = $state('Yanis');
	let size = $state<'short' | 'normal' | 'long'>('normal');
	let bonus = $state(true);
	let avatar = $state(3);
	let lives = $state(3);

	function startFuse(): void {
		deadline = performance.now() + 10_000;
		turn += 1;
		running = true;
	}

	const base: PlayerView = {
		id: 'a',
		name: 'Aya',
		avatar: 1,
		ready: true,
		connected: true,
		host: false,
		alive: true,
		lives: 3,
		score: 12,
		bonus: [],
		bot: false,
		difficulty: null
	};
	const chips: { label: string; player: PlayerView; active?: boolean; typing?: string }[] = [
		{ label: 'normal', player: base },
		{
			label: 'actif',
			player: { ...base, id: 'b', name: 'Ben', avatar: 6, host: true },
			active: true,
			typing: 'さくら'
		},
		{
			label: 'hors ligne',
			player: { ...base, id: 'c', name: 'Chi', avatar: 9, connected: false, lives: 2 }
		},
		{
			label: 'éliminé',
			player: { ...base, id: 'd', name: 'Dai', avatar: 4, alive: false, lives: 0 }
		}
	];
	const sounds: SfxName[] = [
		'click',
		'tick',
		'turn',
		'accept',
		'reject',
		'life',
		'win',
		'lose',
		'boom',
		'out',
		'warn',
		'go',
		'don',
		'ka'
	];
	const iconNames = Object.keys(ICONS) as IconName[];
</script>

<svelte:head><title>Composants · Hajime</title></svelte:head>
<Particles bind:this={particles} />

<div class="page">
	<h1>Composants</h1>
	<p class="lead">Tous les éléments dans tous leurs états. Le thème se change en haut à droite.</p>

	<section class="card">
		<h2>Boutons</h2>
		<div class="row">
			<Button>Principal</Button>
			<Button variant="secondary">Secondaire</Button>
			<Button variant="gold">Doré</Button>
			<Button variant="ghost">Discret</Button>
			<Button variant="danger">Danger</Button>
		</div>
		<div class="row">
			<Button icon="play">Avec icône</Button>
			<Button disabled>Désactivé</Button>
			<Button loading>Chargement</Button>
			<Button pressed>Enfoncé</Button>
			<Button size="sm">Petit</Button>
			<Button size="lg">Grand</Button>
			<Button icon="share" iconOnly label="Partager" />
		</div>
	</section>

	<section class="card">
		<h2>Champs et réglages</h2>
		<div class="grid">
			<TextField label="Pseudo" bind:value={nick} />
			<TextField label="Avec erreur" value="x" error="Ce pseudo est refusé." />
			<TextField label="Code" value="K7M2QX" uppercase hint="6 caractères" />
			<div class="stack">
				<Segmented
					label="Durée"
					value={size}
					options={[
						{ value: 'short', label: 'Courte' },
						{ value: 'normal', label: 'Normale' },
						{ value: 'long', label: 'Longue' }
					]}
					onchange={(v) => (size = v)}
				/>
				<Segmented
					label="Désactivé"
					disabled
					value="normal"
					options={[{ value: 'normal', label: 'Normale' }]}
					onchange={() => {}}
				/>
				<Toggle label="Vie bonus" checked={bonus} onchange={(v) => (bonus = v)} />
				<Toggle label="Désactivé" checked={false} disabled onchange={() => {}} />
			</div>
		</div>
		<AvatarPicker bind:value={avatar} />
	</section>

	<section class="card">
		<h2>Avatars et vies</h2>
		<div class="row">
			{#each { length: AVATAR_COUNT } as _, i (i)}
				<Avatar id={i} size={52} />
			{/each}
			<Avatar id={5} size={52} out />
		</div>
		<div class="row">
			<Lives lives={3} max={3} size={26} />
			<Lives lives={1} max={5} size={26} />
			<Lives {lives} max={3} size={26} />
			<Button size="sm" onclick={() => (lives = lives > 0 ? lives - 1 : 3)}>Perdre une vie</Button>
		</div>
		<div class="chips">
			{#each chips as chip (chip.label)}
				<div>
					<small>{chip.label}</small>
					<PlayerChip player={chip.player} active={chip.active} typing={chip.typing} />
				</div>
			{/each}
		</div>
	</section>

	<section class="card">
		<h2>Bakuro, la bombe</h2>
		<div class="row moods">
			<div><Mascot mood="calm" size={120} /><small>calme</small></div>
			<div><Mascot mood="worried" size={120} /><small>inquiet</small></div>
			<div><Mascot mood="boom" size={120} /><small>explosion</small></div>
			<div><Mascot mood="relief" size={120} /><small>soulagé</small></div>
		</div>
		<div class="bomb-demo">
			<Bomb
				fragment="しょ"
				{turn}
				{deadline}
				fuseMs={10_000}
				{running}
				{clock}
				size={190}
				onspark={(x, y, k) => particles?.spark(x, y, k)}
			/>
			<div class="row">
				<Button onclick={startFuse}>Allumer la mèche</Button>
				<Button variant="secondary" onclick={() => (running = false)}>Arrêter</Button>
				<Button variant="gold" onclick={() => particles?.explode(innerWidth / 2, innerHeight / 2)}
					>Explosion</Button
				>
				<Button variant="gold" onclick={() => particles?.hanabi(3000)}>Feu d’artifice</Button>
			</div>
		</div>
	</section>

	<section class="card">
		<h2>Saisie</h2>
		<WordInput
			fragment="しょ"
			active
			onsubmit={() => {}}
			ontyping={() => {}}
			placeholder="Romaji ou kana"
			error="Il manque « しょ » dans ce mot."
		/>
	</section>

	<section class="card">
		<h2>Bannières et modale</h2>
		<div class="stack">
			<Banner tone="info" icon="clock">Information</Banner>
			<Banner tone="warn" icon="refresh">Connexion perdue. Reconnexion…</Banner>
			<Banner tone="error" icon="wifiOff">Pas de connexion.</Banner>
			<Banner tone="success" icon="check">Mot accepté</Banner>
		</div>
		<Button variant="secondary" onclick={() => (modal = true)}>Ouvrir la modale</Button>
		<Modal bind:open={modal} title="Une modale">
			<p>Le fond est bloqué, Échap ferme, le focus reste dedans.</p>
			<Button onclick={() => (modal = false)}>Compris</Button>
		</Modal>
	</section>

	<section class="card">
		<h2>Icônes</h2>
		<div class="row icons">
			{#each iconNames as name (name)}
				<div class="ic"><Icon {name} size={28} /><small>{name}</small></div>
			{/each}
		</div>
	</section>

	<section class="card">
		<h2>Sons</h2>
		<div class="row">
			{#each sounds as name (name)}
				<Button
					size="sm"
					variant="secondary"
					onclick={() => {
						sfx.unlock();
						sfx.play(name);
					}}>{name}</Button
				>
			{/each}
		</div>
	</section>
</div>

<style>
	.page {
		display: grid;
		gap: 1rem;
		max-width: 60rem;
		margin: 0 auto;
		padding: 0.5rem 1rem 3rem;
	}
	h1 {
		font-size: 2rem;
	}
	.lead {
		margin: -0.5rem 0 0;
		color: var(--text-mute);
	}
	section {
		display: grid;
		gap: 0.9rem;
		padding: 1rem;
	}
	h2 {
		font-size: 1.3rem;
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.9rem;
		align-items: center;
	}
	.grid {
		display: grid;
		gap: 1rem;
		grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
	}
	.stack {
		display: grid;
		gap: 0.6rem;
		align-content: start;
	}
	.chips {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: 1rem;
	}
	small {
		display: block;
		text-align: center;
		color: var(--text-mute);
		font-weight: 700;
	}
	.moods > div {
		display: grid;
		justify-items: center;
	}
	.bomb-demo {
		display: grid;
		gap: 1rem;
		justify-items: center;
		padding-top: 1rem;
	}
	.icons {
		gap: 0.6rem;
	}
	.ic {
		display: grid;
		justify-items: center;
		gap: 0.2rem;
		width: 4.5rem;
	}
</style>
