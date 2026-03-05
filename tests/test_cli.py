"""Tests for the CLI module."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from config_saver.cli import cli


def _make_config(tmp_path: Path) -> Path:
    """Create a test config file with a file handler item."""
    src = tmp_path / "source.txt"
    src.write_text("content", encoding="utf-8")
    config_data = {
        "backup_root": str(tmp_path / "backups"),
        "configs": {
            "test_file": {
                "handler": "file",
                "description": "Test file",
                "source": str(src),
            },
        },
    }
    cfg_path = tmp_path / "config_saver.yaml"
    cfg_path.write_text(yaml.dump(config_data), encoding="utf-8")
    return cfg_path


class TestCliSave:
    """Tests for the save subcommand."""

    def test_save_all(self, tmp_path):
        """Save --all saves configured items."""
        cfg = _make_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(cfg), "save", "--all"])
        assert result.exit_code == 0
        assert "Save complete" in result.output

    def test_save_specific_item(self, tmp_path):
        """Save --items saves only the named item."""
        cfg = _make_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--config", str(cfg), "save", "--items", "test_file"],
        )
        assert result.exit_code == 0
        assert "Saving test_file" in result.output

    def test_save_unknown_item(self, tmp_path):
        """Save with unknown item name shows warning."""
        cfg = _make_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--config", str(cfg), "save", "--items", "nonexistent"],
        )
        assert result.exit_code == 0
        assert "Unknown item" in result.output


class TestCliRestore:
    """Tests for the restore subcommand."""

    def test_restore_dry_run(self, tmp_path):
        """Restore --dry-run shows preview without changes."""
        cfg = _make_config(tmp_path)
        runner = CliRunner()
        # First save
        runner.invoke(cli, ["--config", str(cfg), "save", "--all"])
        # Then dry-run restore
        result = runner.invoke(
            cli,
            ["--config", str(cfg), "restore", "--all", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output


class TestCliList:
    """Tests for the list subcommand."""

    def test_list_shows_items(self, tmp_path):
        """List command shows configured items."""
        cfg = _make_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(cfg), "list"])
        assert result.exit_code == 0
        assert "test_file" in result.output


class TestCliArchives:
    """Tests for the archives subcommand."""

    def test_archives_empty(self, tmp_path):
        """Archives command works with no archives."""
        cfg = _make_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(cfg), "archives"])
        assert result.exit_code == 0
