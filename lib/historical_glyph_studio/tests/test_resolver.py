"""Tests for GlyphResolver."""

import pytest
import numpy as np
from historical_glyph_studio.glyphs.repository import GlyphRepository
from historical_glyph_studio.glyphs.resolver import GlyphResolver
from historical_glyph_studio.config.models import GlyphSourceConfig


def test_resolver_single_char(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    resolver = GlyphResolver(repo, rng)
    record = resolver.resolve("\U00010350")
    assert record.codepoint == 0x10350


def test_resolver_u_plus_notation(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    resolver = GlyphResolver(repo, rng)
    record = resolver.resolve("U+10350")
    assert record.codepoint == 0x10350


def test_resolver_double_plus_notation(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    resolver = GlyphResolver(repo, rng)
    record = resolver.resolve("U++10350")
    assert record.codepoint == 0x10350


def test_resolver_hex_notation(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    resolver = GlyphResolver(repo, rng)
    record = resolver.resolve("10350")
    assert record.codepoint == 0x10350


def test_resolver_invalid_char(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    resolver = GlyphResolver(repo, rng)
    with pytest.raises(KeyError):
        resolver.resolve("A")  # not in glyph set


def test_resolver_family_selection(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    families = repo.families
    if len(families) < 2:
        pytest.skip("Need at least 2 families for this test")
    resolver = GlyphResolver(repo, rng)
    fam = families[0]
    cfg = GlyphSourceConfig(family=fam, selection_mode="fixed")
    record = resolver.resolve("\U00010350", cfg)
    assert record.family == fam


def test_resolver_random_selection_reproducible(glyph_root):
    repo = GlyphRepository(glyph_root)
    rng1 = np.random.default_rng(99)
    rng2 = np.random.default_rng(99)
    r1 = GlyphResolver(repo, rng1).resolve("\U00010350")
    r2 = GlyphResolver(repo, rng2).resolve("\U00010350")
    assert r1.path == r2.path, "Same seed must produce same result"


def test_resolver_available_families(glyph_root, rng):
    repo = GlyphRepository(glyph_root)
    resolver = GlyphResolver(repo, rng)
    fams = resolver.available_families("\U00010350")
    assert len(fams) >= 1
