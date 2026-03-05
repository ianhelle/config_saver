"""VS Code / Insiders profile handler — settings, extensions, snippets."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from config_saver.utils import expand_env_vars

from .base import BaseHandler

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

console = Console()

# Paths per variant (relative to %APPDATA% and %USERPROFILE%)
_VARIANT_CONFIG: dict[str, dict[str, str]] = {
    "code": {
        "user_data": "%APPDATA%\\Code\\User",
        "extensions": "%USERPROFILE%\\.vscode\\extensions",
        "cli_cmd": "code",
    },
    "code-insiders": {
        "user_data": "%APPDATA%\\Code - Insiders\\User",
        "extensions": ("%USERPROFILE%\\.vscode-insiders\\extensions"),
        "cli_cmd": "code-insiders",
    },
}

# Config files/dirs within the User folder to back up
_PROFILE_ITEMS = [
    "settings.json",
    "keybindings.json",
    "snippets",
    "globalStorage",
]


def _get_extensions_list(
    extensions_dir: Path,
) -> list[dict[str, str]]:
    """
    Build a manifest of installed extensions.

    Parses extension directory names which follow the
    pattern: publisher.name-version

    """
    extensions: list[dict[str, str]] = []
    if not extensions_dir.is_dir():
        return extensions
    for ext_dir in sorted(extensions_dir.iterdir()):
        if not ext_dir.is_dir():
            continue
        # Try to read package.json for richer metadata
        pkg = ext_dir / "package.json"
        if pkg.is_file():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                extensions.append({
                    "id": (f"{data.get('publisher', '?')}.{data.get('name', '?')}"),
                    "version": data.get("version", "?"),
                    "dir_name": ext_dir.name,
                })
                continue
            except json.JSONDecodeError, KeyError:
                pass
        extensions.append({
            "id": ext_dir.name,
            "version": "?",
            "dir_name": ext_dir.name,
        })
    return extensions


def _copy_tree_with_progress(
    src: Path,
    dest: Path,
    label: str,
) -> int:
    """
    Copy a directory tree, returning total files copied.

    Shows a progress message for large copies.

    """
    if not src.is_dir():
        return 0
    console.print(f"    Copying {label}...", end=" ")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    count = sum(1 for _ in dest.rglob("*") if _.is_file())
    size_mb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / (1024 * 1024)
    console.print(f"[dim]{count} files ({size_mb:.1f} MB)[/dim]")
    return count


class VSCodeHandler(BaseHandler):
    """Save/restore VS Code and VS Code Insiders profiles."""

    name = "vscode"

    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Save VS Code profile config and extensions."""
        variants = config_item.variants or ["code"]

        for variant in variants:
            vc = _VARIANT_CONFIG.get(variant)
            if not vc:
                console.print(f"  [yellow]⚠ Unknown variant: {variant}[/yellow]")
                continue

            console.print(f"  [bold]{variant}[/bold]")
            user_data = expand_env_vars(vc["user_data"])
            ext_dir = expand_env_vars(vc["extensions"])

            # Save config files to normal backup store
            config_dest = store.item_dir(item_name) / variant
            config_dest.mkdir(parents=True, exist_ok=True)

            for item in _PROFILE_ITEMS:
                src = user_data / item
                if src.is_file():
                    shutil.copy2(src, config_dest / item)
                    console.print(f"    ✓ {item}")
                elif src.is_dir():
                    _copy_tree_with_progress(src, config_dest / item, item)
                else:
                    console.print(f"    [dim]— {item} (not found)[/dim]")

            # Save extension list manifest
            ext_list = _get_extensions_list(ext_dir)
            manifest = config_dest / "extensions_list.json"
            manifest.write_text(
                json.dumps(ext_list, indent=2),
                encoding="utf-8",
            )
            console.print(f"    ✓ extensions_list.json ({len(ext_list)} extensions)")

            # Save extensions to dedicated folder
            # (NOT in latest/archive — single copy)
            ext_backup = store.root / "vscode_extensions" / variant
            _copy_tree_with_progress(ext_dir, ext_backup, "extensions")

    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Restore VS Code profile config and extensions."""
        variants = config_item.variants or ["code"]

        for variant in variants:
            vc = _VARIANT_CONFIG.get(variant)
            if not vc:
                console.print(f"  [yellow]⚠ Unknown variant: {variant}[/yellow]")
                continue

            console.print(f"  [bold]{variant}[/bold]")
            config_src = store.item_dir(item_name) / variant
            if not config_src.is_dir():
                console.print(f"    [yellow]No backup found for {variant}[/yellow]")
                continue

            user_data = expand_env_vars(vc["user_data"])
            ext_dir = expand_env_vars(vc["extensions"])
            self._restore_config_files(config_src, user_data, dry_run)
            self._restore_extensions(store, variant, ext_dir, dry_run)
            self._show_manifest(config_src)

    @staticmethod
    def _restore_config_files(
        config_src: Path,
        user_data: Path,
        dry_run: bool,
    ) -> None:
        """Restore settings, keybindings, snippets, globalStorage."""
        for item in _PROFILE_ITEMS:
            src = config_src / item
            dest = user_data / item
            if not src.exists():
                continue
            if dry_run:
                console.print(f"    [dim]Would restore: {item}[/dim]")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(src, dest)
                console.print(f"    ✓ {item}")
            elif src.is_dir():
                _copy_tree_with_progress(src, dest, item)

    @staticmethod
    def _restore_extensions(
        store: BackupStore,
        variant: str,
        ext_dir: Path,
        dry_run: bool,
    ) -> None:
        """Restore extensions from the dedicated folder."""
        ext_backup = store.root / "vscode_extensions" / variant
        if not ext_backup.is_dir():
            console.print("    [dim]— No extension backup found[/dim]")
            return
        if dry_run:
            ext_count = sum(1 for d in ext_backup.iterdir() if d.is_dir())
            console.print(f"    [dim]Would restore {ext_count} extension(s)[/dim]")
        else:
            _copy_tree_with_progress(ext_backup, ext_dir, "extensions")

    @staticmethod
    def _show_manifest(config_src: Path) -> None:
        """Print extension count from the saved manifest."""
        manifest = config_src / "extensions_list.json"
        if manifest.is_file():
            ext_list = json.loads(manifest.read_text(encoding="utf-8"))
            console.print(f"    {len(ext_list)} extension(s) in profile")
