<script lang="ts">
	/** Night festival backdrop: flat colour bands, a moon, hills, a string of lanterns and a seigaiha waterline. */
	const stars = [
		[40, 60],
		[120, 110],
		[210, 50],
		[320, 90],
		[370, 40],
		[70, 170],
		[260, 150],
		[350, 190],
		[160, 30],
		[20, 130]
	];
	const lanterns = [30, 105, 180, 255, 330];
</script>

<svg
	class="sky"
	viewBox="0 0 400 800"
	preserveAspectRatio="xMidYMax slice"
	aria-hidden="true"
	focusable="false"
>
	<defs>
		<pattern id="seigaiha" width="40" height="20" patternUnits="userSpaceOnUse">
			<g fill="none" stroke="var(--sky-wave)" stroke-width="2">
				<circle cx="20" cy="20" r="18" />
				<circle cx="20" cy="20" r="12" />
				<circle cx="20" cy="20" r="6" />
				<circle cx="0" cy="10" r="18" />
				<circle cx="0" cy="10" r="12" />
				<circle cx="0" cy="10" r="6" />
				<circle cx="40" cy="10" r="18" />
				<circle cx="40" cy="10" r="12" />
				<circle cx="40" cy="10" r="6" />
			</g>
		</pattern>
	</defs>
	<!-- flat bands, darkest at the top -->
	<rect width="400" height="800" fill="var(--sky-1)" />
	<rect y="180" width="400" height="620" fill="var(--sky-2)" />
	<rect y="360" width="400" height="440" fill="var(--sky-3)" />
	<rect y="520" width="400" height="280" fill="var(--sky-4)" />

	{#each stars as [x, y] (x + ':' + y)}
		<path
			d="M{x} {y - 3}l1.4 1.6 1.6 1.4-1.6 1.4-1.4 1.6-1.4-1.6-1.6-1.4 1.6-1.4z"
			fill="var(--sky-star)"
		/>
	{/each}

	<!-- moon: disc plus a flat crescent cut -->
	<circle cx="352" cy="330" r="30" fill="var(--sky-moon)" stroke="var(--sumi)" stroke-width="3" />
	<circle cx="362" cy="322" r="25" fill="var(--sky-2)" />

	<!-- far hills -->
	<path
		d="M0 560 L60 500 L130 548 L210 480 L290 540 L360 492 L400 520 V800 H0z"
		fill="var(--sky-hill-far)"
	/>
	<path
		d="M0 620 L80 566 L170 612 L260 560 L340 604 L400 580 V800 H0z"
		fill="var(--sky-hill-near)"
	/>

	<!-- lantern string -->
	<path d="M-10 18 Q200 52 410 18" fill="none" stroke="var(--sumi)" stroke-width="3" />
	{#each lanterns as x, i (x)}
		{@const y = 30 + Math.sin(((x + 10) / 400) * Math.PI) * 14}
		<g transform="translate({x} {y})">
			<rect x="-3" y="0" width="6" height="8" fill="var(--sumi)" />
			<ellipse
				cx="0"
				cy="22"
				rx="14"
				ry="16"
				fill={i % 2 ? 'var(--shu)' : 'var(--kinpaku)'}
				stroke="var(--sumi)"
				stroke-width="2.5"
			/>
			<path
				d="M-13 17h26M-14 23h28M-13 29h26"
				stroke="var(--sumi)"
				stroke-width="1.6"
				fill="none"
			/>
			<rect x="-7" y="36" width="14" height="5" fill="var(--sumi)" />
		</g>
	{/each}

	<!-- waterline -->
	<rect y="700" width="400" height="100" fill="var(--sky-water)" />
	<rect y="700" width="400" height="100" fill="url(#seigaiha)" />
</svg>

<style>
	.sky {
		position: fixed;
		inset: 0;
		width: 100%;
		height: 100%;
		z-index: -1;
		pointer-events: none;
		--sky-1: #0a1320;
		--sky-2: #0f1b2d;
		--sky-3: #14233a;
		--sky-4: #1a2c48;
		--sky-hill-far: #1b2a44;
		--sky-hill-near: #16233a;
		--sky-water: #101c30;
		--sky-wave: #142238;
		--sky-star: #f5efe3;
		--sky-moon: #e7b94a;
	}
	:global(:root[data-theme='light']) .sky {
		--sky-1: #e6dcc6;
		--sky-2: #efe6d2;
		--sky-3: #f5efe3;
		--sky-4: #f8f3e8;
		--sky-hill-far: #d7cdb6;
		--sky-hill-near: #c8bea8;
		--sky-water: #d9cfb8;
		--sky-wave: #c3b79c;
		--sky-star: #c3b79c;
		--sky-moon: #e7b94a;
	}
</style>
