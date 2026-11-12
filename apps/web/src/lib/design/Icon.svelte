<script lang="ts" module>
	/** One hand-drawn icon family: 24 grid, heavy rounded strokes, no fills except where noted. */
	export const ICONS = {
		copy: 'M8 8h11v12H8z M5 16V4h11',
		share: 'M12 15V4 M7.5 8.5 12 4l4.5 4.5 M5 13v7h14v-7',
		check: 'M4.5 12.5l5 5L19.5 6.5',
		close: 'M6 6l12 12 M18 6L6 18',
		crown: 'M4 18h16 M4.5 8l4.5 4 3-6 3 6 4.5-4-1.5 10h-12z',
		kick: 'M5 12h10 M11 7l5 5-5 5 M19 5v14',
		volume: 'M4 9.5h3.5L12 5.5v13l-4.5-4H4z M15.5 9c1.5 1.5 1.5 4.5 0 6 M18 6.5c3 3 3 8 0 11',
		mute: 'M4 9.5h3.5L12 5.5v13l-4.5-4H4z M16 9.5l5 5 M21 9.5l-5 5',
		gear: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z M12 3v3 M12 18v3 M3 12h3 M18 12h3 M5.6 5.6l2.1 2.1 M16.3 16.3l2.1 2.1 M5.6 18.4l2.1-2.1 M16.3 7.7l2.1-2.1',
		back: 'M19 12H6 M11 6l-6 6 6 6',
		users:
			'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z M2.5 20c0-3.5 2.8-6 6.5-6s6.5 2.5 6.5 6 M16.5 4.5a3 3 0 0 1 0 6 M18 14.3c2 .7 3.5 2.6 3.5 5.7',
		eye: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
		send: 'M4 12l16-8-6 16-2.5-6.5z',
		sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M12 2.5v2 M12 19.5v2 M2.5 12h2 M19.5 12h2 M5.3 5.3l1.4 1.4 M17.3 17.3l1.4 1.4 M5.3 18.7l1.4-1.4 M17.3 6.7l1.4-1.4',
		moon: 'M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z',
		refresh: 'M19.5 12a7.5 7.5 0 1 1-2.4-5.5 M19.5 4v4.5H15',
		home: 'M3.5 11.5L12 4l8.5 7.5 M6 10v10h12V10',
		play: 'M7 4.5l12 7.5-12 7.5z',
		clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3.5 2',
		wifiOff:
			'M3 3l18 18 M2 9c2.5-2 5-3 8-3.3 M22 9c-1.4-1.1-2.9-1.9-4.5-2.5 M5.5 12.5C7 11.3 8.6 10.6 10.5 10.3 M18.5 12.5c-.7-.6-1.5-1.1-2.3-1.5 M9 16c1.7-1.2 4.3-1.2 6 0 M12 19.5v.01',
		chat: 'M4 5h16v11H11l-5 4v-4H4z',
		trophy: 'M7 4h10v6a5 5 0 0 1-10 0z M7 6H4c0 3 1 4.5 3 5 M17 6h3c0 3-1 4.5-3 5 M12 15v4 M8 20h8',
		bolt: 'M13 3L5 13.5h6L10 21l9-11.5h-6z',
		book: 'M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z M5 17a3 3 0 0 1 3-3h11',
		user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4.5 20c.8-3.8 3.9-6 7.5-6s6.7 2.2 7.5 6',
		chevron: 'M6 9l6 6 6-6'
	} as const;
	export type IconName = keyof typeof ICONS;
</script>

<script lang="ts">
	let { name, size = 24, label }: { name: IconName; size?: number; label?: string } = $props();
</script>

<svg
	class="icon"
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="2.6"
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	<path d={ICONS[name]} />
</svg>

<style>
	.icon {
		flex: none;
		display: block;
	}
</style>
