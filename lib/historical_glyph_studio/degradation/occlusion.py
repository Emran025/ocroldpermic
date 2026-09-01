"""
Discriminative-aware occlusion system.

Occludes portions of a glyph mask using blobs (ellipses or irregular polygons)
while protecting highly discriminative regions from complete destruction.

The key invariant:
  Unless `unrestricted=True`, at least one critical discriminative region
  must remain at least partially visible after occlusion.

Algorithm:
  1. Sample N candidate occlusion blobs at random positions/sizes.
  2. For each candidate blob, compute the fraction of critical pixels it covers.
  3. Accept or reject blobs based on discriminative protection constraints.
  4. Apply accepted blobs to the mask.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from typing import Optional, Tuple

from ..config.models import OcclusionConfig, OcclusionLevel
from ..analysis.discriminative import DiscriminativeMap

# Predefined occlusion level → fraction mapping
_LEVEL_FRACTIONS: dict[OcclusionLevel, float] = {
    "none": 0.0,
    "mild": 0.15,
    "moderate": 0.30,
    "severe": 0.50,
    "extreme": 0.70,
}


def _occlusion_fraction(config: OcclusionConfig) -> float:
    if config.custom_fraction is not None:
        return float(np.clip(config.custom_fraction, 0.0, 1.0))
    return _LEVEL_FRACTIONS.get(config.level, 0.3)


def _draw_blob(
    canvas: np.ndarray,
    cy: int,
    cx: int,
    ry: int,
    rx: int,
    angle: float,
    blob_shape: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw a single occlusion blob on a float canvas (0 = occluded)."""
    H, W = canvas.shape
    blob = np.zeros((H, W), dtype=np.uint8)

    if blob_shape == "ellipse" or (blob_shape == "mixed" and rng.random() < 0.5):
        cv2.ellipse(
            blob,
            center=(cx, cy),
            axes=(max(1, rx), max(1, ry)),
            angle=float(angle),
            startAngle=0,
            endAngle=360,
            color=255,
            thickness=-1,
        )
    else:
        # Irregular polygon (approximate with a randomised polygon)
        n_pts = int(rng.integers(5, 9))
        angles = np.sort(rng.uniform(0, 2 * np.pi, n_pts))
        radii_x = rng.uniform(0.6, 1.0, n_pts) * rx
        radii_y = rng.uniform(0.6, 1.0, n_pts) * ry
        pts = np.stack([
            cx + radii_x * np.cos(angles),
            cy + radii_y * np.sin(angles),
        ], axis=1).astype(np.int32)
        cv2.fillPoly(blob, [pts], 255)

    return canvas * (1.0 - blob.astype(np.float32) / 255.0)


def apply_occlusion(
    mask: np.ndarray,
    config: OcclusionConfig,
    rng: np.random.Generator,
    disc_map: Optional[DiscriminativeMap] = None,
) -> np.ndarray:
    """
    Apply discriminative-aware occlusion to a float glyph mask.

    Parameters
    ----------
    mask:
        Float32 (H, W) glyph mask in [0, 1].
    config:
        Occlusion configuration.
    rng:
        Seeded random generator.
    disc_map:
        Optional pre-computed discriminative map at the same spatial resolution
        as *mask*.  If None, occlusion is applied without discriminative protection.

    Returns
    -------
    np.ndarray
        Float32 (H, W) occluded mask.
    """
    if not config.enabled:
        return mask.copy()

    fraction = _occlusion_fraction(config)
    if fraction <= 0:
        return mask.copy()

    H, W = mask.shape
    glyph_area = float((mask > 0.3).sum())
    if glyph_area < 10:
        return mask.copy()

    target_occlude = glyph_area * fraction

    # Resize discriminative map to match mask if needed
    critical_map: Optional[np.ndarray] = None
    if disc_map is not None and config.protect_discriminative and not config.unrestricted:
        dm_score = disc_map.score
        if dm_score.shape != mask.shape:
            from PIL import Image
            pil = Image.fromarray((dm_score * 255).astype(np.uint8))
            pil = pil.resize((W, H), Image.BILINEAR)
            dm_score = np.asarray(pil, dtype=np.float32) / 255.0
        critical_map = (dm_score >= config.discriminative_threshold).astype(np.float32)

    result = mask.copy()
    occluded_area = 0.0
    n_blobs = config.blob_count
    max_attempts = n_blobs * 8

    # Estimate blob size from target fraction
    blob_area_target = target_occlude / n_blobs
    blob_r = max(5, int(np.sqrt(blob_area_target / np.pi)))

    for attempt in range(max_attempts):
        if occluded_area >= target_occlude:
            break

        # Sample blob position within glyph bounding region
        ys, xs = np.where(result > 0.3)
        if len(ys) == 0:
            break
        idx = int(rng.integers(0, len(ys)))
        cy_blob = int(ys[idx])
        cx_blob = int(xs[idx])

        ry = max(3, int(rng.integers(blob_r // 2, blob_r * 2)))
        rx = max(3, int(rng.integers(blob_r // 2, blob_r * 2)))
        angle = float(rng.uniform(0, 180))

        # Check discriminative protection: would this blob destroy all critical regions?
        if critical_map is not None:
            total_critical = float(critical_map.sum())
            if total_critical > 0:
                # Simulate the blob
                test_blob = np.zeros((H, W), dtype=np.float32)
                cv2.ellipse(
                    (test_blob * 255).astype(np.uint8),
                    (cx_blob, cy_blob),
                    (rx, ry),
                    angle, 0, 360, 255, -1,
                )
                test_blob_mask = np.zeros((H, W), dtype=np.uint8)
                cv2.ellipse(test_blob_mask, (cx_blob, cy_blob), (rx, ry), angle, 0, 360, 255, -1)
                test_blob_f = test_blob_mask.astype(np.float32) / 255.0

                surviving_critical = float(
                    (critical_map * result * (1 - test_blob_f)).sum()
                )
                required_critical = float(
                    (critical_map * result).sum()
                )
                # Reject if this blob would erase > 80% of remaining critical area
                if required_critical > 0 and surviving_critical < required_critical * 0.2:
                    continue

        new_result = _draw_blob(result, cy_blob, cx_blob, ry, rx, angle,
                                 config.blob_shape, rng)
        newly_occluded = float(
            ((result > 0.3).astype(float) - (new_result > 0.3).astype(float)).clip(0).sum()
        )
        result = new_result
        occluded_area += newly_occluded

    return result.astype(np.float32)
