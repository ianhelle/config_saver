"""Tests for git_repos handler scanning logic."""

from __future__ import annotations

import subprocess
from pathlib import Path

from config_saver.handlers.git_repos import (
    _find_git_dirs,
    _scan_git_repos,
)


def _init_git_repo(repo_dir: Path) -> None:
    """Initialize a bare git repo for testing."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", str(repo_dir)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "remote",
            "add",
            "origin",
            "https://dev.azure.com/org/proj/_git/repo",
        ],
        capture_output=True,
        check=True,
    )


class TestFindGitDirs:
    """Tests for _find_git_dirs."""

    def test_finds_git_dirs(self, tmp_path):
        """Finds .git directories recursively."""
        repo = tmp_path / "project1"
        _init_git_repo(repo)
        results = _find_git_dirs(tmp_path)
        git_dirs = [r.name for r in results]
        assert ".git" in git_dirs

    def test_skips_node_modules(self, tmp_path):
        """Skips .git inside node_modules."""
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / ".git").mkdir()
        results = _find_git_dirs(tmp_path)
        assert len(results) == 0

    def test_finds_nested_repos(self, tmp_path):
        """Finds repos at different nesting levels."""
        _init_git_repo(tmp_path / "a")
        _init_git_repo(tmp_path / "org" / "b")
        results = _find_git_dirs(tmp_path)
        assert len(results) == 2


class TestScanGitRepos:
    """Tests for _scan_git_repos."""

    def test_scan_returns_repo_info(self, tmp_path):
        """Scan returns metadata for found repos."""
        _init_git_repo(tmp_path / "myrepo")
        repos = _scan_git_repos(tmp_path)
        assert len(repos) == 1
        repo = repos[0]
        assert "path" in repo
        assert "remote_url" in repo
        assert "branch" in repo

    def test_scan_nonexistent_root(self, tmp_path):
        """Scan of nonexistent directory returns empty list."""
        repos = _scan_git_repos(tmp_path / "nope")
        assert repos == []

    def test_scan_captures_remote(self, tmp_path):
        """Scan captures the remote URL."""
        _init_git_repo(tmp_path / "repo1")
        repos = _scan_git_repos(tmp_path)
        assert repos[0]["remote_url"] == "https://dev.azure.com/org/proj/_git/repo"
