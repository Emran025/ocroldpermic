"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
import numpy as np
from pathlib import Path

def _find_glyph_root() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent.parent / "font" / "svg",
        Path(__file__).resolve().parent.parent.parent.parent / "font" / "svg",
        Path(__file__).resolve().parent.parent.parent / "font" / "svg",
        Path("font/svg").resolve(),
        Path("../font/svg").resolve(),
        Path("../../font/svg").resolve(),
    ]
    for p in candidates:
        if p.exists() and list(p.rglob("*.svg")):
            return p
    return candidates[0]

GLYPH_ROOT = _find_glyph_root()


@pytest.fixture(scope="session")
def glyph_root() -> Path:
    """Path to the SVG glyph root directory."""
    if not GLYPH_ROOT.exists():
        pytest.skip(f"Glyph root not found: {GLYPH_ROOT}")
    return GLYPH_ROOT


@pytest.fixture(scope="session")
def studio(glyph_root):
    """A shared GlyphStudio instance for the test session."""
    from historical_glyph_studio import GlyphStudio
    return GlyphStudio(glyph_root=glyph_root, canonical_size=(128, 128))


@pytest.fixture
def rng():
    """A seeded numpy RNG for deterministic tests."""
    return np.random.default_rng(12345)


@pytest.fixture
def sample_char():
    """A well-known Old Permic character."""
    return "\U00010350"


@pytest.fixture
def dummy_mask():
    """A simple synthetic glyph mask (cross shape)."""
    mask = np.zeros((64, 64), dtype=np.float32)
    mask[20:44, 29:35] = 1.0   # vertical bar
    mask[29:35, 10:54] = 1.0   # horizontal bar
    return mask


@pytest.fixture
def dummy_background():
    """A uniform grey background image."""
    return np.full((64, 64, 3), 180, dtype=np.uint8)
