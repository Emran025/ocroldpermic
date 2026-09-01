"""
Central rendering pipeline.

Orchestrates all pipeline stages for a single glyph render:

  GlyphRecord
    → SVG load + rasterize
    → Normalize (float mask)
    → Glyph-space transforms (rotation, perspective, TPS warp)
    → Scale + place onto canvas
    → Material rendering
    → Occlusion / degradation
    → Composition onto background
    → Annotation
    → Resolution degradation (final stage)
    → Export

Returns a RenderResult containing the final image, annotation, and metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from ..config.models import (
    FadedConfig,
    MaterialName,
    RenderConfig,
)
from ..glyphs.normalization import GlyphMask, GlyphNormalizer
from ..glyphs.repository import GlyphRecord
from ..geometry.transforms import rotate_mask, rotate_image, rotate_bbox, sample_rotation
from ..geometry.perspective import (
    build_perspective_matrix,
    apply_perspective_mask,
    apply_perspective_image,
    perspective_bbox,
)
from ..geometry.deformation import build_tps_warp, apply_tps_mask, apply_tps_image
from ..materials import get_material, resolve_material
from ..surfaces import make_background
from ..analysis.discriminative import DiscriminativeMap
from ..degradation.occlusion import apply_occlusion
from ..degradation.blur import apply_gaussian_blur, apply_mask_blur
from ..degradation.erosion import erode_mask
from ..degradation.fading import apply_fading
from ..degradation.resolution import apply_resolution_degradation, scale_bbox_for_degradation
from ..annotation.yolo import BoundingBox, YOLOAnnotation, bbox_from_mask, codepoint_to_class_id
from ..composition.composer import Composer, PlacedGlyph
from ..export.image import GenerationMetadata

log = logging.getLogger(__name__)


@dataclass
class RenderResult:
    """Result of one render call."""

    image: np.ndarray
    """Final RGB uint8 image (H, W, 3)."""

    annotation: YOLOAnnotation
    """YOLO annotation with bounding boxes in final image coordinates."""

    metadata: Optional[GenerationMetadata] = None

    glyph_mask: Optional[np.ndarray] = None
    """Float32 glyph mask on the canvas (for visualisation)."""


class RenderingPipeline:
    """
    Stateless rendering pipeline.

    Parameters
    ----------
    normalizer:
        Shared GlyphNormalizer (carries an internal mask cache).
    yolo_class_base:
        Codepoint of class 0 (default: U+10350 for Old Permic).
    """

    def __init__(
        self,
        normalizer: GlyphNormalizer,
        yolo_class_base: int = 0x10350,
    ) -> None:
        self._normalizer = normalizer
        self._class_base = yolo_class_base
        self._composer = Composer()

    def render_single(
        self,
        record: GlyphRecord,
        config: RenderConfig,
        rng: np.random.Generator,
        disc_map: Optional[DiscriminativeMap] = None,
    ) -> RenderResult:
        """
        Render a single glyph onto a background with all configured effects.

        Parameters
        ----------
        record:
            The resolved GlyphRecord (SVG source).
        config:
            Complete render configuration.
        rng:
            Seeded random generator.
        disc_map:
            Optional pre-computed discriminative map for this codepoint.
        """
        CW, CH = config.canvas_size  # canvas width, height

        # ----------------------------------------------------------------
        # 1. Normalise glyph → float mask at canonical size
        # ----------------------------------------------------------------
        gm = self._normalizer.normalize(record)
        mask = gm.mask.copy()  # (H_can, W_can) float32

        # ----------------------------------------------------------------
        # 2. Scale glyph to fit the canvas
        # ----------------------------------------------------------------
        glyph_dim = max(mask.shape)
        target_dim = int(min(CW, CH) * config.glyph_scale)
        scale_factor = target_dim / max(1, glyph_dim)
        new_h = max(1, int(mask.shape[0] * scale_factor))
        new_w = max(1, int(mask.shape[1] * scale_factor))
        mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        mask = np.clip(mask, 0.0, 1.0).astype(np.float32)

        # ----------------------------------------------------------------
        # 3. Mask-space degradation (erosion, blur on mask)
        # ----------------------------------------------------------------
        if config.degradation.erosion_iterations > 0:
            mask = erode_mask(mask, config.degradation.erosion_iterations)
        if config.degradation.blur_sigma > 0:
            mask = apply_mask_blur(mask, config.degradation.blur_sigma * 0.5)

        # ----------------------------------------------------------------
        # 4. Occlusion (discriminative-aware)
        # ----------------------------------------------------------------
        pre_occ_mask = mask.copy()
        if config.occlusion.enabled:
            mask = apply_occlusion(mask, config.occlusion, rng, disc_map=disc_map)

        # ----------------------------------------------------------------
        # 5. Rotation
        # ----------------------------------------------------------------
        angle = sample_rotation(config.rotation, rng)
        rot_mask, M_rot = rotate_mask(mask, angle)
        mask = rot_mask

        # ----------------------------------------------------------------
        # 6. Perspective warp (optional)
        # ----------------------------------------------------------------
        M_persp = None
        if config.perspective.enabled and config.perspective.max_skew > 0:
            M_persp = build_perspective_matrix(new_h, new_w, config.perspective, rng)
            mask = apply_perspective_mask(mask, M_persp)

        # ----------------------------------------------------------------
        # 7. TPS local warp (optional)
        # ----------------------------------------------------------------
        if config.perspective.local_warp_strength > 0:
            map_x, map_y = build_tps_warp(
                mask.shape[0], mask.shape[1],
                strength=config.perspective.local_warp_strength,
                rng=rng,
            )
            mask = apply_tps_mask(mask, map_x, map_y)

        # ----------------------------------------------------------------
        # 8. Build background canvas
        # ----------------------------------------------------------------
        bg_obj = make_background(config.background if hasattr(config, "background") else (200, 190, 170))  # type: ignore[arg-type]
        background = bg_obj.get(CW, CH, rng)  # (CH, CW, 3) uint8

        # ----------------------------------------------------------------
        # 9. Create glyph-sized background tile for material rendering
        # ----------------------------------------------------------------
        GH, GW = mask.shape
        # Crop/tile background to glyph size for material rendering
        bg_tile = background[:GH, :GW] if GH <= CH and GW <= CW else \
            cv2.resize(background, (GW, GH), interpolation=cv2.INTER_LINEAR)

        # ----------------------------------------------------------------
        # 10. Material rendering
        # ----------------------------------------------------------------
        mat_name = resolve_material(config.material, rng)
        material = get_material(mat_name)

        # Build material-specific config
        mat_kwargs: dict = {}
        if mat_name == "engraved":
            mat_kwargs["config"] = config.engraving
        elif mat_name == "raised":
            mat_kwargs["config"] = config.raised
        elif mat_name in ("faded_black", "faded_white"):
            faded_cfg = FadedConfig(
                color=config.faded.color if mat_name == "faded_black" else (255, 255, 255),
                opacity=config.faded.opacity,
                blur_sigma=config.faded.blur_sigma,
                density_noise=config.faded.density_noise,
                local_fading=config.faded.local_fading,
            )
            if mat_name == "faded_white":
                faded_cfg.color = (255, 255, 255)
            mat_kwargs["config"] = faded_cfg
        elif mat_name == "glass":
            mat_kwargs["config"] = config.glass

        rendered_glyph = material.apply(mask, bg_tile, rng, **mat_kwargs)
        # rendered_glyph: (GH, GW, 3) uint8

        # ----------------------------------------------------------------
        # 11. Place glyph onto canvas & compose
        # ----------------------------------------------------------------
        place_x, place_y = self._composer.layout_single(CW, CH, GW, GH, rng=rng, center=True)

        placed = PlacedGlyph(
            rendered=rendered_glyph,
            glyph_mask=mask,
            codepoint=record.codepoint,
            canvas_x=place_x,
            canvas_y=place_y,
            class_id=codepoint_to_class_id(record.codepoint, base=self._class_base),
        )

        canvas, anno = self._composer.compose(background, [placed], yolo_class_base=self._class_base)

        # ----------------------------------------------------------------
        # 12. Image-level fading
        # ----------------------------------------------------------------
        if config.degradation.fading_alpha > 0:
            canvas = apply_fading(canvas, config.degradation.fading_alpha)

        # ----------------------------------------------------------------
        # 13. Build canvas-sized mask for annotation
        # ----------------------------------------------------------------
        canvas_mask = np.zeros((CH, CW), dtype=np.float32)
        gy0 = place_y
        gx0 = place_x
        gy1 = min(CH, gy0 + GH)
        gx1 = min(CW, gx0 + GW)
        src_y = gy1 - gy0
        src_x = gx1 - gx0
        canvas_mask[gy0:gy1, gx0:gx1] = mask[:src_y, :src_x]

        # Get the primary bbox before resolution degradation
        if anno.boxes:
            class_id_out, bbox_out = anno.boxes[0]
        else:
            bbox_out = bbox_from_mask(canvas_mask, CW, CH)
            class_id_out = codepoint_to_class_id(record.codepoint, base=self._class_base)

        # ----------------------------------------------------------------
        # 14. Final resolution degradation (LAST stage)
        # ----------------------------------------------------------------
        if config.degradation.resolution_scale < 0.99 or config.degradation.add_noise or \
                config.degradation.jpeg_quality is not None:
            canvas = apply_resolution_degradation(canvas, config.degradation, rng)
            # Scale annotations
            s = float(config.degradation.resolution_scale)
            if s < 0.99:
                bbox_out = bbox_out.scale(s)
                anno_final = YOLOAnnotation(
                    image_width=int(CW * s),
                    image_height=int(CH * s),
                )
                anno_final.add(class_id_out, bbox_out)
            else:
                anno_final = anno
        else:
            anno_final = anno

        # ----------------------------------------------------------------
        # 15. Build metadata
        # ----------------------------------------------------------------
        meta = None
        if config.emit_metadata:
            meta = GenerationMetadata(
                character=record.char,
                codepoint=record.codepoint,
                source_family=record.family,
                source_style=record.style,
                operation=mat_name,
                rotation_deg=round(angle, 2),
                occlusion_level=config.occlusion.level if config.occlusion.enabled else "none",
                occlusion_fraction=float(config.occlusion.custom_fraction or 0.0),
                resolution_scale=config.degradation.resolution_scale,
                seed=config.seed,
                bbox_xyxy=[bbox_out.x1, bbox_out.y1, bbox_out.x2, bbox_out.y2],
                canvas_size=[CW, CH],
            )

        return RenderResult(
            image=canvas,
            annotation=anno_final,
            metadata=meta,
            glyph_mask=canvas_mask,
        )

    def render_sequence(
        self,
        records: List[GlyphRecord],
        config: RenderConfig,
        rng: np.random.Generator,
        disc_maps: Optional[dict] = None,
    ) -> RenderResult:
        """
        Render multiple glyphs side-by-side on a shared canvas.

        Parameters
        ----------
        records:
            List of GlyphRecord objects (one per glyph position).
        config:
            Render configuration (canvas_size should be wide enough).
        rng:
            Seeded RNG.
        disc_maps:
            Optional dict mapping codepoint → DiscriminativeMap.
        """
        CW, CH = config.canvas_size

        # Background
        bg_obj = make_background(config.background if hasattr(config, "background") else (200, 190, 170))  # type: ignore[arg-type]
        background = bg_obj.get(CW, CH, rng)

        placed_list: List[PlacedGlyph] = []
        glyph_sizes: List[Tuple[int, int]] = []

        for rec in records:
            gm = self._normalizer.normalize(rec)
            mask = gm.mask.copy()
            glyph_dim = max(mask.shape)
            target_dim = int(min(CW, CH) * config.glyph_scale)
            sf = target_dim / max(1, glyph_dim)
            new_h = max(1, int(mask.shape[0] * sf))
            new_w = max(1, int(mask.shape[1] * sf))
            mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            mask = np.clip(mask, 0.0, 1.0).astype(np.float32)

            angle = sample_rotation(config.rotation, rng)
            mask, M_rot = rotate_mask(mask, angle)
            glyph_sizes.append((mask.shape[1], mask.shape[0]))
            placed_list.append((rec, mask))

        placements = self._composer.layout_sequence(
            CW, CH, glyph_sizes, rng=rng, spacing=15
        )

        final_placed = []
        for i, ((rec, mask), (px, py)) in enumerate(zip(placed_list, placements)):
            GH, GW = mask.shape
            bg_tile = background[:GH, :GW] if GH <= CH and GW <= CW else \
                cv2.resize(background, (GW, GH))

            mat_name = resolve_material(config.material, rng)
            material = get_material(mat_name)
            mat_kwargs: dict = {}
            if mat_name == "engraved":
                mat_kwargs["config"] = config.engraving
            elif mat_name == "raised":
                mat_kwargs["config"] = config.raised
            elif mat_name in ("faded_black", "faded_white"):
                faded_cfg = FadedConfig(
                    color=config.faded.color if mat_name == "faded_black" else (255, 255, 255),
                    opacity=config.faded.opacity,
                    blur_sigma=config.faded.blur_sigma,
                    density_noise=config.faded.density_noise,
                    local_fading=config.faded.local_fading,
                )
                if mat_name == "faded_white":
                    faded_cfg.color = (255, 255, 255)
                mat_kwargs["config"] = faded_cfg
            elif mat_name == "glass":
                mat_kwargs["config"] = config.glass

            rendered = material.apply(mask, bg_tile, rng, **mat_kwargs)

            disc_map = (disc_maps or {}).get(rec.codepoint)
            if config.occlusion.enabled:
                mask = apply_occlusion(mask, config.occlusion, rng, disc_map=disc_map)

            final_placed.append(PlacedGlyph(
                rendered=rendered,
                glyph_mask=mask,
                codepoint=rec.codepoint,
                canvas_x=px,
                canvas_y=py,
            ))

        canvas, anno = self._composer.compose(background, final_placed, yolo_class_base=self._class_base)

        if config.degradation.resolution_scale < 0.99 or config.degradation.add_noise:
            canvas = apply_resolution_degradation(canvas, config.degradation, rng)

        return RenderResult(image=canvas, annotation=anno)
