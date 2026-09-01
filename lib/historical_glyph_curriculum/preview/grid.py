"""
Preview grid utilities for Colab/Jupyter display.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image


def build_preview_grid(
    image_paths: list[str | Path],
    n_cols: int = 6,
    thumb_size: tuple[int, int] = (160, 160),
    padding: int = 4,
    title: str = "",
) -> Image.Image:
    """
    Arrange images in a grid. Returns a PIL Image.

    If fewer images than cells are available, remaining cells are black.
    """
    paths = [Path(p) for p in image_paths]
    n = len(paths)
    if n == 0:
        return Image.new("RGB", (320, 160), (40, 40, 40))

    cols = min(n_cols, n)
    rows = math.ceil(n / cols)

    tw, th = thumb_size
    title_h = 28 if title else 0
    canvas_w = cols * (tw + padding) + padding
    canvas_h = rows * (th + padding) + padding + title_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (30, 30, 30))

    if title:
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(canvas)
            draw.text((padding, 4), title, fill=(220, 220, 220))
        except Exception:
            pass

    for idx, p in enumerate(paths):
        row = idx // cols
        col = idx % cols
        x = padding + col * (tw + padding)
        y = title_h + padding + row * (th + padding)
        try:
            img = Image.open(p).convert("RGB")
            img.thumbnail(thumb_size, Image.LANCZOS)
            # Center in tile
            ox = (tw - img.width) // 2
            oy = (th - img.height) // 2
            canvas.paste(img, (x + ox, y + oy))
        except Exception:
            # Draw a red error tile
            tile = Image.new("RGB", (tw, th), (180, 40, 40))
            canvas.paste(tile, (x, y))

    return canvas


def display_grid_in_colab(
    image_paths: list[str | Path],
    n_cols: int = 6,
    thumb_size: tuple[int, int] = (160, 160),
    title: str = "",
) -> None:
    """
    Display the image grid inline in a Jupyter/Colab notebook.
    Falls back to saving a PNG if IPython is unavailable.
    """
    grid = build_preview_grid(image_paths, n_cols=n_cols, thumb_size=thumb_size, title=title)

    try:
        from IPython import display as ipython_display
        import io
        buf = io.BytesIO()
        grid.save(buf, format="PNG")
        buf.seek(0)
        ipython_display.display(ipython_display.Image(data=buf.read()))
    except Exception:
        # Not in notebook — save to disk
        out = Path("preview_grid.png")
        grid.save(out)
        print(f"Grid saved to: {out}")


def select_preview_samples(
    images_dir: Path,
    n: int = 24,
    strategy: str = "spread",
) -> list[Path]:
    """
    Select *n* representative image paths from *images_dir*.

    Parameters
    ----------
    strategy:
        'spread': evenly distributed through the sorted file list.
        'random': random sample (non-deterministic).
    """
    paths = sorted(images_dir.glob("*.png")) + sorted(images_dir.glob("*.jpg"))
    if not paths:
        return []
    if len(paths) <= n:
        return paths

    if strategy == "spread":
        step = len(paths) / n
        selected = [paths[int(i * step)] for i in range(n)]
        return selected
    else:
        import random
        return random.sample(paths, n)
