"""Hook execution system for pre/post save/restore commands."""

from __future__ import annotations

import subprocess
import sys

from rich.console import Console

from .models import HookConfig

console = Console()


def run_hook(
    hook_name: str,
    command: str | None,
    item_name: str,
) -> bool:
    """
    Execute a hook command via PowerShell.

    Parameters
    ----------
    hook_name : str
        Name of the hook (e.g. 'pre_save', 'post_restore').
    command : str | None
        The shell command to run. If None, no-op.
    item_name : str
        Config item name, for logging context.

    Returns
    -------
    bool
        True if hook succeeded or was skipped, False on failure.

    """
    if not command:
        return True

    console.print(f"  [dim]Running {hook_name} hook for {item_name}...[/dim]")
    try:
        shell = _get_shell()
        result = subprocess.run(  # noqa: S603
            [shell, "-Command", command],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.stdout.strip():
            console.print(f"    {result.stdout.strip()}")
        if result.returncode != 0:
            console.print(
                f"  [yellow]⚠ {hook_name} hook failed (exit {result.returncode})[/yellow]"
            )
            if result.stderr.strip():
                console.print(f"    [dim]{result.stderr.strip()}[/dim]")
            return False
    except subprocess.TimeoutExpired:
        console.print(f"  [yellow]⚠ {hook_name} hook timed out[/yellow]")
        return False
    except FileNotFoundError:
        console.print(f"  [yellow]⚠ Shell not found for {hook_name} hook[/yellow]")
        return False
    return True


def run_hooks_for_phase(
    phase: str,
    hooks: HookConfig,
    item_name: str,
) -> bool:
    """
    Run the appropriate hook for a save/restore phase.

    Parameters
    ----------
    phase : str
        One of 'pre_save', 'post_save', 'pre_restore',
        'post_restore'.
    hooks : HookConfig
        The hook configuration for the item.
    item_name : str
        Config item name, for logging context.

    Returns
    -------
    bool
        True if hook succeeded or was not defined.

    """
    command = getattr(hooks, phase, None)
    return run_hook(phase, command, item_name)


def _get_shell() -> str:
    """Return the appropriate shell executable."""
    if sys.platform == "win32":
        return "powershell.exe"
    return "/bin/sh"  # type: ignore[unreachable]
