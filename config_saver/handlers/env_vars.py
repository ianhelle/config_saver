"""Environment variables handler — save/restore user env vars."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from rich.console import Console

from .base import BaseHandler

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

console = Console()

ENV_BACKUP_FILE = "env_vars.json"


def _get_user_env_vars() -> dict[str, str]:
    """
    Read user environment variables from the Windows registry.

    Returns a dict of variable name → value for the current user.

    """
    result = subprocess.run(  # noqa: S603
        [
            "reg",
            "query",
            "HKCU\\Environment",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    env_vars: dict[str, str] = {}
    if result.returncode != 0:
        return env_vars
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("HKEY_"):
            continue
        parts = line.split(None, 2)
        if len(parts) >= 3:  # noqa: PLR2004
            name, _reg_type, value = parts[0], parts[1], parts[2]
            env_vars[name] = value
    return env_vars


def _filter_vars(
    env_vars: dict[str, str],
    include_vars: list[str] | None,
    exclude_vars: list[str] | None,
) -> dict[str, str]:
    """Apply include/exclude filters to env vars."""
    result = dict(env_vars)
    if include_vars:
        include_set = {v.upper() for v in include_vars}
        result = {k: v for k, v in result.items() if k.upper() in include_set}
    if exclude_vars:
        exclude_set = {v.upper() for v in exclude_vars}
        result = {k: v for k, v in result.items() if k.upper() not in exclude_set}
    return result


class EnvVarsHandler(BaseHandler):
    """Save/restore user environment variables."""

    name = "env_vars"

    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Save user environment variables to a JSON file."""
        env_vars = _get_user_env_vars()
        env_vars = _filter_vars(
            env_vars,
            config_item.include_vars,
            config_item.exclude_vars,
        )
        dest = store.item_dir(item_name)
        out_file = dest / ENV_BACKUP_FILE
        out_file.write_text(
            json.dumps(env_vars, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        console.print(f"  Saved {len(env_vars)} environment variable(s)")

    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Restore user environment variables from backup."""
        src_dir = store.item_dir(item_name)
        backup_file = src_dir / ENV_BACKUP_FILE
        if not backup_file.is_file():
            console.print(f"  [yellow]No env var backup found for {item_name}[/yellow]")
            return

        saved_vars: dict[str, str] = json.loads(backup_file.read_text(encoding="utf-8"))
        current_vars = _get_user_env_vars()

        # Show diff
        added = set(saved_vars) - set(current_vars)
        changed = {
            k
            for k in set(saved_vars) & set(current_vars)
            if saved_vars[k] != current_vars[k]
        }
        if not added and not changed:
            console.print("  No changes needed")
            return

        if added:
            console.print(f"  [green]New variables: {', '.join(sorted(added))}[/green]")
        if changed:
            console.print(
                f"  [yellow]Changed variables: {', '.join(sorted(changed))}[/yellow]"
            )
            for var in sorted(changed):
                console.print(f"    {var}: {current_vars[var]!r} → {saved_vars[var]!r}")

        if dry_run:
            return

        restored = 0
        for var in sorted(added | changed):
            value = saved_vars[var]
            result = subprocess.run(  # noqa: S603
                [
                    "setx",
                    var,
                    value,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                restored += 1
            else:
                console.print(f"  [yellow]⚠ Failed to set {var}[/yellow]")
        console.print(f"  Restored {restored} environment variable(s)")
