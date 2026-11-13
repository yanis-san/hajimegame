import { error } from '@sveltejs/kit';
import { ACCOUNTS } from '#lib/game/config.ts';

/** Accounts are switched off on this build: these pages do not exist. */
export const load = (): void => {
	if (!ACCOUNTS) error(404, 'Not found');
};
