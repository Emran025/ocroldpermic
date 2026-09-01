"""Tests for discriminative analysis."""

import numpy as np
import pytest
from historical_glyph_studio.analysis.discriminative import DiscriminativeAnalyzer
from historical_glyph_studio.analysis.skeleton import compute_skeleton, skeleton_density_map
from historical_glyph_studio.glyphs.normalization import GlyphNormalizer
from historical_glyph_studio.glyphs.repository import GlyphRepository


def test_skeleton_nonempty(dummy_mask):
    skel = compute_skeleton(dummy_mask)
    assert skel.any(), "Skeleton of a cross mask should be non-empty"


def test_skeleton_density_map(dummy_mask):
    density = skeleton_density_map(dummy_mask)
    assert density.shape == dummy_mask.shape
    assert density.min() >= 0.0
    assert density.max() <= 1.0
    assert density.max() > 0


def test_discriminative_maps_computed(glyph_root):
    repo = GlyphRepository(glyph_root)
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    analyzer = DiscriminativeAnalyzer(norm, analysis_size=(64, 64))
    maps = analyzer.analyze(repo)
    assert len(maps) > 0, "Should compute at least one discriminative map"


def test_discriminative_map_values(glyph_root):
    repo = GlyphRepository(glyph_root)
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    analyzer = DiscriminativeAnalyzer(norm, analysis_size=(64, 64))
    maps = analyzer.analyze(repo)
    for cp, dm in maps.items():
        assert dm.score.min() >= 0.0, f"U+{cp:04X}: score should be >= 0"
        assert dm.score.max() <= 1.0, f"U+{cp:04X}: score should be <= 1"
        assert dm.score.max() > 0.0, f"U+{cp:04X}: score should have non-zero values"


def test_discriminative_cached(glyph_root):
    repo = GlyphRepository(glyph_root)
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    analyzer = DiscriminativeAnalyzer(norm, analysis_size=(64, 64))
    maps1 = analyzer.analyze(repo)
    maps2 = analyzer.analyze(repo)
    assert maps1 is maps2 or set(maps1.keys()) == set(maps2.keys()), \
        "Second call should return cached maps"


def test_critical_mask_nonempty(glyph_root):
    repo = GlyphRepository(glyph_root)
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    analyzer = DiscriminativeAnalyzer(norm, analysis_size=(64, 64))
    maps = analyzer.analyze(repo)
    # At least one character should have critical regions
    has_critical = any(dm.critical_mask.any() for dm in maps.values())
    assert has_critical, "At least one character should have critical discriminative regions"
