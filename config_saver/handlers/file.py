"""File copy handler — save/restore files and globs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from config_saver.utils import expand_path

from .base import BaseHandler

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

console = Console()


class FileHandler(BaseHandler):
    """Copy files to/from the backup store."""

    name = "file"

    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Save configured files to the backup store."""
        dest = store.item_dir(item_name)
        paths = self._collect_source_paths(config_item)
        saved = 0
        for src in paths:
            if not src.is_file():
                console.print(f"  [yellow]⚠ Not found: {src}[/yellow]")
                continue
            target = dest / src.name
            shutil.copy2(src, target)
            saved += 1
        console.print(f"  Saved {saved} file(s) to {dest.name}/")

    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Restore files from the backup store."""
        src_dir = store.item_dir(item_name)
        paths = self._collect_source_paths(config_item)
        if not any(src_dir.iterdir()):
            console.print(f"  [yellow]No backup found for {item_name}[/yellow]")
            return

        original_map = {p.name: p for p in paths}
        restored = 0
        for backed_up in src_dir.iterdir():
            if not backed_up.is_file():
                continue
            target = original_map.get(backed_up.name)
            if target is None:
                target = paths[0].parent / backed_up.name
            if dry_run:
                console.print(f"  [dim]Would restore: {backed_up.name} → {target}[/dim]")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backed_up, target)
            restored += 1
        if not dry_run:
            console.print(f"  Restored {restored} file(s) for {item_name}")

    @staticmethod
    def _collect_source_paths(
        config_item: ConfigItem,
    ) -> list[Path]:
        """
        Gather all source file paths from the config item.

        Handles source as string or list, plus additional_files.

        """
        paths: list[Path] = []
        if config_item.source:
            sources = (
                config_item.source
                if isinstance(config_item.source, list)
                else [config_item.source]
            )
            paths.extend(expand_path(s) for s in sources)
        if config_item.additional_files:
            paths.extend(expand_path(f) for f in config_item.additional_files)
        return paths
