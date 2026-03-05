"""Tests for config_saver.config — YAML loading and config search."""

from __future__ import annotations

import pytest
import yaml

from config_saver.config import find_config, load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_config):
        """Load a valid YAML config file."""
        cfg = load_config(tmp_config)
        assert cfg.backup_root is not None
        assert "test_file" in cfg.configs
        assert cfg.configs["test_file"].handler == "file"

    def test_load_config_with_registry(self, tmp_config):
        """Registry config items are parsed correctly."""
        cfg = load_config(tmp_config)
        reg = cfg.configs["test_registry"]
        assert reg.handler == "registry"
        assert reg.keys is not None
        assert len(reg.keys) == 1

    def test_load_empty_file_raises(self, tmp_path):
        """An empty YAML file raises ValueError."""
        empty = tmp_path / "config_saver.yaml"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="Config file is empty"):
            load_config(empty)

    def test_load_invalid_yaml_raises(self, tmp_path):
        """Malformed YAML raises an error."""
        bad = tmp_path / "config_saver.yaml"
        bad.write_text("backup_root: [invalid", encoding="utf-8")
        with pytest.raises(Exception):
            load_config(bad)

    def test_load_missing_handler_raises(self, tmp_path):
        """A config item without handler raises validation error."""
        data = {
            "backup_root": "C:\\backups",
            "configs": {
                "bad_item": {
                    "description": "no handler",
                },
            },
        }
        cfg_path = tmp_path / "config_saver.yaml"
        cfg_path.write_text(yaml.dump(data), encoding="utf-8")
        with pytest.raises(Exception):
            load_config(cfg_path)

    def test_load_config_with_hooks(self, tmp_path):
        """Config items with hooks are parsed correctly."""
        data = {
            "backup_root": str(tmp_path / "backups"),
            "configs": {
                "item1": {
                    "handler": "file",
                    "source": "test.txt",
                    "hooks": {
                        "pre_save": "echo before",
                        "post_restore": "echo after",
                    },
                },
            },
        }
        cfg_path = tmp_path / "config_saver.yaml"
        cfg_path.write_text(yaml.dump(data), encoding="utf-8")
        cfg = load_config(cfg_path)
        hooks = cfg.configs["item1"].hooks
        assert hooks.pre_save == "echo before"
        assert hooks.post_restore == "echo after"


class TestFindConfig:
    """Tests for find_config function."""

    def test_find_in_start_dir(self, tmp_path):
        """Finds config in the explicitly provided directory."""
        cfg = tmp_path / "config_saver.yaml"
        cfg.write_text(
            yaml.dump({"backup_root": "x"}),
            encoding="utf-8",
        )
        found = find_config(start_dir=tmp_path)
        assert found == cfg

    def test_find_yml_extension(self, tmp_path):
        """Finds config with .yml extension."""
        cfg = tmp_path / "config_saver.yml"
        cfg.write_text(
            yaml.dump({"backup_root": "x"}),
            encoding="utf-8",
        )
        found = find_config(start_dir=tmp_path)
        assert found == cfg

    def test_not_found_raises(self, tmp_path, monkeypatch):
        """Raises FileNotFoundError when no config exists."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)
        with pytest.raises(FileNotFoundError):
            find_config(start_dir=empty_dir)
