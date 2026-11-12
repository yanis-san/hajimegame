// Cross-platform task runner (works on Windows without make): `pnpm dev`, `pnpm test`, ...
// Plain TypeScript run by Node itself (type stripping, Node 24+): there is nothing to compile.
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SERVER = path.join(ROOT, 'apps', 'server');
const WEB = path.join(ROOT, 'apps', 'web');

/** A command to run: program, arguments, working directory, extra environment. */
type Step = [cmd: string, args: string[], cwd?: string, env?: Record<string, string>];

/** Run a command to completion; returns its exit code. */
function run(...[cmd, args, cwd = ROOT, env = {}]: Step): number {
	console.log(`\n> ${cmd} ${args.join(' ')}   (${path.relative(ROOT, cwd) || '.'})`);
	const result = spawnSync(cmd, args, {
		cwd,
		stdio: 'inherit',
		shell: process.platform === 'win32',
		env: { ...process.env, PYTHONUTF8: '1', ...env }
	});
	return result.status ?? 1;
}

/** Run every step (even after a failure, to show all problems at once), then exit with the overall result. */
function all(steps: Step[]): never {
	let failed = 0;
	for (const step of steps) failed += run(...step) === 0 ? 0 : 1;
	process.exit(failed ? 1 : 0);
}

const tasks: Record<string, () => void> = {
	bootstrap() {
		all([
			['uv', ['sync'], SERVER],
			['pnpm', ['install'], ROOT],
			['pnpm', ['exec', 'playwright', 'install', 'chromium'], WEB]
		]);
	},

	dev() {
		const env = { ...process.env, PYTHONUTF8: '1', HAJIME_MAX_ROOMS_PER_IP: '200' };
		const shell = process.platform === 'win32';
		const server = spawn(
			'uv',
			['run', 'uvicorn', 'app.main:create_app', '--factory', '--port', '8000', '--reload'],
			{ cwd: SERVER, stdio: 'inherit', shell, env }
		);
		const web = spawn('pnpm', ['exec', 'vite', 'dev', '--port', '5173'], {
			cwd: WEB,
			stdio: 'inherit',
			shell,
			env
		});
		console.log('\n  Game server : http://localhost:8000  (docs: /docs)');
		console.log('  Web app     : http://localhost:5173\n');
		const stop = (): void => {
			for (const child of [server, web]) {
				if (process.platform === 'win32' && child.pid) {
					spawnSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { stdio: 'ignore' });
				} else child.kill('SIGTERM');
			}
			process.exit(0);
		};
		process.on('SIGINT', stop);
		process.on('SIGTERM', stop);
		server.on('exit', stop);
		web.on('exit', stop);
	},

	test() {
		all([
			['uv', ['run', 'pytest', '--cov=app'], SERVER],
			['pnpm', ['exec', 'vitest', 'run', '--project', 'server'], WEB]
		]);
	},

	lint() {
		all([
			['uv', ['run', 'ruff', 'check', '.'], SERVER],
			['uv', ['run', 'ruff', 'format', '--check', '.'], SERVER],
			['uv', ['run', 'mypy', '.'], SERVER],
			['uv', ['run', '--project', 'apps/server', 'python', 'tools/gen_protocol.py', '--check'], ROOT],
			['pnpm', ['exec', 'prettier', '--check', '.'], WEB],
			['pnpm', ['exec', 'eslint', '.'], WEB]
		]);
	},

	typecheck() {
		all([
			['uv', ['run', 'mypy', '.'], SERVER],
			['pnpm', ['exec', 'svelte-check', '--tsconfig', './tsconfig.json'], WEB]
		]);
	},

	build() {
		all([['pnpm', ['exec', 'vite', 'build'], WEB]]);
	},

	e2e() {
		all([['pnpm', ['exec', 'playwright', 'test'], WEB]]);
	},

	protocol() {
		all([['uv', ['run', '--project', 'apps/server', 'python', 'tools/gen_protocol.py'], ROOT]]);
	},

	dictionary() {
		all([['uv', ['run', '--project', 'apps/server', 'python', 'tools/build_dictionary.py'], ROOT]]);
	},

	load() {
		all([['uv', ['run', '--project', 'apps/server', 'python', 'tools/loadtest.py'], ROOT]]);
	}
};

const name = process.argv[2];
if (!name || !(name in tasks)) {
	console.log(`Usage: node tools/tasks.ts <${Object.keys(tasks).join('|')}>`);
	process.exit(name ? 1 : 0);
}
tasks[name]();
