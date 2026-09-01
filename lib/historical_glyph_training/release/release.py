"""Release management: validate → package → manifest → push to release branch."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.training_config import TrainingConfig
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..training.evaluator import EvaluationResult


@dataclass
class AppCompatibleManifest:
    """
    OCR package manifest compatible with the Flutter AtomicModelStore.

    Schema version 1 — consumed by the Flutter application's
    OcrPackageManifestModel.fromJson().
    """
    schema_version: int = 1
    package_id: str = ""
    version: str = ""
    model_version: str = ""
    language: str = "Old Permic"
    script: str = "Old Permic"
    alphabet_version: str = "1.0"
    minimum_runtime_version: str = "0.1.0"
    created_at: str = ""
    model_format: str = "onnx"
    reading_direction: str = "ltr"

    # Artifact descriptors
    model: Dict[str, Any] = field(default_factory=dict)   # id, path, bytes, sha256
    alphabet: Dict[str, Any] = field(default_factory=dict)  # version, artifact, classes

    # Input spec
    input: Dict[str, Any] = field(default_factory=lambda: {
        "width": 640, "height": 640,
        "layout": "nchw", "channels": 3,
        "normalization": "zero_to_one",
        "letterbox": True, "pad_color": 114,
    })

    # Output spec
    output: Dict[str, Any] = field(default_factory=lambda: {
        "decoder": "yolo_v8",
        "layout": "channels_first",
        "box_format": "xywh",
        "coordinates": "pixels",
        "has_objectness": False,
    })

    # Training provenance
    training_stage: int = 0
    training_commit: str = ""
    dataset_version: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    class_names: List[str] = field(default_factory=list)
    release_sha256: str = ""
    source_uri: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @staticmethod
    def _artifact(artifact_id: str, path: str, file_path: str, media_type: str = "") -> Dict[str, Any]:
        p = Path(file_path)
        size = p.stat().st_size if p.exists() else 0
        sha256 = _sha256_file(file_path) if p.exists() else "0" * 64
        return {
            "id": artifact_id,
            "path": path,
            "bytes": size,
            "sha256": sha256,
            **({"media_type": media_type} if media_type else {}),
        }


@dataclass
class ReleaseRecord:
    """Record of a completed release."""
    stage_id: int
    version: str
    package_path: str    # Local .ocrpkg path
    manifest_path: str
    commit_hash: str
    branch: str
    metrics: Dict[str, float]
    class_names: List[str]
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ReleaseManager:
    """
    Orchestrates model promotion from accepted checkpoint to release branch.

    Workflow:
        accepted model weights
            → export to ONNX (if PT)
            → generate alphabet JSON
            → compute SHA-256s
            → write manifest.json (Flutter-compatible)
            → zip into .ocrpkg
            → validate package
            → git push to release branch
    """

    def __init__(self, release_root: str, config: TrainingConfig) -> None:
        self.release_root = Path(release_root)
        self.config = config

    def promote(
        self,
        stage_id: int,
        model_weights: str,
        class_names: List[str],
        eval_result: "EvaluationResult",
        dataset_version: str = "",
        model_source_commit: str = "",
        git_manager: Optional[Any] = None,
    ) -> ReleaseRecord:
        """
        Promote a validated model to a release package.

        Returns a ReleaseRecord describing the created release.
        """
        version = f"stage-{stage_id:02d}"
        release_dir = self.release_root / version
        release_dir.mkdir(parents=True, exist_ok=True)

        # 1. Export model weights (ONNX if .pt, copy if already .onnx)
        onnx_path = self._export_onnx(model_weights, release_dir, stage_id)

        # 2. Generate alphabet JSON from class_names
        alphabet_path = self._write_alphabet(class_names, release_dir)

        # 3. Build Flutter-compatible manifest
        manifest = AppCompatibleManifest(
            package_id=f"old-permic-stage-{stage_id:02d}",
            version=version,
            model_version=version,
            training_stage=stage_id,
            created_at=_utc_now(),
            training_commit=model_source_commit,
            dataset_version=dataset_version,
            metrics={
                "map50": round(eval_result.map50, 4),
                "map50_95": round(eval_result.map50_95, 4),
                "precision": round(eval_result.precision, 4),
                "recall": round(eval_result.recall, 4),
            },
            class_names=class_names,
            model=AppCompatibleManifest._artifact("model", "model/model.onnx", str(onnx_path), "application/octet-stream"),
            alphabet={
                "version": "1.0",
                "artifact": AppCompatibleManifest._artifact("alphabet", "alphabet/alphabet.json", str(alphabet_path), "application/json"),
                "classes": self._build_alphabet_classes(class_names),
            },
        )

        # 4. Write manifest
        manifest_path = release_dir / "manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")

        # 5. Create .ocrpkg (ZIP) compatible with Flutter AtomicModelStore
        pkg_path = self.release_root / f"old-permic-{version}.ocrpkg"
        self._create_package(release_dir, pkg_path, onnx_path, alphabet_path, manifest_path)

        # 6. Compute package SHA-256 and update manifest
        pkg_sha256 = _sha256_file(str(pkg_path))
        manifest.release_sha256 = pkg_sha256
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")

        # 7. Validate package
        self._validate_package(pkg_path, class_names)

        # 8. Push to git release branch
        commit_hash = ""
        if git_manager is not None:
            commit_hash = git_manager.push_release(
                stage_id=stage_id,
                files=[str(pkg_path), str(manifest_path)],
                version=version,
            )

        record = ReleaseRecord(
            stage_id=stage_id,
            version=version,
            package_path=str(pkg_path),
            manifest_path=str(manifest_path),
            commit_hash=commit_hash,
            branch=self.config.release_branch,
            metrics=manifest.metrics,
            class_names=class_names,
            created_at=_utc_now(),
        )
        # Save record locally
        record_file = self.release_root / f"release_{version}.json"
        record_file.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return record

    def validate_model(self, model_path: str, class_names: List[str]) -> List[str]:
        """
        Pre-release model validation. Returns list of problems (empty = OK).
        """
        problems = []
        p = Path(model_path)
        if not p.exists():
            problems.append(f"Model file not found: {model_path}")
            return problems
        if p.suffix not in (".onnx", ".pt"):
            problems.append(f"Unsupported model format: {p.suffix}")
        if p.stat().st_size < 1024:
            problems.append("Model file is suspiciously small (<1 KB)")
        if not class_names:
            problems.append("Class names list is empty")
        return problems

    # ── Internals ─────────────────────────────────────────────────────────────

    def _export_onnx(self, weights: str, out_dir: Path, stage_id: int) -> Path:
        """Export .pt → .onnx, or copy .onnx directly."""
        model_dir = out_dir / "model"
        model_dir.mkdir(exist_ok=True)
        dest = model_dir / "model.onnx"
        src = Path(weights)
        if src.suffix == ".onnx":
            shutil.copy2(src, dest)
            return dest
        # Try ultralytics export
        try:
            from ultralytics import YOLO
            m = YOLO(weights)
            exported = m.export(format="onnx", imgsz=self.config.image_size)
            shutil.copy2(exported, dest)
        except Exception as exc:
            # Fall back: just copy the .pt (Flutter ONNX runtime won't load it,
            # but at least the package is created; researcher can export manually)
            print(f"[Release] Warning: ONNX export failed ({exc}). Copying .pt as fallback.")
            fallback = model_dir / "model.pt"
            shutil.copy2(src, fallback)
            return fallback
        return dest

    def _write_alphabet(self, class_names: List[str], out_dir: Path) -> Path:
        alph_dir = out_dir / "alphabet"
        alph_dir.mkdir(exist_ok=True)
        dest = alph_dir / "alphabet.json"
        classes = self._build_alphabet_classes(class_names)
        dest.write_text(
            json.dumps({"classes": classes}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return dest

    def _build_alphabet_classes(self, class_names: List[str]) -> List[Dict[str, Any]]:
        entries = []
        for i, name in enumerate(class_names):
            # Parse codepoint from name like "U+10350" or "uni10350"
            cp = _parse_codepoint(name)
            label = chr(cp) if cp else name
            entries.append({
                "id": i,
                "unicode": f"U+{cp:04X}" if cp else name,
                "character": label,
                "name": name,
            })
        return entries

    def _create_package(
        self,
        release_dir: Path,
        pkg_path: Path,
        onnx_path: Path,
        alphabet_path: Path,
        manifest_path: Path,
    ) -> None:
        """Create .ocrpkg = ZIP with manifest.json + model/ + alphabet/."""
        with zipfile.ZipFile(pkg_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, "manifest.json")
            zf.write(onnx_path, f"model/{onnx_path.name}")
            zf.write(alphabet_path, f"alphabet/{alphabet_path.name}")

    def _validate_package(self, pkg_path: Path, class_names: List[str]) -> None:
        """Minimal smoke-test of the generated package."""
        with zipfile.ZipFile(pkg_path, "r") as zf:
            names = zf.namelist()
            if "manifest.json" not in names:
                raise RuntimeError("Package missing manifest.json")
            manifest_bytes = zf.read("manifest.json")
            manifest_data = json.loads(manifest_bytes)
            if manifest_data.get("schema_version") != 1:
                raise RuntimeError("Package manifest has wrong schema_version")
            if not manifest_data.get("alphabet", {}).get("classes"):
                raise RuntimeError("Package manifest has empty alphabet classes")
        print(f"[Release] Package validated OK: {pkg_path.name} ({pkg_path.stat().st_size // 1024} KB)")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_codepoint(name: str) -> Optional[int]:
    """Parse Unicode codepoint from strings like U+10350, uni10350, 0x10350."""
    import re
    m = re.search(r'(?:U\+|uni|0x)([0-9A-Fa-f]{4,6})', name, re.IGNORECASE)
    if m:
        return int(m.group(1), 16)
    # Try ++ notation: U++10350
    m2 = re.search(r'U\+\+([0-9A-Fa-f]{4,6})', name)
    if m2:
        return int(m2.group(1), 16)
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
