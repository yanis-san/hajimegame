"""Build the compact Hajime dictionary from JMdict.

Usage (from repo root):
    uv run --project apps/server python tools/build_dictionary.py

Downloads JMdict_e.gz from the EDRDG, filters it and writes
``apps/server/app/japanese/data/dictionary.json.gz``.
Nothing is invented: if the download fails the script stops with an error.

Licence: JMdict is (c) EDRDG, licensed CC BY-SA 4.0. The output carries the attribution in ``meta``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import jaconv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "server"))

from app.japanese.fragments import count_fragments  # noqa: E402
from app.japanese.levels import bucket_for_rank  # noqa: E402

JMDICT_URL = "https://www.edrdg.org/pub/Nihongo/JMdict.gz"  # full file: English plus other languages
FORMAT_VERSION = 3
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
MEANING_MAX = 90
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "apps" / "server" / "app" / "japanese" / "data" / "dictionary.json.gz"

# Entry/sense exclusion thresholds (documented in docs/DICTIONARY.md).
EXCLUDED_MISC = {"vulg", "X", "derog", "obs", "obsc", "rare", "arch", "sl", "joc", "male", "fam", "id", "proverb"}
EXCLUDED_POS = {"pref", "suf", "unc", "ctr", "aux", "aux-v", "aux-adj", "prt", "cop", "n-suf", "n-pref"}
EXCLUDED_KANJI_INFO = {"oK", "iK", "rK", "sK", "ateji"}
EXCLUDED_READING_INFO = {"ik", "ok", "gikun", "sk"}

# Rank: smaller is more common. nfNN covers bands of 500 words.
RANK_ICHI1 = 12  # ichi1: the Ichimango "very common" list, includes basic verbs without nf bands
RANK_COMMON_1 = 25
RANK_COMMON_2 = 40
RANK_OTHER = 99

KANA_RE = re.compile(r"^[ぁ-ゖァ-ヺー]+$")
ENTITY_RE = re.compile(r"&([A-Za-z0-9\-]+);")
STD_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
    except (urllib.error.URLError, OSError) as exc:
        sys.exit(f"Cannot download JMdict ({exc}). Place the file manually with --source. Stopping.")


def load_xml(path: Path) -> ET.Element:
    raw = gzip.open(path, "rt", encoding="utf-8").read()
    start = raw.index("<JMdict>")
    body = raw[start:]
    body = ENTITY_RE.sub(lambda m: m.group(0) if m.group(1) in STD_ENTITIES else f"@{m.group(1)}@", body)
    return ET.fromstring(body)


def rank_from_priorities(tags: list[str]) -> int:
    best = RANK_OTHER
    for tag in tags:
        m = re.fullmatch(r"nf(\d\d)", tag)
        if m:
            best = min(best, int(m.group(1)))
        elif tag == "ichi1":
            best = min(best, RANK_ICHI1)
        elif tag in {"news1", "spec1", "gai1"}:
            best = min(best, RANK_COMMON_1)
        elif tag in {"news2", "ichi2", "spec2", "gai2"}:
            best = min(best, RANK_COMMON_2)
    return best


def clean_tag(text: str | None) -> str:
    return (text or "").strip("@")


def build_meaning(senses: list[ET.Element]) -> tuple[str, str]:
    """Short meanings for an entry: (French, English). Either may be empty; JMdict has little French."""
    best: dict[str, list[str]] = {"fre": [], "eng": []}
    for sense in senses[:4]:
        misc = {clean_tag(m.text) for m in sense.findall("misc")}
        if misc & EXCLUDED_MISC:
            continue
        for lang in best:
            glosses = [
                (g.text or "").strip()
                for g in sense.findall("gloss")
                if g.get(XML_LANG, "eng") == lang and (g.text or "").strip()
            ]
            if glosses:
                best[lang].append(", ".join(glosses[:2]))
    out = []
    for lang in ("fre", "eng"):
        text = "; ".join(best[lang][:3])
        if len(text) > MEANING_MAX:
            text = text[: MEANING_MAX - 1].rstrip(" ,;") + "…"
        out.append(text)
    return out[0], out[1]


def convert(root: ET.Element) -> tuple[list[dict[str, object]], Counter[str]]:
    stats: Counter[str] = Counter()
    entries: list[dict[str, object]] = []
    for entry in root.iter("entry"):
        stats["total"] += 1
        senses = entry.findall("sense")
        usable = []
        for sense in senses:
            pos = {clean_tag(p.text) for p in sense.findall("pos")}
            misc = {clean_tag(m.text) for m in sense.findall("misc")}
            if misc & EXCLUDED_MISC:
                continue
            usable.append(pos)
        if not usable:
            stats["drop_sense_tags"] += 1
            continue
        all_pos = set().union(*usable)
        if all_pos and all_pos <= EXCLUDED_POS:
            stats["drop_pos"] += 1
            continue

        priorities: list[str] = []
        forms: list[str] = []
        for k in entry.findall("k_ele"):
            info = {clean_tag(i.text) for i in k.findall("ke_inf")}
            if info & EXCLUDED_KANJI_INFO:
                continue
            keb = (k.findtext("keb") or "").strip()
            if keb:
                forms.append(keb)
                priorities += [p.text or "" for p in k.findall("ke_pri")]
        readings: list[str] = []
        for r in entry.findall("r_ele"):
            info = {clean_tag(i.text) for i in r.findall("re_inf")}
            if info & EXCLUDED_READING_INFO:
                continue
            reb = (r.findtext("reb") or "").strip()
            if not KANA_RE.match(reb):
                continue
            hira = jaconv.kata2hira(reb)
            if len(hira) < 2:
                continue
            if hira not in readings:
                readings.append(hira)
            priorities += [p.text or "" for p in r.findall("re_pri")]
        if not readings:
            stats["drop_reading"] += 1
            continue
        if any(len(r) > 20 for r in readings):
            readings = [r for r in readings if len(r) <= 20]
            if not readings:
                stats["drop_long"] += 1
                continue
        forms = [f for f in dict.fromkeys(forms) if len(f) <= 20]
        meaning = build_meaning(senses)
        stats["meaning_fr"] += 1 if meaning[0] else 0
        stats["meaning_en"] += 1 if meaning[1] else 0
        entries.append(
            {
                "w": forms,
                "r": readings,
                "k": rank_from_priorities(priorities),
                "p": sorted(all_pos - EXCLUDED_POS - {""})[:3],
                "f": meaning[0],
                "g": meaning[1],
            }
        )
        stats["kept"] += 1
    return entries, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="local JMdict_e.gz (skips download)")
    parser.add_argument("--cache", type=Path, default=ROOT / "tools" / ".cache" / "JMdict.gz")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    source = args.source or args.cache
    if args.source is None and not source.exists():
        print(f"Downloading {JMDICT_URL} ...")
        download(JMDICT_URL, source)
    print("Parsing ...")
    entries, stats = convert(load_xml(source))
    entries.sort(key=lambda e: (e["k"], e["r"]))  # type: ignore[arg-type, return-value]

    ranks = Counter(int(e["k"]) for e in entries)  # type: ignore[call-overload]
    meta = {
        "format": FORMAT_VERSION,
        "source": "JMdict (EDRDG), French and English glosses",
        "licence": "CC BY-SA 4.0, https://www.edrdg.org/edrdg/licence.html",
        "attribution": "This dictionary uses the JMdict file, (c) the Electronic Dictionary Research and "
        "Development Group, used in conformance with the Group's licence.",
        "entries": len(entries),
        "rank_note": "k: smaller is more common (nfNN band, 12 = ichi1, 25 = other *1 priority, 40 = *2 priority, 99 = other)",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fragments = count_fragments((bucket_for_rank(int(e["k"])), e["r"]) for e in entries)  # type: ignore[arg-type, misc]
    meta["fragments"] = len(fragments)
    payload = json.dumps({"meta": meta, "entries": entries, "fragments": fragments}, ensure_ascii=False, separators=(",", ":"))
    with gzip.GzipFile(args.out, "wb", mtime=0) as fh:
        fh.write(payload.encode("utf-8"))

    print(f"Wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KiB gz, {len(payload) / 1e6:.1f} MB raw)")
    for key, value in sorted(stats.items()):
        print(f"  {key}: {value}")
    print(f"  fragments stored: {len(fragments)}")
    print(f"  rank<=6: {sum(v for k, v in ranks.items() if k <= 6)}")
    print(f"  rank<=12: {sum(v for k, v in ranks.items() if k <= 12)}")
    print(f"  rank<=24: {sum(v for k, v in ranks.items() if k <= 24)}")
    print(f"  rank<=40: {sum(v for k, v in ranks.items() if k <= 40)}")
    print(f"  rank 99 (other): {ranks[RANK_OTHER]}")


if __name__ == "__main__":
    main()
