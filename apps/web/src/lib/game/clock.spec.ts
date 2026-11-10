import { describe, expect, it } from 'vitest';
import { ClockSync } from './clock';

/** Simulate a server whose clock is `skew` ms ahead and a link with the given one-way delays. */
function sample(clock: ClockSync, skew: number, up: number, down: number, sentAt = 1000): void {
	const serverTime = sentAt + up + skew; // server stamps the pong on arrival
	const receivedAt = sentAt + up + down;
	clock.addPong(sentAt, receivedAt, serverTime);
}

describe('ClockSync', () => {
	it('is not ready before three samples', () => {
		const clock = new ClockSync();
		sample(clock, 500, 20, 20);
		sample(clock, 500, 20, 20);
		expect(clock.ready).toBe(false);
		sample(clock, 500, 20, 20);
		expect(clock.ready).toBe(true);
	});

	it('recovers the offset on a symmetric link', () => {
		const clock = new ClockSync();
		for (let i = 0; i < 8; i++) sample(clock, 12_345, 30, 30);
		expect(clock.offset).toBeCloseTo(12_345, 0);
		expect(clock.rtt).toBe(60);
	});

	it('ignores samples delayed by queueing (keeps the low-RTT half)', () => {
		const clock = new ClockSync();
		for (let i = 0; i < 5; i++) sample(clock, 800, 25, 25);
		// congested samples: asymmetric and slow, would skew a naive mean by 100+ ms
		for (let i = 0; i < 3; i++) sample(clock, 800, 25, 400);
		expect(Math.abs(clock.offset - 800)).toBeLessThan(5);
	});

	it('stays within 100 ms of the truth under realistic jitter', () => {
		const clock = new ClockSync();
		let seed = 7;
		const rand = () => {
			seed = (seed * 16807) % 2147483647;
			return seed / 2147483647;
		};
		for (let i = 0; i < 12; i++)
			sample(clock, -3_000, 20 + rand() * 80, 20 + rand() * 80, 1000 + i * 120);
		expect(Math.abs(clock.offset + 3_000)).toBeLessThan(100);
	});

	it('converts between server and local time', () => {
		const clock = new ClockSync();
		for (let i = 0; i < 4; i++) sample(clock, 1_000, 10, 10);
		expect(clock.toLocal(clock.serverNow(5_000))).toBeCloseTo(5_000, 5);
		expect(clock.remaining(clock.serverNow(2_000) + 750, 2_000)).toBeCloseTo(750, 5);
	});

	it('drops impossible samples and old samples', () => {
		const clock = new ClockSync(4);
		clock.addPong(100, 50, 0); // negative rtt
		clock.addPong(Number.NaN, 50, 0);
		expect(clock.sampleCount).toBe(0);
		for (let i = 0; i < 10; i++) sample(clock, 0, 10, 10);
		expect(clock.sampleCount).toBe(4);
		clock.reset();
		expect(clock.sampleCount).toBe(0);
		expect(clock.rtt).toBe(0);
	});
});
