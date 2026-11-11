import { defineParams } from '@sveltejs/kit/params';
import { PREFIXED } from './lib/i18n/path.ts';

/** `[[lang=locale]]` in the route tree: only the non-default languages appear in URLs (French is the bare root). */
export const params = defineParams({
	locale: (param: string) => ((PREFIXED as readonly string[]).includes(param) ? param : undefined)
});
