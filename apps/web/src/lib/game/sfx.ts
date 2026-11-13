import { loadPref, savePref } from './session';

/**
 * Synthesised sounds (no audio files, no licensing risk), designed as one family in C major:
 * marimba plucks and glockenspiel bells for feedback, a pulse "coin" for good answers, filtered brass for the
 * fanfare, layered noise and a sub thump for the bomb. Everything goes through one small room reverb and a
 * compressor so layered sounds stay clean and no two sounds differ wildly in loudness.
 */
export type SfxName =
	| 'click'
	| 'tick'
	| 'turn'
	| 'accept'
	| 'reject'
	| 'life'
	| 'boom'
	| 'win'
	| 'lose'
	| 'out'
	| 'warn'
	| 'go'
	| 'don'
	| 'ka'
	| 'crackle';

/** Spoken cues: recordings dropped in `src/lib/audio/voice/` (see the README there). Missing ones are skipped. */
export type VoiceCue = 'hajime' | 'san' | 'ni' | 'ichi' | 'nice' | 'boom' | 'shouri' | 'zannen';
export const VOICE_CUES: readonly VoiceCue[] = [
	'hajime',
	'san',
	'ni',
	'ichi',
	'nice',
	'boom',
	'shouri',
	'zannen'
];

// Vite lists the recordings that exist at build time, so a missing file never causes a failed request.
const voiceFiles = import.meta.glob('../audio/voice/*.{mp3,ogg,wav,m4a,webm}', {
	eager: true,
	query: '?url',
	import: 'default'
}) as Record<string, string>;

/** Minimum seconds between two plays of the same cue, so praise never becomes a nag. */
const VOICE_GAP: Partial<Record<VoiceCue, number>> = { nice: 6 };

/** MIDI note number to frequency. */
const hz = (note: number): number => 440 * 2 ** ((note - 69) / 12);

// C major landmarks used by the sounds below
const C4 = 60;
const E4 = 64;
const G4 = 67;
const C5 = 72;
const E5 = 76;
const G5 = 79;
const B5 = 83;
const C6 = 84;
const E6 = 88;
const G6 = 91;
const C7 = 96;

interface Note {
	freq: number;
	start: number;
	dur: number;
	gain: number;
	type?: OscillatorType;
	wave?: PeriodicWave;
	slideTo?: number;
	attack?: number;
	wet?: number;
	/** low-pass cutoff at the start and at the end of the note: a "wah" that makes brass and plucks */
	lowpass?: [number, number];
	detune?: number;
}

interface Noise {
	start: number;
	dur: number;
	gain: number;
	type: BiquadFilterType;
	from: number;
	to: number;
	wet?: number;
}

/** Loudness balance, measured by rendering each sound offline: small cues quiet, the bomb and the fanfare big. */
const LEVEL: Record<SfxName, number> = {
	click: 3.2,
	tick: 2.6,
	warn: 2.4,
	turn: 1.1,
	accept: 2.6,
	reject: 1.1,
	life: 1.3,
	out: 2.8,
	boom: 2.8,
	win: 1.9,
	lose: 2.2,
	go: 1.6,
	don: 1.7,
	ka: 2.4,
	crackle: 3
};

class SfxEngine {
	#ctx: AudioContext | null = null;
	#master: GainNode | null = null;
	#dry: GainNode | null = null;
	#reverb: ConvolverNode | null = null;
	#noise: AudioBuffer | null = null;
	#pulse: PeriodicWave | null = null;
	#muted = false;
	#volume = 0.7;
	#loaded = false;
	#voices = new Map<string, AudioBuffer[]>();
	#voiceLast = new Map<string, { at: number; index: number }>();
	#scale = 1; // gain multiplier of the sound being scheduled (see LEVEL)

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

	/** True once the audio context is awake: nothing more to unlock. */
	get running(): boolean {
		return this.#ctx?.state === 'running';
	}

