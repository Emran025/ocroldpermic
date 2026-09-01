"""Tests for SVG rasterizer and GlyphNormalizer."""

import pytest
import numpy as np
from historical_glyph_studio.glyphs.rasterizer import SVGRasterizer
from historical_glyph_studio.glyphs.normalization import GlyphNormalizer
from historical_glyph_studio.glyphs.repository import GlyphRepository
from historical_glyph_studio.glyphs.svg_loader import load_svg


def test_svg_load(glyph_root):
    repo = GlyphRepository(glyph_root)
    record = repo.get(0x10350)[0]
    doc = load_svg(record.path)
    assert doc.natural_width_pt > 0
    assert doc.natural_height_pt > 0
    assert len(doc.raw_bytes) > 0


def test_rasterizer_produces_rgba(glyph_root):
    repo = GlyphRepository(glyph_root)
    record = repo.get(0x10350)[0]
    from historical_glyph_studio.glyphs.svg_loader import load_svg
    doc = load_svg(record.path)
    rasterizer = SVGRasterizer()
    arr = rasterizer.rasterize(doc, 128, 128)
    assert arr.shape == (128, 128, 4), f"Expected (128,128,4), got {arr.shape}"
    assert arr.dtype == np.uint8


def test_normalizer_produces_float_mask(glyph_root):
    repo = GlyphRepository(glyph_root)
    record = repo.get(0x10350)[0]
    norm = GlyphNormalizer(canonical_size=(128, 128))
    gm = norm.normalize(record)
    assert gm.mask.dtype == np.float32
    assert gm.mask.min() >= 0.0
    assert gm.mask.max() <= 1.0
    assert gm.mask.max() > 0.01, "Mask should have non-zero pixels"


def test_normalizer_glyph_is_not_outline_only(glyph_root):
    """The full interior of the glyph should have non-zero mask values."""
    repo = GlyphRepository(glyph_root)
    record = repo.get(0x10350)[0]
    norm = GlyphNormalizer(canonical_size=(128, 128))
    gm = norm.normalize(record)
    mask = gm.mask
    # Count interior pixels (not just edge)
    from scipy.ndimage import binary_erosion
    core = binary_erosion(mask > 0.3, iterations=3)
    assert core.sum() > 0, "Glyph mask interior (eroded core) should be non-zero"


def test_normalizer_tight_bbox(glyph_root):
    repo = GlyphRepository(glyph_root)
    record = repo.get(0x10350)[0]
    norm = GlyphNormalizer(canonical_size=(128, 128))
    gm = norm.normalize(record)
    x, y, w, h = gm.tight_bbox
    assert w > 0 and h > 0


def test_normalizer_cache(glyph_root):
    repo = GlyphRepository(glyph_root)
    record = repo.get(0x10350)[0]
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    gm1 = norm.normalize(record)
    gm2 = norm.normalize(record)
    assert gm1 is gm2, "Second call should return cached object"


def test_normalizer_all_chars(glyph_root):
    """All discovered codepoints should rasterize successfully."""
    repo = GlyphRepository(glyph_root)
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    failures = []
    for cp in repo.codepoints:
        record = repo.get(cp)[0]
        try:
            gm = norm.normalize(record)
            assert gm.mask.max() > 0.01
        except Exception as e:
            failures.append((cp, str(e)))
    assert len(failures) == 0, f"Rasterization failures: {failures}"
