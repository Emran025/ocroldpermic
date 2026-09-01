"""AuditTrail: append-only JSONL log of every significant training event."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class AuditTrail:
    """
    Append-only audit trail written in JSON Lines format.

    Every major training event (epoch, checkpoint, remediation, acceptance,
    rejection, release) is appended as a single JSON object on its own line.
    The file is atomic-append safe on a single machine.
    """

    def __init__(self, log_path: str) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, stage_id: Optional[int] = None, **kwargs: Any) -> None:
        """Append one audit record."""
        record: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        if stage_id is not None:
            record["stage"] = stage_id
        record.update(kwargs)
        self._append(json.dumps(record, ensure_ascii=False, default=str))

    # ── Convenience methods ───────────────────────────────────────────────────

    def log_epoch(self, stage_id: int, epoch: int, map50: float, map50_95: float, is_best: bool) -> None:
        self.log("epoch", stage_id, epoch=epoch, map50=round(map50, 4),
                 map50_95=round(map50_95, 4), is_best=is_best)

    def log_checkpoint(self, stage_id: int, epoch: int, commit: str) -> None:
        self.log("checkpoint_saved", stage_id, epoch=epoch, commit=commit)

    def log_remediation_start(self, stage_id: int, round_num: int, weak_classes: list) -> None:
        self.log("remediation_start", stage_id, round=round_num, weak_classes=weak_classes)

    def log_remediation_end(self, stage_id: int, round_num: int, map50_before: float, map50_after: float) -> None:
        self.log("remediation_end", stage_id, round=round_num,
                 map50_before=round(map50_before, 4), map50_after=round(map50_after, 4),
                 delta=round(map50_after - map50_before, 4))

    def log_stage_accepted(self, stage_id: int, map50: float) -> None:
        self.log("stage_accepted", stage_id, map50=round(map50, 4))

    def log_stage_rejected(self, stage_id: int, reason: str) -> None:
        self.log("stage_rejected", stage_id, reason=reason)

    def log_release(self, stage_id: int, version: str, commit: str, branch: str) -> None:
        self.log("model_released", stage_id, version=version, commit=commit, branch=branch)

    def read_all(self) -> list:
        """Read all audit records (for reporting)."""
        if not self.log_path.exists():
            return []
        records = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return records

    def _append(self, line: str) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
