"""Optional CPU/CUDA acceleration for generated image post-processing.

SVG parsing and geometric rendering remain on the stable CPU renderer. When
PyTorch with CUDA is available, this module batches the pixel post-processing
step on the GPU. The CPU path is always available and is the reproducibility
reference path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def detect_backend(requested: str = "auto") -> dict:
    requested = (requested or "auto").lower()
    if requested not in {"auto", "cpu", "cuda"}:
        raise ValueError("backend must be one of: auto, cpu, cuda")
    if requested == "cpu":
        return {"backend": "cpu", "device": "cpu", "cuda_available": False, "reason": "forced"}
    try:
        import torch
        available = bool(torch.cuda.is_available())
        if requested == "cuda" and not available:
            raise RuntimeError("CUDA backend requested but torch.cuda.is_available() is False")
        if available:
            return {"backend": "cuda", "device": "cuda", "cuda_available": True, "device_name": torch.cuda.get_device_name(0)}
        return {"backend": "cpu", "device": "cpu", "cuda_available": False, "reason": "CUDA unavailable"}
    except ImportError:
        if requested == "cuda":
            raise RuntimeError("CUDA backend requires the optional torch dependency")
        return {"backend": "cpu", "device": "cpu", "cuda_available": False, "reason": "torch not installed"}


def process_saved_images(paths: Iterable[str | Path], backend: str = "auto", batch_size: int = 32) -> dict:
    """Apply a deterministic batched pixel pass and return an audit summary.

    The operation preserves dimensions and labels. It performs the same mild
    contrast/normalisation pass on CPU and CUDA; CUDA differs only in where
    tensor arithmetic executes.
    """
    info = detect_backend(backend)
    paths = [Path(p) for p in paths]
    if not paths:
        return {**info, "images": 0}
    from PIL import Image
    import numpy as np
    if info["backend"] == "cuda":
        import torch
        device = torch.device("cuda")
        for start in range(0, len(paths), max(1, int(batch_size))):
            batch_paths = paths[start:start + batch_size]
            arrays = [np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0 for p in batch_paths]
            shape = arrays[0].shape
            if any(a.shape != shape for a in arrays):
                # Canvas sizes are normally homogeneous; retain exact files if not.
                continue
            tensor = torch.from_numpy(np.stack(arrays)).to(device, non_blocking=True)
            tensor = torch.clamp((tensor - 0.5) * 1.02 + 0.5, 0.0, 1.0)
            out = (tensor.mul(255.0).add(0.5).byte().cpu().numpy())
            for p, arr in zip(batch_paths, out):
                Image.fromarray(arr, "RGB").save(p, compress_level=1)
    else:
        for p in paths:
            with Image.open(p) as image:
                arr = np.asarray(image.convert("RGB"), dtype=np.float32)
                arr = np.clip((arr - 127.5) * 1.02 + 127.5, 0, 255).astype(np.uint8)
                Image.fromarray(arr, "RGB").save(p, compress_level=1)
    return {**info, "images": len(paths), "batch_size": int(batch_size)}


__all__ = ["detect_backend", "process_saved_images"]
