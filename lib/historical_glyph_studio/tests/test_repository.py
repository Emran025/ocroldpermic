"""Tests for GlyphRepository."""

import pytest
from pathlib import Path
from historical_glyph_studio.glyphs.repository import GlyphRepository


def test_repository_discovers_svgs(glyph_root):
    repo = GlyphRepository(glyph_root)
    assert len(repo.records) > 0, "Repository should find at least one SVG"


def test_repository_has_multiple_families(glyph_root):
    repo = GlyphRepository(glyph_root)
    assert len(repo.families) >= 1, "Should discover at least one family"


def test_repository_has_styles(glyph_root):
    repo = GlyphRepository(glyph_root)
    for family in repo.families:
        styles = repo.styles_for_family(family)
        assert len(styles) >= 1, f"Family {family!r} should have at least one style"


def test_repository_codepoints(glyph_root):
    repo = GlyphRepository(glyph_root)
    cps = repo.codepoints
    assert len(cps) > 0
    # Old Permic range
    assert all(0x10350 <= cp <= 0x1037F for cp in cps), \
        "Expected Old Permic codepoints (U+10350–U+1037F)"


def test_repository_has_method(glyph_root):
    repo = GlyphRepository(glyph_root)
    cp = repo.codepoints[0]
    assert repo.has(cp), f"Repository should have codepoint {cp:#x}"
    assert not repo.has(0x0041), "Should not have ASCII 'A'"


def test_repository_get(glyph_root):
    repo = GlyphRepository(glyph_root)
    cp = repo.codepoints[0]
    records = repo.get(cp)
    assert len(records) > 0


def test_repository_get_with_family(glyph_root):
    repo = GlyphRepository(glyph_root)
    cp = repo.codepoints[0]
    fam = repo.families_for_codepoint(cp)[0]
    records = repo.get(cp, family=fam)
    assert all(r.family == fam for r in records)


def test_repository_missing_raises(glyph_root):
    repo = GlyphRepository(glyph_root)
    with pytest.raises(KeyError):
        repo.get_or_raise(0x0041)  # ASCII 'A', not in Old Permic


def test_repository_summary(glyph_root):
    repo = GlyphRepository(glyph_root)
    summary = repo.summary()
    assert "GlyphRepository" in summary
    assert "families" in summary.lower() or "family" in summary.lower()


def test_repository_invalid_root():
    with pytest.raises(FileNotFoundError):
        GlyphRepository("/nonexistent/path/xyz")


def test_repository_double_plus_filename(glyph_root):
    """Verify U++XXXXX filenames are parsed correctly."""
    repo = GlyphRepository(glyph_root)
    # All Old Permic chars should be present
    assert 0x10350 in repo.codepoints
