import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

/** Build a fragment -> answers table from the real dictionary so tests can play valid words. */
export default function globalSetup(): void {
	const server = path.resolve(import.meta.dirname, '../../server');
	const code = [
		'import json, sys',
		'sys.stdout.reconfigure(encoding="utf-8")',
		'from app.japanese.dictionary import Dictionary',
		'from app.japanese.kana import fragment_ngrams',
		'from app.japanese.levels import LEVEL_MAX_RANK',
		'd = Dictionary.load()',
		'out = {}',
		'for i in range(len(d)):',
		'    e = d.entry(i)',
		'    if e.rank > LEVEL_MAX_RANK["n4"]:',
		'        continue',
		'    for r in e.readings:',
		'        for g in fragment_ngrams(r):',
		'            bucket = out.setdefault(g, [])',
		'            if len(bucket) < 8:',
		'                bucket.append(r)',
		'print(json.dumps(out, ensure_ascii=False))'
	].join('\n');
	const raw = execFileSync('uv', ['run', 'python', '-c', code], {
		cwd: server,
		encoding: 'utf8',
		maxBuffer: 64 * 1024 * 1024,
		env: { ...process.env, PYTHONUTF8: '1' },
		shell: false
	});
	const dir = path.resolve(import.meta.dirname, '.cache');
	mkdirSync(dir, { recursive: true });
	writeFileSync(path.join(dir, 'answers.json'), raw);
}
