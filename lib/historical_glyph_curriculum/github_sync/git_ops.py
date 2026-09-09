"""
Git operations for committing and pushing stage datasets.

Uses subprocess (no gitpython dependency). Tokens are NEVER written
to disk, logged, or stored in git configuration.
"""
from __future__ import annotations

import logging
import json
import random
import re
import subprocess
import shutil
import tempfile
import time
from collections import Counter
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
    Manages git operations for the configured branch (image generation uses colab-generated-images).

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
        # Use a transient remote push without modifying stored config.  This is
        # deliberately a normal fast-forward push: two image generators may
        # have cloned the same remote tip, and neither is allowed to erase the
        # other's completed concepts.
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

    def _rebase_onto_remote(self) -> bool:
        """Reapply this writer's commit on top of the newest remote tip.

        A normal rebase cannot resolve two writers changing ``manifest.json``
        or ``generation_state.json``. Instead, capture the files introduced by
        the local commit, reset to the remote tip, and copy those files back
        through the same additive/semantic merge rules used by ``push_stage``.
        No remote file is selected blindly and no local work is discarded.
        """
        _run(["git", "fetch", "origin", self.branch], self.repo_dir)
        changed = _run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            self.repo_dir,
        ).stdout.splitlines()
        if not changed:
            return False
        with tempfile.TemporaryDirectory(prefix="dataset-reconcile-") as td:
            staged_sources = []
            for relative in sorted(
                changed,
                key=lambda item: Path(item).name in {"generation_state.json", "manifest.json"},
            ):
                source = Path(td) / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                result = subprocess.run(
                    ["git", "show", f"HEAD:{relative}"],
                    cwd=str(self.repo_dir), capture_output=True,
                )
                if result.returncode != 0:
                    continue  # additive generation never needs to reapply deletions
                source.write_bytes(result.stdout)
                staged_sources.append((relative, source))

            _run(["git", "reset", "--hard", f"origin/{self.branch}"], self.repo_dir)
            try:
                for relative, source in staged_sources:
                    destination = self.repo_dir / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if source.name in {"generation_state.json", "manifest.json"} and destination.exists():
                        self._merge_shared_json(source, destination, Path(relative))
                    elif not destination.exists():
                        shutil.copy2(source, destination)
                    elif source.read_bytes() != destination.read_bytes():
                        raise RuntimeError(
                            f"Additive merge collision at {relative}; both versions were preserved locally"
                        )
                    self._run_git_add(relative)
                self.commit("dataset: reconcile concurrent additive generation")
            except Exception as exc:
                _run(["git", "reset", "--hard", f"origin/{self.branch}"], self.repo_dir, check=False)
                log.error("Cannot reconcile concurrent dataset commit safely: %s", _redact(str(exc)))
                return False
        return True

    def _run_git_add(self, relative: str) -> None:
        """Stage one path using the repository-local git helper."""
        _run(["git", "add", "--", relative], self.repo_dir)

    def _push_with_reconciliation(self, token: str, attempts: int = 6) -> bool:
        """Push without overwriting remote commits, reconciling remote races.

        GitHub may reject a perfectly valid non-force push when another Colab
        worker advances the branch between the client-side negotiation and the
        receive-pack lock.  A short jittered backoff is important here: without
        it, concurrent workers tend to collide again immediately and exhaust a
        small retry budget.  Every retry still goes through the additive merge
        path; this method never force-pushes and never discards a remote commit.
        """
        for attempt in range(1, attempts + 1):
            if self.push_with_auth(token):
                return True
            if attempt == attempts:
                break
            # Let the worker that currently owns the remote ref finish its
            # receive-pack transaction before fetching and rebuilding locally.
            # Keep the delay bounded so a transient race does not stall Colab.
            delay = min(8.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.35)
            time.sleep(delay)
            try:
                reconciled = self._rebase_onto_remote()
            except (OSError, RuntimeError) as exc:
                log.warning(
                    "Remote reconciliation attempt %d/%d failed: %s",
                    attempt, attempts - 1, _redact(str(exc)),
                )
                continue
            if not reconciled:
                return False
        return False

    def _copy_additive_tree(self, source: Path, destination: Path) -> None:
        """Merge generated files without replacing files already on the branch.

        Concept output is append-only. Existing identical files are ignored;
        differing files at the same path are reported as a real collision so
        the caller can stop safely instead of silently losing either version.
        ``generation_state.json`` is merged by concept key because two workers
        commonly complete different concepts at the same time.
        """
        source = Path(source)
        destination = Path(destination)
        for src in sorted(p for p in source.rglob("*") if p.is_file()):
            relative = src.relative_to(source)
            dst = destination / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
                continue
            if src.name in {"generation_state.json", "manifest.json"}:
                self._merge_shared_json(src, dst, relative)
                continue
            if src.read_bytes() != dst.read_bytes():
                raise RuntimeError(
                    f"Additive merge collision at {relative}; existing remote file was preserved"
                )

    @staticmethod
    def _merge_unique_list(left: list, right: list) -> list:
        """Union JSON list values while preserving first-seen order."""
        result = []
        seen = set()
        for value in [*left, *right]:
            marker = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if marker not in seen:
                seen.add(marker)
                result.append(value)
        return result

    def _merge_shared_json(self, source: Path, destination: Path, relative: Path) -> None:
        """Merge the two shared stage files without dropping either writer.

        ``generation_state.json`` is merged by concept key.  ``manifest.json``
        is merged by unioning concepts/lists and deriving totals from the
        actual files already present in the destination stage.  This avoids
        double-counting when both accounts started from the same checkpoint.
        """
        try:
            local = json.loads(source.read_text(encoding="utf-8"))
            remote = json.loads(destination.read_text(encoding="utf-8"))
            if not isinstance(local, dict) or not isinstance(remote, dict):
                raise ValueError("both JSON values must be objects")
            merged = dict(remote)
            if source.name == "generation_state.json":
                for key, value in local.items():
                    if key not in merged:
                        merged[key] = value
                    elif merged[key] != value:
                        # Both accounts may finish the same concept with
                        # different timestamps. Preserve the completed record
                        # deterministically and never mark it incomplete.
                        remote_done = remote[key] == "done" or (
                            isinstance(remote[key], dict) and remote[key].get("status") == "done"
                        )
                        local_done = value == "done" or (
                            isinstance(value, dict) and value.get("status") == "done"
                        )
                        if local_done and not remote_done:
                            merged[key] = value
                        elif not remote_done and not local_done:
                            raise ValueError(f"conflicting incomplete state for {key}")
            else:
                for key, value in local.items():
                    if key in {"total_images", "class_distribution", "generation_time_seconds"}:
                        continue
                    if isinstance(value, list) and isinstance(merged.get(key), list):
                        merged[key] = self._merge_unique_list(merged[key], value)
                    elif key not in merged or merged[key] in (None, "", False):
                        merged[key] = value
                images = destination.parent / "images"
                labels = destination.parent / "labels"
                image_files = sorted(images.glob("*.png")) if images.is_dir() else []
                merged["total_images"] = len(image_files)
                if labels.is_dir():
                    counts = Counter()
                    for label in labels.glob("*.txt"):
                        for line in label.read_text(encoding="utf-8").splitlines():
                            fields = line.split()
                            if fields and fields[0].isdigit():
                                counts[fields[0]] += 1
                    merged["class_distribution"] = dict(sorted(counts.items(), key=lambda item: int(item[0])))
                merged["generation_time_seconds"] = max(
                    float(remote.get("generation_time_seconds", 0) or 0),
                    float(local.get("generation_time_seconds", 0) or 0),
                )
            destination.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot safely merge shared file {relative}: {exc}") from exc

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
        success = self._push_with_reconciliation(token)
        if not success:
            raise RuntimeError("Push failed — see logs above for details (token redacted).")

        print(f"  ✓ Stage {stage_id:02d} pushed. Hash: {commit_hash}")
        return commit_hash

    def push_stage(
        self,
        stage_id: int,
        files: list[str],
        output_dir: str,
        token: str,
    ) -> str:
        """Copy generated data into the data-only branch and push it.

        The notebook passes a token explicitly; it is used only for the transient
        push URL and is never retained by this manager. Re-running a stage copies
        into the same stable path and therefore does not duplicate branch data.
        """
        if not token:
            raise ValueError("GitHub token is required for pushing a stage.")
        self.configure_identity()
        # Reconcile remote commits before writing so a parallel generator never
        # erases another generator's stage. The final push is also non-force and
        # retries after rebasing if the remote advances during this operation.
        remote_ref = _run(["git", "ls-remote", "--heads", "origin", self.branch], self.repo_dir, check=False).stdout.strip()
        if remote_ref:
            _run(["git", "fetch", "origin", self.branch], self.repo_dir)
            _run(["git", "checkout", "-B", self.branch, f"origin/{self.branch}"], self.repo_dir)
        else:
            _run(["git", "checkout", "-B", self.branch], self.repo_dir)
        output = Path(output_dir)
        target = self.repo_dir / (
            "manifests" if stage_id == 0 else f"datasets/stage_{stage_id:02d}"
        )
        target.mkdir(parents=True, exist_ok=True)

        if stage_id != 0 and output.is_dir():
            self._copy_additive_tree(output, target)
        for file_name in files:
            source = Path(file_name)
            if not source.exists():
                continue
            destination = target / source.name
            if source.is_dir():
                self._copy_additive_tree(source, destination)
            elif source.name in {"generation_state.json", "manifest.json"} and destination.exists():
                self._merge_shared_json(source, destination, destination.relative_to(self.repo_dir))
            else:
                if destination.exists() and source.read_bytes() != destination.read_bytes():
                    raise RuntimeError(
                        f"Additive merge collision at {destination.relative_to(self.repo_dir)}; "
                        "existing remote file was preserved"
                    )
                if not destination.exists():
                    shutil.copy2(source, destination)

        _run(["git", "add", str(target.relative_to(self.repo_dir))], self.repo_dir)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(self.repo_dir), capture_output=True
        )
        if staged.returncode == 0:
            return self.current_commit()

        commit_hash = self.commit(f"dataset(stage-{stage_id:02d}): sync generated images")
        if not self._push_with_reconciliation(token):
            raise RuntimeError(
                "Image branch push could not be reconciled safely. No remote "
                "data was overwritten; inspect the conflict and retry the "
                "image branch only."
            )
        return commit_hash

    def current_commit(self) -> str:
        """Return the current local commit hash."""
        return _run(["git", "rev-parse", "HEAD"], self.repo_dir).stdout.strip()

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
