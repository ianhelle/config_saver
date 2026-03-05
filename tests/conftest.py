"""Shared test fixtures for config-saver tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal valid config_saver.yaml in tmp_path."""
    backup_root = tmp_path / "backups"
    config_data = {
        "backup_root": str(backup_root),
        "configs": {
            "test_file": {
                "handler": "file",
                "description": "Test file config",
                "source": str(tmp_path / "source.txt"),
            },
            "test_registry": {
                "handler": "registry",
                "description": "Test registry config",
                "keys": [
                    "HKCU\\Software\\Test\\Key1",
                ],
            },
        },
    }
    config_path = tmp_path / "config_saver.yaml"
    config_path.write_text(yaml.dump(config_data), encoding="utf-8")
    return config_path


@pytest.fixture
def backup_root(tmp_path: Path) -> Path:
    """Return a temp directory to use as backup root."""
    root = tmp_path / "backup_store"
    root.mkdir()
    return root
