"""Checkpoint metadata dataclass — records every saved checkpoint's provenance."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class CheckpointMetadata:
    """Complete provenance record for one saved model checkpoint."""
    stage: int
    epoch: int
    global_step: int
    map50: float
    map50_95: float
    precision: float
    recall: float
    train_loss: float
    val_loss: float
    class_metrics: Dict[str, float] = field(default_factory=dict)  # {class_name: ap50}
    training_config: Dict[str, Any] = field(default_factory=dict)
    dataset_stage: int = 0
    dataset_version: str = ""
    model_source_commit: str = ""
    checkpoint_commit: str = ""
    timestamp: str = ""
    random_seed: int = 42
    runtime: Dict[str, str] = field(default_factory=dict)
    is_best: bool = False
    remediation_round: int = 0  # 0 = normal training

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.dataset_stage == 0:
            self.dataset_stage = self.stage

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointMetadata":
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def summary(self) -> str:
        badge = " [BEST]" if self.is_best else ""
        rem = f" [rem-round {self.remediation_round}]" if self.remediation_round > 0 else ""
        return (
            f"Stage {self.stage:02d} Epoch {self.epoch:03d}{badge}{rem} | "
            f"mAP50={self.map50:.3f} mAP50-95={self.map50_95:.3f} | "
            f"P={self.precision:.3f} R={self.recall:.3f}"
        )
