// Renders every sound offline, checks levels and writes WAV files.   BASE_URL=http://localhost:5273 node scripts/sounds.mjs
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const outDir = new URL('../.sounds/', import.meta.url);
mkdirSync(outDir, { recursive: true });
const names = [
	'click',
	'tick',
	'warn',
	'go',
	'don',
	'ka',
	'turn',
	'accept',
	'reject',
	'life',
	'out',
	'boom',
	'lose',
	'win',
	'crackle'
];

const b = await chromium.launch();
const errors = [];
for (const name of names) {
	const page = await b.newPage();
	page.on('pageerror', (e) => errors.push(`${name}: ${e.message}`));
	await page.goto(BASE + '/design');
	await page.waitForLoadState('networkidle');
	const result = await page.evaluate(async (soundName) => {
		const Real = window.AudioContext;
		let offline;
		window.AudioContext = class {
			constructor() {
				offline = new OfflineAudioContext(2, 44100 * 3, 44100);
				Object.defineProperty(offline, 'state', { get: () => 'running' });
				offline.resume = async () => {};
				return offline;
			}
		};
		const { sfx } = await import('/src/lib/game/sfx.ts');
		sfx.setMuted(false);
		sfx.unlock();
		sfx.play(soundName, soundName === 'warn' ? 2 : 0);
		const buffer = await offline.startRendering();
		window.AudioContext = Real;
		const data = buffer.getChannelData(0);
		let peak = 0,
			last = 0;
		for (let i = 0; i < data.length; i++) {
			const a = Math.abs(data[i]);
			if (Number.isNaN(a)) return { nan: true };
			peak = Math.max(peak, a);
			if (a > 0.003) last = i;
		}
		return { peak, seconds: last / 44100, samples: Array.from(data.slice(0, last + 2000)) };
	}, name);
	await page.close();
	if (result.nan) {
		errors.push(`${name}: NaN`);
		continue;
	}
	const pcm = Buffer.alloc(44 + result.samples.length * 2);
	pcm.write('RIFF', 0);
	pcm.writeUInt32LE(36 + result.samples.length * 2, 4);
	pcm.write('WAVEfmt ', 8);
	pcm.writeUInt32LE(16, 16);
	pcm.writeUInt16LE(1, 20);
	pcm.writeUInt16LE(1, 22);
	pcm.writeUInt32LE(44100, 24);
	pcm.writeUInt32LE(88200, 28);
	pcm.writeUInt16LE(2, 32);
	pcm.writeUInt16LE(16, 34);
	pcm.write('data', 36);
	pcm.writeUInt32LE(result.samples.length * 2, 40);
	result.samples.forEach((s, i) =>
		pcm.writeInt16LE(Math.round(Math.max(-1, Math.min(1, s)) * 32767), 44 + i * 2)
	);
	writeFileSync(new URL(`${name}.wav`, outDir), pcm);
	console.log(
		name.padEnd(8),
		'peak',
		result.peak.toFixed(2),
		'length',
		result.seconds.toFixed(2) + 's'
	);
}
console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no errors');
await b.close();
