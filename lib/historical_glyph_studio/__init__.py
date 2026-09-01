"""
historical_glyph_studio
=======================

A production-quality Python library for generating synthetic images of
historical writing systems from SVG source artwork.

Quick start::

    from historical_glyph_studio import GlyphStudio

    studio = GlyphStudio(glyph_root="font/svg")
    result = studio.render(
        char="\\U00010350",
        background="stone",
        operation="engraved",
        seed=42,
    )
    # result.image → RGB uint8 numpy array
"""

from .studio import GlyphStudio
from .rendering.pipeline import RenderResult
from .config.models import (
    RenderConfig,
    DatasetConfig,
    EngravingConfig,
    RaisedConfig,
    FadedConfig,
    GlassConfig,
    OcclusionConfig,
    DegradationConfig,
    RotationConfig,
    PerspectiveConfig,
    GlyphSourceConfig,
)
from .annotation.yolo import BoundingBox, YOLOAnnotation
from .export.image import GenerationMetadata

__version__ = "0.1.0"

__all__ = [
    "GlyphStudio",
    "RenderResult",
    "RenderConfig",
    "DatasetConfig",
    "EngravingConfig",
    "RaisedConfig",
    "FadedConfig",
    "GlassConfig",
    "OcclusionConfig",
    "DegradationConfig",
    "RotationConfig",
    "PerspectiveConfig",
    "GlyphSourceConfig",
    "BoundingBox",
    "YOLOAnnotation",
    "GenerationMetadata",
]
