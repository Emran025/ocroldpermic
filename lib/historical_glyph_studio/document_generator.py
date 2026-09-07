"""Generate reproducible full-page historical manuscript documents.

The generator composes glyph-level renders from :class:`GlyphStudio` onto
user-provided or procedural backgrounds. It keeps the glyph masks and YOLO
boxes intact, so the visual samples are also valid OCR evaluation artifacts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from .annotation.yolo import YOLOAnnotation, bbox_from_mask, codepoint_to_class_id
from .studio import GlyphStudio


@dataclass(frozen=True)
class DocumentSpec:
    document_id: int
    seed: int
    width: int = 1400
    height: int = 1900
    lines: int = 14
    min_chars: int = 18
    max_chars: int = 30
    background: str = "procedural_parchment"
    material: str = "faded_black"
    include_signature: bool = True
    include_seal: bool = True


def _fit_background(source: Optional[Path], size: tuple[int, int], rng: np.random.Generator) -> Image.Image:
    w, h = size
    if source and source.exists():
        image = Image.open(source).convert("RGB")
    else:
        # Warm parchment fallback; the per-pixel variation is deterministic.
        base = np.full((h, w, 3), [193, 167, 125], dtype=np.float32)
        noise = rng.normal(0, 13, (h, w, 1))
        yy, xx = np.mgrid[:h, :w]
        vignette = ((xx - w / 2) ** 2 / (w / 2) ** 2 + (yy - h / 2) ** 2 / (h / 2) ** 2)
        base += noise - np.clip(vignette[..., None] - 0.7, 0, 1) * 30
        image = Image.fromarray(np.uint8(np.clip(base, 0, 255)), "RGB")
    scale = max(w / image.width, h / image.height)
    resized = image.resize((max(w, int(image.width * scale)), max(h, int(image.height * scale))), Image.Resampling.LANCZOS)
    ox = int(rng.integers(0, max(1, resized.width - w + 1)))
    oy = int(rng.integers(0, max(1, resized.height - h + 1)))
    image = resized.crop((ox, oy, ox + w, oy + h))
    image = ImageEnhance.Contrast(image).enhance(float(rng.uniform(0.78, 1.05)))
    return image.filter(ImageFilter.GaussianBlur(float(rng.uniform(0, 0.35))))


def _paste_masked(page: Image.Image, glyph: np.ndarray, mask: np.ndarray, xy: tuple[int, int]) -> None:
    """Alpha-composite one rendered glyph using its native float mask."""
    layer = Image.fromarray(glyph, "RGB")
    alpha = Image.fromarray(np.uint8(np.clip(mask, 0, 1) * 255), "L")
    page.paste(layer, xy, alpha)


def generate_document(
    studio: GlyphStudio,
    spec: DocumentSpec,
    output_dir: str | Path,
    background_path: Optional[str | Path] = None,
    chars: Optional[Sequence[str]] = None,
) -> Path:
    """Generate one page, its YOLO labels, and an auditable JSON sidecar."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(spec.seed)
    alphabet = list(chars or studio.available_chars())
    if not alphabet:
        raise ValueError("No glyphs were found. Check GLYPH_ROOT and font/svg.")
    page = _fit_background(Path(background_path) if background_path else None, (spec.width, spec.height), rng)
    annotation = YOLOAnnotation(image_width=spec.width, image_height=spec.height)
    records: list[dict] = []
    # Faint ruled lines and age/ink spots evoke the supplied codex while
    # remaining outside the OCR annotation layer.
    draw = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).ImageDraw.Draw(page, "RGBA")
    margin_x = int(spec.width * 0.13)
    top = int(spec.height * 0.12)
    line_gap = int((spec.height * 0.72) / max(spec.lines, 1))
    for line_idx in range(spec.lines + 2):
        yy = top - line_gap // 2 + line_idx * line_gap
        draw.line((margin_x - 20, yy, spec.width - margin_x + 20, yy), fill=(105, 72, 48, int(rng.integers(14, 34))), width=1)
    for _ in range(max(18, spec.width // 45)):
        cx = int(rng.integers(20, spec.width - 20)); cy = int(rng.integers(20, spec.height - 20))
        rx = int(rng.integers(2, 18)); ry = int(rng.integers(2, 12))
        draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=(92, 54, 30, int(rng.integers(5, 24))))
    margin_x = int(spec.width * 0.13)
    top = int(spec.height * 0.12)
    line_gap = int((spec.height * 0.72) / max(spec.lines, 1))
    target_h = max(38, int(line_gap * 0.70))

    for line_idx in range(spec.lines):
        count = int(rng.integers(spec.min_chars, spec.max_chars + 1))
        y = top + line_idx * line_gap + int(rng.integers(-5, 6))
        x = margin_x + int(rng.integers(-12, 13))
        for char_idx in range(count):
            char = alphabet[int(rng.integers(0, len(alphabet)))]
            result = studio.render(
                char=char, background=(155, 130, 95), operation=spec.material,
                family=spec.handwriting_family, style=spec.handwriting_style,
                rotation=(-7, 7), perspective=True, occlusion="mild",
                glyph_scale=float(rng.uniform(0.30, 0.43)),
                canvas_size=(150, 150), seed=int(rng.integers(0, 2**31 - 1)),
                add_noise=True, noise_stddev=float(rng.uniform(1.5, 5.0)),
                blur_sigma=float(rng.uniform(0.0, 0.65)),
                erosion_iterations=int(rng.integers(0, 2)),
                fading_alpha=float(rng.uniform(0.0, 0.08)),
                color=(int(rng.integers(65, 125)), int(rng.integers(25, 75)), int(rng.integers(12, 45))),
            )
            mask = result.glyph_mask
            if mask is None:
                continue
            ys, xs = np.where(mask > 0.08)
            if len(xs) == 0:
                continue
            x0, x1 = int(xs.min()), int(xs.max() + 1)
            y0, y1 = int(ys.min()), int(ys.max() + 1)
            crop_mask = mask[y0:y1, x0:x1]
            crop_image = result.image[y0:y1, x0:x1]
            scale = target_h / max(1, crop_image.shape[0])
            nw, nh = max(2, int(crop_image.shape[1] * scale)), max(2, int(crop_image.shape[0] * scale))
            crop_image = np.asarray(Image.fromarray(crop_image).resize((nw, nh), Image.Resampling.LANCZOS))
            crop_mask = np.asarray(Image.fromarray(np.uint8(crop_mask * 255)).resize((nw, nh), Image.Resampling.BILINEAR), dtype=np.float32) / 255
            if x + nw >= spec.width - margin_x:
                break
            _paste_masked(page, crop_image, crop_mask, (x, y))
            full_mask = np.zeros((spec.height, spec.width), dtype=np.float32)
            full_mask[y:y + nh, x:x + nw] = crop_mask
            bbox = bbox_from_mask(full_mask, spec.width, spec.height)
            annotation.add(codepoint_to_class_id(ord(char), base=0x10350), bbox)
            records.append({"line": line_idx, "column": char_idx, "character": char, "x": x, "y": y, "width": nw, "height": nh})
            x += nw + int(rng.integers(2, 10))

    # Non-OCR marks make the page look archival without polluting glyph labels.
    if spec.include_signature:
        draw = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).ImageDraw.Draw(page, "RGBA")
        sx, sy = int(spec.width * 0.63), int(spec.height * 0.86)
        for _ in range(3):
            pts = [(sx + k * 12, sy + int(rng.normal(0, 11))) for k in range(16)]
            draw.line(pts, fill=(75, 30, 20, 150), width=int(rng.integers(2, 5)), joint="curve")
    if spec.include_seal:
        draw = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).ImageDraw.Draw(page, "RGBA")
        cx, cy, r = int(spec.width * 0.82), int(spec.height * 0.86), int(spec.height * 0.035)
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(120, 35, 24, 125), width=4)
        draw.ellipse((cx-r//2, cy-r//2, cx+r//2, cy+r//2), outline=(120, 35, 24, 105), width=2)

    stem = f"document_{spec.document_id:02d}"
    image_path = out / f"{stem}.png"
    page.save(image_path)
    annotation.save(out / f"{stem}.txt")
    (out / f"{stem}.json").write_text(json.dumps({"spec": asdict(spec), "background_path": str(background_path or ""), "glyphs": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    return image_path


def generate_documents(studio: GlyphStudio, specs: Iterable[DocumentSpec], output_dir: str | Path, backgrounds: Sequence[str | Path] = ()) -> list[Path]:
    backgrounds = list(backgrounds)
    return [generate_document(studio, spec, output_dir, backgrounds[i % len(backgrounds)] if backgrounds else None) for i, spec in enumerate(specs)]

__all__ = ["DocumentSpec", "generate_document", "generate_documents"]
