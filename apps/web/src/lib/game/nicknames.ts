/** Silly romaji names shown as the example in the nickname field (a placeholder, never filled in for the player). */
export const NICKNAMES = [
	'Tanuki Samurai',
	'Onigiri Ninja',
	'Mochi Mochi',
	'Kappa Daisuki',
	'Neko Sensei',
	'Ramen Hakase',
	'Baka Bomber',
	'Sushi Gorilla',
	'Takoyaki Man',
	'Kawaii Bomba',
	'Daikon Taro',
	'Nori Nori',
	'Kabocha Kun',
	'Unagi Dojo',
	'Miso Shiru-chan',
	'Gyoza Panda',
	'Taiyaki Kaiju',
	'Oden Ojisan',
	'Pikapika Neko',
	'Umeboshi Boy'
] as const;

/** One of them at random; ``pick`` is a number in [0, 1) (``Math.random`` by default). */
export function randomNickname(pick: number = Math.random()): string {
	return NICKNAMES[Math.min(NICKNAMES.length - 1, Math.floor(pick * NICKNAMES.length))];
}
