"""TrainingReporter: audit trail, per-stage summaries, and final curriculum report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..state.session import TrainingSession


class TrainingReporter:
    """Generates human-readable and JSON reports from a TrainingSession."""

    def __init__(self, session: TrainingSession, metrics_root: str) -> None:
        self.session = session
        self.metrics_root = Path(metrics_root)
        self.metrics_root.mkdir(parents=True, exist_ok=True)

    def generate_final_report(
        self,
        regression_results: Optional[Dict[int, float]] = None,
        current_weights: str = "",
    ) -> str:
        lines = [
            "=" * 70,
            "  OLD PERMIC OCR — CURRICULUM TRAINING FINAL REPORT",
            f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "=" * 70,
            "",
            "STAGE SUMMARY",
            "-" * 70,
        ]

        total_epochs = 0
        total_remediation = 0
        for sid in sorted(self.session.stages):
            r = self.session.stages[sid]
            status_icon = "✅" if r.status.is_success else ("⏳" if not r.status.is_terminal else "❌")
            lines.append(
                f"  {status_icon} Stage {sid:02d}: {r.status.value:<15} "
                f"mAP50={r.best_map50:.3f}  epochs={r.epochs_completed}  "
                f"remediation={len(r.remediation_rounds)} round(s)"
            )
            total_epochs += r.epochs_completed
            total_remediation += len(r.remediation_rounds)

        lines += [
            "",
            f"  Total epochs trained : {total_epochs}",
            f"  Total remediation    : {total_remediation} rounds",
            f"  Stages completed     : {sum(1 for r in self.session.stages.values() if r.status.is_success)} / {len(self.session.stages)}",
        ]

        if regression_results:
            lines += ["", "REGRESSION TESTING", "-" * 70]
            for sid, map50 in sorted(regression_results.items()):
                icon = "✅" if map50 >= 0.80 else ("⚠️ " if map50 >= 0 else "❌")
                lines.append(f"  {icon} Stage {sid:02d} subset: mAP50={map50:.3f}")

        if current_weights:
            lines += ["", f"  Current best weights: {current_weights}"]

        lines.append("=" * 70)
        report = "\n".join(lines)

        # Save JSON report
        report_data: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stages": {str(sid): r.to_dict() for sid, r in self.session.stages.items()},
            "regression": regression_results or {},
            "current_weights": current_weights,
            "summary": {
                "total_epochs": total_epochs,
                "total_remediation_rounds": total_remediation,
                "stages_completed": sum(1 for r in self.session.stages.values() if r.status.is_success),
            }
        }
        report_path = self.metrics_root / "final_report.json"
        report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

        return report

    def save_stage_metrics(self, stage_id: int, metrics: dict) -> None:
        stage_dir = self.metrics_root / f"stage_{stage_id:02d}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        p = stage_dir / "metrics.json"
        p.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
