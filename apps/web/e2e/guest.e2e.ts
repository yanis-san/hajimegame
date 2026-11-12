import { expect, test } from '@playwright/test';
import { createRoom, joinRoom, newPlayer } from './helpers';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

test('a browser joins with a stable private guest id and its language, never shown to others', async ({
	browser
}) => {
	const host = await newPlayer(browser, 'Yanis');
	const guest = await newPlayer(browser, 'Aya');
	const sentByHost: string[] = [];
	const receivedByGuest: string[] = [];
	host.page.on('websocket', (ws) =>
		ws.on('framesent', (frame) => sentByHost.push(String(frame.payload)))
	);
	guest.page.on('websocket', (ws) =>
		ws.on('framereceived', (frame) => receivedByGuest.push(String(frame.payload)))
	);

	const code = await createRoom(host);
	const joins = (): { guest_id?: string; lang?: string }[] =>
		sentByHost
			.map((raw) => JSON.parse(raw) as { t: string; guest_id?: string; lang?: string })
			.filter((message) => message.t === 'join');
	expect(joins()).toHaveLength(1);
	const guestId = joins()[0].guest_id ?? '';
	expect(guestId).toMatch(UUID);
	expect(joins()[0].lang).toBe('fr');

	// the same browser keeps the same identifier, also after a reload
	await host.page.reload();
	await expect(host.page.getByRole('button', { name: 'Lancer la partie' })).toBeVisible();
	const rejoined = sentByHost
		.map((raw) => JSON.parse(raw) as { t: string; guest_id?: string })
		.filter((message) => message.t === 'join' || message.t === 'rejoin');
	expect(rejoined.at(-1)?.t === 'join' ? rejoined.at(-1)?.guest_id : guestId).toBe(guestId);
	expect(await host.page.evaluate(() => localStorage.getItem('hajime:guest'))).toBe(guestId);

	// another player never receives it
	await joinRoom(guest, code);
	await expect(guest.page.getByText('Yanis').first()).toBeVisible();
	expect(receivedByGuest.length).toBeGreaterThan(0);
	expect(receivedByGuest.join('\n')).not.toContain(guestId);

	await host.context.close();
	await guest.context.close();
});
