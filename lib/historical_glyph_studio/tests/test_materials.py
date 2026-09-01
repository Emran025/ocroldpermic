"""Tests for all material renderers."""

import pytest
import numpy as np
from historical_glyph_studio.materials import get_material
from historical_glyph_studio.config.models import (
    EngravingConfig, RaisedConfig, FadedConfig, GlassConfig
)


def _make_mask(size=64):
    """Create a simple cross-shaped mask."""
    m = np.zeros((size, size), dtype=np.float32)
    m[size//4:3*size//4, size//2-4:size//2+4] = 1.0
    m[size//2-4:size//2+4, size//4:3*size//4] = 1.0
    return m


def _make_bg(size=64):
    return np.full((size, size, 3), 180, dtype=np.uint8)


@pytest.fixture
def mask():
    return _make_mask()


@pytest.fixture
def background():
    return _make_bg()


@pytest.fixture
def rng_local():
    return np.random.default_rng(42)


# ------------------------------------------------------------------
# Engraved
# ------------------------------------------------------------------

def test_engraved_output_shape(mask, background, rng_local):
    mat = get_material("engraved")
    result = mat.apply(mask, background, rng_local, config=EngravingConfig())
    assert result.shape == background.shape
    assert result.dtype == np.uint8


def test_engraved_darkens_interior(mask, background, rng_local):
    """
    Regression test: engraving must produce actual depth variation inside the glyph.
    The interior of the carved region should be darker than the surrounding surface.
    """
    mat = get_material("engraved")
    cfg = EngravingConfig(depth=1.5, shadow_strength=0.8)
    result = mat.apply(mask, background, rng_local, config=cfg)

    glyph_pixels = result[mask > 0.5]
    non_glyph_pixels = result[mask < 0.1]

    mean_interior = float(glyph_pixels.mean())
    mean_background = float(non_glyph_pixels.mean())
    assert mean_interior < mean_background, (
        f"Engraved interior ({mean_interior:.1f}) should be darker "
        f"than background ({mean_background:.1f})"
    )


def test_engraved_interior_has_variation(mask, background, rng_local):
    """The interior must show spatial variation — not a flat single value."""
    mat = get_material("engraved")
    result = mat.apply(mask, background, rng_local, config=EngravingConfig(depth=1.2))
    interior = result[mask > 0.5].astype(float)
    assert interior.std() > 1.0, "Engraved interior must have per-pixel variation"


# ------------------------------------------------------------------
# Raised
# ------------------------------------------------------------------

def test_raised_output_shape(mask, background, rng_local):
    mat = get_material("raised")
    result = mat.apply(mask, background, rng_local, config=RaisedConfig())
    assert result.shape == background.shape


def test_raised_brightens_interior(mask, background, rng_local):
    mat = get_material("raised")
    result = mat.apply(mask, background, rng_local, config=RaisedConfig(
        highlight_strength=0.8, height=1.5
    ))
    interior = float(result[mask > 0.5].mean())
    bg_mean = float(background.mean())
    assert interior > bg_mean * 0.9, "Raised surface should not significantly darken interior"


# ------------------------------------------------------------------
# Faded
# ------------------------------------------------------------------

def test_faded_black_uses_full_interior(mask, background, rng_local):
    """
    The full body of the glyph must be present — not just an outline.
    Erode the mask; core pixels must also be affected.
    """
    mat = get_material("faded_black")
    cfg = FadedConfig(color=(0, 0, 0), opacity=0.6, blur_sigma=0.0, density_noise=0.0)
    result = mat.apply(mask, background, rng_local, config=cfg)

    from scipy.ndimage import binary_erosion
    core = binary_erosion(mask > 0.5, iterations=4)
    if not core.any():
        pytest.skip("Mask too small for core erosion test")

    core_diff = background[core].astype(float) - result[core].astype(float)
    assert core_diff.mean() > 5.0, "Faded black: core pixels should be darkened"


def test_faded_white(mask, background, rng_local):
    mat = get_material("faded_white")
    cfg = FadedConfig(color=(255, 255, 255), opacity=0.5)
    result = mat.apply(mask, background, rng_local, config=cfg)
    assert result.shape == background.shape
    interior = float(result[mask > 0.5].mean())
    assert interior > float(background[mask > 0.5].mean()), "Faded white should brighten interior"


# ------------------------------------------------------------------
# Glass
# ------------------------------------------------------------------

def test_glass_output_shape(mask, background, rng_local):
    mat = get_material("glass")
    result = mat.apply(mask, background, rng_local, config=GlassConfig())
    assert result.shape == background.shape


def test_glass_interior_contributes(mask, background, rng_local):
    """
    Critical regression test: glass must alter pixels INSIDE the glyph, not
    just at its outline.  The eroded core of the glyph must differ from the
    background.
    """
    from scipy.ndimage import binary_erosion
    mat = get_material("glass")
    cfg = GlassConfig(refraction_strength=5.0, fresnel_strength=0.5, interior_variation=0.3)
    result = mat.apply(mask, background, rng_local, config=cfg)

    core = binary_erosion(mask > 0.5, iterations=3)
    if not core.any():
        pytest.skip("Mask core too small")

    core_diff = np.abs(result[core].astype(float) - background[core].astype(float))
    assert core_diff.mean() > 1.0, (
        "Glass: interior core must differ from original background "
        "(refraction/caustic must reach the interior)"
    )


def test_glass_not_outline_only(mask, background, rng_local):
    """Edge pixels should NOT account for all glass effect."""
    from scipy.ndimage import binary_erosion, binary_dilation
    mat = get_material("glass")
    result = mat.apply(mask, background, rng_local, config=GlassConfig(refraction_strength=4.0))

    binary = mask > 0.5
    edge = binary_dilation(binary) & ~binary_erosion(binary, iterations=2)
    interior = binary_erosion(binary, iterations=3)

    if not interior.any():
        pytest.skip("No interior pixels available")

    interior_change = np.abs(result[interior].astype(float) - background[interior].astype(float)).mean()
    edge_change = np.abs(result[edge].astype(float) - background[edge].astype(float)).mean()

    # Interior change should be meaningfully non-zero (>10% of edge change)
    assert interior_change > edge_change * 0.1, \
        f"Interior change ({interior_change:.2f}) too small vs edge change ({edge_change:.2f})"
