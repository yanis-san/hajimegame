import type { RequestHandler } from './$types';

/** Liveness probe for the web container (the game server has its own /healthz and /readyz). */
export const GET: RequestHandler = () =>
	new Response('ok', { headers: { 'content-type': 'text/plain', 'cache-control': 'no-store' } });
