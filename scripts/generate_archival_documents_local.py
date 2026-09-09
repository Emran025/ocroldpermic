#!/usr/bin/env python3
"""Generate the 32 archival manuscript images locally.

Run from the repository root:
    python scripts/generate_archival_documents_local.py

DOCUMENT_##_LINES below contain real Old Permic Unicode text extracted from the
written-komi-corpus-old-komi repository; edit them to choose other corpus passages. Each document must contain exactly 14 lines. The script writes PNG, YOLO
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
# Source: https://github.com/langdoc/written-komi-corpus-old-komi (old_komi.conllu)
# Document 01 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_01_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 02 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_02_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 03 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_03_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 04 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_04_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 05 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_05_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 06 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_06_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 07 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_07_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 08 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_08_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 09 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_09_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 10 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_10_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 11 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_11_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 12 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_12_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 13 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_13_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 14 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_14_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 15 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_15_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 16 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_16_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 17 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_17_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 18 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_18_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 19 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_19_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 20 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_20_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 21 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_21_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 22 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_22_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 23 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_23_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 24 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_24_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 25 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_25_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 26 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_26_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 27 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_27_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 28 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_28_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 29 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_29_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 30 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_30_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 31 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_31_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
]

# Document 32 — real Old Permic Unicode text from written-komi-corpus-old-komi
DOCUMENT_32_LINES = [
    '𐍜𐍗𐍔𐍙𐍡𐍡𐍚𐍡𐍔𐍝𐍛𐍝𐍩𐍟𐍙𐍜𐍯𐍛𐍯𐍥𐍢𐍯𐍜𐍔',
    '𐍝𐍩𐍚𐍠𐍔𐍚𐍐𐍜𐍩𐍠𐍢𐍩𐍡𐍮𐍐𐍥𐍣𐍚𐍩𐍡𐍐𐍜𐍝𐍙',
    '𐍚𐍯𐍛𐍓𐍯𐍥𐍔𐍣',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
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
