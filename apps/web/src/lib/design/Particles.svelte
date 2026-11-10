<script lang="ts" module>
	export interface BurstOptions {
		count?: number;
		colors?: string[];
		speed?: number;
		gravity?: number;
		size?: number;
		life?: number;
		shape?: 'square' | 'dot' | 'line' | 'petal';
		/** emission cone in radians: [from, to] (default full circle) */
		spread?: [number, number];
	}
</script>

<script lang="ts">
	import { onMount } from 'svelte';

	interface Particle {
		x: number;
		y: number;
		vx: number;
		vy: number;
		g: number;
		life: number;
		max: number;
		size: number;
		color: string;
		shape: NonNullable<BurstOptions['shape']>;
		rot: number;
		vr: number;
	}

	const PALETTE = ['#e8412d', '#e7b94a', '#f5efe3', '#f4a6b8', '#7fb069'];

	let canvas: HTMLCanvasElement | undefined = $state();
	let particles: Particle[] = [];
	let raf = 0;
	let last = 0;
	let width = 0;
	let height = 0;
	let dpr = 1;
	let reduced = false;
	// Hanabi: rockets that rise then burst
	let rockets: { x: number; y: number; vy: number; targetY: number; color: string }[] = [];

	onMount(() => {
		reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		resize();
		window.addEventListener('resize', resize);
		return () => {
			window.removeEventListener('resize', resize);
			cancelAnimationFrame(raf);
		};
	});

	function resize(): void {
		if (!canvas) return;
		dpr = Math.min(2, window.devicePixelRatio || 1);
		width = window.innerWidth;
		height = window.innerHeight;
		canvas.width = Math.round(width * dpr);
		canvas.height = Math.round(height * dpr);
	}

	function start(): void {
		if (raf) return;
		last = performance.now();
		raf = requestAnimationFrame(tick);
	}

	/** Particles for an event: explosion, sparks, confetti. Does nothing visible with reduced motion. */
	export function burst(x: number, y: number, options: BurstOptions = {}): void {
		const {
			count = 24,
			colors = PALETTE,
			speed = 260,
			gravity = 520,
			size = 7,
			life = 0.8,
			shape = 'square',
			spread = [0, Math.PI * 2]
		} = options;
		const n = reduced ? Math.min(4, count) : count;
		for (let i = 0; i < n; i++) {
			const angle = spread[0] + Math.random() * (spread[1] - spread[0]);
			const v = speed * (0.35 + Math.random() * 0.65);
			particles.push({
				x,
				y,
				vx: Math.cos(angle) * (reduced ? 0 : v),
				vy: Math.sin(angle) * (reduced ? 0 : v),
				g: reduced ? 0 : gravity,
				life: 0,
				max: reduced ? 0.35 : life * (0.7 + Math.random() * 0.5),
				size: size * (0.6 + Math.random() * 0.8),
				color: colors[Math.floor(Math.random() * colors.length)],
				shape,
				rot: Math.random() * Math.PI,
				vr: (Math.random() - 0.5) * 10
			});
		}
		start();
	}

	/** A few tiny sparks, used while the fuse burns. */
	export function spark(x: number, y: number, intensity = 1): void {
		if (reduced) return;
		burst(x, y, {
			count: Math.ceil(2 * intensity),
			colors: ['#e7b94a', '#e8412d', '#f5efe3'],
			speed: 90 + 90 * intensity,
			gravity: 260,
			size: 3.2,
			life: 0.4,
			shape: 'dot',
			spread: [Math.PI * 1.1, Math.PI * 1.9]
		});
	}

	/** Big explosion at (x, y). */
	export function explode(x: number, y: number): void {
		burst(x, y, { count: 44, speed: 420, size: 10, life: 0.9, shape: 'square' });
		burst(x, y, {
			count: 16,
			colors: ['#f4a6b8'],
			speed: 220,
			gravity: 140,
			size: 12,
			life: 1.2,
			shape: 'petal'
		});
	}

	/** Firework show for the winner. */
	export function hanabi(duration = 4500): void {
		if (reduced) {
			burst(width / 2, height / 3, { count: 4 });
			return;
		}
		const launches = Math.round(duration / 650);
		for (let i = 0; i < launches; i++) {
			setTimeout(() => {
				rockets.push({
					x: width * (0.15 + Math.random() * 0.7),
					y: height,
					vy: -(height * (1.1 + Math.random() * 0.3)),
					targetY: height * (0.15 + Math.random() * 0.3),
					color: PALETTE[Math.floor(Math.random() * PALETTE.length)]
				});
				start();
			}, i * 650);
		}
	}

	function tick(now: number): void {
		const dt = Math.min(0.05, (now - last) / 1000);
		last = now;
		const ctx = canvas?.getContext('2d');
		if (!ctx) {
			raf = 0;
			return;
		}
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, width, height);

		for (const r of rockets) {
			r.y += r.vy * dt;
			ctx.fillStyle = r.color;
			ctx.fillRect(r.x - 2, r.y, 4, 14);
			if (r.y <= r.targetY) {
				burst(r.x, r.y, {
					count: 46,
					colors: [r.color, '#f5efe3', '#e7b94a'],
					speed: 300,
					gravity: 220,
					size: 9,
					life: 1.3,
					shape: 'line'
				});
				r.y = -9999;
			}
		}
		rockets = rockets.filter((r) => r.y > -9000);

		for (const p of particles) {
			p.life += dt;
			p.vy += p.g * dt;
			p.x += p.vx * dt;
			p.y += p.vy * dt;
			p.rot += p.vr * dt;
			const alpha = Math.max(0, 1 - p.life / p.max);
			ctx.globalAlpha = reduced ? alpha : alpha > 0.35 ? 1 : alpha / 0.35; // opaque, then a quick fade
			ctx.fillStyle = p.color;
			ctx.strokeStyle = p.color;
			if (p.shape === 'square') {
				ctx.save();
				ctx.translate(p.x, p.y);
				ctx.rotate(p.rot);
				ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
				ctx.restore();
			} else if (p.shape === 'dot') {
				ctx.beginPath();
				ctx.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2);
				ctx.fill();
			} else if (p.shape === 'line') {
				const len = Math.hypot(p.vx, p.vy) || 1;
				ctx.lineWidth = 3;
				ctx.lineCap = 'round';
				ctx.beginPath();
				ctx.moveTo(p.x, p.y);
				ctx.lineTo(p.x - (p.vx / len) * p.size, p.y - (p.vy / len) * p.size);
				ctx.stroke();
			} else {
				ctx.save();
				ctx.translate(p.x, p.y);
				ctx.rotate(p.rot);
				ctx.beginPath();
				ctx.ellipse(0, 0, p.size / 2, p.size / 3, 0, 0, Math.PI * 2);
				ctx.fill();
				ctx.restore();
			}
		}
		ctx.globalAlpha = 1;
		particles = particles.filter((p) => p.life < p.max);

		if (particles.length || rockets.length) {
			raf = requestAnimationFrame(tick);
		} else {
			raf = 0; // nothing left to draw: the loop stops
			ctx.clearRect(0, 0, width, height);
		}
	}
</script>

<canvas bind:this={canvas} aria-hidden="true"></canvas>

<style>
	canvas {
		position: fixed;
		inset: 0;
		width: 100vw;
		height: 100dvh;
		pointer-events: none;
		z-index: 60;
	}
</style>
