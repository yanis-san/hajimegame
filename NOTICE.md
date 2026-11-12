# Third-party material

The source code of this repository is under the MIT License (see `LICENSE`). The material below is not covered by
that licence: it keeps its own, and its notices must be kept when you redistribute it.

| What | Where | Licence |
| --- | --- | --- |
| **JMdict** dictionary data (words, readings, meanings in English and French), (c) the Electronic Dictionary Research and Development Group | `apps/server/app/japanese/data/dictionary.json.gz` | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) via the [EDRDG licence](https://www.edrdg.org/edrdg/licence.html). The compiled file is an adaptation of JMdict, so it stays under CC BY-SA 4.0 (share alike) |
| **Example sentences** and their translations, from the Tatoeba project and its contributors | same file (`s` field) | [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/), source <https://tatoeba.org> |
| **Fonts**: JetBrains Mono, Shippori Mincho, Zen Kaku Gothic New, Zen Maru Gothic | installed from `@fontsource/*` | SIL Open Font License 1.1 |
| **wanakana** (romaji and kana conversion) and the other npm and Python dependencies | `pnpm-lock.yaml`, `apps/server/uv.lock` | their own licences (mostly MIT, BSD, Apache-2.0) |

How the dictionary is built, with the filters applied, is in `docs/DICTIONARY.md`. The game's credits page
(`/credits`) shows the same attributions to players.
