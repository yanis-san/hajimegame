import type { Config } from 'prettier';

// `tailwindStylesheet` belongs to prettier-plugin-tailwindcss, which prettier's own Config type does not know.
const config: Config & { tailwindStylesheet: string } = {
	useTabs: true,
	singleQuote: true,
	trailingComma: 'none',
	printWidth: 100,
	plugins: ['prettier-plugin-svelte', 'prettier-plugin-tailwindcss'],
	overrides: [{ files: '*.svelte', options: { parser: 'svelte' } }],
	tailwindStylesheet: './src/routes/layout.css'
};

export default config;
