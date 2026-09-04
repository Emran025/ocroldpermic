"""
Per-worker render function — must be TOP-LEVEL for ProcessPoolExecutor pickling.

This module contains only plain functions and a module-level studio cache.
No class methods, no lambdas.
"""
from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Module-level cache so each worker process reuses the same GlyphStudio
# instance across multiple samples (avoids repeated SVG discovery).
_STUDIO_CACHE: dict[str, object] = {}


def _get_studio(glyph_root: str, canonical_size: tuple):
    """Return cached GlyphStudio for this worker process."""
    key = f"{glyph_root}::{canonical_size}"
    if key not in _STUDIO_CACHE:
        from historical_glyph_studio import GlyphStudio
        _STUDIO_CACHE[key] = GlyphStudio(
            glyph_root=glyph_root,
            canonical_size=canonical_size,
            cache_masks=True,
        )
    return _STUDIO_CACHE[key]


def render_one_sample(args: dict) -> Optional[dict]:
    """
    Render a single glyph image and save it to disk.

    Parameters (all in *args* dict)
    ---------------------------------
    glyph_root : str
    char : str
    background : str | tuple
    operation : str
    rotation_min : float
    rotation_max : float
    perspective : bool
    perspective_skew : float
    occlusion : str | None
    protect_discriminative : bool
    blur_sigma : float
    erosion_iters : int
    resolution_scale : float
    noise_stddev : float
    fading_alpha : float
    jpeg_quality : int | None
    glyph_scale : float
    canvas_size : tuple[int,int]
    family : str | None
    seed : int
    output_img_path : str
    output_lbl_path : str
    output_meta_path : str
    canonical_size : tuple[int,int]
    is_sequence : bool      -- if True, use render_sequence
    chars : list[str]       -- used when is_sequence=True

    Returns
    -------
    dict with metadata keys, or None on failure.
    """
    try:
        glyph_root = args["glyph_root"]
        canonical = tuple(args.get("canonical_size", (128, 128)))
        studio = _get_studio(glyph_root, canonical)

        char = args.get("char", "")
        chars = args.get("chars", [char])
        seed = int(args["seed"])
        is_sequence = bool(args.get("is_sequence", False))
        canvas_size = tuple(args.get("canvas_size", (512, 512)))

        # Build rotation spec
        rot_min = float(args.get("rotation_min", -1.0))
        rot_max = float(args.get("rotation_max", 1.0))
        rotation: tuple | bool = (rot_min, rot_max) if rot_min != rot_max else False

        render_kwargs = dict(
            background=args.get("background", "stone"),
            operation=args.get("operation", "faded_black"),
            rotation=rotation,
            occlusion=args.get("occlusion") or False,
            perspective=bool(args.get("perspective", False)),
            glyph_scale=float(args.get("glyph_scale", 0.55)),
            canvas_size=canvas_size,
            seed=seed,
            family=args.get("family") or None,
            resolution_scale=float(args.get("resolution_scale", 1.0)),
            add_noise=float(args.get("noise_stddev", 0.0)) > 0,
            noise_stddev=float(args.get("noise_stddev", 0.0)),
            blur_sigma=float(args.get("blur_sigma", 0.0)),
            erosion_iterations=int(args.get("erosion_iters", 0)),
            max_skew=float(args.get("perspective_skew", 0.0)),
            jpeg_quality=args.get("jpeg_quality"),
        )

        def _render_once():
            if is_sequence and len(chars) > 1:
                return studio.render_sequence(
                    chars=chars,
                    canvas_size=canvas_size,
                    seed=seed,
                    background=render_kwargs["background"],
                    operation=render_kwargs["operation"],
                    rotation=rotation,
                )
            return studio.render(**{**render_kwargs, "char": chars[0] if chars else char})

        try:
            result = _render_once()
        except ValueError as first_error:
            # Some historical SVG sources are syntactically valid but produce
            # an empty mask in the active rasterizer. Try another family/style
            # for the same codepoint instead of silently dropping the sample.
            if is_sequence or "empty (all-zero) mask" not in str(first_error):
                raise
            requested_char = chars[0] if chars else char
            codepoint = ord(requested_char) if len(requested_char) == 1 else int(
                requested_char.removeprefix("U+").removeprefix("U++"), 16
            )
            last_error = first_error
            recovered = False
            for record in studio._repo.get(codepoint):
                try:
                    render_kwargs["family"] = record.family or None
                    render_kwargs["style"] = record.style or None
                    result = _render_once()
                    recovered = True
                    log.warning(
                        "Recovered codepoint U+%04X with alternate source %s/%s",
                        codepoint, record.family, record.style or "(root)",
                    )
                    break
                except ValueError as candidate_error:
                    if "empty (all-zero) mask" in str(candidate_error):
                        last_error = candidate_error
                        continue
                    raise
            if not recovered:
                raise last_error

        # Save image
        img_path = Path(args["output_img_path"])
        img_path.parent.mkdir(parents=True, exist_ok=True)

        from PIL import Image as PILImage
        PILImage.fromarray(result.image).save(img_path)

        # Save label
        lbl_path = Path(args["output_lbl_path"])
        lbl_path.parent.mkdir(parents=True, exist_ok=True)
        if result.annotation:
            result.annotation.save(lbl_path)
        else:
            lbl_path.write_text("")

        # Save metadata
        import json
        meta_path = Path(args["output_meta_path"])
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta = result.metadata.to_dict() if result.metadata else {}
        meta["seed"] = seed
        meta["canvas_size"] = list(canvas_size)
        meta["chars"] = chars
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        return {
            "img_path": str(img_path),
            "lbl_path": str(lbl_path),
            "char": chars[0] if chars else char,
            "seed": seed,
            "operation": args.get("operation", ""),
            **meta,
        }

    except Exception:
        log.warning("render_one_sample failed:\n%s", traceback.format_exc())
        return None
