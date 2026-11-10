<script lang="ts">
	import { page } from '$app/state';
	import ErrorScreen from '#lib/design/ErrorScreen.svelte';
	import { t } from '#lib/i18n/index.ts';
</script>

<svelte:head><title>{t('error.404.title')} · Hajime</title></svelte:head>

{#if page.status === 404}
	<ErrorScreen title={t('error.404.title')} body={t('error.404.body')} />
{:else}
	<ErrorScreen title={t('error.generic.title')} body={t('error.generic.body')} mood="worried" />
{/if}
