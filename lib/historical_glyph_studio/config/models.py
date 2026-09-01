"""
historical_glyph_studio — Config models.

All configuration objects are plain dataclasses (no external validation library
dependency). Range validation is handled in config/validation.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional, Sequence, Tuple, Union

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

RGBColor = Tuple[int, int, int]
RGBAColor = Tuple[int, int, int, int]
ColorSpec = Union[RGBColor, RGBAColor]
BackgroundSpec = Union[ColorSpec, str, Path, "np.ndarray", "PIL.Image.Image"]  # noqa: F821

OcclusionLevel = Literal["none", "mild", "moderate", "severe", "extreme"]
MaterialName = Literal["engraved", "raised", "faded_black", "faded_white", "glass", "random"]
SelectionMode = Literal["random", "weighted", "fixed"]


# ---------------------------------------------------------------------------
# Glyph source selection
# ---------------------------------------------------------------------------


@dataclass
class GlyphSourceConfig:
    """Controls how a glyph's SVG source is selected."""

    family: Optional[str] = None
    """Exact family name, e.g. '01_Original_Handwriting'. None → auto-select."""

    style: Optional[str] = None
    """Exact style name, e.g. 'Bold'. None → auto-select."""

    selection_mode: SelectionMode = "random"
    """How to pick among available sources when family/style are not fixed."""

    family_weights: Optional[dict[str, float]] = None
    """Optional per-family sampling weight for 'weighted' mode."""


# ---------------------------------------------------------------------------
# Rotation / geometric config
# ---------------------------------------------------------------------------


@dataclass
class RotationConfig:
    """Rotation parameters."""

    enabled: bool = True
    min_deg: float = -18.0
    max_deg: float = 18.0
    fixed_deg: Optional[float] = None
    """If set, always rotate by this exact angle."""


@dataclass
class PerspectiveConfig:
    """Perspective / warp parameters."""

    enabled: bool = False
    max_skew: float = 0.08
    """Maximum fractional skew applied to corners (0 → no perspective)."""
    keystone_strength: float = 0.05
    local_warp_strength: float = 0.0
    """Thin-plate-spline local warp amplitude (0 = disabled)."""


# ---------------------------------------------------------------------------
# Material configs
# ---------------------------------------------------------------------------


@dataclass
class EngravingConfig:
    depth: float = 1.0
    """Normalized cavity depth (0–2)."""
    edge_sharpness: float = 0.5
    shadow_strength: float = 0.6
    highlight_strength: float = 0.35
    light_direction: Tuple[float, float] = (-1.0, -1.0)
    """(dx, dy) unnormalized light direction vector."""
    light_softness: float = 2.0
    """Sigma of normal-map smoothing."""
    surface_roughness: float = 0.05
    irregularity: float = 0.1


@dataclass
class RaisedConfig:
    height: float = 1.0
    edge_softness: float = 1.0
    shadow_strength: float = 0.4
    highlight_strength: float = 0.5
    light_direction: Tuple[float, float] = (-1.0, -1.0)
    light_softness: float = 2.0
    irregularity: float = 0.08


@dataclass
class FadedConfig:
    color: RGBColor = (0, 0, 0)
    opacity: float = 0.35
    """0 → invisible, 1 → fully opaque."""
    blur_sigma: float = 0.8
    density_noise: float = 0.15
    """Stddev of per-pixel density noise."""
    local_fading: float = 0.0
    """Amount of nonuniform fading gradient across the glyph."""


@dataclass
class GlassConfig:
    refraction_strength: float = 3.0
    """Pixel displacement amplitude."""
    transparency: float = 0.25
    fresnel_strength: float = 0.4
    highlight_softness: float = 2.0
    interior_variation: float = 0.12
    thickness_scale: float = 1.0


# ---------------------------------------------------------------------------
# Degradation / occlusion
# ---------------------------------------------------------------------------


@dataclass
class OcclusionConfig:
    enabled: bool = False
    level: OcclusionLevel = "moderate"
    """Predefined level or use custom_fraction."""
    custom_fraction: Optional[float] = None
    """Override fraction of glyph area to occlude (0–1)."""
    protect_discriminative: bool = True
    """If True, avoid occluding highly discriminative regions."""
    discriminative_threshold: float = 0.6
    """Score above which a region is considered 'critical'."""
    unrestricted: bool = False
    """If True, ignore discriminative protection."""
    blob_count: int = 3
    blob_shape: Literal["ellipse", "polygon", "mixed"] = "mixed"


@dataclass
class DegradationConfig:
    blur_sigma: float = 0.0
    erosion_iterations: int = 0
    fading_alpha: float = 0.0
    resolution_scale: float = 1.0
    """1.0 = no downscaling; 0.5 = half resolution."""
    add_noise: bool = False
    noise_stddev: float = 5.0
    jpeg_quality: Optional[int] = None
    """If set, simulate JPEG compression at this quality (1–95)."""


# ---------------------------------------------------------------------------
# Top-level render config
# ---------------------------------------------------------------------------


@dataclass
class RenderConfig:
    """Complete configuration for a single render call."""

    # Glyph
    char: str = ""
    source: GlyphSourceConfig = field(default_factory=GlyphSourceConfig)

    # Canvas
    canvas_size: Tuple[int, int] = (512, 512)
    """(width, height) of the output image before resolution scaling."""
    glyph_scale: float = 0.6
    """Glyph occupies this fraction of the shorter canvas dimension."""

    # Material
    material: MaterialName = "engraved"
    color: RGBColor = (40, 40, 40)

    # Geometry
    rotation: RotationConfig = field(default_factory=RotationConfig)
    perspective: PerspectiveConfig = field(default_factory=PerspectiveConfig)

    # Material params
    engraving: EngravingConfig = field(default_factory=EngravingConfig)
    raised: RaisedConfig = field(default_factory=RaisedConfig)
    faded: FadedConfig = field(default_factory=FadedConfig)
    glass: GlassConfig = field(default_factory=GlassConfig)

    # Degradation
    occlusion: OcclusionConfig = field(default_factory=OcclusionConfig)
    degradation: DegradationConfig = field(default_factory=DegradationConfig)

    # Reproducibility
    seed: Optional[int] = None

    # Output
    emit_metadata: bool = True
    emit_yolo: bool = True


# ---------------------------------------------------------------------------
# Batch dataset config
# ---------------------------------------------------------------------------


@dataclass
class DatasetConfig:
    """Configuration for batch dataset generation."""

    chars: Sequence[str] = field(default_factory=list)
    count: int = 100
    output_dir: Union[str, Path] = "dataset"
    balanced: bool = True
    """Balance class distribution across chars."""
    char_weights: Optional[dict[str, float]] = None

    # Per-sample overrides / ranges
    materials: Sequence[MaterialName] = field(
        default_factory=lambda: ["engraved", "raised", "faded_black", "faded_white", "glass"]
    )
    material_selection: SelectionMode = "random"

    canvas_size: Tuple[int, int] = (512, 512)
    glyph_scale_range: Tuple[float, float] = (0.4, 0.7)

    rotation: RotationConfig = field(default_factory=RotationConfig)
    perspective: PerspectiveConfig = field(default_factory=lambda: PerspectiveConfig(enabled=True))
    occlusion: OcclusionConfig = field(
        default_factory=lambda: OcclusionConfig(enabled=True, level="moderate")
    )
    degradation: DegradationConfig = field(
        default_factory=lambda: DegradationConfig(resolution_scale=0.9, add_noise=True)
    )

    workers: int = 1
    seed: Optional[int] = None
