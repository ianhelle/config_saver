"""Tests for config_saver.models — Pydantic config schema."""

from __future__ import annotations

import pytest

from config_saver.models import BackupConfig, ConfigItem, HookConfig


class TestHookConfig:
    """Tests for HookConfig model."""

    def test_defaults_are_none(self):
        """All hook fields default to None."""
        hook = HookConfig()
        assert hook.pre_save is None
        assert hook.post_save is None
        assert hook.pre_restore is None
        assert hook.post_restore is None

    def test_set_hooks(self):
        """Hook fields accept string commands."""
        hook = HookConfig(
            pre_save="echo pre",
            post_restore="echo post",
        )
        assert hook.pre_save == "echo pre"
        assert hook.post_restore == "echo post"


class TestConfigItem:
    """Tests for ConfigItem model."""

    def test_minimal_item(self):
        """A config item only requires a handler name."""
        item = ConfigItem(handler="file")
        assert item.handler == "file"
        assert item.description == ""
        assert item.source is None
        assert item.hooks == HookConfig()

    def test_file_handler_fields(self):
        """File handler fields are parsed correctly."""
        item = ConfigItem(
            handler="file",
            source="%APPDATA%\\Code\\settings.json",
            additional_files=["%USERPROFILE%\\.bashrc"],
        )
        assert item.source == "%APPDATA%\\Code\\settings.json"
        assert item.additional_files == ["%USERPROFILE%\\.bashrc"]

    def test_source_as_list(self):
        """Source field accepts a list of paths."""
        item = ConfigItem(
            handler="file",
            source=["file1.txt", "file2.txt"],
        )
        assert isinstance(item.source, list)
        assert len(item.source) == 2

    def test_registry_handler_fields(self):
        """Registry handler fields are parsed correctly."""
        item = ConfigItem(
            handler="registry",
            keys=["HKCU\\Software\\Test"],
        )
        assert item.keys == ["HKCU\\Software\\Test"]

    def test_git_repos_handler_fields(self):
        """Git repos handler fields are parsed correctly."""
        item = ConfigItem(
            handler="git_repos",
            scan_roots=["E:\\src"],
        )
        assert item.scan_roots == ["E:\\src"]

    def test_env_vars_handler_fields(self):
        """Env vars handler fields are parsed correctly."""
        item = ConfigItem(
            handler="env_vars",
            scope="user",
            include_vars=["PATH", "JAVA_HOME"],
            exclude_vars=["TEMP", "TMP"],
        )
        assert item.scope == "user"
        assert item.include_vars == ["PATH", "JAVA_HOME"]
        assert item.exclude_vars == ["TEMP", "TMP"]

    def test_env_vars_defaults(self):
        """Env vars fields default to user scope and no filters."""
        item = ConfigItem(handler="env_vars")
        assert item.scope == "user"
        assert item.include_vars is None
        assert item.exclude_vars is None

    def test_hooks_embedded(self):
        """Hooks are parsed when nested in a config item."""
        item = ConfigItem(
            handler="file",
            hooks=HookConfig(post_restore="code --install-extension ext"),
        )
        assert item.hooks.post_restore == "code --install-extension ext"

    def test_extra_fields_allowed(self):
        """Unknown fields are accepted via extra='allow'."""
        item = ConfigItem(
            handler="custom",
            custom_field="custom_value",
        )
        assert item.model_extra is not None
        assert item.model_extra["custom_field"] == "custom_value"


class TestBackupConfig:
    """Tests for BackupConfig top-level model."""

    def test_minimal_config(self):
        """A config requires only backup_root."""
        cfg = BackupConfig(backup_root="C:\\backups")
        assert cfg.backup_root == "C:\\backups"
        assert cfg.configs == {}

    def test_full_config(self):
        """A config with multiple items parses correctly."""
        cfg = BackupConfig(
            backup_root="C:\\backups",
            configs={
                "vscode": ConfigItem(
                    handler="file",
                    source="settings.json",
                ),
                "registry": ConfigItem(
                    handler="registry",
                    keys=["HKCU\\Test"],
                ),
            },
        )
        assert len(cfg.configs) == 2
        assert "vscode" in cfg.configs
        assert cfg.configs["registry"].handler == "registry"

    def test_model_validate_from_dict(self):
        """BackupConfig.model_validate works from raw dict."""
        raw = {
            "backup_root": "C:\\backups",
            "configs": {
                "item1": {
                    "handler": "file",
                    "source": "test.txt",
                },
            },
        }
        cfg = BackupConfig.model_validate(raw)
        assert cfg.configs["item1"].handler == "file"

    def test_missing_backup_root_raises(self):
        """Missing backup_root raises a validation error."""
        with pytest.raises(Exception):
            BackupConfig.model_validate({"configs": {}})
