"""Git repo scanner handler — record and re-clone repos."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from config_saver.utils import expand_path

from .base import BaseHandler

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

console = Console()

REPOS_MANIFEST = "repos.json"
CLONE_SCRIPT = "clone_repos.ps1"

# Directories to skip during recursive scan
SKIP_DIRS = frozenset({
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
})


def _scan_git_repos(root: Path) -> list[dict[str, str]]:
    """
    Recursively scan for git repos under root.

    Returns a list of dicts with repo metadata.

    """
    repos: list[dict[str, str]] = []
    if not root.is_dir():
        console.print(f"  [yellow]⚠ Scan root not found: {root}[/yellow]")
        return repos

    for git_dir in _find_git_dirs(root):
        repo_dir = git_dir.parent
        info = _get_repo_info(repo_dir, root)
        if info:
            repos.append(info)
    return repos


def _find_git_dirs(root: Path) -> list[Path]:
    """Find all .git directories under root, skipping junk dirs."""
    results: list[Path] = []
    try:
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            if entry.name in SKIP_DIRS:
                if entry.name == ".git":
                    results.append(entry)
                continue
            if entry.name == ".git":
                results.append(entry)
            else:
                results.extend(_find_git_dirs(entry))
    except PermissionError:
        pass
    return results


def _get_repo_info(
    repo_dir: Path,
    scan_root: Path,
) -> dict[str, str] | None:
    """Extract metadata from a git repo directory."""
    try:
        remote = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo_dir), "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        remote_url = ""
        for line in remote.stdout.splitlines():
            if "(fetch)" in line:
                parts = line.split()
                if len(parts) >= 2:  # noqa: PLR2004
                    remote_url = parts[1]
                break

        branch = subprocess.run(  # noqa: S603
            [
                "git",
                "-C",
                str(repo_dir),
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        current_branch = branch.stdout.strip() or "main"

        try:
            rel_path = repo_dir.relative_to(scan_root)
        except ValueError:
            rel_path = repo_dir

        return {
            "path": str(rel_path),
            "remote_url": remote_url,
            "branch": current_branch,
            "absolute_path": str(repo_dir),
        }
    except Exception:  # noqa: BLE001
        return None


class GitReposHandler(BaseHandler):
    """Scan directories for git repos and generate clone scripts."""

    name = "git_repos"

    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Scan for git repos and save manifest + clone script."""
        if not config_item.scan_roots:
            console.print(f"  [yellow]No scan_roots configured for {item_name}[/yellow]")
            return

        all_repos: list[dict[str, str]] = []
        for root_str in config_item.scan_roots:
            root = expand_path(root_str)
            console.print(f"  Scanning {root}...")
            repos = _scan_git_repos(root)
            # Tag each repo with its scan root
            for repo in repos:
                repo["scan_root"] = root_str
            all_repos.extend(repos)

        dest = store.item_dir(item_name)

        # Save JSON manifest
        manifest = dest / REPOS_MANIFEST
        manifest.write_text(
            json.dumps(all_repos, indent=2),
            encoding="utf-8",
        )

        # Generate clone script
        script = dest / CLONE_SCRIPT
        lines = [
            "# Auto-generated clone script",
            "# Run this to re-clone all repositories",
            "",
        ]
        for repo in all_repos:
            if not repo["remote_url"]:
                lines.append(f"# Skipped (no remote): {repo['path']}")
                continue
            clone_dir = repo["absolute_path"]
            lines.append(f'git clone "{repo["remote_url"]}" "{clone_dir}"')
            if repo["branch"] != "main":
                lines.append(f'git -C "{clone_dir}" checkout {repo["branch"]}')
            lines.append("")
        script.write_text("\n".join(lines), encoding="utf-8")

        console.print(f"  Found {len(all_repos)} repo(s), saved manifest + clone script")

    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Show repo manifest and optionally run clone script."""
        src_dir = store.item_dir(item_name)
        manifest_file = src_dir / REPOS_MANIFEST
        if not manifest_file.is_file():
            console.print(f"  [yellow]No repo manifest found for {item_name}[/yellow]")
            return

        repos: list[dict[str, str]] = json.loads(manifest_file.read_text(encoding="utf-8"))
        console.print(f"  Found {len(repos)} repo(s):")
        for repo in repos:
            status = "✓" if Path(repo["absolute_path"]).is_dir() else "✗"
            console.print(f"    {status} {repo['path']} ({repo['remote_url']})")

        missing = [
            r for r in repos if not Path(r["absolute_path"]).is_dir() and r["remote_url"]
        ]
        if not missing:
            console.print("  All repos already present")
            return

        if dry_run:
            console.print(f"  [dim]Would clone {len(missing)} repo(s)[/dim]")
            return

        console.print(f"  Cloning {len(missing)} missing repo(s)...")
        for repo in missing:
            console.print(f"  Cloning {repo['path']}...")
            clone_dir = Path(repo["absolute_path"])
            clone_dir.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(  # noqa: S603
                [
                    "git",
                    "clone",
                    repo["remote_url"],
                    str(clone_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                console.print(
                    f"  [yellow]⚠ Failed to clone"
                    f" {repo['path']}:"
                    f" {result.stderr.strip()}"
                    f"[/yellow]"
                )
