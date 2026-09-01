"""Stage and master manifests for research traceability."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class StageManifest:
    """Complete metadata record for one generated stage."""

    stage_id: int
    stage_name: str
    total_images: int
    class_distribution: Dict[int, int]
    materials_used: List[str]
    families_used: List[str]
    resolution_range: tuple
    seed: int
    approved: bool
    commit_hash: Optional[str]
    generation_time_seconds: float
    concept_summaries: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["class_distribution"] = {str(k): v for k, v in self.class_distribution.items()}
        return d

    @staticmethod
    def from_dict(d: dict) -> "StageManifest":
        d2 = dict(d)
        d2["class_distribution"] = {int(k): v for k, v in d2.get("class_distribution", {}).items()}
        d2["resolution_range"] = tuple(d2.get("resolution_range", (0, 0)))
        d2.setdefault("concept_summaries", [])
        return StageManifest(**d2)


def save_stage_manifest(manifest: StageManifest, output_dir: Path) -> Path:
    """Serialize and write manifest.json inside *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_stage_manifest(manifest_path: Path) -> StageManifest:
    """Load a StageManifest from a manifest.json file."""
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return StageManifest.from_dict(data)


def build_master_manifest(
    stage_manifests: List[StageManifest],
    output_path: Path,
) -> dict:
    """
    Combine all stage manifests into a single master_manifest.json.

    Returns
    -------
    dict
        The master manifest data structure.
    """
    total_images = sum(m.total_images for m in stage_manifests)
    total_annotations = sum(sum(m.class_distribution.values()) for m in stage_manifests)

    # Aggregate class distribution
    all_classes: Dict[int, int] = {}
    for m in stage_manifests:
        for cls_id, cnt in m.class_distribution.items():
            all_classes[cls_id] = all_classes.get(cls_id, 0) + cnt

    all_families = sorted(set(f for m in stage_manifests for f in m.families_used))
    all_materials = sorted(set(mat for m in stage_manifests for mat in m.materials_used))
    all_commits = [m.commit_hash for m in stage_manifests if m.commit_hash]

    master = {
        "version": "1.0",
        "total_images": total_images,
        "total_annotations": total_annotations,
        "total_classes": len(all_classes),
        "n_stages": len(stage_manifests),
        "all_families": all_families,
        "all_materials": all_materials,
        "commit_hashes": all_commits,
        "class_distribution": {str(k): v for k, v in sorted(all_classes.items())},
        "stages": [m.to_dict() for m in stage_manifests],
        "generation_total_seconds": sum(m.generation_time_seconds for m in stage_manifests),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    return master
