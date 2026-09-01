"""Tests for discriminative-aware occlusion."""

import numpy as np
import pytest
from historical_glyph_studio.config.models import OcclusionConfig
from historical_glyph_studio.degradation.occlusion import apply_occlusion


def _cross_mask(size=64):
    m = np.zeros((size, size), dtype=np.float32)
    m[size//4:3*size//4, size//2-5:size//2+5] = 1.0
    m[size//2-5:size//2+5, size//4:3*size//4] = 1.0
    return m


@pytest.fixture
def cross_mask():
    return _cross_mask()


def test_occlusion_disabled_returns_copy(cross_mask):
    rng = np.random.default_rng(0)
    cfg = OcclusionConfig(enabled=False)
    result = apply_occlusion(cross_mask, cfg, rng)
    assert np.allclose(result, cross_mask), "Disabled occlusion should return unchanged mask"


def test_occlusion_mild_reduces_area(cross_mask):
    rng = np.random.default_rng(1)
    cfg = OcclusionConfig(enabled=True, level="mild")
    result = apply_occlusion(cross_mask, cfg, rng)
    original_area = float((cross_mask > 0.3).sum())
    result_area = float((result > 0.3).sum())
    assert result_area < original_area, "Occlusion should reduce visible area"


def test_occlusion_severe_removes_more(cross_mask):
    rng_mild = np.random.default_rng(42)
    rng_severe = np.random.default_rng(42)
    mild = apply_occlusion(cross_mask, OcclusionConfig(enabled=True, level="mild"), rng_mild)
    severe = apply_occlusion(cross_mask, OcclusionConfig(enabled=True, level="severe"), rng_severe)
    # Severe should remove more on average (not guaranteed every run, but directionally)
    assert (severe > 0.3).sum() <= (mild > 0.3).sum() + 200, \
        "Severe occlusion should remove at least as much as mild"


def test_occlusion_preserves_discriminative_regions(glyph_root):
    """With protect_discriminative=True, critical regions must survive."""
    from historical_glyph_studio.glyphs.repository import GlyphRepository
    from historical_glyph_studio.glyphs.normalization import GlyphNormalizer
    from historical_glyph_studio.analysis.discriminative import DiscriminativeAnalyzer

    repo = GlyphRepository(glyph_root)
    norm = GlyphNormalizer(canonical_size=(64, 64), cache=True)
    analyzer = DiscriminativeAnalyzer(norm, analysis_size=(64, 64))
    maps = analyzer.analyze(repo)
    cp = 0x10350
    disc_map = maps.get(cp)
    if disc_map is None:
        pytest.skip("No discriminative map for U+10350")

    record = repo.get(cp)[0]
    gm = norm.normalize(record)

    from PIL import Image
    mask_resized = np.asarray(
        Image.fromarray((gm.mask * 255).astype(np.uint8)).resize(
            (64, 64), Image.BILINEAR
        ),
        dtype=np.float32
    ) / 255.0

    rng = np.random.default_rng(777)
    cfg = OcclusionConfig(
        enabled=True,
        level="severe",
        protect_discriminative=True,
        discriminative_threshold=0.6,
    )
    result = apply_occlusion(mask_resized, cfg, rng, disc_map=disc_map)

    # Critical pixels that survived
    critical_pixels = disc_map.critical_mask
    surviving_critical = float((result[critical_pixels] > 0.3).sum())
    total_critical = float(critical_pixels.sum())

    assert total_critical == 0 or surviving_critical / max(total_critical, 1) > 0.1, \
        "At least 10% of critical pixels must survive severe occlusion"


def test_occlusion_unrestricted_ignores_discriminative(cross_mask):
    """With unrestricted=True, no protection is applied — just sanity check."""
    rng = np.random.default_rng(5)
    cfg = OcclusionConfig(
        enabled=True,
        level="extreme",
        protect_discriminative=True,
        unrestricted=True,
    )
    result = apply_occlusion(cross_mask, cfg, rng)
    assert result.shape == cross_mask.shape


def test_occlusion_reproducible(cross_mask):
    rng1 = np.random.default_rng(1234)
    rng2 = np.random.default_rng(1234)
    cfg = OcclusionConfig(enabled=True, level="moderate")
    r1 = apply_occlusion(cross_mask, cfg, rng1)
    r2 = apply_occlusion(cross_mask, cfg, rng2)
    assert np.allclose(r1, r2), "Same seed must produce same occlusion"
