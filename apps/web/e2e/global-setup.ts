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
		'd = Dictionary.load()',
		'out = {}',
		'starts = {}',
		'nends = {}',
		'for i in range(len(d)):',
		'    e = d.entry(i)',
		'    for r in e.readings:',
		'        for g in fragment_ngrams(r):',
		'            bucket = out.setdefault(g, [])',
		'            if len(bucket) < 8:',
		'                bucket.append(r)',
		'        if r[-1] not in "ゃゅょぁぃぅぇぉゎっーん" and len(r) >= 3:',
		'            st = starts.setdefault(r[0], [])',
		'            if len(st) < 8:',
		'                st.append(r)',
		'        if r[-1] == "ん" and len(r) >= 3:',
		'            ne = nends.setdefault(r[0], [])',
		'            if len(ne) < 8:',
		'                ne.append(r)',
		'print(json.dumps({"contains": out, "starts": starts, "nends": nends}, ensure_ascii=False))'
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
