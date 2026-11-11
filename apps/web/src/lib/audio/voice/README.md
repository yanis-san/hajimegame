# Voice recordings

Drop your own recordings in this folder. Each file is picked up automatically at build time (`.mp3`, `.ogg`, `.wav`, `.m4a` or `.webm`). A cue with no file is simply silent, so you can add them one by one.

| File name                  | When it plays                                                   | What to say (suggestion)               |
| -------------------------- | --------------------------------------------------------------- | -------------------------------------- |
| `hajime`                   | the game starts                                                 | 「はじめ！」 (hajime!), loud and short |
| `san`, `ni`, `ichi`        | the 3-2-1 countdown                                             | 「さん」「に」「いち」                 |
| `nice1`, `nice2`, `nice3`… | you found a word (at most every 6 s, one file picked at random) | 「よし！」「いいね！」「すごい！」     |
| `boom`                     | the bomb explodes on you                                        | 「あっ！」 or 「ばくはつ！」           |
| `shouri`                   | you win                                                         | 「しょうり！」 or 「やったー！」       |
| `zannen`                   | you lose                                                        | 「ざんねん…」                          |

Tips:

- Record in a quiet room and trim the silence at the start: the cue should begin at once.
- Keep each file under 2 seconds and normalise the volume so all files are about as loud.
- Several files for one cue (`nice1`, `nice2`, …) are played at random, never the same twice in a row.
- Restart `pnpm dev` after adding a file so the new recording is picked up.
