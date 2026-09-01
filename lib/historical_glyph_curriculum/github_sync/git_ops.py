"""
Git operations for committing and pushing stage datasets.

Uses subprocess (no gitpython dependency). Tokens are NEVER written
to disk, logged, or stored in git configuration.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: Path, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a git command, redacting any token from logged output."""
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=capture, text=True)
    if check and result.returncode != 0:
        # Redact any token-like strings before logging
        err = _redact(result.stderr or result.stdout or "")
        raise RuntimeError(f"git command failed: {' '.join(cmd[:3])}\n{err}")
    return result


def _redact(text: str) -> str:
    """Remove GitHub tokens (ghp_*, github_pat_*, or Bearer tokens) from text."""
    text = re.sub(r"(https?://)([^@\s]+@)", r"\1***@", text)
    text = re.sub(r"ghp_[A-Za-z0-9]{36}", "***REDACTED***", text)
    text = re.sub(r"github_pat_[A-Za-z0-9_]{82}", "***REDACTED***", text)
    return text


class GitManager:
    """
    Manages git operations for the colab-checkpoints branch.

    Parameters
    ----------
    repo_dir:
        Path to the local git repository root.
    remote_url:
        HTTPS remote URL (without token).
    branch:
        Target branch name.
    """

    def __init__(
        self,
        repo_dir: Path,
        remote_url: str,
        branch: str = "colab-checkpoints",
    ) -> None:
        self.repo_dir = Path(repo_dir)
        self.remote_url = remote_url
        self.branch = branch
        self._original_remote: Optional[str] = None

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def configure_identity(
        self,
        name: str = "Glyph Studio Bot",
        email: str = "bot@glyphstudio.ai",
    ) -> None:
        """Set git user.name and user.email (required on fresh Colab sessions)."""
        _run(["git", "config", "user.name", name], self.repo_dir)
        _run(["git", "config", "user.email", email], self.repo_dir)

    # ------------------------------------------------------------------
    # Repository info
    # ------------------------------------------------------------------

    def verify_repo(self) -> dict:
        """
        Verify this is a valid git repo and return repo info.

        Raises
        ------
        RuntimeError
            If the directory is not a git repository.
        """
        try:
            remote = _run(["git", "remote", "get-url", "origin"], self.repo_dir).stdout.strip()
            branch = _run(["git", "branch", "--show-current"], self.repo_dir).stdout.strip()
            status = _run(["git", "status", "--short"], self.repo_dir).stdout.strip()
        except RuntimeError as e:
            raise RuntimeError(f"Not a valid git repository at {self.repo_dir}: {e}")
        return {
            "remote_url": _redact(remote),
            "current_branch": branch,
            "status": status,
            "working_dir": str(self.repo_dir),
        }

    # ------------------------------------------------------------------
    # Staging and committing
    # ------------------------------------------------------------------

    def stage_files(self, paths: list[str | Path]) -> None:
        """Stage one or more files/directories."""
        str_paths = [str(p) for p in paths]
        _run(["git", "add"] + str_paths, self.repo_dir)

    def commit(self, message: str) -> str:
        """Create a git commit. Returns the short commit hash."""
        _run(["git", "commit", "-m", message], self.repo_dir)
        result = _run(["git", "rev-parse", "--short", "HEAD"], self.repo_dir)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Pushing
    # ------------------------------------------------------------------

    def _auth_url(self, token: str) -> str:
        """Build an authenticated HTTPS URL. Token is only held in memory."""
        url = self.remote_url.rstrip("/")
        if url.startswith("https://github.com/"):
            return url.replace("https://", f"https://{token}@")
        return url

    def push_with_auth(self, token: str) -> bool:
        """
        Push to the remote branch using a temporary authenticated URL.

        The token is injected into the URL in memory only — never written
        to git config, disk, or printed.
        """
        auth_url = self._auth_url(token)
        # Use a transient remote push without modifying stored config
        result = subprocess.run(
            ["git", "push", auth_url, f"HEAD:{self.branch}"],
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            err = _redact(result.stderr or result.stdout)
            log.error("Push failed: %s", err)
            return False
        return True

    # ------------------------------------------------------------------
    # Full workflow
    # ------------------------------------------------------------------

    def commit_and_push_stage(
        self,
        stage_id: int,
        stage_name: str,
        dataset_dir: Path,
        token: str,
        previews_dir: Optional[Path] = None,
        metadata_dir: Optional[Path] = None,
    ) -> str:
        """
        Add, commit, and push one stage dataset.

        Parameters
        ----------
        token:
            GitHub personal access token. Never stored or logged.

        Returns
        -------
        str
            Short commit hash.
        """
        # Pre-flight check
        info = self.verify_repo()
        print(f"  Repository: {info['remote_url']}")
        print(f"  Branch:     {info['current_branch']} → {self.branch}")

        # Stage files
        to_add = [dataset_dir]
        if previews_dir and previews_dir.exists():
            to_add.append(previews_dir)
        if metadata_dir and metadata_dir.exists():
            to_add.append(metadata_dir)

        print(f"  Staging {len(to_add)} directories...")
        self.stage_files(to_add)

        # Commit
        msg = f"dataset(stage-{stage_id:02d}): add {stage_name} samples"
        commit_hash = self.commit(msg)
        print(f"  Committed: {commit_hash}")

        # Push
        print(f"  Pushing to {self.branch}...")
        success = self.push_with_auth(token)
        if not success:
            raise RuntimeError("Push failed — see logs above for details (token redacted).")

        print(f"  ✓ Stage {stage_id:02d} pushed. Hash: {commit_hash}")
        return commit_hash

    # ------------------------------------------------------------------
    # Clone helper (class method, used from notebook)
    # ------------------------------------------------------------------

    @staticmethod
    def clone(
        url: str,
        branch: str,
        target_dir: Path,
        token: Optional[str] = None,
    ) -> "GitManager":
        """
        Clone a repository to *target_dir* and return a GitManager for it.

        Parameters
        ----------
        token:
            Optional auth token for private repos.
        """
        target_dir = Path(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        auth_url = url
        if token:
            if url.startswith("https://github.com/"):
                auth_url = url.replace("https://", f"https://{token}@")

        cmd = ["git", "clone", "--branch", branch, "--depth", "1", auth_url, str(target_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err = _redact(result.stderr)
            raise RuntimeError(f"Clone failed: {err}")

        return GitManager(repo_dir=target_dir, remote_url=url, branch=branch)
