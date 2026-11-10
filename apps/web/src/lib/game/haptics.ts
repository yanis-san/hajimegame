/** Vibration is a bonus: it does not exist on iOS Safari, so nothing may depend on it. */
export type HapticName = 'tap' | 'accept' | 'reject' | 'boom' | 'win';

const PATTERNS: Record<HapticName, number | number[]> = {
	tap: 8,
	accept: [14, 30, 14],
	reject: [40, 40, 40],
	boom: [90, 40, 160],
	win: [20, 40, 20, 40, 60]
};

export function haptic(name: HapticName): void {
	try {
		if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
			navigator.vibrate(PATTERNS[name]);
		}
	} catch {
		/* ignore */
	}
}
