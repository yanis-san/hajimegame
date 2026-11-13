<script lang="ts">
	import Icon from './Icon.svelte';
	import { LOCALES, getLocale, isLocale, t, type Locale } from '#lib/i18n/index.ts';

	let { onchange }: { onchange: (locale: Locale) => void } = $props();

	function pick(event: Event): void {
		const value = (event.currentTarget as HTMLSelectElement).value;
		if (isLocale(value)) onchange(value);
	}
</script>

<label class="lang">
	<span class="text">{t('lang.label')}</span>
	<span class="field">
		<select aria-label={t('lang.label')} value={getLocale()} onchange={pick}>
			{#each LOCALES as option (option.code)}
				<option value={option.code} lang={option.code}>{option.name}</option>
			{/each}
		</select>
		<Icon name="chevron" size={18} />
	</span>
</label>

<style>
	.lang {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--text-mute);
		font-size: 0.85rem;
		font-weight: 700;
	}
	.field {
		position: relative;
		display: inline-flex;
		align-items: center;
	}
	select {
		appearance: none;
		min-height: 40px;
		padding: 0.3rem 2rem 0.45rem 0.85rem;
		background: var(--surface-2);
		color: var(--text);
		border: var(--line) solid var(--sumi);
		border-radius: 11px;
		box-shadow:
			inset 0 -4px 0 rgb(0 0 0 / 0.22),
			0 4px 0 var(--sumi);
		font: inherit;
		font-size: 0.95rem;
		font-weight: 700;
		cursor: pointer;
		transition:
			transform var(--t-fast) var(--ease-pop),
			box-shadow var(--t-fast) var(--ease-snap);
	}
	/* the arrow is an icon laid over the select, so it matches the rest of the set */
	.field :global(svg) {
		position: absolute;
		right: 0.55rem;
		pointer-events: none;
		color: var(--text);
	}
	@media (hover: hover) {
		select:hover {
			transform: translateY(-2px);
			box-shadow:
				inset 0 -4px 0 rgb(0 0 0 / 0.22),
				0 6px 0 var(--sumi);
		}
	}
	select:focus-visible {
		outline: 3px solid var(--kinpaku);
		outline-offset: 3px;
	}
	/* the smallest phones (320 px): the bar has no spare pixel, so the select gives some back */
	@media (max-width: 380px) {
		select {
			padding: 0.3rem 1.7rem 0.45rem 0.6rem;
			font-size: 0.9rem;
		}
		.field :global(svg) {
			right: 0.35rem;
		}
	}
	/* phones: only the select, the label stays available to screen readers */
	@media (max-width: 640px) {
		.text {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip-path: inset(50%);
		}
	}
</style>
