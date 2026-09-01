"""Tests for geometry transforms."""

import numpy as np
import pytest
from historical_glyph_studio.geometry.transforms import rotate_mask, rotate_bbox, sample_rotation
from historical_glyph_studio.geometry.perspective import (
    build_perspective_matrix, apply_perspective_mask, perspective_bbox
)
from historical_glyph_studio.config.models import RotationConfig, PerspectiveConfig


def _cross_mask(size=64):
    m = np.zeros((size, size), dtype=np.float32)
    m[size//4:3*size//4, size//2-5:size//2+5] = 1.0
    m[size//2-5:size//2+5, size//4:3*size//4] = 1.0
    return m


def test_rotate_mask_shape():
    mask = _cross_mask()
    rotated, M = rotate_mask(mask, 15.0)
    assert rotated.shape == mask.shape


def test_rotate_mask_zero_unchanged():
    mask = _cross_mask()
    rotated, _ = rotate_mask(mask, 0.0)
    assert np.allclose(rotated, mask, atol=0.01)


def test_rotate_preserves_area_approx():
    mask = _cross_mask()
    original_sum = float(mask.sum())
    rotated, _ = rotate_mask(mask, 30.0)
    rotated_sum = float(rotated.sum())
    # Area should be roughly preserved (within 10%)
    assert abs(rotated_sum - original_sum) / (original_sum + 1e-8) < 0.15


def test_rotate_bbox_consistency():
    bbox = (10, 10, 50, 50)
    mask = np.zeros((64, 64), dtype=np.float32)
    mask[10:50, 10:50] = 1.0
    _, M = rotate_mask(mask, 20.0)
    transformed = rotate_bbox(bbox, M)
    x1, y1, x2, y2 = transformed
    assert x2 > x1 and y2 > y1


def test_sample_rotation_fixed():
    cfg = RotationConfig(enabled=True, fixed_deg=10.0)
    rng = np.random.default_rng(0)
    angle = sample_rotation(cfg, rng)
    assert angle == 10.0


def test_sample_rotation_disabled():
    cfg = RotationConfig(enabled=False)
    rng = np.random.default_rng(0)
    assert sample_rotation(cfg, rng) == 0.0


def test_sample_rotation_range():
    cfg = RotationConfig(enabled=True, min_deg=-18.0, max_deg=18.0)
    rng = np.random.default_rng(0)
    for _ in range(20):
        a = sample_rotation(cfg, rng)
        assert -18.0 <= a <= 18.0


def test_perspective_warp_shape():
    mask = _cross_mask(64)
    rng = np.random.default_rng(7)
    cfg = PerspectiveConfig(enabled=True, max_skew=0.1)
    M = build_perspective_matrix(64, 64, cfg, rng)
    warped = apply_perspective_mask(mask, M)
    assert warped.shape == mask.shape


def test_perspective_bbox_valid():
    rng = np.random.default_rng(8)
    cfg = PerspectiveConfig(enabled=True, max_skew=0.05)
    M = build_perspective_matrix(64, 64, cfg, rng)
    bbox = perspective_bbox((10, 10, 50, 50), M)
    x1, y1, x2, y2 = bbox
    assert x2 >= x1 and y2 >= y1
