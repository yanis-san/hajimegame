import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import { deleteAccount, fetchAccount, signIn, signUp } from './auth';

const GUEST = '11111111-2222-4333-8444-555555555555';

const reply = (status: number, body: unknown): typeof fetch =>
	vi.fn(async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

describe('account client', () => {
	beforeEach(() =>
		vi.stubGlobal('localStorage', { getItem: () => GUEST, setItem: () => undefined })
	);
	afterEach(() => vi.unstubAllGlobals());

	it('sends the browser identifier with sign-up so past games follow the account', async () => {
		const fetcher = reply(201, { username: 'Aya', email: 'a@b.fr', email_verified: false });
		await signUp(
			{
				username: 'Aya',
				password: 'longenough',
				email: ' a@b.fr ',
				birthDate: '1995-06-15',
				captcha: 'tok'
			},
			fetcher
		);
		const [url, init] = (fetcher as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
			string,
			RequestInit
		];
		expect(url).toBe('/api/auth/register');
		expect(JSON.parse(init.body as string)).toEqual({
			username: 'Aya',
			password: 'longenough',
			email: 'a@b.fr', // trimmed
			birth_date: '1995-06-15',
			captcha: 'tok',
			guest_id: GUEST
		});
		expect((init.headers as Record<string, string>)['X-Hajime-Client']).toBe('web');
	});

	it('sends it with sign-in too, so a second device brings its games along', async () => {
		const fetcher = reply(200, { username: 'Aya' });
		await signIn({ username: 'Aya', password: 'longenough' }, fetcher);
		const init = (fetcher as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit;
		expect(JSON.parse(init.body as string).guest_id).toBe(GUEST);
	});

	it('turns the server code into an ApiError', async () => {
		const error = await signIn(
			{ username: 'Aya', password: 'x' },
			reply(401, { detail: 'bad_credentials' })
		).catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		expect(error).toMatchObject({ status: 401, detail: 'bad_credentials' });
	});

	it('falls back to a generic code when the answer is not the expected shape', async () => {
		const error = await deleteAccount('pw', reply(500, { detail: [{ loc: ['x'] }] })).catch(
			(e: unknown) => e
		);
		expect(error).toMatchObject({ status: 500, detail: 'error' });
	});

	it('reads who is signed in', async () => {
		const user = { username: 'Aya', email: null, email_verified: false };
		expect(await fetchAccount(reply(200, { user }))).toEqual(user);
		expect(await fetchAccount(reply(200, { user: null }))).toBeNull();
	});
});
