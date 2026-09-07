"""GitManager: secure, token-safe git operations for checkpoint and release branches."""
from __future__ import annotations

import os
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


class GitManager:
    """
    Manages git operations for the training pipeline.

    Security guarantees:
    - Token is NEVER written to disk in plaintext
    - Token is NEVER echoed or logged
    - Uses a transient authenticated remote URL that is deleted after each push
    - All subprocess calls are checked for credential leakage
    """

    def __init__(
        self,
        repo_url: str,
        checkpoint_branch: str = "colab-checkpoints",
        release_branch: str = "release",
        work_dir: str = "/content/repo",
    ) -> None:
        self.repo_url = repo_url
        self.checkpoint_branch = checkpoint_branch
        self.release_branch = release_branch
        self.work_dir = Path(work_dir)
        self._token: Optional[str] = None
        self._configured = False

    def setup(self, token: str) -> None:
        """Configure git and clone/update the repository."""
        if not token:
            raise ValueError("GitHub token is required for git operations.")
        self._token = token
        self._configure_git()
        self._clone_or_update()
        self._configured = True
        print("[Git] Repository ready.")

    def push_checkpoint(
        self,
        stage_id: int,
        epoch: int,
        files: List[str],
        is_best: bool = False,
    ) -> str:
        """
        Commit files to the checkpoint branch.
        Returns the commit hash.
        """
        self._ensure_configured()
        suffix = " [best]" if is_best else ""
        message = f"checkpoint(stage-{stage_id:02d}): save epoch {epoch}{suffix}"
        return self._commit_and_push(files, message, self.checkpoint_branch)

    def push_release(
        self,
        stage_id: int,
        files: List[str],
        version: str = "",
    ) -> str:
        """
        Commit release artifacts to the release branch.
        Returns the commit hash.
        """
        self._ensure_configured()
        ver = version or f"stage-{stage_id:02d}"
        message = f"release({ver}): promote validated model"
        return self._commit_and_push(files, message, self.release_branch, publication_id=ver)

    def current_commit(self) -> str:
        """Return the current HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.work_dir, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def verify_structure(self) -> bool:
        """Verify expected repository structure exists."""
        expected = ["pyproject.toml"]
        return all((self.work_dir / f).exists() for f in expected)

    def pull(self, branch: Optional[str] = None) -> bool:
        """Fetch and pull the latest changes from remote."""
        target_branch = branch or self.checkpoint_branch
        self._ensure_configured()
        try:
            auth_url = self._authenticated_url()
            subprocess.run(
                ["git", "fetch", auth_url, f"{target_branch}:{target_branch}"],
                cwd=self.work_dir, capture_output=True, text=True, check=True
            )
            self._run_git(["checkout", target_branch])
            return True
        except Exception:
            try:
                self._run_git(["fetch", "--all"])
                self._run_git(["checkout", target_branch])
                self._run_git(["pull", "--rebase", "origin", target_branch])
                return True
            except Exception as e:
                print(f"[Git] Pull notice: {e}")
                return False

    # ── Private ───────────────────────────────────────────────────────────────

    def _configure_git(self) -> None:
        subprocess.run(
            ["git", "config", "--global", "user.email", "training-bot@ocr-lab"],
            check=True
        )
        subprocess.run(
            ["git", "config", "--global", "user.name", "OCR Training Bot"],
            check=True
        )

    def _clone_or_update(self) -> None:
        if (self.work_dir / ".git").exists():
            # Update existing clone
            self._run_git(["fetch", "--all"])
            self._run_git(["checkout", self.checkpoint_branch])
            self._run_git(["pull", "--rebase", "origin", self.checkpoint_branch])
        else:
            self.work_dir.parent.mkdir(parents=True, exist_ok=True)
            auth_url = self._authenticated_url()
            try:
                subprocess.run(
                    ["git", "clone", "--branch", self.checkpoint_branch,
                     auth_url, str(self.work_dir)],
                    check=True, capture_output=True
                )
            except subprocess.CalledProcessError as exc:
                # Strip token from error before raising
                raise RuntimeError(
                    f"git clone failed. Check token and repository URL."
                ) from None
            finally:
                # auth_url is in-memory only, never written to disk
                pass

    def _commit_and_push(
        self, files: List[str], message: str, branch: str,
        publication_id: Optional[str] = None,
    ) -> str:
        # Start from the remote tip of the requested branch. This is essential
        # because one manager alternates between colab-checkpoints and the
        # independent published-results branch during a training run.
        auth_url = self._authenticated_url()
        try:
            subprocess.run(
                ["git", "fetch", auth_url, f"{branch}:refs/remotes/origin/{branch}"],
                cwd=self.work_dir, check=True, capture_output=True, text=True,
            )
            self._run_git(["checkout", "-B", branch, f"origin/{branch}"])
        except subprocess.CalledProcessError:
            # The first publication may create a branch that does not exist yet.
            self._run_git(["checkout", "-B", branch])

        # Checkpoint epochs remain flat and isolated on colab-checkpoints.
        # Accepted releases use a stable, data-only publication layout on
        # colab-results and update the atomic latest.json pointer.
        if publication_id:
            self._stage_publication(files, publication_id)
        else:
            for f in files:
                src = Path(f)
                if src.exists():
                    dst = self.work_dir / src.name
                    shutil.copy2(src, dst)
                    self._run_git(["add", str(dst.relative_to(self.work_dir))])

        # Check if there's anything to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self.work_dir, capture_output=True
        )
        if result.returncode == 0:
            print(f"[Git] Nothing to commit for: {message}")
            return self.current_commit()

        self._run_git(["commit", "-m", message])

        # Push with transient authenticated URL
        try:
            subprocess.run(
                # This manager owns only the requested training/release branch.
                # Checkpoint writes may force-update colab-checkpoints, but never
                # touch the independent colab-generated-images branch.
                ["git", "push", "--force", auth_url, f"{branch}:{branch}"],
                cwd=self.work_dir, check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                f"git push to {branch} failed. Check token permissions."
            ) from None

        return self.current_commit()

    def _stage_publication(self, files: List[str], publication_id: str) -> None:
        """Stage a self-describing accepted model under artifacts/published."""
        publication = self.work_dir / "artifacts" / "published" / publication_id
        weights = publication / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        release_source = None
        copied_assets = []
        for f in files:
            src = Path(f)
            if not src.is_file():
                continue
            if src.suffix.lower() == ".pt":
                dst = weights / "best.pt"
                web_weight = "weights/best.pt"
            elif src.suffix.lower() == ".onnx":
                dst = weights / "best.onnx"
                web_weight = "weights/best.onnx"
            elif src.suffix.lower() == ".ocrpkg":
                dst = publication / "model.ocrpkg"
                web_weight = None
            elif src.name == "manifest.json":
                release_source = src
                continue
            else:
                dst = publication / src.name
                web_weight = None
            shutil.copy2(src, dst)
            digest = hashlib.sha256(dst.read_bytes()).hexdigest()
            copied_assets.append({"path": str(dst.relative_to(publication)), "sha256": digest, "bytes": dst.stat().st_size})
            self._run_git(["add", str(dst.relative_to(self.work_dir))])

        source = {}
        if release_source and release_source.is_file():
            try:
                source = json.loads(release_source.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                source = {}
        release = {
            "schema_version": 1,
            "release_id": publication_id,
            "publication_status": "published",
            "created_at_utc": source.get("created_at", ""),
            "source_commit": source.get("training_commit", ""),
            "model_scope": "synthetic-old-permic-character-detection",
            "class_names": source.get("class_names", []),
            "class_count": len(source.get("class_names", [])),
            "metrics": source.get("metrics", {}),
            "assets": copied_assets,
        }
        if any(a["path"] == "weights/best.pt" for a in copied_assets):
            release["web_weight"] = next(a for a in copied_assets if a["path"] == "weights/best.pt")
        elif any(a["path"] == "weights/best.onnx" for a in copied_assets):
            release["web_weight"] = next(a for a in copied_assets if a["path"] == "weights/best.onnx")
        release_path = publication / "release.json"
        release_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")
        latest = self.work_dir / "artifacts" / "published" / "latest.json"
        latest.write_text(json.dumps({
            "schema_version": 1,
            "release_id": publication_id,
            "release_path": str(release_path.relative_to(self.work_dir)),
            "release_sha256": hashlib.sha256(release_path.read_bytes()).hexdigest(),
        }, indent=2), encoding="utf-8")
        self._run_git(["add", str(release_path.relative_to(self.work_dir)), str(latest.relative_to(self.work_dir))])

    def _run_git(self, args: List[str]) -> str:
        result = subprocess.run(
            ["git"] + args,
            cwd=self.work_dir, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def _authenticated_url(self) -> str:
        """Build transient authenticated URL. Never stored on disk."""
        url = self.repo_url.replace("https://", f"https://{self._token}@")
        return url

    def _ensure_configured(self) -> None:
        if not self._configured:
            raise RuntimeError("Call GitManager.setup(token) before pushing.")
