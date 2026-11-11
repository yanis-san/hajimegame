<script lang="ts">
	/**
	 * Night festival backdrop. It does not depend on the screen shape: one even seigaiha pattern over the whole page
	 * and low hills along the bottom edge. Nothing stretches with the window.
	 */
</script>

<div class="sky" aria-hidden="true">
	<svg class="pattern" width="100%" height="100%" focusable="false">
		<defs>
			<pattern id="seigaiha" width="48" height="24" patternUnits="userSpaceOnUse">
				<g fill="none" stroke="var(--sky-wave)" stroke-width="2">
					<circle cx="24" cy="24" r="22" />
					<circle cx="24" cy="24" r="15" />
					<circle cx="24" cy="24" r="8" />
					<circle cx="0" cy="12" r="22" />
					<circle cx="0" cy="12" r="15" />
					<circle cx="0" cy="12" r="8" />
					<circle cx="48" cy="12" r="22" />
					<circle cx="48" cy="12" r="15" />
					<circle cx="48" cy="12" r="8" />
				</g>
			</pattern>
		</defs>
		<rect width="100%" height="100%" fill="url(#seigaiha)" />
	</svg>

	<svg class="hills" viewBox="0 0 400 100" preserveAspectRatio="none" focusable="false">
		<path
			d="M0 62 L55 28 L120 56 L200 14 L280 52 L350 24 L400 44 V100 H0z"
			fill="var(--sky-hill-far)"
		/>
		<path d="M0 82 L70 56 L160 78 L250 50 L330 74 L400 60 V100 H0z" fill="var(--sky-hill-near)" />
	</svg>
</div>

<style>
	.sky {
		position: fixed;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		overflow: hidden;
		background: var(--sky-bg);
		--sky-bg: #0f1b2d;
		--sky-wave: #15243b;
		--sky-hill-far: #17263f;
		--sky-hill-near: #1b2c49;
	}
	:global(:root[data-theme='light']) .sky {
		--sky-bg: #f5efe3;
		--sky-wave: #e9dfc9;
		--sky-hill-far: #e2d8c1;
		--sky-hill-near: #d8ceb6;
	}
	.pattern {
		position: absolute;
		inset: 0;
	}
	.hills {
		position: absolute;
		left: 0;
		bottom: 0;
		width: 100%;
		height: clamp(5rem, 18vh, 11rem);
	}
</style>
