"""Resource detection and auto-tuning for generation workers."""
from __future__ import annotations

import os
import shutil
import subprocess
import logging
from dataclasses import dataclass
from typing import NamedTuple

log = logging.getLogger(__name__)


@dataclass
class ResourceProfile:
    """Available system resources and recommended generation parameters."""

    cpu_count: int
    cpu_logical: int
    ram_gb: float
    gpu_available: bool
    gpu_name: str
    gpu_memory_gb: float
    disk_free_gb: float
    recommended_workers: int
    recommended_batch_size: int

    @property
    def gpu_vram_gb(self) -> float:
        """Alias for gpu_memory_gb."""
        return self.gpu_memory_gb

    def to_dict(self) -> dict:
        return {
            "cpu_count": self.cpu_count,
            "cpu_logical": self.cpu_logical,
            "ram_gb": round(self.ram_gb, 2),
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "gpu_memory_gb": round(self.gpu_memory_gb, 2),
            "gpu_vram_gb": round(self.gpu_memory_gb, 2),
            "disk_free_gb": round(self.disk_free_gb, 2),
            "recommended_workers": self.recommended_workers,
            "recommended_batch_size": self.recommended_batch_size,
        }


def _try_gpu_torch() -> tuple[bool, str, float]:
    """Try torch.cuda for GPU info."""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            return True, name, mem
    except ImportError:
        pass
    return False, "", 0.0


def _try_gpu_nvidia_smi() -> tuple[bool, str, float]:
    """Fallback: parse nvidia-smi for GPU info."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = out.stdout.strip().split(",")
            name = parts[0].strip()
            mem_mb = float(parts[1].strip())
            return True, name, mem_mb / 1024.0
    except Exception:
        pass
    return False, "", 0.0


def detect_resources() -> ResourceProfile:
    """
    Detect available CPU, RAM, GPU, and disk resources.

    Returns
    -------
    ResourceProfile
        Populated profile with recommended worker/batch parameters.
    """
    import psutil

    cpu_physical = psutil.cpu_count(logical=False) or 1
    cpu_logical = psutil.cpu_count(logical=True) or 1
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    # GPU: try torch first, then nvidia-smi
    gpu_avail, gpu_name, gpu_mem = _try_gpu_torch()
    if not gpu_avail:
        gpu_avail, gpu_name, gpu_mem = _try_gpu_nvidia_smi()

    # Disk free for the working directory
    disk = shutil.disk_usage(os.getcwd())
    disk_free_gb = disk.free / (1024 ** 3)

    # Recommend workers: rendering is CPU-bound (SVG rasterization)
    # Don't oversaturate; leave cores for I/O and OS
    recommended_workers = min(4, max(1, cpu_physical // 2))

    # Recommend batch size based on RAM
    extra_ram = max(0.0, ram_gb - 4.0)
    recommended_batch = int(min(128, max(8, 8 + extra_ram * 4)))

    return ResourceProfile(
        cpu_count=cpu_physical,
        cpu_logical=cpu_logical,
        ram_gb=ram_gb,
        gpu_available=gpu_avail,
        gpu_name=gpu_name,
        gpu_memory_gb=gpu_mem,
        disk_free_gb=disk_free_gb,
        recommended_workers=recommended_workers,
        recommended_batch_size=recommended_batch,
    )


def print_resource_report(profile: ResourceProfile) -> None:
    """Print a clean resource summary to stdout."""
    print("=" * 50)
    print("  Resource Profile")
    print("=" * 50)
    print(f"  CPU (physical):    {profile.cpu_count}")
    print(f"  CPU (logical):     {profile.cpu_logical}")
    print(f"  RAM:               {profile.ram_gb:.1f} GB")
    if profile.gpu_available:
        print(f"  GPU:               {profile.gpu_name}")
        print(f"  GPU Memory:        {profile.gpu_memory_gb:.1f} GB")
    else:
        print("  GPU:               Not available")
    print(f"  Disk Free:         {profile.disk_free_gb:.1f} GB")
    print(f"  Recommended Workers:    {profile.recommended_workers}")
    print(f"  Recommended Batch Size: {profile.recommended_batch_size}")
    print("=" * 50)


class TunedResources(NamedTuple):
    """Auto-tuned worker and batch configuration."""

    workers: int
    batch_size: int


def auto_tune(
    profile: ResourceProfile,
    mode_or_workers: int | str | None = None,
    override_batch: int | None = None,
    *,
    mode: str | None = None,
    override_workers: int | None = None,
) -> TunedResources:
    """
    Return auto-tuned (workers, batch_size) after applying mode presets and user overrides.

    Parameters
    ----------
    profile:
        Detected resource profile.
    mode_or_workers:
        Generation mode string ('dev' | 'medium' | 'full') or worker count override.
    override_batch:
        If not None, use this instead of the recommended batch size.
    mode:
        Generation mode string ('dev' | 'medium' | 'full').
    override_workers:
        Explicit worker count override.

    Returns
    -------
    TunedResources (NamedTuple of workers, batch_size)
        Can be accessed via attributes (.workers, .batch_size) or unpacked as a tuple (w, b).
    """
    effective_mode = mode
    workers_val = override_workers

    if mode_or_workers is not None:
        if isinstance(mode_or_workers, str):
            if mode_or_workers.strip().isdigit():
                if workers_val is None:
                    workers_val = int(mode_or_workers.strip())
            else:
                if effective_mode is None:
                    effective_mode = mode_or_workers.strip().lower()
        elif isinstance(mode_or_workers, (int, float)):
            if workers_val is None:
                workers_val = int(mode_or_workers)

    # Base recommendation by mode
    if effective_mode == "dev":
        base_workers = min(2, profile.recommended_workers)
        base_batch = min(16, profile.recommended_batch_size)
    else:
        base_workers = profile.recommended_workers
        base_batch = profile.recommended_batch_size

    workers = workers_val if workers_val is not None else base_workers
    batch = override_batch if override_batch is not None else base_batch

    return TunedResources(workers=int(max(1, workers)), batch_size=int(max(1, batch)))
