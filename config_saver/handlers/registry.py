"""Windows registry handler — export/import registry keys."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from rich.console import Console

from .base import BaseHandler

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

console = Console()


def _safe_filename(key: str) -> str:
    """Convert a registry key path to a safe filename."""
    return key.replace("\\", "_").replace("/", "_") + ".reg"


class RegistryHandler(BaseHandler):
    """Export/import Windows registry keys via reg.exe."""

    name = "registry"

    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Export registry keys to .reg files in the backup store."""
        if not config_item.keys:
            console.print(f"  [yellow]No registry keys configured for {item_name}[/yellow]")
            return
        dest = store.item_dir(item_name)
        saved = 0
        for key in config_item.keys:
            out_file = dest / _safe_filename(key)
            result = subprocess.run(  # noqa: S603
                [
                    "reg",
                    "export",
                    key,
                    str(out_file),
                    "/y",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                saved += 1
            else:
                console.print(
                    f"  [yellow]⚠ Failed to export {key}: {result.stderr.strip()}[/yellow]"
                )
        console.print(f"  Exported {saved}/{len(config_item.keys)} registry key(s)")

    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Import .reg files from the backup store."""
        src_dir = store.item_dir(item_name)
        reg_files = sorted(src_dir.glob("*.reg"))
        if not reg_files:
            console.print(f"  [yellow]No registry backups found for {item_name}[/yellow]")
            return

        for reg_file in reg_files:
            if dry_run:
                console.print(f"  [dim]Would import: {reg_file.name}[/dim]")
                continue
            result = subprocess.run(  # noqa: S603
                ["reg", "import", str(reg_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                console.print(f"  Imported {reg_file.name}")
            else:
                console.print(
                    f"  [yellow]⚠ Failed to import"
                    f" {reg_file.name}:"
                    f" {result.stderr.strip()}"
                    f"[/yellow]"
                )
