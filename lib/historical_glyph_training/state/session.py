"""Training session: persistent JSON state file for Colab-resilient resumption."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .stage_state import StageRecord, StageStatus


class TrainingSession:
    """
    Persistent, resumable training session.

    Stores stage records to disk as JSON so that Colab disconnections
    never lose training progress. All writes are atomic (write temp → rename).

    Usage::

        session = TrainingSession.load_or_create("/content/training_session.json")
        session.start_stage(1)
        ...
        session.accept_stage(1)
        session.save()
    """

    def __init__(
        self,
        session_file: str,
        stages: Optional[Dict[int, StageRecord]] = None,
        created_at: str = "",
        model_source_commit: str = "",
        config_snapshot: Optional[dict] = None,
    ) -> None:
        self.session_file = Path(session_file)
        self.stages: Dict[int, StageRecord] = stages or {}
        self.created_at = created_at or _utc_now()
        self.model_source_commit = model_source_commit
        self.config_snapshot = config_snapshot or {}

    # ── Persistence ──────────────────────────────────────────────────────────

    @classmethod
    def load_or_create(cls, session_file: str) -> "TrainingSession":
        """Load an existing session or create a new one."""
        path = Path(session_file)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                stages = {
                    int(k): StageRecord.from_dict(v)
                    for k, v in data.get("stages", {}).items()
                }
                return cls(
                    session_file=session_file,
                    stages=stages,
                    created_at=data.get("created_at", ""),
                    model_source_commit=data.get("model_source_commit", ""),
                    config_snapshot=data.get("config_snapshot", {}),
                )
            except Exception as exc:
                print(f"[Session] Warning: could not load session ({exc}). Starting fresh.")
        return cls(session_file=session_file)

    def save(self) -> None:
        """Atomically write session to disk."""
        data = {
            "created_at": self.created_at,
            "updated_at": _utc_now(),
            "model_source_commit": self.model_source_commit,
            "config_snapshot": self.config_snapshot,
            "stages": {str(k): v.to_dict() for k, v in self.stages.items()},
        }
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=self.session_file.parent, suffix=".json.tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            Path(tmp_path).replace(self.session_file)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ── Stage accessors ───────────────────────────────────────────────────────

    def get_stage(self, stage_id: int) -> StageRecord:
        """Return the record for a stage, creating it if it doesn't exist."""
        if stage_id not in self.stages:
            self.stages[stage_id] = StageRecord(stage_id=stage_id)
        return self.stages[stage_id]

    def start_stage(self, stage_id: int) -> StageRecord:
        record = self.get_stage(stage_id)
        record.started_at = _utc_now()
        record.transition(StageStatus.PREPARING)
        self.save()
        return record

    def accept_stage(self, stage_id: int, note: str = "") -> StageRecord:
        record = self.get_stage(stage_id)
        record.transition(StageStatus.ACCEPTED, note)
        self.save()
        return record

    def reject_stage(self, stage_id: int, note: str = "") -> StageRecord:
        record = self.get_stage(stage_id)
        record.transition(StageStatus.REJECTED, note)
        self.save()
        return record

    def mark_released(self, stage_id: int, commit: str, branch: str) -> StageRecord:
        record = self.get_stage(stage_id)
        record.release_commit = commit
        record.release_branch = branch
        record.transition(StageStatus.RELEASED)
        self.save()
        return record

    def mark_failed(self, stage_id: int, reason: str = "") -> StageRecord:
        record = self.get_stage(stage_id)
        record.transition(StageStatus.FAILED, reason)
        self.save()
        return record

    # ── Resume helpers ────────────────────────────────────────────────────────

    @property
    def current_stage_id(self) -> int:
        """The lowest incomplete stage (starts from 1)."""
        for stage_id in sorted(self.stages):
            if not self.stages[stage_id].status.is_success:
                return stage_id
        # All done or nothing started — return next
        if self.stages:
            return max(self.stages) + 1
        return 1

    @property
    def last_completed_stage(self) -> Optional[int]:
        """The highest stage that reached ACCEPTED or RELEASED."""
        done = [
            sid for sid, r in self.stages.items() if r.status.is_success
        ]
        return max(done) if done else None

    def summary(self) -> str:
        lines = [f"Training Session — {self.created_at}"]
        for sid in sorted(self.stages):
            r = self.stages[sid]
            lines.append(
                f"  Stage {sid:02d}: {r.status.value:15s} "
                f"| mAP50={r.best_map50:.3f} "
                f"| epochs={r.epochs_completed} "
                f"| remediation={len(r.remediation_rounds)} rounds"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"TrainingSession(stages={list(self.stages)}, current={self.current_stage_id})"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
