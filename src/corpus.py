"""Read, normalize, and track provenance for text corpora."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any


FINAL_FORMS = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})


def normalize(text: str, alphabet: str = "hebrew", map_final_forms: bool = False) -> str:
    """Remove combining marks and retain letters from the selected alphabet.

    Hebrew: retain Alef through Tav; preserve final forms by default.
    Latin: convert to uppercase and retain A-Z.
    """
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    if alphabet == "hebrew":
        if map_final_forms:
            text = text.translate(FINAL_FORMS)
        return "".join(ch for ch in text if "א" <= ch <= "ת")
    if alphabet == "latin":
        text = text.upper()
        return "".join(ch for ch in text if "A" <= ch <= "Z")
    raise ValueError("alphabet must be 'hebrew' or 'latin'")


def _flatten_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)


def load_corpus(path: Path, alphabet: str, raw_json: bool = False, version_title: str | None = None, map_final_forms: bool = False) -> tuple[str, dict[str, Any]]:
    """Load plain text or a Sefaria JSON response and return corpus plus manifest."""
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    decoded = raw.decode("utf-8-sig")
    selected_version = None
    if raw_json:
        payload = json.loads(decoded)
        versions = payload.get("versions") if isinstance(payload, dict) else None
        if isinstance(versions, list):
            candidates = [v for v in versions if v.get("versionTitle") == version_title] if version_title else versions
            if len(candidates) != 1:
                raise ValueError("Sefaria v3 JSON requires one version; if several exist, provide the exact --version-title")
            selected_version = candidates[0]
            decoded = " ".join(_flatten_strings(selected_version.get("text", [])))
            if not decoded:
                raise ValueError("The selected version contains no text")
        else:
            if version_title:
                raise ValueError("--version-title requires Sefaria v3 JSON with a versions field")
            selected_version = payload
            fields = ("he",) if alphabet == "hebrew" else ("text",) if "text" in payload else ("en",)
            pieces = list(_flatten_strings(payload.get(fields[0], [])))
            if not pieces:
                raise ValueError(f"JSON has no recognized text fields: {fields}")
            decoded = " ".join(pieces)
    corpus = normalize(decoded, alphabet=alphabet, map_final_forms=map_final_forms)
    manifest = {
        "source_file": str(path),
        "source_sha256": digest,
        "alphabet": alphabet,
        "normalization": ("NFD; remove combining marks; retain Alef-Tav; preserve final forms" + (" (mapped to common forms)" if map_final_forms else "")) if alphabet == "hebrew" else "NFD; remove combining marks; uppercase A-Z",
        "raw_bytes": len(raw),
        "normalized_length": len(corpus),
        "alphabet_symbols": len(set(corpus)),
    }
    if selected_version is not None:
        manifest["version_title"] = selected_version.get("versionTitle")
        manifest["version_source"] = selected_version.get("versionSource")
        manifest["license"] = selected_version.get("license")
    return corpus, manifest


def load_targets(path: Path, alphabet: str, map_final_forms: bool = False) -> list[dict[str, Any]]:
    """Read JSON as [{group, terms:[{label,word}]}] or {group:[words]}."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    groups = []
    if isinstance(payload, dict):
        for group, words in payload.items():
            terms = [{"label": str(word), "word": str(word)} for word in words]
            groups.append({"group": group, "terms": terms})
    elif isinstance(payload, list):
        groups = payload
    else:
        raise ValueError("targets must be a JSON object or list")
    result = []
    for group in groups:
        group_name = str(group.get("group", "sem grupo"))
        for term in group.get("terms", []):
            word = normalize(str(term["word"]), alphabet=alphabet, map_final_forms=map_final_forms)
            if not word:
                raise ValueError(f"Target is empty after normalization: {term}")
            result.append({"group": group_name, "label": str(term.get("label", term["word"])), "word": word, "original": str(term["word"])})
    return result
