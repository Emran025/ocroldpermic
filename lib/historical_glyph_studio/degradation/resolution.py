"""
Resolution degradation pipeline.

Applied as the FINAL stage after all rendering, composition, and annotation
geometry are established.  Simulates low-resolution scans, old photographs,
JPEG artefacts, and sensor noise without corrupting the annotation geometry.

Important: annotations must be computed BEFORE calling this module, using the
logical (pre-degradation) image dimensions.
"""

from __future__ import annotations

import io
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..config.models import DegradationConfig


def apply_resolution_degradation(
    image: np.ndarray,
    config: DegradationConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Apply final-stage resolution and quality degradation.

    Parameters
    ----------
    image:
        RGB uint8 (H, W, 3) — full-resolution rendered image.
    config:
        DegradationConfig with resolution_scale, noise settings, etc.
    rng:
        Seeded random generator.

    Returns
    -------
    np.ndarray
        Degraded RGB uint8 image.  The SPATIAL DIMENSIONS may be smaller
        than the input if resolution_scale < 1.0.
    """
    result = image.copy()
    H, W = result.shape[:2]

    # 1. Blur before downscale (anti-aliasing + soft focus)
    if config.blur_sigma > 0:
        result = cv2.GaussianBlur(result, (0, 0), config.blur_sigma)

    # 2. Resolution downscaling
    scale = float(np.clip(config.resolution_scale, 0.05, 1.0))
    if scale < 0.99:
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        # Downscale with AREA interpolation (best quality for downsampling)
        result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 3. Sensor noise (Gaussian)
    if config.add_noise and config.noise_stddev > 0:
        noise = rng.normal(0, config.noise_stddev, result.shape).astype(np.float32)
        result = np.clip(result.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # 4. JPEG compression artefacts
    if config.jpeg_quality is not None:
        quality = int(np.clip(config.jpeg_quality, 1, 95))
        pil = Image.fromarray(result)
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        result = np.asarray(Image.open(buf), dtype=np.uint8)

    return result


def scale_bbox_for_degradation(
    bbox_xyxy: tuple[int, int, int, int],
    resolution_scale: float,
) -> tuple[int, int, int, int]:
    """
    Scale an annotation bounding box to match the degraded image resolution.

    Call this AFTER apply_resolution_degradation to adjust the bbox.
    """
    s = float(resolution_scale)
    x1, y1, x2, y2 = bbox_xyxy
    return (
        int(x1 * s),
        int(y1 * s),
        int(x2 * s),
        int(y2 * s),
    )
