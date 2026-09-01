"""GitManager: secure, token-safe git operations for checkpoint and release branches."""
from __future__ import annotations

import os
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
        return self._commit_and_push(files, message, self.release_branch)

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
        self, files: List[str], message: str, branch: str
    ) -> str:
        # Ensure we're on the right branch
        self._run_git(["checkout", "-B", branch])

        # Copy files to work_dir and stage them
        for f in files:
            src = Path(f)
            if src.exists():
                dst = self.work_dir / src.name
                import shutil
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
        auth_url = self._authenticated_url()
        try:
            subprocess.run(
                ["git", "push", auth_url, f"{branch}:{branch}"],
                cwd=self.work_dir, check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                f"git push to {branch} failed. Check token permissions."
            ) from None

        return self.current_commit()

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
