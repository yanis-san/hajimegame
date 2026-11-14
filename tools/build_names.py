"""Build the table of proper names of the kanji game from JMnedict.

Usage (from repo root):
    uv run --project apps/server python tools/build_names.py

JMdict has few proper names (it knows 上野 only as the old province of Kōzuke), but a player who sees 野 and writes
``ueno`` means the district of Tokyo or the family name, which JMnedict has. JMnedict is the names dictionary of the
EDRDG (CC BY-SA 4.0), the same group and licence as JMdict.

Kept: place names, railway stations and family names, written with kanji that are in the kanji table (the JLPT kanji)
and at most four characters long, in any of their readings. Not kept: given names, companies, works, unclassified
names, and anything written with a kanji that is not in the table. The game accepts such a name only in the kanji
game, never in the others.

Output: ``apps/server/app/japanese/data/names.json.gz``: ``{"n": {"うえの": ["上野", ...]}}`` (reading -> written forms).
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.edrdg.org/pub/Nihongo/JMnedict.xml.gz"
DEFAULT_OUT = ROOT / "apps" / "server" / "app" / "japanese" / "data" / "names.json.gz"
KANJI_TABLE = ROOT / "apps" / "server" / "app" / "japanese" / "data" / "kanji.json.gz"
DEFAULT_CACHE = ROOT / "tools" / ".cache" / "JMnedict.xml.gz"
KEPT_TYPES = {"place name", "railway station", "family or surname"}  # the names the XML parser expands the codes to
MAX_LENGTH = 4
HAN = re.compile("[一-鿿]")


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "bakahatsu-data-builder"})
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 - fixed https URL above
        path.write_bytes(response.read())


def build(source: Path) -> dict[str, list[str]]:
    with gzip.open(KANJI_TABLE, "rt", encoding="utf-8") as fh:
        kanji = set(json.load(fh)["k"])
    names: dict[str, set[str]] = {}
    with gzip.open(source, "rb") as fh:
        for _, node in ET.iterparse(fh, events=("end",)):
            if node.tag != "entry":
                continue
            types = {(t.text or "") for t in node.iter("name_type")}
            forms = [k.findtext("keb") or "" for k in node.findall("k_ele")]
            readings = [r.findtext("reb") or "" for r in node.findall("r_ele")]
            node.clear()
            if not types & KEPT_TYPES:
                continue
            good = [
                f
                for f in forms
                if 0 < len(f) <= MAX_LENGTH
                and any(c in kanji for c in f)
                and all(c in kanji for c in f if HAN.match(c))
            ]
            for reading in readings:
                if reading and all("぀" <= c <= "ゟ" or c == "ー" for c in reading):  # hiragana only
                    for form in good:
                        names.setdefault(reading, set()).add(form)
    return {r: sorted(f) for r, f in sorted(names.items())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.source.exists():
        print(f"Downloading {URL} ...")
        download(URL, args.source)
    names = build(args.source)
    total = sum(len(f) for f in names.values())
    if total < 100_000 or "うえの" not in names or "上野" not in names["うえの"]:
        sys.exit(f"suspicious data, nothing written: {len(names)} readings, {total} pairs")
    meta = {
        "format": 1,
        "source": "JMnedict (EDRDG): place names, railway stations and family names written with the JLPT kanji.",
        "licence": "CC BY-SA 4.0, https://www.edrdg.org/edrdg/licence.html",
        "readings": len(names),
        "pairs": total,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump({"meta": meta, "n": names}, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {args.out} ({args.out.stat().st_size // 1024} KiB): {len(names)} readings, {total} pairs")


if __name__ == "__main__":
    main()
