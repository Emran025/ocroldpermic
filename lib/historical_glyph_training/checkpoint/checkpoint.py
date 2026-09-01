"""CheckpointManager: policy-driven checkpoint saving, loading, and resume detection."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from ..config.training_config import CheckpointPolicy
from .metadata import CheckpointMetadata


class CheckpointManager:
    """
    Manages model checkpoints according to a configurable policy.

    Maintains a local registry of all checkpoints so that, after a Colab
    disconnection, the system can identify the latest valid checkpoint and
    resume training from it.

    Directory layout::

        run_dir/
            checkpoints/
                epoch_001_best.pt
                epoch_001_best.json
                epoch_005.pt
                epoch_005.json
                registry.json
    """

    _REGISTRY = "registry.json"

    def __init__(
        self,
        run_dir: str,
        policy: CheckpointPolicy = CheckpointPolicy.BEST_ONLY,
        every_n: int = 5,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.ckpt_dir = self.run_dir / "checkpoints"
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)
        self.policy = policy
        self.every_n = every_n
        self._registry: List[dict] = self._read_registry()

    def should_save(self, epoch: int, is_best: bool) -> bool:
        if self.policy == CheckpointPolicy.BEST_ONLY:
            return is_best
        if self.policy == CheckpointPolicy.EVERY_EPOCH:
            return True
        if self.policy == CheckpointPolicy.EVERY_N_EPOCHS:
            return (epoch % self.every_n == 0)
        if self.policy == CheckpointPolicy.EPOCH_AND_BEST:
            return is_best or (epoch % self.every_n == 0)
        return is_best

    def save(self, weights_path: str, metadata: CheckpointMetadata) -> str:
        """
        Copy weights + write metadata JSON. Returns the saved weights path.
        """
        suffix = "_best" if metadata.is_best else ""
        name = f"epoch_{metadata.epoch:03d}{suffix}"
        dst_weights = self.ckpt_dir / f"{name}.pt"
        dst_meta = self.ckpt_dir / f"{name}.json"

        src = Path(weights_path)
        if src.exists():
            shutil.copy2(src, dst_weights)
        else:
            dst_weights.touch()  # Placeholder if weights not found

        dst_meta.write_text(
            json.dumps(metadata.to_dict(), indent=2), encoding="utf-8"
        )

        # Update registry
        entry = {**metadata.to_dict(), "weights_file": str(dst_weights)}
        # Mark previous best as not-best if this is best
        if metadata.is_best:
            for e in self._registry:
                e["is_best"] = False
        self._registry.append(entry)
        self._write_registry()
        return str(dst_weights)

    def latest(self) -> Optional[CheckpointMetadata]:
        """Most recently saved checkpoint."""
        if not self._registry:
            return None
        last = self._registry[-1]
        return CheckpointMetadata.from_dict(last)

    def best(self) -> Optional[CheckpointMetadata]:
        """Checkpoint with the highest mAP50."""
        bests = [e for e in self._registry if e.get("is_best")]
        if bests:
            return CheckpointMetadata.from_dict(bests[-1])
        if self._registry:
            return CheckpointMetadata.from_dict(
                max(self._registry, key=lambda e: e.get("map50", 0.0))
            )
        return None

    def list_all(self) -> List[CheckpointMetadata]:
        return [CheckpointMetadata.from_dict(e) for e in self._registry]

    def find_resume_point(self) -> Optional[Tuple[str, CheckpointMetadata]]:
        """
        Find the latest valid checkpoint for Colab resume.
        Returns (weights_path, metadata) or None.
        """
        # Try best first, then latest
        for entry in reversed(self._registry):
            weights = Path(entry.get("weights_file", ""))
            if weights.exists() and weights.stat().st_size > 0:
                return str(weights), CheckpointMetadata.from_dict(entry)
        return None

    # ── Registry I/O ──────────────────────────────────────────────────────────

    def _write_registry(self) -> None:
        registry_path = self.ckpt_dir / self._REGISTRY
        tmp = registry_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._registry, indent=2), encoding="utf-8")
        tmp.replace(registry_path)

    def _read_registry(self) -> List[dict]:
        registry_path = self.ckpt_dir / self._REGISTRY
        if not registry_path.exists():
            return []
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
