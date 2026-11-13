"""Build the kanji table of the kanji game from KANJIDIC2 and the JLPT lists of Jonathan Waller.

Usage (from repo root):
    uv run --project apps/server python tools/build_kanji.py

Sources, nothing invented, the script stops with an error when a download fails:
  * KANJIDIC2 (EDRDG, CC BY-SA 4.0): the readings (on and kun) and the meanings of every kanji.
  * The JLPT levels N5 to N1: the JLPT has published no official kanji lists since 2010. The lists of Jonathan Waller
    (https://www.tanos.co.uk/jlpt/, CC BY) are the ones everybody uses; they are read here from the open data set
    ``davidluzgouveia/kanji-data`` (MIT), which extracted them with scripts (field ``jlpt_new``). The levels are
    therefore indicative, and the game says so.

Output: ``apps/server/app/japanese/data/kanji.json.gz``, one entry per kanji that has a level:
``{"k": {"土": [5, ["ど", "と"], ["つち"], "soil; earth", "terre; sol"]}}`` (level, on readings, kun readings
without their okurigana, English and French meanings).
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import jaconv

ROOT = Path(__file__).resolve().parent.parent
KANJIDIC_URL = "https://www.edrdg.org/kanjidic/kanjidic2.xml.gz"
LEVELS_URL = "https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji.json"
DEFAULT_OUT = ROOT / "apps" / "server" / "app" / "japanese" / "data" / "kanji.json.gz"
DEFAULT_CACHE = ROOT / "tools" / ".cache"


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "bakahatsu-data-builder"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - fixed https URLs above
        path.write_bytes(response.read())


def kun_stem(reading: str) -> str:
    """``た.べる`` -> ``た``, ``-ゆ.き`` -> ``ゆ``, ``うま.れる`` -> ``うま``: the part that is the kanji itself.

    The okurigana is written in kana after the kanji, it is not part of the reading of the kanji. A reading that
    starts or ends with a dash is a prefix or a suffix form: the dash goes, the kana stays.
    """
    return reading.split(".", 1)[0].strip("-").strip()


def build(kanjidic: Path, levels: Path) -> dict[str, list[object]]:
    new_levels: dict[str, int] = {
        k: int(v["jlpt_new"]) for k, v in json.loads(levels.read_text(encoding="utf-8")).items() if v.get("jlpt_new")
    }
    table: dict[str, list[object]] = {}
    with gzip.open(kanjidic, "rb") as fh:
        for _, node in ET.iterparse(fh, events=("end",)):
            if node.tag != "character":
                continue
            literal = (node.findtext("literal") or "").strip()
            level = new_levels.get(literal)
            if level:
                on: list[str] = []
                kun: list[str] = []
                en: list[str] = []
                fr: list[str] = []
                for reading in node.iter("reading"):
                    kind = reading.get("r_type")
                    text = (reading.text or "").strip()
                    if kind == "ja_on":
                        hira = jaconv.kata2hira(text)
                        if hira and hira not in on:
                            on.append(hira)
                    elif kind == "ja_kun":
                        stem = kun_stem(text)
                        if stem and stem not in kun:
                            kun.append(stem)
                for meaning in node.iter("meaning"):
                    lang = meaning.get("m_lang") or "en"
                    text = (meaning.text or "").strip()
                    if lang == "en" and text and len(en) < 3:
                        en.append(text)
                    elif lang == "fr" and text and len(fr) < 3:
                        fr.append(text)
                table[literal] = [level, on, kun, "; ".join(en), "; ".join(fr)]
            node.clear()
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    kanjidic = args.cache / "kanjidic2.xml.gz"
    levels = args.cache / "kanji-levels.json"
    for url, path in ((KANJIDIC_URL, kanjidic), (LEVELS_URL, levels)):
        if not path.exists():
            print(f"Downloading {url} ...")
            download(url, path)
    table = build(kanjidic, levels)
    counts = {n: sum(1 for v in table.values() if v[0] == n) for n in (5, 4, 3, 2, 1)}
    if sum(counts.values()) < 2000 or any(c == 0 for c in counts.values()):
        sys.exit(f"suspicious data, nothing written: {counts}")
    meta = {
        "format": 1,
        "kanjidic": "This table uses the KANJIDIC2 file, (c) the Electronic Dictionary Research and Development Group, "
        "used in conformance with the Group's licence (CC BY-SA 4.0).",
        "levels": "JLPT levels N5-N1 (indicative): Jonathan Waller's lists, https://www.tanos.co.uk/jlpt/ (CC BY), "
        "read from the data set github.com/davidluzgouveia/kanji-data (MIT).",
        "counts": {f"N{n}": c for n, c in counts.items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump({"meta": meta, "k": table}, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {args.out} ({args.out.stat().st_size // 1024} KiB): {meta['counts']}")


if __name__ == "__main__":
    main()
