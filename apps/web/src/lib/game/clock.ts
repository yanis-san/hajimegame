/**
 * Estimates the offset between this device clock and the server clock, NTP style.
 *
 * For each ping we know when it left (t0), when the pong came back (t1, both on performance.now()) and the server
 * time stamped in the pong (s). Assuming symmetric latency, the server time at t1 is s + rtt / 2, so
 * offset = s + rtt / 2 - t1. We keep the last samples and take the median of the lowest-RTT half, which discards
 * the samples delayed by queueing.
 */
export interface ClockSample {
	offset: number;
	rtt: number;
}

export class ClockSync {
	#samples: ClockSample[] = [];
	#offset = 0;
	readonly #max: number;

	constructor(maxSamples = 16) {
		this.#max = maxSamples;
	}

	get ready(): boolean {
		return this.#samples.length >= 3;
	}

	get sampleCount(): number {
		return this.#samples.length;
	}

	/** server time minus local time, in ms */
	get offset(): number {
		return this.#offset;
	}

	/** Best known round trip time, in ms (0 when unknown). */
	get rtt(): number {
		if (this.#samples.length === 0) return 0;
		return Math.min(...this.#samples.map((s) => s.rtt));
	}

	addPong(sentAt: number, receivedAt: number, serverTime: number): void {
		const rtt = receivedAt - sentAt;
		if (!Number.isFinite(rtt) || rtt < 0) return;
		const offset = serverTime + rtt / 2 - receivedAt;
		this.#samples.push({ offset, rtt });
		if (this.#samples.length > this.#max) this.#samples.shift();
		this.#recompute();
	}

	#recompute(): void {
		const byRtt = [...this.#samples].sort((a, b) => a.rtt - b.rtt);
		const best = byRtt.slice(0, Math.max(1, Math.ceil(byRtt.length / 2)));
		const offsets = best.map((s) => s.offset).sort((a, b) => a - b);
		const mid = Math.floor(offsets.length / 2);
		this.#offset = offsets.length % 2 ? offsets[mid] : (offsets[mid - 1] + offsets[mid]) / 2;
	}

	/** Current server time in ms. */
	serverNow(localNow: number = performance.now()): number {
		return localNow + this.#offset;
	}

	/** Convert a server timestamp to the local performance.now() timebase. */
	toLocal(serverTime: number): number {
		return serverTime - this.#offset;
	}

	/** Milliseconds left until a server deadline (negative once passed). */
	remaining(serverDeadline: number, localNow: number = performance.now()): number {
		return serverDeadline - this.serverNow(localNow);
	}

	reset(): void {
		this.#samples = [];
		this.#offset = 0;
	}
}
