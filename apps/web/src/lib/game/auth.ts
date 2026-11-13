import { apiUrl } from './config';
import { ApiError } from './api';
import { getGuestId } from './guest';
import { getLocale } from '#lib/i18n/index.ts';

/** The signed-in player, as the server describes them. */
export interface Account {
	username: string;
	email: string | null;
	email_verified: boolean;
}

const HEADERS = { 'Content-Type': 'application/json', 'X-Hajime-Client': 'web' };

async function call<T>(
	path: string,
	init: { method?: 'GET' | 'POST'; body?: unknown } = {},
	fetcher: typeof fetch = fetch
): Promise<T> {
	const response = await fetcher(apiUrl(path), {
		method: init.method ?? 'POST',
		headers: HEADERS,
		body: init.body === undefined ? undefined : JSON.stringify(init.body)
	});
	if (!response.ok) {
		const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
		throw new ApiError(response.status, typeof body.detail === 'string' ? body.detail : 'error');
	}
	return (await response.json()) as T;
}

/** Who is signed in on this browser, or null for a guest. */
export async function fetchAccount(fetcher: typeof fetch = fetch): Promise<Account | null> {
	const body = await call<{ user: Account | null }>('/api/auth/me', { method: 'GET' }, fetcher);
	return body.user;
}

/** The browser's guest identifier travels with sign-up and sign-in: that is what attaches past games. */
export async function signUp(
	input: {
		username: string;
		password: string;
		email: string;
		/** YYYY-MM-DD, as a date field gives it */
		birthDate: string;
		captcha: string;
	},
	fetcher: typeof fetch = fetch
): Promise<Account> {
	return call<Account>(
		'/api/auth/register',
		{
			body: {
				username: input.username,
				password: input.password,
				email: input.email.trim(),
				birth_date: input.birthDate,
				lang: getLocale(), // the e-mail is written in the language of the page
				captcha: input.captcha,
				guest_id: getGuestId()
			}
		},
		fetcher
	);
}

export async function signIn(
	input: { username: string; password: string },
	fetcher: typeof fetch = fetch
): Promise<void> {
	await call('/api/auth/login', { body: { ...input, guest_id: getGuestId() } }, fetcher);
}

/** The page behind the link of the message: confirms the address. Resolves true when the link was good. */
export async function verifyEmail(token: string, fetcher: typeof fetch = fetch): Promise<boolean> {
	try {
		await call('/api/auth/verify', { body: { token } }, fetcher);
		return true;
	} catch (error) {
		if (error instanceof ApiError && error.status === 400) return false; // unknown, used or expired
		throw error;
	}
}

/** Ask for the message again (signed in, address not confirmed yet). */
export async function resendVerification(fetcher: typeof fetch = fetch): Promise<void> {
	await call('/api/auth/verify/resend', { body: { lang: getLocale() } }, fetcher);
}

export async function signOut(fetcher: typeof fetch = fetch): Promise<void> {
	await call('/api/auth/logout', {}, fetcher);
}

export async function deleteAccount(
	password: string,
	fetcher: typeof fetch = fetch
): Promise<void> {
	await call('/api/auth/delete', { body: { password } }, fetcher);
}
