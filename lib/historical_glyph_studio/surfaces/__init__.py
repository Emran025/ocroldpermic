"""Surfaces package + background factory."""
from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

from .base import Background
from .solid import SolidBackground
from .image import ImageBackground
from .procedural import ProceduralBackground, SurfaceType

BackgroundSpec = Union[
    tuple,          # RGB or RGBA color
    str,            # file path or surface name
    Path,           # file path
    np.ndarray,     # numpy array
    Image.Image,    # PIL image
]


def make_background(spec: BackgroundSpec) -> Background:
    """
    Factory that converts any background specification into a Background object.

    Accepted *spec* values:
      - ``(R, G, B)`` or ``(R, G, B, A)`` tuple → SolidBackground
      - ``'stone'``, ``'paper'``, ``'wood'`` etc. → ProceduralBackground
      - File path string / Path → ImageBackground
      - PIL Image → ImageBackground
      - NumPy array → ImageBackground
    """
    _SURFACE_NAMES = {"stone", "paper", "wood", "sand", "plaster", "metal"}

    if isinstance(spec, tuple):
        rgb = spec[:3]
        return SolidBackground(color=(int(rgb[0]), int(rgb[1]), int(rgb[2])))

    if isinstance(spec, str):
        if spec in _SURFACE_NAMES:
            return ProceduralBackground(surface=spec)  # type: ignore[arg-type]
        # Treat as file path
        return ImageBackground(source=Path(spec))

    if isinstance(spec, Path):
        return ImageBackground(source=spec)

    if isinstance(spec, np.ndarray):
        return ImageBackground(source=spec)

    if isinstance(spec, Image.Image):
        return ImageBackground(source=spec)

    raise TypeError(
        f"Cannot create Background from type {type(spec).__name__!r}. "
        "Expected: tuple, str, Path, np.ndarray, or PIL.Image."
    )


__all__ = [
    "Background",
    "SolidBackground",
    "ImageBackground",
    "ProceduralBackground",
    "make_background",
    "SurfaceType",
    "BackgroundSpec",
]
