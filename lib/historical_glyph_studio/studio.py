"""
GlyphStudio — the single public entry point for the library.

Usage
-----
::

    from historical_glyph_studio import GlyphStudio

    studio = GlyphStudio(glyph_root="font/svg")

    result = studio.render(
        char="\\U00010350",
        background=(190, 175, 155),
        operation="engraved",
        seed=42,
    )
    # result.image  → RGB uint8 numpy array
    # result.annotation → YOLOAnnotation
    # result.metadata   → GenerationMetadata

    studio.generate_dataset(
        chars=studio.available_chars(),
        count=500,
        output_dir="dataset/",
    )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from .config.models import (
    DatasetConfig,
    DegradationConfig,
    EngravingConfig,
    FadedConfig,
    GlassConfig,
    GlyphSourceConfig,
    MaterialName,
    OcclusionConfig,
    PerspectiveConfig,
    RaisedConfig,
    RenderConfig,
    RotationConfig,
    SelectionMode,
)
from .glyphs.normalization import GlyphNormalizer
from .glyphs.rasterizer import SVGRasterizer
from .glyphs.repository import GlyphRepository
from .glyphs.resolver import GlyphResolver
from .analysis.discriminative import DiscriminativeAnalyzer, DiscriminativeMap
from .export.image import GenerationMetadata, ImageExporter
from .rendering.pipeline import RenderingPipeline, RenderResult
from .surfaces import BackgroundSpec

log = logging.getLogger(__name__)


class GlyphStudio:
    """
    Top-level façade for the Historical Glyph Simulation Studio.

    Parameters
    ----------
    glyph_root:
        Root directory containing glyph family subdirectories.
    canonical_size:
        (H, W) resolution at which SVGs are internally rasterized.
    yolo_class_base:
        Codepoint of YOLO class 0.  For Old Permic set to 0x10350.
        Set to 0 for a generic 0-based index.
    cache_masks:
        Cache rasterized masks in memory for repeated access.
    analysis_cache_path:
        Optional .npz file path to persist discriminative maps between runs.
    """

    def __init__(
        self,
        glyph_root: str | Path,
        canonical_size: Tuple[int, int] = (256, 256),
        yolo_class_base: int = 0x10350,
        cache_masks: bool = True,
        analysis_cache_path: Optional[str | Path] = None,
    ) -> None:
        self._root = Path(glyph_root).resolve()
        self._repo = GlyphRepository(self._root)
        self._rasterizer = SVGRasterizer()
        self._normalizer = GlyphNormalizer(
            rasterizer=self._rasterizer,
            canonical_size=canonical_size,
            cache=cache_masks,
        )
        self._pipeline = RenderingPipeline(self._normalizer, yolo_class_base=yolo_class_base)
        self._exporter = ImageExporter()
        self._class_base = yolo_class_base

        _cache = Path(analysis_cache_path) if analysis_cache_path else None
        self._analyzer = DiscriminativeAnalyzer(
            normalizer=self._normalizer,
            cache_path=_cache,
        )
        self._disc_maps: Optional[Dict[int, DiscriminativeMap]] = None

        log.info(self._repo.summary())

    # ------------------------------------------------------------------
    # Repository inspection
    # ------------------------------------------------------------------

    def available_chars(self) -> List[str]:
        """Return all Unicode characters discoverable in the glyph root."""
        return [chr(cp) for cp in self._repo.codepoints]

    def available_families(self) -> List[str]:
        """Return all discovered family names."""
        return self._repo.families

    def repository_summary(self) -> str:
        """Human-readable summary of the glyph repository."""
        return self._repo.summary()

    # ------------------------------------------------------------------
    # Discriminative analysis
    # ------------------------------------------------------------------

    def run_analysis(self) -> Dict[int, DiscriminativeMap]:
        """
        Run (or return cached) discriminative analysis on the full glyph set.

        Returns a dict mapping codepoint → DiscriminativeMap.
        This is called automatically on the first `render()` call when
        occlusion with `protect_discriminative=True` is requested.
        """
        if self._disc_maps is None:
            self._disc_maps = self._analyzer.analyze(self._repo)
        return self._disc_maps

    # ------------------------------------------------------------------
    # Single render
    # ------------------------------------------------------------------

    def render(
        self,
        char: str,
        background: BackgroundSpec = (200, 190, 170),
        operation: MaterialName = "engraved",
        rotation: Union[Tuple[float, float], float, bool] = True,
        occlusion: Union[bool, str] = False,
        perspective: bool = False,
        glyph_scale: float = 0.6,
        canvas_size: Tuple[int, int] = (512, 512),
        seed: Optional[int] = None,
        family: Optional[str] = None,
        style: Optional[str] = None,
        resolution_scale: float = 1.0,
        **kwargs: Any,
    ) -> RenderResult:
        """
        Render a single glyph.

        Parameters
        ----------
        char:
            Unicode character or 'U+10350' code-point string.
        background:
            RGB tuple, surface name ('stone','paper',...), or image path.
        operation:
            Material name: 'engraved', 'raised', 'faded_black', 'faded_white',
            'glass', or 'random'.
        rotation:
            True  → random ±18°
            False → no rotation
            float → fixed angle
            (min, max) → random within range
        occlusion:
            False  → disabled
            True   → moderate level
            str    → 'mild'|'moderate'|'severe'|'extreme'
        perspective:
            Whether to add perspective distortion.
        seed:
            Integer seed for full reproducibility.
        family, style:
            Pin to a specific SVG source family/style.
        """
        rng = np.random.default_rng(seed)

        # --- Build rotation config ---
        if rotation is False:
            rot_cfg = RotationConfig(enabled=False)
        elif rotation is True:
            rot_cfg = RotationConfig(enabled=True, min_deg=-18.0, max_deg=18.0)
        elif isinstance(rotation, (int, float)):
            rot_cfg = RotationConfig(enabled=True, fixed_deg=float(rotation))
        else:
            mn, mx = float(rotation[0]), float(rotation[1])
            rot_cfg = RotationConfig(enabled=True, min_deg=mn, max_deg=mx)

        # --- Build occlusion config ---
        if occlusion is False:
            occ_cfg = OcclusionConfig(enabled=False)
        elif occlusion is True:
            occ_cfg = OcclusionConfig(enabled=True, level="moderate", protect_discriminative=True)
        else:
            occ_cfg = OcclusionConfig(enabled=True, level=str(occlusion), protect_discriminative=True)  # type: ignore[arg-type]

        # --- Build perspective config ---
        persp_cfg = PerspectiveConfig(
            enabled=perspective,
            max_skew=kwargs.get("max_skew", 0.08),
            local_warp_strength=kwargs.get("local_warp_strength", 0.0),
        )

        # --- Build degradation config ---
        deg_cfg = DegradationConfig(
            resolution_scale=resolution_scale,
            add_noise=kwargs.get("add_noise", False),
            noise_stddev=kwargs.get("noise_stddev", 5.0),
            blur_sigma=kwargs.get("blur_sigma", 0.0),
            erosion_iterations=kwargs.get("erosion_iterations", 0),
            jpeg_quality=kwargs.get("jpeg_quality", None),
        )

        # --- Material sub-configs from kwargs ---
        engraving_cfg = kwargs.get("engraving", EngravingConfig())
        raised_cfg = kwargs.get("raised_config", RaisedConfig())
        faded_cfg = kwargs.get("faded_config", FadedConfig(
            color=(0, 0, 0),
            opacity=kwargs.get("opacity", 0.4),
        ))
        glass_cfg = kwargs.get("glass_config", GlassConfig())

        config = RenderConfig(
            char=char,
            source=GlyphSourceConfig(
                family=family,
                style=style,
                selection_mode="fixed" if (family or style) else "random",
            ),
            canvas_size=canvas_size,
            glyph_scale=glyph_scale,
            material=operation,
            rotation=rot_cfg,
            perspective=persp_cfg,
            engraving=engraving_cfg,
            raised=raised_cfg,
            faded=faded_cfg,
            glass=glass_cfg,
            occlusion=occ_cfg,
            degradation=deg_cfg,
            seed=seed,
            emit_metadata=True,
            emit_yolo=True,
        )

        # Store background spec on config (pipeline reads it)
        config.background = background  # type: ignore[attr-defined]

        # Resolve glyph
        resolver = GlyphResolver(self._repo, rng)
        record = resolver.resolve(char, config.source)

        # Get discriminative map if needed
        disc_map: Optional[DiscriminativeMap] = None
        if occ_cfg.enabled and occ_cfg.protect_discriminative:
            disc_maps = self.run_analysis()
            disc_map = disc_maps.get(record.codepoint)

        return self._pipeline.render_single(record, config, rng, disc_map=disc_map)

    # ------------------------------------------------------------------
    # Multi-glyph render
    # ------------------------------------------------------------------

    def render_sequence(
        self,
        chars: List[str],
        background: BackgroundSpec = (200, 190, 170),
        operation: MaterialName = "engraved",
        rotation: Union[Tuple[float, float], float, bool] = True,
        canvas_size: Tuple[int, int] = (1024, 512),
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> RenderResult:
        """Render multiple glyphs side-by-side on one canvas."""
        rng = np.random.default_rng(seed)

        rot_cfg = RotationConfig(enabled=bool(rotation)) if isinstance(rotation, bool) else \
            RotationConfig(enabled=True, fixed_deg=float(rotation)) if isinstance(rotation, (int, float)) else \
            RotationConfig(enabled=True, min_deg=float(rotation[0]), max_deg=float(rotation[1]))

        config = RenderConfig(
            canvas_size=canvas_size,
            material=operation,
            rotation=rot_cfg,
            seed=seed,
        )
        config.background = background  # type: ignore[attr-defined]

        resolver = GlyphResolver(self._repo, rng)
        records = [resolver.resolve(c) for c in chars]

        return self._pipeline.render_sequence(records, config, rng)

    # ------------------------------------------------------------------
    # Batch dataset generation
    # ------------------------------------------------------------------

    def generate_dataset(
        self,
        chars: Optional[Sequence[str]] = None,
        count: int = 100,
        output_dir: str | Path = "dataset",
        balanced: bool = True,
        materials: Optional[Sequence[MaterialName]] = None,
        backgrounds: Optional[Sequence[BackgroundSpec]] = None,
        canvas_size: Tuple[int, int] = (512, 512),
        rotation: Union[Tuple[float, float], float, bool] = True,
        occlusion: Union[bool, str] = False,
        perspective: bool = False,
        resolution_scale: float = 1.0,
        add_noise: bool = False,
        seed: Optional[int] = None,
        image_format: str = "png",
    ) -> List[Path]:
        """
        Generate a batch of synthetic training images.

        Parameters
        ----------
        chars:
            Characters to include.  None → all available characters.
        count:
            Total number of images to generate.
        output_dir:
            Root output directory.  YOLO-style subdirectories (images/, labels/)
            are created automatically.
        balanced:
            If True, distribute count evenly among chars.
        materials:
            Materials to cycle through.  None → all five materials.
        backgrounds:
            List of background specs to cycle through.  None → stone texture.
        seed:
            Master seed.  Individual samples get reproducible seeds derived from it.

        Returns
        -------
        List of saved image paths.
        """
        if chars is None:
            chars = self.available_chars()
        if not chars:
            raise ValueError("No characters available in glyph repository.")

        all_chars = list(chars)
        materials = list(materials or ["engraved", "raised", "faded_black", "faded_white", "glass"])
        backgrounds = list(backgrounds or ["stone"])

        out = Path(output_dir)
        img_dir = out / "images"
        lbl_dir = out / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        master_rng = np.random.default_rng(seed)

        # Build per-sample assignment list
        if balanced:
            samples_per_char = max(1, count // len(all_chars))
            remainder = count - samples_per_char * len(all_chars)
            assignments = all_chars * samples_per_char
            if remainder > 0:
                extras = list(master_rng.choice(all_chars, size=remainder, replace=True))
                assignments += extras
        else:
            assignments = list(master_rng.choice(all_chars, size=count, replace=True))

        # Shuffle
        master_rng.shuffle(assignments)  # type: ignore[arg-type]

        saved_paths: List[Path] = []
        for i, char in enumerate(assignments):
            sample_seed = int(master_rng.integers(0, 2**31))
            mat = materials[i % len(materials)]
            bg = backgrounds[i % len(backgrounds)]

            try:
                result = self.render(
                    char=char,
                    background=bg,
                    operation=mat,
                    rotation=rotation,
                    occlusion=occlusion,
                    perspective=perspective,
                    canvas_size=canvas_size,
                    seed=sample_seed,
                    resolution_scale=resolution_scale,
                    add_noise=add_noise,
                )
            except Exception as exc:
                log.warning("Skipping sample %d (char=%r): %s", i, char, exc)
                continue

            cp_hex = f"{ord(char):05X}" if len(char) == 1 else "XXXXX"
            stem = f"{i:06d}_U{cp_hex}_{mat}"

            img_path = self._exporter.save(
                image=result.image,
                output_dir=img_dir,
                stem=stem,
                image_format=image_format,
            )
            if result.annotation:
                result.annotation.save(lbl_dir / f"{stem}.txt")
            if result.metadata:
                import json
                (lbl_dir / f"{stem}.json").write_text(
                    json.dumps(result.metadata.to_dict(), indent=2),
                    encoding="utf-8",
                )

            saved_paths.append(img_path)
            if (i + 1) % 50 == 0:
                log.info("Generated %d / %d samples", i + 1, len(assignments))

        log.info("Dataset generation complete. %d images saved to %s", len(saved_paths), out)
        return saved_paths
