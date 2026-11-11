# Dictionary

Source: the full JMdict file from the EDRDG (English plus French and other glosses), licence CC BY-SA 4.0 (https://www.edrdg.org/edrdg/licence.html).
Rebuild with `make dictionary` (downloads the file, filters, writes `apps/server/app/japanese/data/dictionary.json.gz`).
The compiled file is committed so the game works right after cloning.

## Filters (documented thresholds)

- Dropped entries: every sense tagged `vulg`, `X`, `derog`, `obs`, `obsc`, `rare`, `arch`, `sl`, `joc`, `male`, `fam`, `id` or `proverb`.
- Dropped entries whose parts of speech are only prefix, suffix, counter, auxiliary, particle, copula or unclassified.
- Dropped forms: irregular, outdated or rarely used kanji/reading (`oK`, `iK`, `rK`, `sK`, `ateji`, `ik`, `ok`, `gikun`, `sk`).
- Dropped readings: single kana, anything that is not hiragana/katakana/long mark, longer than 20 characters.
- JMdict has no proper-noun entries (that is JMnedict), so none are present.
- Result: about 207 000 entries, 2.4 MB gzipped.

## No levels

The game has no JLPT or any other word level: every word of the dictionary is playable. Difficulty comes only from
the fuse (it shortens as the game goes on) and from lives. Each entry still carries a commonness rank `k` (smaller is
more common: the smallest `nfNN` band, 12 for `ichi1`, 25 for other `*1` priorities, 40 for `*2`, else 99). It is used
only to order suggestions (CPU players, test helpers), never to refuse a word.

## Fragments

Units are a kana plus its trailing small kana (ゃゅょぁぃぅぇぉゎっ). Fragments are 1 to 3 units, matched as plain
substrings that never cut a unit. A fragment is playable if at least N words (default 80) contain it. The tier
easy/medium/hard splits the playable fragments by word count into thirds; it follows how well a player is doing
(response time), not any word level.

## Meanings

Each entry keeps a short meaning in both languages (up to 3 senses, 2 glosses each, 90 characters): French (`f`) and
English (`g`). The game always shows both with FR and EN badges, and only English when JMdict has no French.
Limit: JMdict has French glosses for only about 10 500 of the 211 000 kept entries. Nothing is machine translated.
