"""Generate reproducible manuscript pages with geometry-aware writing.

The document renderer treats the supplied photograph as a physical writing
surface rather than a flat backdrop. Text is composed in a canonical page
coordinate system, projected through an estimated page quadrilateral, and then
subjected to a low-frequency fold field. Glyph masks and YOLO boxes are warped
with exactly the same transform as the visible ink.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional, Sequence

import cv2
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
    handwriting_family: str = "01_Original_Handwriting"
    handwriting_style: str = "Original"
    include_signature: bool = True
    include_seal: bool = True
    surface_warp: float = 1.0
    writing_margin: float = 0.105
    line_curve: float = 0.018


def _fit_background(source: Optional[Path], size: tuple[int, int], rng: np.random.Generator) -> Image.Image:
    w, h = size
    if source and source.exists():
        image = Image.open(source).convert("RGB")
    else:
        yy, xx = np.mgrid[:h, :w]
        base = np.zeros((h, w, 3), dtype=np.float32)
        base[:] = [185.0, 148.0, 100.0]
        low = rng.normal(0, 1, (max(2, h // 18), max(2, w // 18)))
        low = np.asarray(Image.fromarray(np.uint8(np.clip(low * 28 + 128, 0, 255))).resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32) - 128
        fibre = rng.normal(0, 7.5, (h, w, 1))
        vignette = ((xx - w / 2) ** 2 / (w / 2) ** 2 + (yy - h / 2) ** 2 / (h / 2) ** 2)
        base += low[..., None] * 0.62 + fibre
        base -= np.clip(vignette[..., None] - 0.35, 0, 1) * 24
        cadence = max(20, int(h * 0.0335))
        for line_y in range(int(h * 0.04), h, cadence):
            band = np.exp(-((yy - line_y) / 9.0) ** 2) * rng.uniform(2.0, 8.0)
            base -= band[..., None] * np.array([0.9, 0.65, 0.4])
        for _ in range(max(10, w // 100)):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            rx, ry = rng.uniform(12, 110), rng.uniform(8, 90)
            stain = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
            base -= stain[..., None] * rng.uniform(2, 15) * np.array([0.85, 0.55, 0.3])
        image = Image.fromarray(np.uint8(np.clip(base, 0, 255)), "RGB")
    scale = max(w / image.width, h / image.height)
    resized = image.resize((max(w, int(image.width * scale)), max(h, int(image.height * scale))), Image.Resampling.LANCZOS)
    ox = int(rng.integers(0, max(1, resized.width - w + 1)))
    oy = int(rng.integers(0, max(1, resized.height - h + 1)))
    image = resized.crop((ox, oy, ox + w, oy + h))
    return ImageEnhance.Contrast(image).enhance(float(rng.uniform(0.78, 1.05))).filter(ImageFilter.GaussianBlur(float(rng.uniform(0, 0.35))))


def _estimate_page_quad(page: np.ndarray) -> np.ndarray:
    """Estimate the paper quadrilateral, with a conservative inset fallback."""
    h, w = page.shape[:2]
    gray = cv2.cvtColor(page, cv2.COLOR_RGB2GRAY)
    smooth = cv2.GaussianBlur(gray, (0, 0), 3)
    threshold = float(np.percentile(smooth, 24))
    dark = cv2.threshold(smooth, threshold, 255, cv2.THRESH_BINARY_INV)[1]
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 0.38 * w * h:
            continue
        perimeter = cv2.arcLength(contour, True)
        poly = cv2.approxPolyDP(contour, 0.035 * perimeter, True)
        if len(poly) == 4 and area > best_area:
            best, best_area = poly.reshape(4, 2).astype(np.float32), area
    if best is None:
        inset_x, inset_y = 0.07 * w, 0.055 * h
        best = np.array([[inset_x, inset_y], [w - inset_x, inset_y], [w - inset_x, h - inset_y], [inset_x, h - inset_y]], dtype=np.float32)
    # Order clockwise: top-left, top-right, bottom-right, bottom-left.
    center = best.mean(axis=0)
    angles = np.arctan2(best[:, 1] - center[1], best[:, 0] - center[0])
    best = best[np.argsort(angles)]
    start = int(np.argmin(best.sum(axis=1)))
    return np.roll(best, -start, axis=0).astype(np.float32)


def _surface_maps(width: int, height: int, amount: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Create smooth paper-fold displacement fields in canonical coordinates."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:height, :width].astype(np.float32)
    u, v = xx / max(1, width - 1), yy / max(1, height - 1)
    amp = amount * max(1.0, min(width, height) * 0.006)
    waves = (
        np.sin(u * rng.uniform(5.0, 10.0) + rng.uniform(0, 6.3)) * amp * rng.uniform(.25, .65)
        + np.sin(v * rng.uniform(3.0, 7.0) + rng.uniform(0, 6.3)) * amp * rng.uniform(.15, .45)
    )
    folds = np.zeros_like(waves)
    for _ in range(2):
        fx, fy = rng.uniform(.15, .85), rng.uniform(.12, .88)
        spread = rng.uniform(.025, .09)
        folds += np.exp(-(((u - fx) ** 2 + (v - fy) ** 2) / spread)) * rng.uniform(-.7, .7) * amp
    dy = waves + folds
    dx = np.gradient(dy, axis=1) * rng.uniform(.35, .8)
    return dx.astype(np.float32), dy.astype(np.float32)


def _warp(mask: np.ndarray, matrix: np.ndarray, out_size: tuple[int, int], dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = mask.shape[:2]
    # First warp canonical page into the detected paper quadrilateral.
    projected = cv2.warpPerspective(mask.astype(np.float32), matrix, out_size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    ph, pw = projected.shape[:2]
    grid_x, grid_y = np.meshgrid(np.arange(pw, dtype=np.float32), np.arange(ph, dtype=np.float32))
    return cv2.remap(projected, grid_x - cv2.resize(dx, (pw, ph)), grid_y - cv2.resize(dy, (pw, ph)), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def _composite_ink(canvas: np.ndarray, alpha_canvas: np.ndarray, patch: np.ndarray, patch_mask: np.ndarray, x: int, y: int, material: str) -> None:
    """Composite ink with a pressed/raised edge instead of a flat sticker."""
    ph, pw = patch_mask.shape
    h, w = alpha_canvas.shape
    if x < 0 or y < 0 or x + pw > w or y + ph > h:
        return
    m = np.clip(patch_mask, 0, 1).astype(np.float32)
    # Renderer outputs can contain a pale material highlight. Convert that
    # highlight into restrained brown/black pigment so the glyph is embedded
    # in the page instead of looking like a white sticker.
    luminance = cv2.cvtColor(patch.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    if material == "engraved":
        gx = cv2.Sobel(m, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=3)
        relief = np.clip(0.5 + 0.28 * gx - 0.20 * gy, 0.18, 0.9)
        base = np.array([62.0, 36.0, 22.0], dtype=np.float32)
        colour = base[None, None, :] * (0.72 + 0.42 * luminance[..., None]) * relief[..., None]
        strength = np.clip(m * 0.86 + cv2.GaussianBlur(m, (0, 0), 1.2) * 0.18, 0, 1)
    else:
        base = np.array([58.0, 34.0, 21.0], dtype=np.float32)
        colour = base[None, None, :] * (0.72 + 0.42 * luminance[..., None])
        strength = np.clip(m * 0.78 + cv2.GaussianBlur(m, (0, 0), .65) * 0.16, 0, 1)
    old = alpha_canvas[y:y + ph, x:x + pw]
    weight = strength * (1.0 - old)
    canvas[y:y + ph, x:x + pw] = canvas[y:y + ph, x:x + pw] * (1 - weight[..., None]) + colour * weight[..., None]
    alpha_canvas[y:y + ph, x:x + pw] = np.maximum(old, strength)


def generate_document(studio: GlyphStudio, spec: DocumentSpec, output_dir: str | Path, background_path: Optional[str | Path] = None, chars: Optional[Sequence[str]] = None) -> Path:
    """Generate a geometry-aware page, YOLO labels, and an auditable sidecar."""
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(spec.seed)
    alphabet = list(chars or studio.available_chars())
    if not alphabet:
        raise ValueError("No glyphs were found. Check GLYPH_ROOT and font/svg.")
    page = _fit_background(Path(background_path) if background_path else None, (spec.width, spec.height), rng)
    page_array = np.asarray(page).copy()
    quad = _estimate_page_quad(page_array)
    canonical = np.array([[0, 0], [spec.width - 1, 0], [spec.width - 1, spec.height - 1], [0, spec.height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(canonical, quad)
    dx, dy = _surface_maps(spec.width, spec.height, spec.surface_warp, spec.seed + 991)
    flat_ink = np.zeros_like(page_array, dtype=np.float32)
    flat_alpha = np.zeros((spec.height, spec.width), dtype=np.float32)
    glyph_masks: list[tuple[str, np.ndarray, dict]] = []
    margin_x = int(spec.width * spec.writing_margin)
    top = int(spec.height * 0.12); bottom = int(spec.height * 0.86)
    usable_h = max(1, bottom - top)
    line_gap = usable_h / max(spec.lines, 1)
    target_h = max(38, int(line_gap * 0.67))

    # Lines follow the same curved local surface as glyph baselines.
    for line_idx in range(spec.lines + 2):
        y0 = top - line_gap * .45 + line_idx * line_gap
        pts = []
        for x in np.linspace(margin_x * .75, spec.width - margin_x * .75, 80):
            u = x / spec.width - .5
            yy = y0 + spec.line_curve * spec.height * (u * u * 2.0 - .25) + dy[int(np.clip(y0, 0, spec.height - 1)), int(np.clip(x, 0, spec.width - 1))]
            pts.append((int(x), int(yy)))
        line = np.zeros((spec.height, spec.width), dtype=np.uint8)
        cv2.polylines(line, [np.asarray(pts, np.int32)], False, 255, 1, cv2.LINE_AA)
        line = _warp(line, matrix, (spec.width, spec.height), dx, dy)
        page_array = np.clip(page_array.astype(np.float32) - line[..., None] * np.array([.10, .07, .045]), 0, 255).astype(np.uint8)

    for line_idx in range(spec.lines):
        count = int(rng.integers(spec.min_chars, spec.max_chars + 1))
        y = int(top + line_idx * line_gap + rng.integers(-5, 6))
        x = margin_x + int(rng.integers(-12, 13))
        for char_idx in range(count):
            char = alphabet[int(rng.integers(0, len(alphabet)))]
            result = studio.render(char=char, background=(155, 130, 95), operation=spec.material, family=spec.handwriting_family, style=spec.handwriting_style, rotation=(-7, 7), perspective=True, occlusion="mild", glyph_scale=float(rng.uniform(.30, .43)), canvas_size=(150, 150), seed=int(rng.integers(0, 2**31 - 1)), add_noise=True, noise_stddev=float(rng.uniform(1.5, 5.0)), blur_sigma=float(rng.uniform(0, .65)), erosion_iterations=int(rng.integers(0, 2)), fading_alpha=float(rng.uniform(0, .08)), color=(int(rng.integers(65, 125)), int(rng.integers(25, 75)), int(rng.integers(12, 45))))
            if result.glyph_mask is None:
                continue
            mask = result.glyph_mask
            ys, xs = np.where(mask > .08)
            if len(xs) == 0:
                continue
            y0, y1, x0, x1 = int(ys.min()), int(ys.max() + 1), int(xs.min()), int(xs.max() + 1)
            crop_mask, crop_image = mask[y0:y1, x0:x1], result.image[y0:y1, x0:x1]
            scale = target_h / max(1, crop_image.shape[0])
            nw, nh = max(2, int(crop_image.shape[1] * scale)), max(2, int(crop_image.shape[0] * scale))
            crop_image = np.asarray(Image.fromarray(crop_image).resize((nw, nh), Image.Resampling.LANCZOS))
            crop_mask = np.asarray(Image.fromarray(np.uint8(crop_mask * 255)).resize((nw, nh), Image.Resampling.BILINEAR), dtype=np.float32) / 255
            if x + nw >= spec.width - margin_x:
                break
            baseline_bend = spec.line_curve * spec.height * (((x / spec.width) - .5) ** 2 * 2.0 - .25)
            yy = int(y + baseline_bend + dy[min(spec.height - 1, max(0, y)), min(spec.width - 1, max(0, x))])
            _composite_ink(flat_ink, flat_alpha, crop_image, crop_mask, x, yy, spec.material)
            glyph_flat = np.zeros((spec.height, spec.width), dtype=np.float32)
            glyph_flat[yy:yy + nh, x:x + nw] = crop_mask
            glyph_masks.append((char, _warp(glyph_flat, matrix, (spec.width, spec.height), dx, dy), {"line": line_idx, "column": char_idx, "x": x, "y": yy, "width": nw, "height": nh}))
            x += nw + int(rng.integers(2, 10))

    ink_rgb = cv2.warpPerspective(flat_ink.astype(np.uint8), matrix, (spec.width, spec.height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    ink_alpha = _warp(flat_alpha, matrix, (spec.width, spec.height), dx, dy)
    # ``ink_rgb`` is already premultiplied by the local alpha in the flat
    # canvas. Blend it once, rather than multiplying by alpha a second time.
    page_array = np.clip(page_array.astype(np.float32) * (1 - ink_alpha[..., None]) + ink_rgb.astype(np.float32), 0, 255).astype(np.uint8)
    annotation = YOLOAnnotation(image_width=spec.width, image_height=spec.height)
    records = []
    for char, warped_mask, record in glyph_masks:
        bbox = bbox_from_mask(warped_mask, spec.width, spec.height)
        annotation.add(codepoint_to_class_id(ord(char), base=0x10350), bbox)
        record = dict(record)
        record["projected_bbox"] = [
            (bbox.x1 + bbox.x2) / (2.0 * spec.width),
            (bbox.y1 + bbox.y2) / (2.0 * spec.height),
            bbox.width / spec.width,
            bbox.height / spec.height,
        ]
        records.append({**record, "character": char})

    image_path = out / f"document_{spec.document_id:02d}.png"
    Image.fromarray(page_array, "RGB").save(image_path)
    annotation.save(out / f"document_{spec.document_id:02d}.txt")
    (out / f"document_{spec.document_id:02d}.json").write_text(json.dumps({"spec": asdict(spec), "background_path": str(background_path or ""), "paper_quad": quad.tolist(), "surface_warp": {"model": "homography+low_frequency_fold_field", "amount": spec.surface_warp}, "glyphs": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    return image_path


def generate_documents(studio: GlyphStudio, specs: Iterable[DocumentSpec], output_dir: str | Path, backgrounds: Sequence[str | Path] = ()) -> list[Path]:
    backgrounds = list(backgrounds)
    return [generate_document(studio, spec, output_dir, backgrounds[i % len(backgrounds)] if backgrounds else None) for i, spec in enumerate(specs)]


__all__ = ["DocumentSpec", "generate_document", "generate_documents"]
