"""Stage state machine: PENDING → TRAINING → EVALUATING → ACCEPTED/FAILED/REJECTED."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class StageStatus(str, Enum):
    """Lifecycle state for a single curriculum stage."""
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    TRAINING = "TRAINING"
    EVALUATING = "EVALUATING"
    REMEDIATING = "REMEDIATING"
    RE_EVALUATING = "RE_EVALUATING"
    ACCEPTED = "ACCEPTED"
    RELEASED = "RELEASED"
    # Failure states
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"
    INTERRUPTED = "INTERRUPTED"

    @property
    def is_terminal(self) -> bool:
        return self in (
            StageStatus.ACCEPTED,
            StageStatus.RELEASED,
            StageStatus.FAILED,
            StageStatus.TIMEOUT,
            StageStatus.REJECTED,
            StageStatus.INTERRUPTED,
        )

    @property
    def is_success(self) -> bool:
        return self in (StageStatus.ACCEPTED, StageStatus.RELEASED)


@dataclass
class RemediationRecord:
    """Record of one remediation round within a stage."""
    round_number: int
    weak_classes: List[str]           # class names that triggered remediation
    reserve_samples_used: int
    extra_epochs: int
    map50_before: float
    map50_after: float
    per_class_before: Dict[str, float]
    per_class_after: Dict[str, float]
    success: bool
    started_at: str = ""
    ended_at: str = ""


@dataclass
class CheckpointRef:
    """Reference to a saved model checkpoint."""
    epoch: int
    map50: float
    map50_95: float
    commit_hash: str
    branch: str
    path: str
    is_best: bool
    saved_at: str = ""


@dataclass
class StageRecord:
    """Complete record of one curriculum stage's training history."""
    stage_id: int
    status: StageStatus = StageStatus.PENDING
    started_at: str = ""
    ended_at: str = ""

    # Training progress
    epochs_completed: int = 0
    best_epoch: int = 0
    best_map50: float = 0.0
    best_map50_95: float = 0.0

    # Final metrics
    final_map50: float = 0.0
    final_map50_95: float = 0.0
    final_recall: float = 0.0
    final_precision: float = 0.0
    final_class_metrics: Dict[str, float] = field(default_factory=dict)

    # Per-class final AP50
    class_ap50: Dict[str, float] = field(default_factory=dict)
    class_recall: Dict[str, float] = field(default_factory=dict)

    # Weak classes (class names below threshold)
    weak_classes: List[str] = field(default_factory=list)

    # Remediation history
    remediation_rounds: List[RemediationRecord] = field(default_factory=list)

    # Checkpoints
    checkpoints: List[CheckpointRef] = field(default_factory=list)

    # Release
    release_commit: str = ""
    release_branch: str = ""

    # Overrides
    human_override: Optional[str] = None  # 'accept' | 'reject' | 'skip_remediation'
    override_reason: str = ""

    # Regression (previous-stage subset mAP50s)
    regression_results: Dict[int, float] = field(default_factory=dict)

    # Dataset info
    dataset_version: str = ""
    train_samples: int = 0
    val_samples: int = 0
    reserve_samples: int = 0

    # Model source
    model_source_commit: str = ""

    # Audit notes
    notes: List[str] = field(default_factory=list)

    def transition(self, new_status: StageStatus, note: str = "") -> None:
        """Transition to a new status; record timestamp and optional note."""
        self.status = new_status
        if new_status.is_terminal:
            self.ended_at = _utc_now()
        if note:
            self.notes.append(f"[{_utc_now()}] {new_status.value}: {note}")

    def add_checkpoint(self, ckpt: CheckpointRef) -> None:
        if ckpt.is_best:
            for c in self.checkpoints:
                c.is_best = False
        self.checkpoints.append(ckpt)

    def best_checkpoint(self) -> Optional[CheckpointRef]:
        bests = [c for c in self.checkpoints if c.is_best]
        if bests:
            return bests[-1]
        if self.checkpoints:
            return max(self.checkpoints, key=lambda c: c.map50)
        return None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["remediation_rounds"] = [asdict(r) for r in self.remediation_rounds]
        d["checkpoints"] = [asdict(c) for c in self.checkpoints]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageRecord":
        data = dict(data)
        data["status"] = StageStatus(data.get("status", "PENDING"))
        data["remediation_rounds"] = [
            RemediationRecord(**r) for r in data.get("remediation_rounds", [])
        ]
        data["checkpoints"] = [
            CheckpointRef(**c) for c in data.get("checkpoints", [])
        ]
        return cls(**data)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
