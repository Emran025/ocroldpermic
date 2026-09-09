#!/usr/bin/env python3
"""Generate the 32 archival manuscript images locally.

Run from the repository root:
    python scripts/generate_archival_documents_local.py

DOCUMENT_##_LINES below contain corpus-derived Old Komi text transliterated into
Old Permic using the alphabet documented by the corpus. This is a linguistic
reconstruction for rendering, not a historical facsimile. Each document contains exactly 14 non-empty lines. The script writes PNG, YOLO
TXT, metadata JSON, and a contact sheet to the local output directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


# ── Editable text: one block per output image ─────────────────────────────────
# Source: https://github.com/langdoc/written-komi-corpus-old-komi (original/*-orig.txt + docs/README.md alphabet)
# Document 01 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_01_LINES = [
    '𐍜𐍔𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍩𐍝𐍟𐍙𐍙𐍜𐍨𐍛𐍨',
    '𐍥𐍢𐍨𐍜𐍔𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍞𐍐',
    '𐍥𐍣𐍚𐍩𐍡𐍜𐍙𐍝𐍚𐍨𐍛𐍓𐍐𐍥𐍔𐍣𐍡𐍔𐍥𐍞',
    '𐍛𐍜𐍩𐍡𐍥𐍙𐍡𐍙𐍔𐍝𐍐𐍣𐍠𐍐𐍜𐍛𐍣𐍜𐍐𐍜',
    '𐍑𐍠𐍙𐍢𐍣𐍟𐍣𐍓𐍩𐍠𐍨𐍝𐍟𐍣𐍚𐍨𐍥𐍛𐍣𐍡',
    '𐍨𐍛𐍣𐍩𐍩𐍡𐍣𐍩𐍨𐍝𐍤𐍩𐍜𐍛𐍩𐍝𐍡𐍨𐍛𐍩',
    '𐍝𐍛𐍣𐍝𐍥𐍩𐍠𐍩𐍞𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍥𐍙',
    '𐍝𐍙𐍐𐍡𐍩𐍝𐍙𐍓𐍙𐍡𐍡𐍥𐍙𐍝𐍜𐍩𐍝𐍣𐍩𐍐',
    '𐍞𐍔𐍠𐍩𐍡𐍡𐍣𐍛𐍐𐍛𐍩𐍜𐍐𐍢𐍨𐍓𐍡𐍨𐍛𐍨',
    '𐍥𐍓𐍨𐍜𐍨𐍥𐍟𐍨𐍥𐍙𐍙𐍡𐍣𐍩𐍐𐍝𐍨𐍛𐍣𐍡',
    '𐍤𐍩𐍜𐍛𐍩𐍝𐍩𐍨𐍡𐍓𐍩𐍠𐍨𐍥𐍙𐍙𐍞𐍠𐍑𐍨',
    '𐍠𐍢𐍙𐍡𐍜𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔𐍙𐍔𐍝𐍜𐍩𐍑',
    '𐍐𐍠𐍐𐍩𐍓𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣𐍩',
    '𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜𐍔',
]

# Document 02 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_02_LINES = [
    '𐍜𐍙𐍝𐍚𐍨𐍛𐍓𐍐𐍥𐍔𐍣𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥',
    '𐍙𐍡𐍙𐍔𐍝𐍐𐍣𐍠𐍐𐍜𐍛𐍣𐍜𐍐𐍜𐍑𐍠𐍙𐍢𐍣',
    '𐍟𐍣𐍓𐍩𐍠𐍨𐍝𐍟𐍣𐍚𐍨𐍥𐍛𐍣𐍡𐍨𐍛𐍣𐍩𐍩',
    '𐍡𐍣𐍩𐍨𐍝𐍤𐍩𐍜𐍛𐍩𐍝𐍡𐍨𐍛𐍩𐍝𐍛𐍣𐍝𐍥',
    '𐍩𐍠𐍩𐍞𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍥𐍙𐍝𐍙𐍐𐍡𐍩',
    '𐍝𐍙𐍓𐍙𐍡𐍡𐍥𐍙𐍝𐍜𐍩𐍝𐍣𐍩𐍐𐍞𐍔𐍠𐍩𐍡',
    '𐍡𐍣𐍛𐍐𐍛𐍩𐍜𐍐𐍢𐍨𐍓𐍡𐍨𐍛𐍨𐍥𐍓𐍨𐍜𐍨',
    '𐍥𐍟𐍨𐍥𐍙𐍙𐍡𐍣𐍩𐍐𐍝𐍨𐍛𐍣𐍡𐍤𐍩𐍜𐍛𐍩',
    '𐍝𐍩𐍨𐍡𐍓𐍩𐍠𐍨𐍥𐍙𐍙𐍞𐍠𐍑𐍨𐍠𐍢𐍙𐍡𐍜',
    '𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔𐍙𐍔𐍝𐍜𐍩𐍑𐍐𐍠𐍐𐍩𐍓',
    '𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣𐍩𐍐𐍓𐍡𐍣𐍔',
    '𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜𐍔𐍓𐍣𐍐𐍙𐍥',
    '𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟𐍩𐍓𐍩𐍡𐍢𐍙𐍙',
    '𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍟𐍣𐍓',
]

# Document 03 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_03_LINES = [
    '𐍜𐍐𐍜𐍑𐍠𐍙𐍢𐍣𐍟𐍣𐍓𐍩𐍠𐍨𐍝𐍟𐍣𐍚𐍨𐍥',
    '𐍛𐍣𐍡𐍨𐍛𐍣𐍩𐍩𐍡𐍣𐍩𐍨𐍝𐍤𐍩𐍜𐍛𐍩𐍝𐍡',
    '𐍨𐍛𐍩𐍝𐍛𐍣𐍝𐍥𐍩𐍠𐍩𐍞𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜',
    '𐍡𐍥𐍙𐍝𐍙𐍐𐍡𐍩𐍝𐍙𐍓𐍙𐍡𐍡𐍥𐍙𐍝𐍜𐍩𐍝',
    '𐍣𐍩𐍐𐍞𐍔𐍠𐍩𐍡𐍡𐍣𐍛𐍐𐍛𐍩𐍜𐍐𐍢𐍨𐍓𐍡',
    '𐍨𐍛𐍨𐍥𐍓𐍨𐍜𐍨𐍥𐍟𐍨𐍥𐍙𐍙𐍡𐍣𐍩𐍐𐍝𐍨',
    '𐍛𐍣𐍡𐍤𐍩𐍜𐍛𐍩𐍝𐍩𐍨𐍡𐍓𐍩𐍠𐍨𐍥𐍙𐍙𐍞',
    '𐍠𐍑𐍨𐍠𐍢𐍙𐍡𐍜𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔𐍙𐍔𐍝',
    '𐍜𐍩𐍑𐍐𐍠𐍐𐍩𐍓𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢',
    '𐍔𐍣𐍩𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣',
    '𐍝𐍜𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡',
    '𐍟𐍩𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓',
    '𐍝𐍨𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝',
    '𐍙𐍡𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡',
]

# Document 04 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_04_LINES = [
    '𐍤𐍩𐍜𐍛𐍩𐍝𐍡𐍨𐍛𐍩𐍝𐍛𐍣𐍝𐍥𐍩𐍠𐍩𐍞𐍙',
    '𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍥𐍙𐍝𐍙𐍐𐍡𐍩𐍝𐍙𐍓𐍙𐍡',
    '𐍡𐍥𐍙𐍝𐍜𐍩𐍝𐍣𐍩𐍐𐍞𐍔𐍠𐍩𐍡𐍡𐍣𐍛𐍐𐍛',
    '𐍩𐍜𐍐𐍢𐍨𐍓𐍡𐍨𐍛𐍨𐍥𐍓𐍨𐍜𐍨𐍥𐍟𐍨𐍥𐍙',
    '𐍙𐍡𐍣𐍩𐍐𐍝𐍨𐍛𐍣𐍡𐍤𐍩𐍜𐍛𐍩𐍝𐍩𐍨𐍡𐍓',
    '𐍩𐍠𐍨𐍥𐍙𐍙𐍞𐍠𐍑𐍨𐍠𐍢𐍙𐍡𐍜𐍣𐍩𐍙𐍥𐍙',
    '𐍙𐍡𐍜𐍔𐍙𐍔𐍝𐍜𐍩𐍑𐍐𐍠𐍐𐍩𐍓𐍙𐍜𐍚𐍩𐍜',
    '𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣𐍩𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣𐍨',
    '𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐𐍜',
    '𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟𐍩𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐',
    '𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙',
    '𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩',
    '𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍢',
    '𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓𐍐𐍡',
]

# Document 05 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_05_LINES = [
    '𐍙𐍝𐍙𐍐𐍡𐍩𐍝𐍙𐍓𐍙𐍡𐍡𐍥𐍙𐍝𐍜𐍩𐍝𐍣𐍩',
    '𐍐𐍞𐍔𐍠𐍩𐍡𐍡𐍣𐍛𐍐𐍛𐍩𐍜𐍐𐍢𐍨𐍓𐍡𐍨𐍛',
    '𐍨𐍥𐍓𐍨𐍜𐍨𐍥𐍟𐍨𐍥𐍙𐍙𐍡𐍣𐍩𐍐𐍝𐍨𐍛𐍣',
    '𐍡𐍤𐍩𐍜𐍛𐍩𐍝𐍩𐍨𐍡𐍓𐍩𐍠𐍨𐍥𐍙𐍙𐍞𐍠𐍑',
    '𐍨𐍠𐍢𐍙𐍡𐍜𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔𐍙𐍔𐍝𐍜𐍩',
    '𐍑𐍐𐍠𐍐𐍩𐍓𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣',
    '𐍩𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜',
    '𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟𐍩',
    '𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨',
    '𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡',
    '𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥',
    '𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛',
    '𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥',
    '𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙',
]

# Document 06 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_06_LINES = [
    '𐍐𐍞𐍔𐍠𐍩𐍡𐍡𐍣𐍛𐍐𐍛𐍩𐍜𐍐𐍢𐍨𐍓𐍡𐍨𐍛',
    '𐍨𐍥𐍓𐍨𐍜𐍨𐍥𐍟𐍨𐍥𐍙𐍙𐍡𐍣𐍩𐍐𐍝𐍨𐍛𐍣',
    '𐍡𐍤𐍩𐍜𐍛𐍩𐍝𐍩𐍨𐍡𐍓𐍩𐍠𐍨𐍥𐍙𐍙𐍞𐍠𐍑',
    '𐍨𐍠𐍢𐍙𐍡𐍜𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔𐍙𐍔𐍝𐍜𐍩',
    '𐍑𐍐𐍠𐍐𐍩𐍓𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣',
    '𐍩𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜',
    '𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟𐍩',
    '𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨',
    '𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡',
    '𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥',
    '𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛',
    '𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥',
    '𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙',
    '𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤',
]

# Document 07 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_07_LINES = [
    '𐍐𐍝𐍨𐍛𐍣𐍡𐍤𐍩𐍜𐍛𐍩𐍝𐍩𐍨𐍡𐍓𐍩𐍠𐍨𐍥',
    '𐍙𐍙𐍞𐍠𐍑𐍨𐍠𐍢𐍙𐍡𐍜𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔',
    '𐍙𐍔𐍝𐍜𐍩𐍑𐍐𐍠𐍐𐍩𐍓𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛',
    '𐍡𐍩𐍢𐍔𐍣𐍩𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙',
    '𐍝𐍜𐍣𐍝𐍜𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨',
    '𐍝𐍨𐍡𐍟𐍩𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓',
    '𐍤𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥',
    '𐍐𐍡𐍝𐍙𐍡𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝',
    '𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍢𐍣𐍙𐍩𐍚',
    '𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓𐍐𐍡𐍣𐍔𐍠𐍩',
    '𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣𐍐𐍛𐍚𐍣𐍙𐍚',
    '𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍐𐍠𐍐',
    '𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡𐍢𐍔𐍠𐍜𐍩𐍓',
    '𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡𐍢𐍩𐍜𐍟𐍨𐍥',
]

# Document 08 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_08_LINES = [
    '𐍜𐍣𐍩𐍙𐍥𐍙𐍙𐍡𐍜𐍔𐍙𐍔𐍝𐍜𐍩𐍑𐍐𐍠𐍐𐍩',
    '𐍓𐍙𐍜𐍚𐍩𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣𐍩𐍐𐍓𐍡𐍣',
    '𐍔𐍠𐍙𐍓𐍣𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜𐍔𐍓𐍣𐍐𐍙',
    '𐍥𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟𐍩𐍓𐍩𐍡𐍢𐍙',
    '𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍟𐍣',
    '𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡𐍝𐍐𐍝𐍙𐍐',
    '𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝𐍐𐍓',
    '𐍝𐍨𐍓𐍢𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚𐍕𐍙',
    '𐍓𐍝𐍨𐍓𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡𐍝𐍨',
    '𐍡𐍡𐍙𐍣𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙',
    '𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙',
    '𐍥𐍙𐍙𐍡𐍢𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢',
    '𐍙𐍡𐍩𐍡𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩',
    '𐍜𐍝𐍐𐍝𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩',
]

# Document 09 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_09_LINES = [
    '𐍜𐍔𐍓𐍐𐍛𐍡𐍩𐍢𐍔𐍣𐍩𐍐𐍓𐍡𐍣𐍔𐍠𐍙𐍓𐍣',
    '𐍨𐍛𐍢𐍙𐍙𐍝𐍜𐍣𐍝𐍜𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐',
    '𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟𐍩𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡',
    '𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝',
    '𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥',
    '𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢𐍣',
    '𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓𐍐',
    '𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣𐍐',
    '𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠𐍐',
    '𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡𐍢',
    '𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡𐍢',
    '𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝𐍟',
    '𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚𐍣',
    '𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢𐍙',
]

# Document 10 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_10_LINES = [
    '𐍜𐍔𐍓𐍣𐍐𐍙𐍥𐍐𐍡𐍣𐍐𐍜𐍨𐍥𐍚𐍨𐍝𐍨𐍡𐍟',
    '𐍩𐍓𐍩𐍡𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝',
    '𐍨𐍓𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙',
    '𐍡𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔',
    '𐍥𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓',
    '𐍛𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙',
    '𐍥𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝',
    '𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩',
    '𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡𐍢𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩',
    '𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛',
    '𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜',
    '𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩',
    '𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛',
    '𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣',
]

# Document 11 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_11_LINES = [
    '𐍢𐍙𐍙𐍐𐍝𐍙𐍡𐍐𐍙𐍚𐍩𐍓𐍤𐍐𐍓𐍝𐍨𐍓𐍢𐍣',
    '𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡𐍝𐍐𐍝',
    '𐍙𐍐𐍡𐍜𐍔𐍓𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝',
    '𐍐𐍓𐍝𐍨𐍓𐍢𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚',
    '𐍕𐍙𐍓𐍝𐍨𐍓𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡',
    '𐍝𐍨𐍡𐍡𐍙𐍣𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥',
    '𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝',
    '𐍩𐍙𐍥𐍙𐍙𐍡𐍢𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐',
    '𐍥𐍢𐍙𐍡𐍩𐍡𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛',
    '𐍓𐍩𐍜𐍝𐍐𐍝𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩',
    '𐍡𐍩𐍠𐍓𐍩𐍚𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠',
    '𐍩𐍡𐍙𐍥𐍔𐍢𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒',
    '𐍨𐍓𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐',
    '𐍙𐍩𐍛𐍚𐍣𐍚𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟',
]

# Document 12 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_12_LINES = [
    '𐍝𐍙𐍣𐍐𐍙𐍥𐍐𐍡𐍝𐍙𐍡𐍝𐍐𐍝𐍙𐍐𐍡𐍜𐍔𐍓',
    '𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢',
    '𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓',
    '𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣',
    '𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠',
    '𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡',
    '𐍢𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡',
    '𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝',
    '𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚',
    '𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢',
    '𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢',
    '𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚',
    '𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝',
    '𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙',
]

# Document 13 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_13_LINES = [
    '𐍥𐍩𐍙𐍐𐍓𐍝𐍨𐍓𐍡𐍔𐍥𐍜𐍣𐍝𐍐𐍓𐍝𐍨𐍓𐍢',
    '𐍣𐍢𐍣𐍙𐍩𐍚𐍩𐍓𐍣𐍓𐍛𐍨𐍥𐍚𐍕𐍙𐍓𐍝𐍨𐍓',
    '𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣',
    '𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠',
    '𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡',
    '𐍢𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡',
    '𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝',
    '𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚',
    '𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢',
    '𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢',
    '𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚',
    '𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝',
    '𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙',
    '𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠',
]

# Document 14 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_14_LINES = [
    '𐍐𐍡𐍣𐍔𐍠𐍩𐍠𐍓𐍩𐍙𐍥𐍙𐍙𐍡𐍝𐍨𐍡𐍡𐍙𐍣',
    '𐍐𐍛𐍚𐍣𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠',
    '𐍐𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡',
    '𐍢𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡',
    '𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝',
    '𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚',
    '𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢',
    '𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢',
    '𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚',
    '𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝',
    '𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙',
    '𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠',
    '𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝',
    '𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩',
]

# Document 15 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_15_LINES = [
    '𐍙𐍚𐍥𐍙𐍙𐍝𐍙𐍟𐍨𐍥𐍙𐍙𐍡𐍐𐍣𐍠𐍐𐍜𐍡𐍐',
    '𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡𐍢𐍔𐍠𐍜',
    '𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡𐍢𐍩𐍜𐍟',
    '𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝𐍟𐍨𐍥𐍙',
    '𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚𐍣𐍢𐍙𐍡',
    '𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢𐍙𐍡𐍡𐍙',
    '𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍑',
    '𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚𐍚𐍩𐍓𐍩',
    '𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝𐍨𐍣𐍩𐍨',
    '𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙𐍡𐍝𐍨𐍣',
    '𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠𐍐𐍐𐍞𐍠',
    '𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝𐍨𐍡𐍑𐍨',
    '𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩𐍢𐍙𐍝𐍨',
    '𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛𐍛𐍙𐍥𐍑𐍣𐍐𐍚',
]

# Document 16 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_16_LINES = [
    '𐍜𐍡𐍐𐍠𐍐𐍩𐍠𐍓𐍩𐍤𐍩𐍜𐍝𐍩𐍙𐍥𐍙𐍙𐍡𐍢',
    '𐍔𐍠𐍜𐍩𐍓𐍥𐍙𐍛𐍩𐍙𐍒𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡𐍢',
    '𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝𐍟',
    '𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚𐍣',
    '𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢𐍙',
    '𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢𐍙',
    '𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚𐍚',
    '𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝𐍨',
    '𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙𐍡',
    '𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠𐍐',
    '𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝𐍨',
    '𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩𐍢',
    '𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛𐍛𐍙𐍥𐍑',
    '𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛𐍛𐍩𐍜𐍥',
]

# Document 17 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_17_LINES = [
    '𐍢𐍐𐍥𐍢𐍙𐍡𐍩𐍡𐍢𐍩𐍜𐍟𐍨𐍥𐍙𐍣𐍐𐍛𐍒𐍚',
    '𐍩𐍛𐍓𐍩𐍜𐍝𐍐𐍝𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡',
    '𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑',
    '𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙',
    '𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙',
    '𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡',
    '𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨',
    '𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓',
    '𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩',
    '𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢',
    '𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩',
    '𐍜𐍐𐍥𐍞𐍛𐍛𐍙𐍥𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜',
    '𐍚𐍩𐍝𐍩𐍛𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨',
    '𐍠𐍢𐍙𐍡𐍑𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩',
]

# Document 18 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_18_LINES = [
    '𐍟𐍨𐍥𐍙𐍙𐍣𐍠𐍐𐍜𐍜𐍩𐍡𐍙𐍩𐍡𐍩𐍠𐍓𐍩𐍚',
    '𐍣𐍢𐍙𐍡𐍤𐍩𐍛𐍩𐍥𐍩𐍡𐍑𐍣𐍠𐍩𐍡𐍙𐍥𐍔𐍢',
    '𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓𐍐𐍥𐍢',
    '𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚',
    '𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝',
    '𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙',
    '𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠',
    '𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝',
    '𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩',
    '𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛𐍛𐍙𐍥',
    '𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛𐍛𐍩𐍜',
    '𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡𐍑𐍩𐍓𐍩',
    '𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙𐍝𐍨𐍡𐍟',
    '𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡𐍝𐍨𐍛',
]

# Document 19 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_19_LINES = [
    '𐍥𐍔𐍢𐍙𐍡𐍡𐍙𐍙𐍩𐍣𐍔𐍠𐍛𐍣𐍙𐍠𐍒𐍨𐍓𐍓',
    '𐍐𐍥𐍢𐍙𐍡𐍙𐍑𐍩𐍥𐍢𐍙𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛',
    '𐍚𐍣𐍚𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢',
    '𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡',
    '𐍞𐍙𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡',
    '𐍐𐍠𐍠𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛',
    '𐍩𐍙𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜',
    '𐍩𐍝𐍩𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛',
    '𐍛𐍙𐍥𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛',
    '𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡𐍑',
    '𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙𐍝',
    '𐍨𐍡𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡',
    '𐍝𐍨𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡𐍩',
    '𐍑𐍙𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍔',
]

# Document 20 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_20_LINES = [
    '𐍡𐍣𐍨𐍙𐍜𐍐𐍙𐍩𐍛𐍚𐍣𐍚𐍚𐍩𐍓𐍩𐍡𐍡𐍓𐍐',
    '𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍙𐍥𐍩',
    '𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢',
    '𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐',
    '𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩',
    '𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥',
    '𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛𐍛𐍙𐍥𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚',
    '𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩',
    '𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡𐍑𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡',
    '𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙𐍝𐍨𐍡𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔',
    '𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡𐍝𐍨𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩',
    '𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡𐍩𐍑𐍙𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝',
    '𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍔𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡',
    '𐍔𐍡𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩',
]

# Document 21 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_21_LINES = [
    '𐍓𐍐𐍥𐍢𐍙𐍡𐍙𐍟𐍣𐍒𐍢𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍙',
    '𐍥𐍩𐍙𐍡𐍝𐍨𐍡𐍐𐍤𐍨𐍡𐍞𐍙𐍙𐍡𐍝𐍨𐍣𐍩𐍨',
    '𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡𐍐𐍠𐍠𐍐𐍐𐍞𐍠𐍐𐍐',
    '𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛𐍩𐍙𐍝𐍨𐍡𐍑𐍨𐍓𐍩',
    '𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜𐍩𐍝𐍩𐍢𐍙𐍝𐍨𐍝𐍡',
    '𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛𐍛𐍙𐍥𐍑𐍣𐍐𐍚𐍨𐍛',
    '𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛',
    '𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡𐍑𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐',
    '𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙𐍝𐍨𐍡𐍟𐍣𐍚𐍨𐍒𐍩𐍝',
    '𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡𐍝𐍨𐍛𐍣𐍙𐍞𐍚𐍛𐍨',
    '𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡𐍩𐍑𐍙𐍡𐍔𐍡𐍢𐍨𐍠𐍙',
    '𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍔𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩',
    '𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍞𐍩𐍘𐍟𐍝𐍨𐍡',
    '𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡',
]

# Document 22 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_22_LINES = [
    '𐍞𐍙𐍙𐍡𐍝𐍨𐍣𐍩𐍨𐍝𐍢𐍣𐍟𐍣𐍓𐍨𐍝𐍨𐍝𐍡',
    '𐍐𐍠𐍠𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍛',
    '𐍩𐍙𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩𐍜',
    '𐍩𐍝𐍩𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛',
    '𐍛𐍙𐍥𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛',
    '𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡𐍑',
    '𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙𐍝',
    '𐍨𐍡𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡',
    '𐍝𐍨𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡𐍩',
    '𐍑𐍙𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍔',
    '𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓𐍙𐍡𐍝',
    '𐍨𐍡𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐𐍡𐍩𐍝',
    '𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍡𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍞𐍩',
    '𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚𐍩𐍙𐍓𐍟𐍣𐍚𐍥𐍙𐍡𐍩',
]

# Document 23 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_23_LINES = [
    '𐍡𐍐𐍠𐍠𐍐𐍐𐍞𐍠𐍐𐍐𐍜𐍐𐍟𐍙𐍟𐍩𐍛𐍢𐍩𐍡',
    '𐍛𐍩𐍙𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍩𐍓𐍒𐍩𐍢𐍥𐍩𐍛𐍩',
    '𐍜𐍩𐍝𐍩𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞',
    '𐍛𐍛𐍙𐍥𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩',
    '𐍛𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡',
    '𐍑𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙',
    '𐍝𐍨𐍡𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙',
    '𐍡𐍝𐍨𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡',
    '𐍩𐍑𐍙𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞',
    '𐍔𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓𐍙𐍡',
    '𐍝𐍨𐍡𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐𐍡𐍩',
    '𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍡𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍞',
    '𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚𐍩𐍙𐍓𐍟𐍣𐍚𐍥𐍙𐍡',
    '𐍩𐍢𐍙𐍩𐍢𐍙𐍣𐍨𐍛𐍨𐍝𐍚𐍩𐍓𐍚𐍩𐍣𐍨𐍛𐍨',
]

# Document 24 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_24_LINES = [
    '𐍩𐍢𐍙𐍝𐍨𐍝𐍡𐍔𐍥𐍚𐍕𐍢𐍩𐍜𐍐𐍥𐍞𐍛𐍛𐍙',
    '𐍥𐍑𐍣𐍐𐍚𐍨𐍛𐍨𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍝𐍩𐍛𐍛𐍩',
    '𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢𐍙𐍡𐍑𐍩𐍓',
    '𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛𐍩𐍙𐍝𐍨𐍡',
    '𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡𐍝𐍨',
    '𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡𐍩𐍑𐍙',
    '𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍔𐍕𐍐',
    '𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡',
    '𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐𐍡𐍩𐍝𐍚𐍣',
    '𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍡𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍞𐍩𐍠𐍜',
    '𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚𐍩𐍙𐍓𐍟𐍣𐍚𐍥𐍙𐍡𐍩𐍢𐍙',
    '𐍩𐍢𐍙𐍣𐍨𐍛𐍨𐍝𐍚𐍩𐍓𐍚𐍩𐍣𐍨𐍛𐍨𐍝𐍝𐍨',
    '𐍣𐍨𐍛𐍨𐍝𐍡𐍔𐍥𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩',
    '𐍝𐍞𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍥𐍟𐍩𐍝𐍓𐍙',
]

# Document 25 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_25_LINES = [
    '𐍝𐍩𐍛𐍛𐍩𐍜𐍥𐍨𐍛𐍟𐍩𐍛𐍢𐍩𐍡𐍙𐍢𐍨𐍠𐍢',
    '𐍙𐍡𐍑𐍩𐍓𐍩𐍝𐍚𐍐𐍠𐍢𐍐𐍩𐍡𐍚𐍨𐍢𐍩𐍝𐍛',
    '𐍩𐍙𐍝𐍨𐍡𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡',
    '𐍥𐍙𐍡𐍝𐍨𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐',
    '𐍡𐍡𐍩𐍑𐍙𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩',
    '𐍝𐍞𐍔𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓',
    '𐍙𐍡𐍝𐍨𐍡𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐',
    '𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍡𐍔𐍢𐍙𐍡𐍝𐍨𐍛',
    '𐍣𐍞𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚𐍩𐍙𐍓𐍟𐍣𐍚𐍥',
    '𐍙𐍡𐍩𐍢𐍙𐍩𐍢𐍙𐍣𐍨𐍛𐍨𐍝𐍚𐍩𐍓𐍚𐍩𐍣𐍨',
    '𐍛𐍨𐍝𐍝𐍨𐍣𐍨𐍛𐍨𐍝𐍡𐍔𐍥𐍢𐍨𐍠𐍙𐍡𐍝𐍨',
    '𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍥',
    '𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍣𐍩𐍙𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚',
    '𐍨𐍛𐍙𐍐𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍥𐍔𐍢𐍙',
]

# Document 26 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_26_LINES = [
    '𐍟𐍣𐍚𐍨𐍒𐍩𐍝𐍡𐍔𐍥𐍞𐍛𐍜𐍩𐍡𐍥𐍙𐍡𐍝𐍨',
    '𐍛𐍣𐍙𐍞𐍚𐍛𐍨𐍒𐍩𐍝𐍚𐍨𐍛𐍙𐍐𐍡𐍡𐍩𐍑𐍙',
    '𐍡𐍔𐍡𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍔𐍕𐍐',
    '𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡',
    '𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐𐍡𐍩𐍝𐍚𐍣',
    '𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍡𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍞𐍩𐍠𐍜',
    '𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚𐍩𐍙𐍓𐍟𐍣𐍚𐍥𐍙𐍡𐍩𐍢𐍙',
    '𐍩𐍢𐍙𐍣𐍨𐍛𐍨𐍝𐍚𐍩𐍓𐍚𐍩𐍣𐍨𐍛𐍨𐍝𐍝𐍨',
    '𐍣𐍨𐍛𐍨𐍝𐍡𐍔𐍥𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩',
    '𐍝𐍞𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍥𐍟𐍩𐍝𐍓𐍙',
    '𐍡𐍝𐍨𐍡𐍣𐍩𐍙𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍙𐍐𐍡',
    '𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍥𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣',
    '𐍣𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍐𐍓𐍩𐍝𐍜𐍔𐍗𐍩𐍡',
    '𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍢𐍔𐍝𐍙𐍓𐍜𐍔𐍗𐍩𐍡𐍩𐍞',
]

# Document 27 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_27_LINES = [
    '𐍞𐍔𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍡𐍟𐍩𐍝𐍓𐍙',
    '𐍡𐍝𐍨𐍡𐍞𐍩𐍘𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍘𐍐𐍡',
    '𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍡𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣',
    '𐍞𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚𐍩𐍙𐍓𐍟𐍣𐍚𐍥𐍙',
    '𐍡𐍩𐍢𐍙𐍩𐍢𐍙𐍣𐍨𐍛𐍨𐍝𐍚𐍩𐍓𐍚𐍩𐍣𐍨𐍛',
    '𐍨𐍝𐍝𐍨𐍣𐍨𐍛𐍨𐍝𐍡𐍔𐍥𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡',
    '𐍑𐍨𐍓𐍩𐍝𐍞𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡𐍔𐍥𐍟',
    '𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍣𐍩𐍙𐍟𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨',
    '𐍛𐍙𐍐𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍥𐍔𐍢𐍙𐍡',
    '𐍝𐍨𐍛𐍣𐍣𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍐𐍓𐍩𐍝𐍜',
    '𐍔𐍗𐍩𐍡𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍢𐍔𐍝𐍙𐍓𐍜𐍔𐍗',
    '𐍩𐍡𐍩𐍞𐍔𐍕𐍐𐍔𐍘𐍜𐍩𐍞𐍔𐍕𐍐𐍤𐍔𐍠𐍨𐍓',
    '𐍩𐍞𐍔𐍕𐍐𐍚𐍣𐍛𐍢𐍩𐍜𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍜',
    '𐍴𐍝𐍓𐍨𐍡𐍔𐍛𐍣𐍝𐍚𐍐𐍠𐍡𐍐𐍛𐍨𐍙𐍡𐍢𐍩',
]

# Document 28 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_28_LINES = [
    '𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍞𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍚',
    '𐍩𐍙𐍓𐍟𐍣𐍚𐍥𐍙𐍡𐍩𐍢𐍙𐍩𐍢𐍙𐍣𐍨𐍛𐍨𐍝',
    '𐍚𐍩𐍓𐍚𐍩𐍣𐍨𐍛𐍨𐍝𐍝𐍨𐍣𐍨𐍛𐍨𐍝𐍡𐍔𐍥',
    '𐍢𐍨𐍠𐍙𐍡𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍕𐍐𐍟𐍩𐍛𐍢',
    '𐍩𐍡𐍩𐍝𐍡𐍔𐍥𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍣𐍩𐍙𐍟',
    '𐍝𐍨𐍡𐍜𐍩𐍓𐍚𐍨𐍛𐍙𐍐𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛',
    '𐍢𐍩𐍡𐍥𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍣𐍩𐍠𐍜𐍩𐍓𐍤𐍙',
    '𐍝𐍨𐍡𐍐𐍓𐍩𐍝𐍜𐍔𐍗𐍩𐍡𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨',
    '𐍢𐍔𐍝𐍙𐍓𐍜𐍔𐍗𐍩𐍡𐍩𐍞𐍔𐍕𐍐𐍔𐍘𐍜𐍩𐍞',
    '𐍔𐍕𐍐𐍤𐍔𐍠𐍨𐍓𐍩𐍞𐍔𐍕𐍐𐍚𐍣𐍛𐍢𐍩𐍜𐍩',
    '𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍜𐍴𐍝𐍓𐍨𐍡𐍔𐍛𐍣𐍝𐍚𐍐𐍠',
    '𐍡𐍐𐍛𐍨𐍙𐍡𐍢𐍩𐍜𐍳𐍔𐍕𐍙𐍓𐍩𐍒𐍴𐍡𐍛𐍨',
    '𐍝𐍟𐍐𐍳𐍔𐍛𐍛𐍩𐍝𐍛𐍨𐍓𐍴𐍝𐍨𐍡𐍩𐍝𐍢𐍐',
    '𐍠𐍨𐍞𐍐𐍚𐍩𐍴𐍡𐍒𐍐𐍕𐍐𐍛𐍐𐍜𐍜𐍔𐍓𐍢𐍩',
]

# Document 29 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_29_LINES = [
    '𐍣𐍨𐍛𐍨𐍝𐍝𐍨𐍣𐍨𐍛𐍨𐍝𐍡𐍔𐍥𐍢𐍨𐍠𐍙𐍡',
    '𐍝𐍨𐍡𐍑𐍨𐍓𐍩𐍝𐍞𐍕𐍐𐍟𐍩𐍛𐍢𐍩𐍡𐍩𐍝𐍡',
    '𐍔𐍥𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍣𐍩𐍙𐍟𐍝𐍨𐍡𐍜𐍩',
    '𐍓𐍚𐍨𐍛𐍙𐍐𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍥𐍔',
    '𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍣𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍐𐍓',
    '𐍩𐍝𐍜𐍔𐍗𐍩𐍡𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍢𐍔𐍝𐍙𐍓',
    '𐍜𐍔𐍗𐍩𐍡𐍩𐍞𐍔𐍕𐍐𐍔𐍘𐍜𐍩𐍞𐍔𐍕𐍐𐍤𐍔',
    '𐍠𐍨𐍓𐍩𐍞𐍔𐍕𐍐𐍚𐍣𐍛𐍢𐍩𐍜𐍩𐍜𐍨𐍛𐍨𐍥',
    '𐍢𐍨𐍜𐍴𐍝𐍓𐍨𐍡𐍔𐍛𐍣𐍝𐍚𐍐𐍠𐍡𐍐𐍛𐍨𐍙',
    '𐍡𐍢𐍩𐍜𐍳𐍔𐍕𐍙𐍓𐍩𐍒𐍴𐍡𐍛𐍨𐍝𐍟𐍐𐍳𐍔',
    '𐍛𐍛𐍩𐍝𐍛𐍨𐍓𐍴𐍝𐍨𐍡𐍩𐍝𐍢𐍐𐍠𐍨𐍞𐍐𐍚',
    '𐍩𐍴𐍡𐍒𐍐𐍕𐍐𐍛𐍐𐍜𐍜𐍔𐍓𐍢𐍩𐍓𐍓𐍐𐍝𐍨',
    '𐍓𐍣𐍕𐍩𐍜𐍩𐍴𐍡𐍓𐍐𐍠𐍨𐍝𐍜𐍔𐍓𐍩𐍓𐍢𐍩',
    '𐍕𐍓𐍩𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍙𐍜𐍣𐍚𐍩𐍓𐍞𐍩𐍙𐍢',
]

# Document 30 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_30_LINES = [
    '𐍡𐍔𐍥𐍟𐍩𐍝𐍓𐍙𐍡𐍝𐍨𐍡𐍣𐍩𐍙𐍟𐍝𐍨𐍡𐍜',
    '𐍩𐍓𐍚𐍨𐍛𐍙𐍐𐍡𐍩𐍝𐍚𐍣𐍙𐍟𐍩𐍛𐍢𐍩𐍡𐍥',
    '𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍣𐍩𐍠𐍜𐍩𐍓𐍤𐍙𐍝𐍨𐍡𐍐',
    '𐍓𐍩𐍝𐍜𐍔𐍗𐍩𐍡𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍢𐍔𐍝𐍙',
    '𐍓𐍜𐍔𐍗𐍩𐍡𐍩𐍞𐍔𐍕𐍐𐍔𐍘𐍜𐍩𐍞𐍔𐍕𐍐𐍤',
    '𐍔𐍠𐍨𐍓𐍩𐍞𐍔𐍕𐍐𐍚𐍣𐍛𐍢𐍩𐍜𐍩𐍜𐍨𐍛𐍨',
    '𐍥𐍢𐍨𐍜𐍴𐍝𐍓𐍨𐍡𐍔𐍛𐍣𐍝𐍚𐍐𐍠𐍡𐍐𐍛𐍨',
    '𐍙𐍡𐍢𐍩𐍜𐍳𐍔𐍕𐍙𐍓𐍩𐍒𐍴𐍡𐍛𐍨𐍝𐍟𐍐𐍳',
    '𐍔𐍛𐍛𐍩𐍝𐍛𐍨𐍓𐍴𐍝𐍨𐍡𐍩𐍝𐍢𐍐𐍠𐍨𐍞𐍐',
    '𐍚𐍩𐍴𐍡𐍒𐍐𐍕𐍐𐍛𐍐𐍜𐍜𐍔𐍓𐍢𐍩𐍓𐍓𐍐𐍝',
    '𐍨𐍓𐍣𐍕𐍩𐍜𐍩𐍴𐍡𐍓𐍐𐍠𐍨𐍝𐍜𐍔𐍓𐍩𐍓𐍢',
    '𐍩𐍕𐍓𐍩𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍙𐍜𐍣𐍚𐍩𐍓𐍞𐍩𐍙',
    '𐍢𐍨𐍠𐍚𐍩𐍠𐍝𐍨𐍡𐍛𐍩𐍝𐍐𐍑𐍣𐍛𐍚𐍔𐍕𐍐',
    '𐍥𐍐𐍝𐍔𐍡𐍚𐍐𐍜𐍝𐍨𐍜𐍚𐍩𐍳𐍔𐍳𐍥𐍙𐍡𐍣',
]

# Document 31 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_31_LINES = [
    '𐍛𐍢𐍩𐍡𐍥𐍔𐍢𐍙𐍡𐍝𐍨𐍛𐍣𐍣𐍩𐍠𐍜𐍩𐍓𐍤',
    '𐍙𐍝𐍨𐍡𐍐𐍓𐍩𐍝𐍜𐍔𐍗𐍩𐍡𐍩𐍜𐍨𐍛𐍨𐍥𐍢',
    '𐍨𐍢𐍔𐍝𐍙𐍓𐍜𐍔𐍗𐍩𐍡𐍩𐍞𐍔𐍕𐍐𐍔𐍘𐍜𐍩',
    '𐍞𐍔𐍕𐍐𐍤𐍔𐍠𐍨𐍓𐍩𐍞𐍔𐍕𐍐𐍚𐍣𐍛𐍢𐍩𐍜',
    '𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍜𐍴𐍝𐍓𐍨𐍡𐍔𐍛𐍣𐍝𐍚𐍐',
    '𐍠𐍡𐍐𐍛𐍨𐍙𐍡𐍢𐍩𐍜𐍳𐍔𐍕𐍙𐍓𐍩𐍒𐍴𐍡𐍛',
    '𐍨𐍝𐍟𐍐𐍳𐍔𐍛𐍛𐍩𐍝𐍛𐍨𐍓𐍴𐍝𐍨𐍡𐍩𐍝𐍢',
    '𐍐𐍠𐍨𐍞𐍐𐍚𐍩𐍴𐍡𐍒𐍐𐍕𐍐𐍛𐍐𐍜𐍜𐍔𐍓𐍢',
    '𐍩𐍓𐍓𐍐𐍝𐍨𐍓𐍣𐍕𐍩𐍜𐍩𐍴𐍡𐍓𐍐𐍠𐍨𐍝𐍜',
    '𐍔𐍓𐍩𐍓𐍢𐍩𐍕𐍓𐍩𐍚𐍣𐍤𐍩𐍜𐍚𐍩𐍙𐍜𐍣𐍚',
    '𐍩𐍓𐍞𐍩𐍙𐍢𐍨𐍠𐍚𐍩𐍠𐍝𐍨𐍡𐍛𐍩𐍝𐍐𐍑𐍣',
    '𐍛𐍚𐍔𐍕𐍐𐍥𐍐𐍝𐍔𐍡𐍚𐍐𐍜𐍝𐍨𐍜𐍚𐍩𐍳𐍔',
    '𐍳𐍥𐍙𐍡𐍣𐍡𐍚𐍣𐍛𐍨𐍛𐍩𐍛𐍕𐍙𐍡𐍨𐍭𐍔𐍥',
    '𐍔𐍝𐍙𐍡𐍣𐍡𐍜𐍩𐍜𐍩𐍒𐍨𐍥𐍣𐍕𐍩𐍜𐍴𐍗𐍓',
]

# Document 32 — corpus-based Old Komi transliteration (not a historical facsimile)
DOCUMENT_32_LINES = [
    '𐍔𐍘𐍜𐍩𐍞𐍔𐍕𐍐𐍤𐍔𐍠𐍨𐍓𐍩𐍞𐍔𐍕𐍐𐍚𐍣',
    '𐍛𐍢𐍩𐍜𐍩𐍜𐍨𐍛𐍨𐍥𐍢𐍨𐍜𐍴𐍝𐍓𐍨𐍡𐍔𐍛',
    '𐍣𐍝𐍚𐍐𐍠𐍡𐍐𐍛𐍨𐍙𐍡𐍢𐍩𐍜𐍳𐍔𐍕𐍙𐍓𐍩',
    '𐍒𐍴𐍡𐍛𐍨𐍝𐍟𐍐𐍳𐍔𐍛𐍛𐍩𐍝𐍛𐍨𐍓𐍴𐍝𐍨',
    '𐍡𐍩𐍝𐍢𐍐𐍠𐍨𐍞𐍐𐍚𐍩𐍴𐍡𐍒𐍐𐍕𐍐𐍛𐍐𐍜',
    '𐍜𐍔𐍓𐍢𐍩𐍓𐍓𐍐𐍝𐍨𐍓𐍣𐍕𐍩𐍜𐍩𐍴𐍡𐍓𐍐',
    '𐍠𐍨𐍝𐍜𐍔𐍓𐍩𐍓𐍢𐍩𐍕𐍓𐍩𐍚𐍣𐍤𐍩𐍜𐍚𐍩',
    '𐍙𐍜𐍣𐍚𐍩𐍓𐍞𐍩𐍙𐍢𐍨𐍠𐍚𐍩𐍠𐍝𐍨𐍡𐍛𐍩',
    '𐍝𐍐𐍑𐍣𐍛𐍚𐍔𐍕𐍐𐍥𐍐𐍝𐍔𐍡𐍚𐍐𐍜𐍝𐍨𐍜',
    '𐍚𐍩𐍳𐍔𐍳𐍥𐍙𐍡𐍣𐍡𐍚𐍣𐍛𐍨𐍛𐍩𐍛𐍕𐍙𐍡',
    '𐍨𐍭𐍔𐍥𐍔𐍝𐍙𐍡𐍣𐍡𐍜𐍩𐍜𐍩𐍒𐍨𐍥𐍣𐍕𐍩',
    '𐍜𐍴𐍗𐍓𐍨𐍞𐍐𐍝𐍴𐍡𐍡𐍨𐍝𐍩𐍢𐍢𐍐𐍝𐍔𐍡',
    '𐍨𐍞𐍩𐍙𐍟𐍐𐍜𐍢𐍙𐍴𐍝𐍛𐍨𐍜𐍔𐍗𐍩𐍡𐍚𐍙',
    '𐍡𐍛𐍩𐍝𐍔𐍳𐍳𐍔𐍥𐍜𐍔𐍗𐍩𐍡𐍞𐍩𐍐𐍝𐍓𐍨',
]

TEXT_LINES_BY_DOCUMENT = [
    DOCUMENT_01_LINES, DOCUMENT_02_LINES, DOCUMENT_03_LINES, DOCUMENT_04_LINES,
    DOCUMENT_05_LINES, DOCUMENT_06_LINES, DOCUMENT_07_LINES, DOCUMENT_08_LINES,
    DOCUMENT_09_LINES, DOCUMENT_10_LINES, DOCUMENT_11_LINES, DOCUMENT_12_LINES,
    DOCUMENT_13_LINES, DOCUMENT_14_LINES, DOCUMENT_15_LINES, DOCUMENT_16_LINES,
    DOCUMENT_17_LINES, DOCUMENT_18_LINES, DOCUMENT_19_LINES, DOCUMENT_20_LINES,
    DOCUMENT_21_LINES, DOCUMENT_22_LINES, DOCUMENT_23_LINES, DOCUMENT_24_LINES,
    DOCUMENT_25_LINES, DOCUMENT_26_LINES, DOCUMENT_27_LINES, DOCUMENT_28_LINES,
    DOCUMENT_29_LINES, DOCUMENT_30_LINES, DOCUMENT_31_LINES, DOCUMENT_32_LINES,
]


def _validate_text(lines_by_document, expected_count=32):
    if len(lines_by_document) != expected_count:
        raise ValueError(f'Expected {expected_count} documents, got {len(lines_by_document)}')
    for i, lines in enumerate(lines_by_document, 1):
        if len(lines) != 14:
            raise ValueError(f'DOCUMENT_{i:02d}_LINES must contain exactly 14 lines; got {len(lines)}')
        if any(not isinstance(line, str) for line in lines):
            raise TypeError(f'DOCUMENT_{i:02d}_LINES must contain strings only')


def _make_contact_sheet(paths, output_path):
    from PIL import Image, ImageDraw
    imgs = [Image.open(p).convert('RGB').resize((210, 285)) for p in paths]
    cols, rows = 4, 8
    sheet = Image.new('RGB', (210 * cols, 305 * rows), (40, 30, 20))
    draw = ImageDraw.Draw(sheet)
    for i, image in enumerate(imgs):
        x, y = (i % cols) * 210, (i // cols) * 305
        sheet.paste(image, (x, y))
        draw.text((x + 5, y + 287), f'document_{i + 1:02d}', fill=(255, 235, 190))
    sheet.save(output_path)


def main():
    parser = argparse.ArgumentParser(description='Generate 32 local archival manuscript images')
    parser.add_argument('--repo-root', type=Path, default=_repo_root(), help='Repository root containing font/svg')
    parser.add_argument('--background-dir', type=Path, default=None, help='Folder of parchment/document images')
    parser.add_argument('--output-dir', type=Path, default=None, help='Output folder')
    parser.add_argument('--seed', type=int, default=20260907)
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    background_dir = (args.background_dir or repo_root / 'user_backgrounds').expanduser().resolve()
    output_dir = (args.output_dir or repo_root / 'local_archival_documents_32').expanduser().resolve()
    glyph_root = repo_root / 'font' / 'svg'
    if not glyph_root.is_dir():
        raise FileNotFoundError(f'Glyph directory not found: {glyph_root}')
    background_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Import after validating the local repo, so the script works without install.
    sys.path.insert(0, str(repo_root / 'lib'))
    from historical_glyph_studio import GlyphStudio
    from historical_glyph_studio.document_generator import DocumentSpec, generate_documents

    _validate_text(TEXT_LINES_BY_DOCUMENT)
    backgrounds = sorted(
        p for p in background_dir.rglob('*')
        if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff'}
    )
    studio = GlyphStudio(glyph_root=glyph_root)
    specs = [
        DocumentSpec(
            document_id=i + 1,
            seed=args.seed + i,
            lines=len(TEXT_LINES_BY_DOCUMENT[i]),
            min_chars=18,
            max_chars=30,
            text_lines=TEXT_LINES_BY_DOCUMENT[i],
            material=('faded_black' if i % 3 else 'engraved'),
            handwriting_family='01_Original_Handwriting',
            handwriting_style='Original',
            background='provided_document_surface',
            surface_warp=1.0,
            include_signature=True,
            include_seal=(i % 2 == 0),
        )
        for i in range(32)
    ]
    paths = generate_documents(studio, specs, output_dir, backgrounds)
    contact_sheet = output_dir / 'contact_sheet.png'
    _make_contact_sheet(paths, contact_sheet)
    manifest = {
        'status': 'PASS', 'documents': len(paths), 'output_dir': str(output_dir),
        'backgrounds': [str(p) for p in backgrounds], 'seed': args.seed,
        'text_mode': 'explicit_fixed_lines',
    }
    (output_dir / 'generation_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
