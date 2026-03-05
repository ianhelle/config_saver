"""YAML configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import BackupConfig


def load_config(config_path: Path) -> BackupConfig:
    """Load and validate a config-saver YAML file."""
    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ValueError(f"Config file is empty: {config_path}")
    return BackupConfig.model_validate(raw)


def find_config(start_dir: Path | None = None) -> Path:
    """
    Search for config_saver.yaml in standard locations.

    Search order:
    1. Explicit start_dir (if given)
    2. Current working directory
    3. User home directory (~/.config/config_saver/)
    """
    names = ["config_saver.yaml", "config_saver.yml"]
    search_dirs: list[Path] = []
    if start_dir:
        search_dirs.append(start_dir)
    search_dirs.append(Path.cwd())
    search_dirs.append(Path.home() / ".config" / "config_saver")

    for d in search_dirs:
        for name in names:
            candidate = d / name
            if candidate.is_file():
                return candidate

    raise FileNotFoundError(
        "No config_saver.yaml found. Searched: " + ", ".join(str(d) for d in search_dirs)
    )
