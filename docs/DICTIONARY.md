# Dictionary and difficulty levels

Source: JMdict_e from the EDRDG, licence CC BY-SA 4.0 (https://www.edrdg.org/edrdg/licence.html).
Rebuild with `make dictionary` (downloads the file, filters, writes `apps/server/app/japanese/data/dictionary.json.gz`).
The compiled file is committed so the game works right after cloning.

## Filters (documented thresholds)

- Dropped entries: every sense tagged `vulg`, `X`, `derog`, `obs`, `obsc`, `rare`, `arch`, `sl`, `joc`, `male`, `fam`, `id` or `proverb`.
- Dropped entries whose parts of speech are only prefix, suffix, counter, auxiliary, particle, copula or unclassified.
- Dropped forms: irregular, outdated or rarely used kanji/reading (`oK`, `iK`, `rK`, `sK`, `ateji`, `ik`, `ok`, `gikun`, `sk`).
- Dropped readings: single kana, anything that is not hiragana/katakana/long mark, longer than 20 characters.
- JMdict has no proper-noun entries (that is JMnedict), so none are present.
- Result: about 207 000 entries, 2.4 MB gzipped.

## Levels

The JLPT stopped publishing official lists, so levels are derived from JMdict frequency data. Each entry has a rank
(smaller is more common): the smallest `nfNN` band (500 words each), 12 for `ichi1`, 25 for other `*1` priorities
(`news1`, `spec1`, `gai1`), 40 for `*2`, else 99.

| Level | Accepts rank up to | Approx. words |
| --- | --- | --- |
| n5 | 6 | 3 000 |
| n4 | 12 | 11 700 |
| n3 | 24 | 15 600 |
| n2 | 40 | 29 800 |
| n1 | 99 | all |

Limit: this is a frequency proxy, not the real JLPT syllabus. To use a community JLPT list instead, change
`LEVEL_MAX_RANK` or the `k` field in `tools/build_dictionary.py`; nothing else depends on the source.

## Fragments

Units are a kana plus its trailing small kana (ゃゅょぁぃぅぇぉゎっ). Fragments are 1 to 3 units, matched as plain
substrings that never cut a unit. A fragment is playable for a level if at least N words (default 80) contain it;
small levels halve N until 30 fragments exist (the effective N is reported by `FragmentTable.min_words`).
Tier easy/medium/hard splits playable fragments by word count into thirds.
