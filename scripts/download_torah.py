#!/usr/bin/env python3
"""Download a fixed edition from the static Sefaria dump and build a local Torah corpus.

This utility uses static JSON files from the export bucket and does not call API
endpoints. Subsequent analysis runs entirely offline.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.corpus import normalize


SOURCE_DIR = ROOT / "data" / "source" / "sefaria"
DATA_DIR = ROOT / "data"
VERSION = "Tanach with Text Only"
EXPECTED_LICENSE = "Public Domain"
BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
CHAPTERS = {"Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34}
VERSES = {"Genesis": 1533, "Exodus": 1210, "Leviticus": 859, "Numbers": 1288, "Deuteronomy": 956}
BASE_URL = "https://storage.googleapis.com/sefaria-export/json/Tanakh/Torah"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flatten(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item)


def download_book(book: str) -> tuple[bytes, dict, list[str]]:
    encoded_version = "Tanach%20with%20Text%20Only"
    url = f"{BASE_URL}/{book}/Hebrew/{encoded_version}.json"
    request = urllib.request.Request(url, headers={"User-Agent": "BibleCode-local-corpus/1.0"})
    print(f"Downloading {book}: requesting static file from the Sefaria dump")
    with urllib.request.urlopen(request, timeout=60) as response:
        expected_size = int(response.headers.get("Content-Length", "0") or 0)
        chunks = []
        received = 0
        while True:
            chunk = response.read(32768)
            if not chunk:
                break
            chunks.append(chunk)
            received += len(chunk)
            suffix = f"/{expected_size:,} bytes" if expected_size else " bytes"
            prefix = f"\r  Transferido: {received:,}{suffix}"
            print(prefix, end="", flush=True)
        if chunks:
            print()
        raw = b"".join(chunks)
    payload = json.loads(raw.decode("utf-8-sig"))
    if payload.get("title") != book:
        raise ValueError(f"Unexpected title for {book}: {payload.get('title')!r}")
    if payload.get("versionTitle") != VERSION:
        raise ValueError(f"Unexpected edition for {book}: {payload.get('versionTitle')!r}")
    if payload.get("language") != "he":
        raise ValueError(f"Unexpected language for {book}: {payload.get('language')!r}")
    if payload.get("license") != EXPECTED_LICENSE:
        raise ValueError(f"License for {book} is not {EXPECTED_LICENSE!r}: {payload.get('license')!r}")
    chapters = payload.get("text")
    if not isinstance(chapters, list) or len(chapters) != CHAPTERS[book]:
        got = len(chapters) if isinstance(chapters, list) else type(chapters).__name__
        raise ValueError(f"Invalid chapter count for {book}: {got}; expected {CHAPTERS[book]}")
    verses = list(flatten(chapters))
    if len(verses) != VERSES[book]:
        raise ValueError(f"Verse count changed for {book}: {len(verses)}; expected {VERSES[book]} for this export")
    if not verses or any(not verse.strip() for verse in verses):
        raise ValueError(f"Missing or empty verses in {book}")
    return raw, payload, verses


def main() -> int:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_verses: list[str] = []
    sources = []
    for book in BOOKS:
        raw, payload, verses = download_book(book)
        filename = f"{book}_Hebrew_Tanach_with_Text_Only.json"
        target = SOURCE_DIR / filename
        temp = target.with_suffix(target.suffix + ".part")
        temp.write_bytes(raw)
        temp.replace(target)
        url = f"{BASE_URL}/{book}/Hebrew/Tanach%20with%20Text%20Only.json"
        sources.append({
            "book": book,
            "file": str(target.relative_to(ROOT)),
            "url": url,
            "sha256": sha256(raw),
            "version_title": payload["versionTitle"],
            "version_source": payload.get("versionSource"),
            "language": payload["language"],
            "license": payload["license"],
            "chapter_count": len(payload["text"]),
            "verse_count": len(verses),
        })
        all_verses.extend(verses)
        print(f"Downloaded and validated: {book} ({len(verses)} verses)")

    raw_text = "\n".join(all_verses) + "\n"
    normalized = normalize(raw_text, "hebrew", map_final_forms=False)
    merged_finals = normalize(raw_text, "hebrew", map_final_forms=True)
    if len(normalized) < 300_000:
        raise ValueError(f"Normalized corpus is suspiciously short: {len(normalized):,} letters")

    raw_path = DATA_DIR / "torah_hebrew.txt"
    clean_path = DATA_DIR / "torah_els.txt"
    merged_path = DATA_DIR / "torah_els_merged_finals.txt"
    raw_bytes = raw_text.encode("utf-8")
    clean_bytes = (normalized + "\n").encode("utf-8")
    merged_bytes = (merged_finals + "\n").encode("utf-8")
    raw_path.write_bytes(raw_bytes)
    clean_path.write_bytes(clean_bytes)
    merged_path.write_bytes(merged_bytes)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_collection": "Sefaria-Export static JSON files in Google Cloud Storage; no API endpoint used",
        "source_index": "https://github.com/Sefaria/Sefaria-Export",
        "version_title": VERSION,
        "version_source": sources[0]["version_source"],
        "language": "Hebrew",
        "license": EXPECTED_LICENSE,
        "books_canonical_order": BOOKS,
        "normalization": "NFD; remove Unicode combining marks; keep Hebrew letters Alef-Tav including final forms; remove all other characters",
        "verse_separator_in_raw_file": "newline",
        "raw_text_file": str(raw_path.relative_to(ROOT)),
        "raw_text_sha256": sha256(raw_bytes),
        "els_text_file": str(clean_path.relative_to(ROOT)),
        "els_text_sha256": sha256(clean_bytes),
        "normalized_letter_count": len(normalized),
        "distinct_symbols": len(set(normalized)),
        "merged_final_forms_alternative": {
            "file": str(merged_path.relative_to(ROOT)),
            "sha256": sha256(merged_bytes),
            "letter_count": len(merged_finals),
            "normalization": "same as primary corpus, then map ךםןףץ to כמנפצ",
        },
        "chapter_count": sum(item["chapter_count"] for item in sources),
        "verse_count": sum(item["verse_count"] for item in sources),
        "source_files": sources,
    }
    manifest_path = DATA_DIR / "torah_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Torah corpus ready: {manifest['normalized_letter_count']:,} letters, {manifest['verse_count']:,} verses")
    print(f"Offline analysis corpus: {clean_path}")
    print(f"Edition, license, and hash manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
