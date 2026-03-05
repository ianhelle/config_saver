"""Backup store — manages latest/ and archive/ directory structure."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .utils import expand_path


class BackupStore:
    """Manages the backup directory structure with latest + timestamped archives."""

    def __init__(self, backup_root: str, *, max_archives: int = 10) -> None:
        """Initialize the backup store with the given root path."""
        self.root = expand_path(backup_root)
        self.latest_dir = self.root / "latest"
        self.archive_dir = self.root / "archive"
        self.max_archives = max_archives

    def ensure_dirs(self) -> None:
        """Create the backup directory structure if it doesn't exist."""
        self.latest_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def item_dir(self, item_name: str, *, archive_ts: str | None = None) -> Path:
        """
        Get the backup directory for a specific config item.

        Args:
            item_name: Name of the config item (e.g. 'vscode_profile').
            archive_ts: If given, return path in a specific archive snapshot.

        """
        if archive_ts:
            base = self.archive_dir / archive_ts
        else:
            base = self.latest_dir
        d = base / item_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_archive_snapshot(self) -> str:
        """
        Copy the current latest/ to a timestamped archive.

        Returns the timestamp string used for the archive directory name.
        """
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        dest = self.archive_dir / ts
        if self.latest_dir.exists() and any(self.latest_dir.iterdir()):
            shutil.copytree(self.latest_dir, dest, dirs_exist_ok=True)
        else:
            dest.mkdir(parents=True, exist_ok=True)
        self._prune_archives()
        return ts

    def _prune_archives(self) -> None:
        """Remove oldest archives exceeding max_archives."""
        archives = self.list_archives()
        for old_ts in archives[self.max_archives :]:
            shutil.rmtree(self.archive_dir / old_ts)

    def list_archives(self) -> list[str]:
        """List available archive timestamps, newest first."""
        if not self.archive_dir.exists():
            return []
        return [
            d.name for d in sorted(self.archive_dir.iterdir(), reverse=True) if d.is_dir()
        ]

    def list_items(self, archive_ts: str | None = None) -> list[str]:
        """List config items present in a backup (latest or specific archive)."""
        base = self.archive_dir / archive_ts if archive_ts else self.latest_dir
        if not base.exists():
            return []
        return [d.name for d in sorted(base.iterdir()) if d.is_dir()]
