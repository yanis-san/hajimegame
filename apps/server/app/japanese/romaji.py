"""Server-side romaji to hiragana conversion (Hepburn plus common Nihon/Kunrei variants).

The server never trusts the client conversion: raw romaji is converted here with this table.
"""

from __future__ import annotations

_VOWELS = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}

_ROWS: dict[str, str] = {
    "k": "かきくけこ",
    "s": "さしすせそ",
    "t": "たちつてと",
    "n": "なにぬねの",
    "h": "はひふへほ",
    "m": "まみむめも",
    "r": "らりるれろ",
    "g": "がぎぐげご",
    "z": "ざじずぜぞ",
    "d": "だぢづでど",
    "b": "ばびぶべぼ",
    "p": "ぱぴぷぺぽ",
}

_TABLE: dict[str, str] = dict(_VOWELS)
for _consonant, _kana in _ROWS.items():
    for _vowel, _k in zip("aiueo", _kana, strict=True):
        _TABLE[_consonant + _vowel] = _k

_TABLE.update({"ya": "や", "yu": "ゆ", "yo": "よ", "wa": "わ", "wo": "を", "wi": "うぃ", "we": "うぇ"})

# Digraphs: consonant + y + vowel
for _c, _base in {
    "k": "き",
    "g": "ぎ",
    "s": "し",
    "z": "じ",
    "t": "ち",
    "d": "ぢ",
    "n": "に",
    "h": "ひ",
    "b": "び",
    "p": "ぴ",
    "m": "み",
    "r": "り",
}.items():
    for _v, _small in (("a", "ゃ"), ("u", "ゅ"), ("o", "ょ")):
        _TABLE[f"{_c}y{_v}"] = _base + _small
    _TABLE[f"{_c}ye"] = _base + "ぇ"

_TABLE.update(
    {
        "shi": "し",
        "sha": "しゃ",
        "shu": "しゅ",
        "sho": "しょ",
        "she": "しぇ",
        "chi": "ち",
        "cha": "ちゃ",
        "chu": "ちゅ",
        "cho": "ちょ",
        "che": "ちぇ",
        "tsu": "つ",
        "fu": "ふ",
        "fa": "ふぁ",
        "fi": "ふぃ",
        "fe": "ふぇ",
        "fo": "ふぉ",
        "ji": "じ",
        "ja": "じゃ",
        "ju": "じゅ",
        "jo": "じょ",
        "je": "じぇ",
        "ti": "てぃ",
        "tu": "とぅ",
        "di": "でぃ",
        "du": "どぅ",
        "tsa": "つぁ",
        "tsi": "つぃ",
        "tse": "つぇ",
        "tso": "つぉ",
        "wha": "うぁ",
        "va": "ゔぁ",
        "vi": "ゔぃ",
        "vu": "ゔ",
        "ve": "ゔぇ",
        "vo": "ゔぉ",
        # Kunrei / Nihon variants
        "si": "し",
        "sya": "しゃ",
        "syu": "しゅ",
        "syo": "しょ",
        "tya": "ちゃ",
        "tyu": "ちゅ",
        "tyo": "ちょ",
        "zya": "じゃ",
        "zyu": "じゅ",
        "zyo": "じょ",
        "jya": "じゃ",
        "jyu": "じゅ",
        "jyo": "じょ",
        "cya": "ちゃ",
        "cyu": "ちゅ",
        "cyo": "ちょ",
        "hu": "ふ",
        # Explicit small kana
        "xa": "ぁ",
        "xi": "ぃ",
        "xu": "ぅ",
        "xe": "ぇ",
        "xo": "ぉ",
        "la": "ぁ",
        "li": "ぃ",
        "lu": "ぅ",
        "le": "ぇ",
        "lo": "ぉ",
        "xya": "ゃ",
        "xyu": "ゅ",
        "xyo": "ょ",
        "lya": "ゃ",
        "lyu": "ゅ",
        "lyo": "ょ",
        "xtu": "っ",
        "xtsu": "っ",
        "ltu": "っ",
        "ltsu": "っ",
        "xwa": "ゎ",
    }
)
# "tu" is つ (Nihon/Kunrei, WanaKana convention), overriding the Western "tu" -> とぅ entry above.
_TABLE["tu"] = "つ"
_TABLE["du"] = "づ"

_MACRON = {"ā": "aa", "ī": "ii", "ū": "uu", "ē": "ee", "ō": "ou"}
_MAX_KEY = max(len(k) for k in _TABLE)
_CONSONANTS = set("bcdfghjklmpqrstvwxyz")  # n handled separately


def romaji_to_hiragana(text: str) -> str:
    """Convert romaji to hiragana. Unknown characters are kept as is (and will fail dictionary lookup)."""
    s = text.lower()
    for macron, expansion in _MACRON.items():
        s = s.replace(macron, expansion)
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "-":
            out.append("ー")
            i += 1
            continue
        if c == "'":
            i += 1
            continue
        if c == "n":
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt == "'":
                out.append("ん")
                i += 2
                continue
            if nxt == "n":
                after = s[i + 2] if i + 2 < n else ""
                # "nn" is a single ん unless followed by a vowel or y ("konnichiwa" keeps its own n)
                if after == "" or (after not in "aiueoy'"):
                    out.append("ん")
                    i += 2
                    continue
                out.append("ん")
                i += 1
                continue
            if nxt == "" or nxt not in "aiueoy":
                out.append("ん")
                i += 1
                continue
        # sokuon: doubled consonant, or "tch"
        if c in _CONSONANTS and i + 1 < n and (s[i + 1] == c or (c == "t" and s.startswith("tch", i))):
            out.append("っ")
            i += 1
            continue
        for size in range(min(_MAX_KEY, n - i), 0, -1):
            chunk = s[i : i + size]
            kana = _TABLE.get(chunk)
            if kana is not None:
                out.append(kana)
                i += size
                break
        else:
            out.append(c)
            i += 1
    return "".join(out)
