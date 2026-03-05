"""Click-based CLI for config-saver."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from config_saver.config import find_config, load_config
from config_saver.handlers import *  # noqa: F403, F401
from config_saver.handlers.base import get_handler, list_handlers
from config_saver.hooks import run_hooks_for_phase
from config_saver.models import BackupConfig
from config_saver.store import BackupStore

console = Console()


def _load(config_path: str | None) -> tuple[BackupConfig, BackupStore]:
    """Load config and create backup store."""
    try:
        path = Path(config_path) if config_path else find_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    cfg = load_config(path)
    store = BackupStore(cfg.backup_root, max_archives=cfg.max_archives)
    store.ensure_dirs()
    return cfg, store


def _resolve_items(
    cfg: BackupConfig,
    all_flag: bool,
    items_str: str | None,
) -> list[str]:
    """Determine which config items to process."""
    if all_flag:
        return list(cfg.configs.keys())
    if items_str:
        requested = [i.strip() for i in items_str.split(",")]
        valid = []
        for name in requested:
            if name in cfg.configs:
                valid.append(name)
            else:
                console.print(f"[yellow]⚠ Unknown item: {name}[/yellow]")
        return valid
    return _interactive_select(cfg)


def _interactive_select(cfg: BackupConfig) -> list[str]:
    """Prompt user to select config items interactively."""
    items = list(cfg.configs.keys())
    if not items:
        console.print("[yellow]No config items defined[/yellow]")
        return []

    console.print("\n[bold]Available config items:[/bold]")
    for i, name in enumerate(items, 1):
        desc = cfg.configs[name].description or name
        console.print(f"  {i}. {name} — {desc}")
    console.print(f"  {len(items) + 1}. [bold]All[/bold]")

    try:
        choice = input("\nSelect items (comma-separated numbers, or 'a' for all): ").strip()
    except KeyboardInterrupt, EOFError:
        return []

    if choice.lower() in ("a", "all", str(len(items) + 1)):
        return items

    selected: list[str] = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx])
    return selected


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to config YAML file.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: str | None) -> None:
    """Config Saver — save and restore Windows configuration."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    if ctx.invoked_subcommand is None:
        _interactive_main(config_path)


def _interactive_main(config_path: str | None) -> None:
    """Show interactive menu when run without subcommand."""
    console.print("\n[bold]Config Saver[/bold] — save and restore configuration\n")
    console.print("  1. Save configurations")
    console.print("  2. Restore configurations")
    console.print("  3. List configured items")
    console.print("  4. Show backup archives")
    console.print("  5. Exit")

    try:
        choice = input("\nSelect action: ").strip()
    except KeyboardInterrupt, EOFError:
        return

    if choice == "1":
        cfg, store = _load(config_path)
        items = _interactive_select(cfg)
        _do_save(cfg, store, items)
    elif choice == "2":
        cfg, store = _load(config_path)
        items = _interactive_select(cfg)
        _do_restore(cfg, store, items, dry_run=False)
    elif choice == "3":
        cfg, store = _load(config_path)
        _do_list(cfg, store)
    elif choice == "4":
        cfg, store = _load(config_path)
        _do_archives(store)


@cli.command()
@click.option("--all", "all_flag", is_flag=True, help="Save all items.")
@click.option("--items", "items_str", default=None, help="Comma-separated item names.")
@click.pass_context
def save(ctx: click.Context, all_flag: bool, items_str: str | None) -> None:
    """Save configuration items to backup."""
    cfg, store = _load(ctx.obj["config_path"])
    items = _resolve_items(cfg, all_flag, items_str)
    _do_save(cfg, store, items)


@cli.command()
@click.option("--all", "all_flag", is_flag=True, help="Restore all items.")
@click.option("--items", "items_str", default=None, help="Comma-separated item names.")
@click.option("--dry-run", is_flag=True, help="Preview without applying changes.")
@click.option("--archive", default=None, help="Restore from a specific archive timestamp.")
@click.pass_context
def restore(
    ctx: click.Context,
    all_flag: bool,
    items_str: str | None,
    dry_run: bool,
    archive: str | None,
) -> None:
    """Restore configuration items from backup."""
    cfg, store = _load(ctx.obj["config_path"])
    items = _resolve_items(cfg, all_flag, items_str)
    _do_restore(cfg, store, items, dry_run=dry_run, archive_ts=archive)


@cli.command(name="list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List configured items and backup status."""
    cfg, store = _load(ctx.obj["config_path"])
    _do_list(cfg, store)


@cli.command()
@click.pass_context
def archives(ctx: click.Context) -> None:
    """Show available backup archives."""
    cfg, store = _load(ctx.obj["config_path"])
    _do_archives(store)


def _do_save(cfg: BackupConfig, store: BackupStore, items: list[str]) -> None:
    """Execute save for the given items."""
    if not items:
        console.print("[yellow]No items selected[/yellow]")
        return

    # Archive current state before overwriting
    store.create_archive_snapshot()

    for name in items:
        config_item = cfg.configs[name]
        console.print(f"\n[bold]Saving {name}...[/bold]")
        run_hooks_for_phase("pre_save", config_item.hooks, name)

        try:
            handler = get_handler(config_item.handler)
            handler.save(name, config_item, store)
        except Exception as e:  # noqa: BLE001
            console.print(f"  [red]Error: {e}[/red]")
            continue

        run_hooks_for_phase("post_save", config_item.hooks, name)

    console.print("\n[green]✓ Save complete[/green]")


def _do_restore(
    cfg: BackupConfig,
    store: BackupStore,
    items: list[str],
    *,
    dry_run: bool = False,
    archive_ts: str | None = None,  # noqa: ARG001
) -> None:
    """Execute restore for the given items."""
    if not items:
        console.print("[yellow]No items selected[/yellow]")
        return

    if dry_run:
        console.print("[dim]Dry run — no changes will be made[/dim]\n")

    for name in items:
        config_item = cfg.configs[name]
        console.print(f"\n[bold]Restoring {name}...[/bold]")

        if not dry_run:
            run_hooks_for_phase("pre_restore", config_item.hooks, name)

        try:
            handler = get_handler(config_item.handler)
            handler.restore(name, config_item, store, dry_run=dry_run)
        except Exception as e:  # noqa: BLE001
            console.print(f"  [red]Error: {e}[/red]")
            continue

        if not dry_run:
            run_hooks_for_phase("post_restore", config_item.hooks, name)

    if not dry_run:
        console.print("\n[green]✓ Restore complete[/green]")


def _do_list(cfg: BackupConfig, store: BackupStore) -> None:
    """Display configured items and their backup status."""
    table = Table(title="Config Items")
    table.add_column("Name", style="bold")
    table.add_column("Handler")
    table.add_column("Description")
    table.add_column("Backed Up", justify="center")

    backed_up_items = set(store.list_items())

    for name, item in cfg.configs.items():
        has_backup = "✓" if name in backed_up_items else "—"
        table.add_row(name, item.handler, item.description, has_backup)

    console.print(table)
    console.print(f"\nRegistered handlers: {', '.join(list_handlers())}")


def _do_archives(store: BackupStore) -> None:
    """Display available archive timestamps."""
    archives_list = store.list_archives()
    if not archives_list:
        console.print("No archives found")
        return
    console.print("[bold]Available archives:[/bold]")
    for ts in archives_list:
        items = store.list_items(archive_ts=ts)
        console.print(f"  {ts} ({len(items)} items)")
