"""Tests for VS Code handler."""

from __future__ import annotations

import json
from pathlib import Path

from config_saver.handlers.vscode import (
    VSCodeHandler,
    _get_extensions_list,
)
from config_saver.models import ConfigItem
from config_saver.store import BackupStore


def _setup_vscode_dirs(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """Create mock VS Code user data and extensions dirs."""
    user_data = tmp_path / "AppData" / "Code" / "User"
    user_data.mkdir(parents=True)
    (user_data / "settings.json").write_text('{"editor.fontSize": 14}', encoding="utf-8")
    (user_data / "keybindings.json").write_text("[]", encoding="utf-8")
    snippets = user_data / "snippets"
    snippets.mkdir()
    (snippets / "python.json").write_text('{"snip": {}}', encoding="utf-8")

    ext_dir = tmp_path / "vscode_ext"
    ext_dir.mkdir()
    ext1 = ext_dir / "ms-python.python-2024.1.0"
    ext1.mkdir()
    (ext1 / "package.json").write_text(
        json.dumps({
            "publisher": "ms-python",
            "name": "python",
            "version": "2024.1.0",
        }),
        encoding="utf-8",
    )
    (ext1 / "extension.js").write_text("// ext", encoding="utf-8")
    return user_data, ext_dir


class TestGetExtensionsList:
    """Tests for _get_extensions_list."""

    def test_parses_extensions(self, tmp_path):
        """Reads package.json to build extension manifest."""
        _, ext_dir = _setup_vscode_dirs(tmp_path)
        result = _get_extensions_list(ext_dir)
        assert len(result) == 1
        assert result[0]["id"] == "ms-python.python"
        assert result[0]["version"] == "2024.1.0"

    def test_empty_dir(self, tmp_path):
        """Returns empty list for dir with no extensions."""
        empty = tmp_path / "empty_ext"
        empty.mkdir()
        assert _get_extensions_list(empty) == []

    def test_missing_dir(self, tmp_path):
        """Returns empty list for nonexistent dir."""
        assert _get_extensions_list(tmp_path / "nope") == []

    def test_no_package_json(self, tmp_path):
        """Falls back to dir name when package.json missing."""
        ext_dir = tmp_path / "exts"
        ext_dir.mkdir()
        (ext_dir / "some-ext-1.0.0").mkdir()
        result = _get_extensions_list(ext_dir)
        assert len(result) == 1
        assert result[0]["id"] == "some-ext-1.0.0"


class TestVSCodeHandlerSave:
    """Tests for VSCodeHandler.save."""

    def test_save_config_files(self, tmp_path, monkeypatch):
        """Saves settings, keybindings, snippets to backup store."""
        user_data, ext_dir = _setup_vscode_dirs(tmp_path)
        monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        # Point handler at our test dirs
        from config_saver.handlers import vscode

        monkeypatch.setitem(
            vscode._VARIANT_CONFIG,
            "code",
            {
                "user_data": str(user_data),
                "extensions": str(ext_dir),
                "cli_cmd": "code",
            },
        )

        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="vscode", variants=["code"])

        handler = VSCodeHandler()
        handler.save("vscode_test", item, store)

        config_dest = store.item_dir("vscode_test") / "code"
        assert (config_dest / "settings.json").is_file()
        assert (config_dest / "keybindings.json").is_file()
        assert (config_dest / "snippets").is_dir()
        assert (config_dest / "extensions_list.json").is_file()

        # Extensions in dedicated folder
        ext_backup = store.root / "vscode_extensions" / "code"
        assert ext_backup.is_dir()
        assert any(ext_backup.iterdir())

    def test_save_extension_manifest(self, tmp_path, monkeypatch):
        """Extension manifest contains correct metadata."""
        user_data, ext_dir = _setup_vscode_dirs(tmp_path)
        from config_saver.handlers import vscode

        monkeypatch.setitem(
            vscode._VARIANT_CONFIG,
            "code",
            {
                "user_data": str(user_data),
                "extensions": str(ext_dir),
                "cli_cmd": "code",
            },
        )

        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="vscode", variants=["code"])

        VSCodeHandler().save("vsc", item, store)

        manifest = store.item_dir("vsc") / "code" / "extensions_list.json"
        ext_list = json.loads(manifest.read_text(encoding="utf-8"))
        assert len(ext_list) == 1
        assert ext_list[0]["id"] == "ms-python.python"


class TestVSCodeHandlerRestore:
    """Tests for VSCodeHandler.restore."""

    def test_restore_dry_run(self, tmp_path, monkeypatch):
        """Dry run doesn't write any files."""
        user_data, ext_dir = _setup_vscode_dirs(tmp_path)
        from config_saver.handlers import vscode

        monkeypatch.setitem(
            vscode._VARIANT_CONFIG,
            "code",
            {
                "user_data": str(user_data),
                "extensions": str(ext_dir),
                "cli_cmd": "code",
            },
        )

        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="vscode", variants=["code"])

        handler = VSCodeHandler()
        handler.save("vsc_dr", item, store)

        # Delete originals
        (user_data / "settings.json").unlink()

        handler.restore("vsc_dr", item, store, dry_run=True)
        # File should NOT be restored
        assert not (user_data / "settings.json").exists()

    def test_restore_writes_files(self, tmp_path, monkeypatch):
        """Restore copies files back to original locations."""
        user_data, ext_dir = _setup_vscode_dirs(tmp_path)
        from config_saver.handlers import vscode

        monkeypatch.setitem(
            vscode._VARIANT_CONFIG,
            "code",
            {
                "user_data": str(user_data),
                "extensions": str(ext_dir),
                "cli_cmd": "code",
            },
        )

        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="vscode", variants=["code"])

        handler = VSCodeHandler()
        handler.save("vsc_r", item, store)

        # Modify settings
        (user_data / "settings.json").write_text('{"changed": true}', encoding="utf-8")

        handler.restore("vsc_r", item, store)
        restored = json.loads((user_data / "settings.json").read_text(encoding="utf-8"))
        assert restored.get("editor.fontSize") == 14

    def test_unknown_variant_warns(self, tmp_path):
        """Unknown variant is skipped with warning."""
        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(
            handler="vscode",
            variants=["code-nightly"],
        )
        handler = VSCodeHandler()
        # Should not crash
        handler.save("vsc_unk", item, store)
        handler.restore("vsc_unk", item, store)
