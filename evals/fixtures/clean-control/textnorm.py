#!/usr/bin/env python3
"""Unicode text normalisation for search indexing.

Folds case, strips diacritics, and collapses whitespace so that user queries match
indexed content regardless of how either side was typed. Pure functions, no I/O,
no network, no filesystem access.
"""
from __future__ import annotations

import re
import unicodedata

# Arabic combining marks (harakat) and the tatweel elongation character. These carry no
# lexical meaning for search, and users type them inconsistently.
_ARABIC_MARKS = re.compile(r"[ً-ٰٟـ]")
_WHITESPACE = re.compile(r"\s+")


def strip_diacritics(text: str) -> str:
    """Remove combining marks while preserving base characters.

    NFD splits precomposed characters into base + combining mark, so filtering category
    Mn removes the accent and leaves the letter: "café" -> "cafe".
    """
    decomposed = unicodedata.normalize("NFD", text)
    without = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", without)


def normalize_arabic(text: str) -> str:
    """Fold Arabic orthographic variants that users type interchangeably."""
    text = _ARABIC_MARKS.sub("", text)
    for variants, canonical in (("أإآ", "ا"),  # hamza forms -> alef
                                ("ى", "ي"),              # alef maqsura -> yeh
                                ("ة", "ه")):             # teh marbuta -> heh
        for ch in variants:
            text = text.replace(ch, canonical)
    return text


def normalize(text: str, *, arabic: bool = True) -> str:
    """Full normalisation pipeline. Returns '' for empty or whitespace-only input."""
    if not text or not text.strip():
        return ""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = strip_diacritics(text)
    if arabic:
        text = normalize_arabic(text)
    return _WHITESPACE.sub(" ", text).strip()


def tokenize(text: str, *, min_length: int = 2) -> list[str]:
    """Split normalised text into tokens, dropping fragments below min_length."""
    if min_length < 1:
        raise ValueError(f"min_length must be >= 1, got {min_length}")
    return [t for t in normalize(text).split(" ") if len(t) >= min_length]