	/**
	 * Browsers only start audio from a real user gesture (a click, a tap, a key press; not F12, Ctrl or a scroll):
	 * call this from the events that are one. Chrome tells whether the page has had one; asking before only makes
	 * a console warning and leaves the context asleep, so in that case this waits for the next event.
	 */
	unlock(): void {
		this.load();
		const activation = (navigator as { userActivation?: { isActive: boolean } }).userActivation;
		if (!this.#ctx && activation && !activation.isActive) return;
		try {
			if (!this.#ctx) {
				const Ctor =
					window.AudioContext ??
					(window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
				if (!Ctor) return;
				this.#build(new Ctor());
			}
			if (this.#ctx?.state === 'suspended') void this.#ctx.resume();
		} catch {
			/* audio is optional */
		}
	}

	/** voices -> dry bus + reverb send -> compressor -> master volume -> speakers */
	#build(ctx: AudioContext): void {
		this.#ctx = ctx;
		const compressor = ctx.createDynamicsCompressor();
		compressor.threshold.value = -16;
		compressor.knee.value = 18;
		compressor.ratio.value = 4;
		compressor.attack.value = 0.003;
		compressor.release.value = 0.15;
		this.#master = ctx.createGain();
		compressor.connect(this.#master).connect(ctx.destination);
		this.#dry = ctx.createGain();
		this.#dry.connect(compressor);
		this.#reverb = ctx.createConvolver();
		this.#reverb.buffer = this.#impulse(ctx, 0.55);
		this.#reverb.connect(compressor);
		this.#applyVolume();
		void this.#loadVoices(ctx);
	}

	/** A small bright room: decaying noise, a little darker toward the end. */
	#impulse(ctx: AudioContext, seconds: number): AudioBuffer {
		const length = Math.floor(ctx.sampleRate * seconds);
		const buffer = ctx.createBuffer(2, length, ctx.sampleRate);
		for (let channel = 0; channel < 2; channel++) {
			const data = buffer.getChannelData(channel);
			let smooth = 0;
			for (let i = 0; i < length; i++) {
				const decay = (1 - i / length) ** 2.6;
				const white = Math.random() * 2 - 1;
				smooth += (white - smooth) * (0.55 - 0.4 * (i / length)); // one-pole low-pass, darker over time
				data[i] = smooth * decay;
			}
		}
		return buffer;
	}

	/** 25% pulse wave: the classic "coin" timbre, softened by a low-pass at the note level. */
	#pulseWave(ctx: AudioContext): PeriodicWave {
		if (this.#pulse) return this.#pulse;
		const harmonics = 40;
		const duty = 0.25;
		const real = new Float32Array(harmonics);
		const imag = new Float32Array(harmonics);
		for (let n = 1; n < harmonics; n++)
			real[n] = (2 / (n * Math.PI)) * Math.sin(n * Math.PI * duty);
		this.#pulse = ctx.createPeriodicWave(real, imag);
		return this.#pulse;
	}

	play(name: SfxName, step = 0): void {
		this.load();
		const ctx = this.#ctx;
		if (!ctx || this.#muted || ctx.state !== 'running') return;
		const t = ctx.currentTime + 0.01;
		this.#scale = LEVEL[name];
		switch (name) {
			case 'click': {
				// a soft "pop" with a hair of random pitch so repeated presses never sound mechanical
				const detune = 1 + (Math.random() - 0.5) * 0.06;
				this.#note({
					freq: 640 * detune,
					slideTo: 1020 * detune,
					start: t,
					dur: 0.07,
					gain: 0.16,
					attack: 0.002
				});
				this.#note({
					freq: hz(E6) * detune,
					start: t,
					dur: 0.05,
					gain: 0.03,
					type: 'triangle',
					attack: 0.002
				});
				break;
			}
			case 'tick':
				this.#don(t, 0.4, 1.5); // a small drum counts the seconds
				break;
			case 'go':
				// start of the game: the big drum and a wooden clack on top
				this.#odaiko(t);
				this.#hyoshigi(t, 1);
				this.#bell(hz(C6), t + 0.02, 1.2, 0.12, 0.4);
				break;
			case 'don':
				this.#don(t, 1, 1);
				break;
			case 'ka':
				this.#ka(t, 1);
				break;
			case 'warn': {
				// last seconds of your turn: three rising wood ticks, the last one a little louder
				const level = Math.min(2, Math.max(0, step));
				this.#ka(t, 0.8 + level * 0.15);
				this.#don(t, 0.35 + level * 0.1, 1.5 + level * 0.12);
				break;
			}
			case 'turn':
				// "ding-dong": two bells, rising
				this.#don(t, 0.3, 1.4);
				this.#bell(hz(G5), t, 0.9, 0.2, 0.28);
				this.#bell(hz(C6), t + 0.12, 1.1, 0.22, 0.3);
				break;
			case 'accept':
				// coin: a pulse note then a held pulse note a fourth above, with a bell sparkle on top
				this.#note({
					freq: hz(B5),
					start: t,
					dur: 0.07,
					gain: 0.1,
					wave: this.#pulseWave(ctx),
					lowpass: [5200, 3000],
					attack: 0.003
				});
				this.#note({
					freq: hz(E6),
					start: t + 0.07,
					dur: 0.38,
					gain: 0.1,
					wave: this.#pulseWave(ctx),
					lowpass: [5200, 1800],
					attack: 0.003,
					wet: 0.2
				});
				this.#bell(hz(C7 + 4), t + 0.07, 0.6, 0.06, 0.35);
				this.#pluck(hz(E5), t, 0.2, 0.12);
				break;
			case 'reject':
				// a friendly "bonk": two soft falling notes, no harshness
				this.#note({
					freq: hz(E4 + 1),
					start: t,
					dur: 0.11,
					gain: 0.2,
					type: 'triangle',
					lowpass: [1500, 700],
					attack: 0.004
				});
				this.#note({
					freq: hz(C4 + 1),
					slideTo: hz(C4 - 2),
					start: t + 0.1,
					dur: 0.26,
					gain: 0.22,
					type: 'triangle',
					lowpass: [1400, 500],
					attack: 0.004
				});
				this.#note({ freq: 120, slideTo: 60, start: t + 0.1, dur: 0.18, gain: 0.25, type: 'sine' });
				break;
			case 'life':
				// a rising glockenspiel arpeggio
				[C6, E6, G6, C7].forEach((n, i) => this.#bell(hz(n), t + i * 0.065, 0.7, 0.14, 0.4));
				this.#pluck(hz(C5), t, 0.3, 0.12);
				break;
			case 'out':
				// eliminated: a falling whoosh
				this.#note({
					freq: 520,
					slideTo: 90,
					start: t,
					dur: 0.45,
					gain: 0.16,
					type: 'triangle',
					lowpass: [2400, 300]
				});
				this.#noiseHit({
					start: t,
					dur: 0.4,
					gain: 0.12,
					type: 'bandpass',
					from: 3000,
					to: 300,
					wet: 0.2
				});
				break;
			case 'boom':
				this.#noiseHit({ start: t, dur: 0.12, gain: 0.34, type: 'bandpass', from: 5500, to: 1400 }); // the crack
				this.#note({
					freq: 150,
					slideTo: 32,
					start: t,
					dur: 0.7,
					gain: 0.75,
					type: 'sine',
					attack: 0.004
				}); // sub thump
				this.#noiseHit({
					start: t + 0.01,
					dur: 1.0,
					gain: 0.5,
					type: 'lowpass',
					from: 900,
					to: 55,
					wet: 0.45
				}); // rumble
				this.#note({
					freq: 780,
					slideTo: 90,
					start: t + 0.05,
					dur: 0.45,
					gain: 0.08,
					type: 'triangle',
					lowpass: [3000, 400]
				}); // cartoon fall
				break;
			case 'win':
				this.#winPattern(t);
				break;
			case 'lose':
				// a gentle "wah wah wah wahhh", never cruel, over one low drum beat
				this.#don(t, 0.5, 0.75);
				[G4, G4 - 1, G4 - 2].forEach((n, i) =>
					this.#note({
						freq: hz(n),
						start: t + i * 0.2,
						dur: 0.2,
						gain: 0.14,
						type: 'triangle',
						lowpass: [1800, 700],
						attack: 0.01,
						wet: 0.2
					})
				);
				this.#note({
					freq: hz(G4 - 3),
					slideTo: hz(G4 - 6),
					start: t + 0.6,
					dur: 0.6,
					gain: 0.15,
					type: 'triangle',
					lowpass: [1800, 400],
					attack: 0.01,
					wet: 0.25
				});
				break;
			case 'crackle':
				this.#noiseHit({ start: t, dur: 0.03, gain: 0.05, type: 'highpass', from: 4200, to: 4200 });
				break;
		}
	}

	/** Matsuri-style: a taiko pattern (don ka don ka, don don) into the big drum, then the brass fanfare. */
	#winPattern(t: number): void {
		this.#don(t, 0.9, 1);
		this.#ka(t + 0.12, 0.8);
		this.#don(t + 0.24, 0.8, 1.12);
		this.#ka(t + 0.36, 0.8);
		this.#don(t + 0.48, 0.95, 1);
		this.#don(t + 0.6, 1, 1.12);
		this.#odaiko(t + 0.78);
		this.#hyoshigi(t + 0.78, 0.8);
		this.#fanfare(t + 0.78);
	}

	/** Short victory tune: triplet run up to a held high C over a brass chord and a cymbal wash. */
	#fanfare(t: number): void {
		const run = [G4, C5, E5, G5];
		run.forEach((n, i) => this.#brass(hz(n), t + i * 0.1, 0.16, 0.09));
		this.#brass(hz(C6), t + 0.4, 1.0, 0.1);
		[E5, G5, C6].forEach((n) => this.#brass(hz(n), t + 0.4, 1.1, 0.045));
		[C6, E6, G6, C7, G6, E6, C7].forEach((n, i) =>
			this.#bell(hz(n), t + 0.55 + i * 0.075, 0.9, 0.08, 0.45)
		);
		this.#noiseHit({
			start: t + 0.4,
			dur: 1.1,
			gain: 0.07,
			type: 'highpass',
			from: 6500,
			to: 6500,
			wet: 0.5
		});
	}

	/** Taiko, centre hit: a falling sine body, a longer low partner, a skin overtone and a slap of noise. */
	#don(t: number, power: number, pitch: number): void {
		this.#note({
			freq: 170 * pitch,
			slideTo: 68 * pitch,
			start: t,
			dur: 0.38,
			gain: 0.9 * power,
			attack: 0.002,
			wet: 0.3
		});
		this.#note({
			freq: 108 * pitch,
			slideTo: 60 * pitch,
			start: t,
			dur: 0.55,
			gain: 0.5 * power,
			attack: 0.003,
			wet: 0.3
		});
		this.#note({
			freq: 340 * pitch,
			slideTo: 150 * pitch,
			start: t,
			dur: 0.12,
			gain: 0.2 * power,
			type: 'triangle',
			attack: 0.001
		});
		this.#noiseHit({
			start: t,
			dur: 0.05,
			gain: 0.25 * power,
			type: 'bandpass',
			from: 2200,
			to: 700
		});
	}

	/** Taiko, rim hit ("ka"): a dry, bright knock. */
	#ka(t: number, power: number): void {
		this.#noiseHit({
			start: t,
			dur: 0.045,
			gain: 0.3 * power,
			type: 'bandpass',
			from: 3800,
			to: 2200,
			wet: 0.12
		});
		this.#note({
			freq: 520,
			slideTo: 400,
			start: t,
			dur: 0.06,
			gain: 0.3 * power,
			type: 'triangle',
			attack: 0.001
		});
	}

	/** Odaiko: the huge drum. Deep, long, with a rumble. */
	#odaiko(t: number): void {
		this.#note({ freq: 125, slideTo: 42, start: t, dur: 1.0, gain: 1.1, attack: 0.003, wet: 0.35 });
		this.#note({ freq: 72, slideTo: 36, start: t, dur: 1.3, gain: 0.6, attack: 0.004, wet: 0.35 });
		this.#note({
			freq: 300,
			slideTo: 120,
			start: t,
			dur: 0.14,
			gain: 0.25,
			type: 'triangle',
			attack: 0.001
		});
		this.#noiseHit({ start: t, dur: 0.07, gain: 0.35, type: 'bandpass', from: 2000, to: 600 });
		this.#noiseHit({
			start: t,
			dur: 0.7,
			gain: 0.25,
			type: 'lowpass',
			from: 600,
			to: 60,
			wet: 0.45
		});
	}

	/** Hyoshigi: two wooden clappers struck together, the sharp "clack" that opens a kabuki scene. */
	#hyoshigi(t: number, power: number): void {
		this.#note({
			freq: 1900,
			slideTo: 1500,
			start: t,
			dur: 0.04,
			gain: 0.3 * power,
			type: 'triangle',
			attack: 0.001,
			wet: 0.15
		});
		this.#note({ freq: 3300, start: t, dur: 0.02, gain: 0.12 * power, attack: 0.001 });
		this.#noiseHit({
			start: t,
			dur: 0.018,
			gain: 0.2 * power,
			type: 'highpass',
			from: 5000,
			to: 5000
		});
	}

	/** Marimba-like pluck: a sine plus a quickly fading overtone. */
	#pluck(freq: number, t: number, dur: number, gain: number): void {
		this.#note({ freq, start: t, dur, gain, attack: 0.003, wet: 0.15 });
		this.#note({ freq: freq * 4, start: t, dur: dur * 0.25, gain: gain * 0.35, attack: 0.002 });
	}

	/** Glockenspiel / music-box bell: inharmonic partials, the high ones dying first. */
	#bell(freq: number, t: number, dur: number, gain: number, wet: number): void {
		const partials: [number, number, number][] = [
			[1, 1, 1],
			[2.76, 0.45, 0.6],
			[5.4, 0.22, 0.35],
			[8.93, 0.1, 0.2]
		];
		for (const [ratio, level, life] of partials) {
			if (freq * ratio > 12000) continue;
			this.#note({
				freq: freq * ratio,
				start: t,
				dur: dur * life,
				gain: gain * level,
				attack: 0.002,
				wet
			});
		}
	}

	/** Warm brass: two detuned saws through a low-pass that opens then settles. */
	#brass(freq: number, t: number, dur: number, gain: number): void {
		for (const detune of [-7, 7]) {
			this.#note({
				freq,
				start: t,
				dur,
				gain,
				type: 'sawtooth',
				detune,
				lowpass: [700, 3200],
				attack: 0.02,
				wet: 0.25
			});
		}
	}

	/** Decodes the recordings found at build time. Runs once, in the background, after the first user gesture. */
	async #loadVoices(ctx: AudioContext): Promise<void> {
		for (const [path, url] of Object.entries(voiceFiles)) {
			try {
				const cue = (path.split('/').pop() ?? '').replace(/\.[^.]+$/, '').replace(/\d+$/, '');
				const data = await (await fetch(url)).arrayBuffer();
				const buffer = await ctx.decodeAudioData(data);
				this.#voices.set(cue, [...(this.#voices.get(cue) ?? []), buffer]);
			} catch {
				/* a broken file only loses that one cue */
			}
		}
	}

	/** Plays one of the recordings for a cue (when there are several, never the same twice in a row). */
	voice(cue: VoiceCue): boolean {
		this.load();
		const ctx = this.#ctx;
		const takes = this.#voices.get(cue);
		if (!ctx || this.#muted || ctx.state !== 'running' || !takes?.length) return false;
		const last = this.#voiceLast.get(cue);
		if (last && ctx.currentTime - last.at < (VOICE_GAP[cue] ?? 0)) return false;
		let index = Math.floor(Math.random() * takes.length);
		if (takes.length > 1 && last && index === last.index) index = (index + 1) % takes.length;
		this.#voiceLast.set(cue, { at: ctx.currentTime, index });
		const src = ctx.createBufferSource();
		src.buffer = takes[index];
		const gain = ctx.createGain();
		src.connect(gain);
		this.#route(gain, 0.12);
		src.start();
		return true;
	}

	/** Which cues have at least one recording (for the sound showcase page). */
	hasVoice(cue: VoiceCue): boolean {
		return (this.#voices.get(cue)?.length ?? 0) > 0;
	}

	#note(n: Note): void {
		const ctx = this.#ctx;
		if (!ctx || !this.#dry) return;
		const osc = ctx.createOscillator();
		if (n.wave) osc.setPeriodicWave(n.wave);
		else osc.type = n.type ?? 'sine';
		osc.frequency.setValueAtTime(n.freq, n.start);
		if (n.slideTo) osc.frequency.exponentialRampToValueAtTime(n.slideTo, n.start + n.dur);
		if (n.detune) osc.detune.value = n.detune;

		const env = ctx.createGain();
		env.gain.setValueAtTime(0.0001, n.start);
		env.gain.exponentialRampToValueAtTime(n.gain * this.#scale, n.start + (n.attack ?? 0.006));
		env.gain.exponentialRampToValueAtTime(0.0001, n.start + n.dur);

		let source: AudioNode = osc;
		if (n.lowpass) {
			const filter = ctx.createBiquadFilter();
			filter.type = 'lowpass';
			filter.frequency.setValueAtTime(n.lowpass[0], n.start);
			filter.frequency.exponentialRampToValueAtTime(Math.max(60, n.lowpass[1]), n.start + n.dur);
			source.connect(filter);
			source = filter;
		}
		source.connect(env);
		this.#route(env, n.wet ?? 0);
		osc.start(n.start);
		osc.stop(n.start + n.dur + 0.03);
	}

	#noiseHit(n: Noise): void {
		const ctx = this.#ctx;
		if (!ctx || !this.#dry) return;
		if (!this.#noise) {
			const buffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
			const data = buffer.getChannelData(0);
			for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
			this.#noise = buffer;
		}
		const src = ctx.createBufferSource();
		src.buffer = this.#noise;
		const filter = ctx.createBiquadFilter();
		filter.type = n.type;
		filter.frequency.setValueAtTime(n.from, n.start);
		if (n.to !== n.from) filter.frequency.exponentialRampToValueAtTime(n.to, n.start + n.dur);
		const env = ctx.createGain();
		env.gain.setValueAtTime(n.gain * this.#scale, n.start);
		env.gain.exponentialRampToValueAtTime(0.0001, n.start + n.dur);
		src.connect(filter).connect(env);
		this.#route(env, n.wet ?? 0);
		src.start(n.start);
		src.stop(n.start + n.dur + 0.03);
	}

	#route(node: AudioNode, wet: number): void {
		const ctx = this.#ctx;
		if (!ctx || !this.#dry || !this.#reverb) return;
		node.connect(this.#dry);
		if (wet > 0) {
			const send = ctx.createGain();
			send.gain.value = wet;
			node.connect(send).connect(this.#reverb);
		}
	}
}

export const sfx = new SfxEngine();
