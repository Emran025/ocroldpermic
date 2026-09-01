"""Resource detection and auto-tuning for generation workers."""
from __future__ import annotations

import os
import shutil
import subprocess
import logging
from dataclasses import dataclass

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

    def to_dict(self) -> dict:
        return {
            "cpu_count": self.cpu_count,
            "cpu_logical": self.cpu_logical,
            "ram_gb": round(self.ram_gb, 2),
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "gpu_memory_gb": round(self.gpu_memory_gb, 2),
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


def auto_tune(
    profile: ResourceProfile,
    override_workers: int | None = None,
    override_batch: int | None = None,
) -> tuple[int, int]:
    """
    Return (workers, batch_size) after applying any user overrides.

    Parameters
    ----------
    profile:
        Detected resource profile.
    override_workers:
        If not None, use this instead of the recommended value.
    override_batch:
        If not None, use this instead of the recommended value.

    Returns
    -------
    (workers, batch_size)
    """
    workers = override_workers if override_workers is not None else profile.recommended_workers
    batch = override_batch if override_batch is not None else profile.recommended_batch_size
    return int(max(1, workers)), int(max(1, batch))
