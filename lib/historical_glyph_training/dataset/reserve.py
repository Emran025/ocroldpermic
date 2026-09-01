"""Reserve pool: diverse sample selection for targeted weak-class remediation."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ReservePool:
    """
    Manages the reserved dataset pool for targeted remediation.

    Selects diverse samples for weak classes, tracking which samples
    have been used in previous remediation rounds to avoid repetition.
    """

    def __init__(self, reserve_files: List[str], stage_id: int) -> None:
        self.stage_id = stage_id
        self._all_files = list(reserve_files)
        self._used: Dict[int, Set[str]] = {}  # {round: {file, ...}}
        self._class_index: Dict[int, List[str]] = {}  # {class_id: [files]}
        self._build_class_index()

    # ── Public API ────────────────────────────────────────────────────────────

    def select_for_remediation(
        self,
        weak_class_ids: List[int],
        round_number: int,
        max_samples_per_class: int = 100,
    ) -> List[str]:
        """
        Select diverse reserve samples relevant to weak classes.

        Prioritizes:
        1. Unused samples (not used in previous rounds)
        2. Diversity across metadata dimensions (material/family from filename)
        """
        used_so_far: Set[str] = set()
        for used_set in self._used.values():
            used_so_far |= used_set

        selected: List[str] = []
        seen: Set[str] = set()

        for cid in weak_class_ids:
            candidates = self._class_index.get(cid, [])
            # Prefer unused
            unused = [f for f in candidates if f not in used_so_far]
            pool = unused if unused else candidates
            # Diverse selection
            diverse = self._select_diverse(pool, max_samples_per_class)
            for f in diverse:
                if f not in seen:
                    selected.append(f)
                    seen.add(f)

        return selected

    def mark_used(self, files: List[str], round_number: int) -> None:
        self._used.setdefault(round_number, set()).update(files)

    def available_for_class(self, class_id: int) -> List[str]:
        return list(self._class_index.get(class_id, []))

    def stats(self) -> Dict[str, Any]:
        total_used = len({f for s in self._used.values() for f in s})
        return {
            "total_reserve": len(self._all_files),
            "total_used": total_used,
            "classes_with_reserve": len(self._class_index),
            "rounds": list(self._used.keys()),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_class_index(self) -> None:
        for img_path in self._all_files:
            for cid in self._read_class_ids(img_path):
                self._class_index.setdefault(cid, []).append(img_path)

    def _read_class_ids(self, image_path: str) -> List[int]:
        label = self._label_path(image_path)
        if not label.exists():
            return []
        ids = []
        for line in label.read_text().strip().splitlines():
            parts = line.split()
            if parts:
                try:
                    ids.append(int(parts[0]))
                except ValueError:
                    pass
        return ids

    def _label_path(self, image_path: str) -> Path:
        p = Path(image_path)
        label = Path(str(p.parent).replace("images", "labels")) / (p.stem + ".txt")
        if label.exists():
            return label
        return p.with_suffix(".txt")

    def _select_diverse(self, files: List[str], n: int) -> List[str]:
        """
        Select up to n files maximising diversity.
        Parses filename metadata like mat-{material}_rot-{angle}_... where available.
        Falls back to even spacing across the sorted list.
        """
        if len(files) <= n:
            return list(files)

        # Extract diversity keys from filename
        keyed = [(self._diversity_key(f), f) for f in files]
        keyed.sort(key=lambda x: x[0])

        # Spread selection across sorted diverse list
        step = len(keyed) / n
        return [keyed[int(i * step)][1] for i in range(n)]

    def _diversity_key(self, path: str) -> str:
        name = Path(path).stem
        # Try to parse metadata: mat, family, rot, degrad
        parts = []
        for key in ("mat", "fam", "rot", "deg", "bg"):
            m = re.search(rf"{key}[-_]([a-zA-Z0-9.]+)", name)
            if m:
                parts.append(m.group(1))
        return "_".join(parts) if parts else name
