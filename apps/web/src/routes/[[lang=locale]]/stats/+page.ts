import { redirect } from '@sveltejs/kit';
import { GAME_IDS } from '#lib/games/registry.ts';
import { localeFromPath, localizePath } from '#lib/i18n/index.ts';
import type { PageLoad } from './$types';

/** With a single game there is nothing to choose: go straight to its statistics. */
export const load: PageLoad = ({ url }) => {
	if (GAME_IDS.length === 1) {
		redirect(307, localizePath(`/stats/${GAME_IDS[0]}`, localeFromPath(url.pathname)));
	}
};
