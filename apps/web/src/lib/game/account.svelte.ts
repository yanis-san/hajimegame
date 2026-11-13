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

const HINT = 'hajime:signed-in-as';

/** The name of whoever was signed in last time, so the header can show the right buttons at once. */
export function rememberedName(): string | null {
	try {
		return localStorage.getItem(HINT);
	} catch {
		return null;
	}
}

export async function refreshAccount(): Promise<void> {
	try {
		account.user = await fetchAccount();
	} catch {
		account.user = null; // server unreachable or no database: the player simply stays a guest
	}
	try {
		if (account.user) localStorage.setItem(HINT, account.user.username);
		else localStorage.removeItem(HINT);
	} catch {
		/* storage can be missing: the header then waits for the server */
	}
}
