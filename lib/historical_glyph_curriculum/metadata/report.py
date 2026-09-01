"""Curriculum progress report generator."""
from __future__ import annotations

from pathlib import Path

from .manifest import StageManifest


def generate_curriculum_report(master_manifest: dict, output_path: Path) -> str:
    """
    Generate a markdown curriculum report and save it to *output_path*.

    Returns the markdown string.
    """
    stages = master_manifest.get("stages", [])
    total_images = master_manifest.get("total_images", 0)
    total_ann = master_manifest.get("total_annotations", 0)
    total_classes = master_manifest.get("total_classes", 0)
    total_secs = master_manifest.get("generation_total_seconds", 0.0)
    throughput = total_images / total_secs if total_secs > 0 else 0.0

    lines = [
        "# Historical Glyph Dataset — Curriculum Report",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Images | {total_images:,} |",
        f"| Total Annotations | {total_ann:,} |",
        f"| Unique Classes | {total_classes} |",
        f"| Stages Completed | {len(stages)} / 12 |",
        f"| Total Generation Time | {total_secs/3600:.2f} hours |",
        f"| Average Throughput | {throughput:.1f} img/s |",
        "",
        "## Stage Summary",
        "",
        "| Stage | Name | Images | Classes | Commit |",
        "|-------|------|--------|---------|--------|",
    ]

    for s in stages:
        sid = s.get("stage_id", "?")
        sname = s.get("stage_name", "")
        simgs = s.get("total_images", 0)
        scls = len(s.get("class_distribution", {}))
        shash = s.get("commit_hash") or "—"
        lines.append(f"| {sid:02d} | {sname} | {simgs:,} | {scls} | `{shash}` |")

    lines += [
        "",
        "## Source Families",
        "",
    ]
    for fam in master_manifest.get("all_families", []):
        lines.append(f"- {fam}")

    lines += [
        "",
        "## Materials Used",
        "",
    ]
    for mat in master_manifest.get("all_materials", []):
        lines.append(f"- {mat}")

    lines += [
        "",
        "## Class Distribution (top 20)",
        "",
        "| Class ID | Count |",
        "|----------|-------|",
    ]
    dist = {int(k): v for k, v in master_manifest.get("class_distribution", {}).items()}
    for cls_id, cnt in sorted(dist.items(), key=lambda x: -x[1])[:20]:
        lines.append(f"| {cls_id} | {cnt:,} |")

    report = "\n".join(lines)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def print_stage_summary(manifest: StageManifest) -> None:
    """Pretty-print a stage summary to stdout."""
    print(f"\n{'='*55}")
    print(f"  Stage {manifest.stage_id:02d}: {manifest.stage_name}")
    print(f"{'='*55}")
    print(f"  Images:           {manifest.total_images:,}")
    print(f"  Classes:          {len(manifest.class_distribution)}")
    print(f"  Materials:        {', '.join(manifest.materials_used)}")
    print(f"  Approved:         {'✓' if manifest.approved else '✗'}")
    print(f"  Commit:           {manifest.commit_hash or 'not committed'}")
    print(f"  Time:             {manifest.generation_time_seconds:.1f}s")
    print(f"{'='*55}\n")
