import { fetchAccount, type Account } from './auth';

/**
 * Who is signed in, shared by every page. `undefined` until the server has answered (a page must not flash
 * "sign in" for someone who is already signed in), `null` for a guest.
 */
export const account = $state<{ user: Account | null | undefined }>({ user: undefined });

let loading: Promise<void> | null = null;

/** Asks the server once; call `refreshAccount` after signing in or out. */
export function loadAccount(): Promise<void> {
	loading ??= refreshAccount();
	return loading;
}

export async function refreshAccount(): Promise<void> {
	try {
		account.user = await fetchAccount();
	} catch {
		account.user = null; // server unreachable or no database: the player simply stays a guest
	}
}
