"""Resource monitor: auto-detect GPU, RAM, CPU and suggest training parameters."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ResourceProfile:
    """Detected compute resources and suggested hyperparameters."""
    gpu_name: str
    gpu_vram_gb: float
    cuda_available: bool
    cpu_count: int
    ram_gb: float
    disk_free_gb: float
    suggested_batch_size: int
    suggested_workers: int
    device_string: str
    runtime_info: Dict[str, str] = field(default_factory=dict)

    def report(self) -> str:
        lines = [
            "┌─── Resource Profile ───────────────────────────────────┐",
            f"│  GPU : {self.gpu_name:<46}│",
            f"│  VRAM: {self.gpu_vram_gb:5.1f} GB   CUDA: {'Yes' if self.cuda_available else 'No':<38}│",
            f"│  CPU : {self.cpu_count} cores   RAM: {self.ram_gb:.1f} GB"
            f"   Disk free: {self.disk_free_gb:.1f} GB{'':<5}│",
            f"│  → batch_size={self.suggested_batch_size}   workers={self.suggested_workers}"
            f"   device='{self.device_string}'{'':<8}│",
            "└────────────────────────────────────────────────────────┘",
        ]
        return "\n".join(lines)


class ResourceMonitor:
    """Auto-detects available compute resources and suggests training parameters."""

    def detect(self, dataset_root: str = "/content") -> ResourceProfile:
        cuda_available, gpu_name, gpu_vram_gb = self._detect_gpu()
        cpu_count = os.cpu_count() or 2
        ram_gb = self._ram_gb()
        disk_free_gb = self._disk_free_gb(dataset_root)
        batch_size = self._suggest_batch(gpu_vram_gb, cuda_available)
        workers = min(cpu_count // 2, 8)
        device = "0" if cuda_available else "cpu"

        runtime = {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "gpu": gpu_name,
        }
        try:
            import torch
            runtime["torch"] = torch.__version__
            runtime["cuda"] = torch.version.cuda or "n/a"
        except ImportError:
            pass

        return ResourceProfile(
            gpu_name=gpu_name,
            gpu_vram_gb=gpu_vram_gb,
            cuda_available=cuda_available,
            cpu_count=cpu_count,
            ram_gb=ram_gb,
            disk_free_gb=disk_free_gb,
            suggested_batch_size=batch_size,
            suggested_workers=workers,
            device_string=device,
            runtime_info=runtime,
        )

    def log_profile(self, profile: ResourceProfile) -> None:
        print(profile.report())

    # ── Private ───────────────────────────────────────────────────────────────

    def _detect_gpu(self):
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_memory / 1e9
                return True, name, round(vram, 1)
        except ImportError:
            pass
        # Try nvidia-smi
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                timeout=5, text=True
            ).strip()
            if out:
                parts = out.split(",")
                name = parts[0].strip()
                vram_mb = float(parts[1].strip())
                return True, name, round(vram_mb / 1024, 1)
        except Exception:
            pass
        return False, "CPU only", 0.0

    def _ram_gb(self) -> float:
        try:
            import psutil
            return round(psutil.virtual_memory().total / 1e9, 1)
        except ImportError:
            pass
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        return round(int(line.split()[1]) / 1e6, 1)
        except Exception:
            pass
        return 0.0

    def _disk_free_gb(self, path: str) -> float:
        try:
            st = shutil.disk_usage(path)
            return round(st.free / 1e9, 1)
        except Exception:
            return 0.0

    def _suggest_batch(self, vram_gb: float, cuda: bool) -> int:
        if not cuda:
            return 4
        if vram_gb < 4:
            return 4
        if vram_gb < 8:
            return 8
        if vram_gb < 16:
            return 16
        return 32
