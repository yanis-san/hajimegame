import { loadPref, savePref } from './session';

/**
 * Synthesised interface sounds (no audio files, no licensing risk). One family: short square and triangle blips on
 * a pentatonic scale, plus noise for the bomb. Mixed at similar levels.
 */
export type SfxName =
	'click' | 'accept' | 'reject' | 'boom' | 'win' | 'tick' | 'turn' | 'life' | 'crackle';

// C D E G A: the yo pentatonic scale
const C5 = 523.25;
const D5 = 587.33;
const E5 = 659.25;
const G5 = 783.99;
const A5 = 880;
const C6 = 1046.5;

type Wave = OscillatorType;

class SfxEngine {
	#ctx: AudioContext | null = null;
	#master: GainNode | null = null;
	#noise: AudioBuffer | null = null;
	#muted = false;
	#volume = 0.7;
	#loaded = false;

	load(): void {
		if (this.#loaded) return;
		this.#loaded = true;
		this.#muted = loadPref('muted', false);
		this.#volume = loadPref('volume', 0.7);
	}

	get muted(): boolean {
		this.load();
		return this.#muted;
	}

	get volume(): number {
		this.load();
		return this.#volume;
	}

	setMuted(muted: boolean): void {
		this.#muted = muted;
		savePref('muted', muted);
		this.#applyVolume();
	}

	setVolume(volume: number): void {
		this.#volume = Math.min(1, Math.max(0, volume));
		savePref('volume', this.#volume);
		this.#applyVolume();
	}

	#applyVolume(): void {
		if (this.#master) this.#master.gain.value = this.#muted ? 0 : this.#volume;
	}

	/** iOS only starts audio from a user gesture: call this from the first tap or key press. */
	unlock(): void {
		this.load();
		try {
			if (!this.#ctx) {
				const Ctor =
					window.AudioContext ??
					(window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
				if (!Ctor) return;
				this.#ctx = new Ctor();
				this.#master = this.#ctx.createGain();
				this.#master.connect(this.#ctx.destination);
				this.#applyVolume();
			}
			if (this.#ctx.state === 'suspended') void this.#ctx.resume();
		} catch {
			/* audio is optional */
		}
	}

	play(name: SfxName): void {
		this.load();
		const ctx = this.#ctx;
		if (!ctx || this.#muted || ctx.state !== 'running') return;
		const t = ctx.currentTime + 0.005;
		switch (name) {
			case 'click':
				this.#tone(1200, t, 0.04, 'square', 0.08);
				break;
			case 'tick':
				this.#tone(880, t, 0.05, 'triangle', 0.16);
				break;
			case 'turn':
				this.#tone(E5, t, 0.08, 'triangle', 0.2);
				this.#tone(A5, t + 0.08, 0.14, 'triangle', 0.2);
				break;
			case 'accept':
				this.#tone(E5, t, 0.07, 'square', 0.11);
				this.#tone(A5, t + 0.07, 0.16, 'square', 0.11);
				break;
			case 'reject':
				this.#tone(196, t, 0.2, 'sawtooth', 0.13, 120);
				break;
			case 'life':
				[C5, E5, G5, C6].forEach((f, i) => this.#tone(f, t + i * 0.06, 0.12, 'triangle', 0.18));
				break;
			case 'win':
				[C5, E5, G5, C6, G5, C6].forEach((f, i) => this.#tone(f, t + i * 0.11, 0.2, 'square', 0.1));
				this.#tone(D5, t + 0.7, 0.5, 'triangle', 0.14);
				break;
			case 'boom':
				this.#noiseBurst(t, 0.5, 900, 0.5);
				this.#tone(140, t, 0.45, 'sine', 0.5, 38);
				break;
			case 'crackle':
				this.#noiseBurst(t, 0.03, 4200, 0.05);
				break;
		}
	}

	#tone(
		freq: number,
		start: number,
		duration: number,
		type: Wave,
		gain: number,
		slideTo?: number
	): void {
		const ctx = this.#ctx;
		if (!ctx || !this.#master) return;
		const osc = ctx.createOscillator();
		const env = ctx.createGain();
		osc.type = type;
		osc.frequency.setValueAtTime(freq, start);
		if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, start + duration);
		env.gain.setValueAtTime(0.0001, start);
		env.gain.exponentialRampToValueAtTime(gain, start + 0.008);
		env.gain.exponentialRampToValueAtTime(0.0001, start + duration);
		osc.connect(env).connect(this.#master);
		osc.start(start);
		osc.stop(start + duration + 0.02);
	}

	#noiseBurst(start: number, duration: number, cutoff: number, gain: number): void {
		const ctx = this.#ctx;
		if (!ctx || !this.#master) return;
		if (!this.#noise) {
			const buffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
			const data = buffer.getChannelData(0);
			for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
			this.#noise = buffer;
		}
		const src = ctx.createBufferSource();
		src.buffer = this.#noise;
		const filter = ctx.createBiquadFilter();
		filter.type = 'lowpass';
		filter.frequency.setValueAtTime(cutoff, start);
		filter.frequency.exponentialRampToValueAtTime(80, start + duration);
		const env = ctx.createGain();
		env.gain.setValueAtTime(gain, start);
		env.gain.exponentialRampToValueAtTime(0.0001, start + duration);
		src.connect(filter).connect(env).connect(this.#master);
		src.start(start);
		src.stop(start + duration + 0.02);
	}
}

export const sfx = new SfxEngine();
