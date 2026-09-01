"""Image-file-based background — loads an external photo or PIL image."""
from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

from .base import Background


class ImageBackground(Background):
    """
    Background from a file path, PIL image, or numpy array.

    The image is cropped/resized to fit the canvas without distortion.
    A random crop is used so that every call (with a different RNG state)
    may yield a different region of the source image.
    """

    def __init__(self, source: Union[str, Path, Image.Image, np.ndarray]) -> None:
        if isinstance(source, (str, Path)):
            self._pil = Image.open(source).convert("RGB")
        elif isinstance(source, np.ndarray):
            self._pil = Image.fromarray(
                source if source.ndim == 3 else np.stack([source] * 3, axis=-1)
            ).convert("RGB")
        elif isinstance(source, Image.Image):
            self._pil = source.convert("RGB")
        else:
            raise TypeError(f"Unsupported background source type: {type(source)}")

    def get(self, width: int, height: int, rng: np.random.Generator) -> np.ndarray:
        src = self._pil
        sw, sh = src.size

        # Scale so that the source covers the canvas
        scale = max(width / sw, height / sh)
        nw = max(int(sw * scale), width)
        nh = max(int(sh * scale), height)
        if (nw, nh) != (sw, sh):
            src = src.resize((nw, nh), Image.LANCZOS)

        # Random crop
        max_dx = nw - width
        max_dy = nh - height
        ox = int(rng.integers(0, max_dx + 1))
        oy = int(rng.integers(0, max_dy + 1))
        crop = src.crop((ox, oy, ox + width, oy + height))
        return np.asarray(crop, dtype=np.uint8)
