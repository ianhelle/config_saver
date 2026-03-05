"""Tests for the file copy handler."""

from __future__ import annotations

from config_saver.handlers.file import FileHandler
from config_saver.models import ConfigItem
from config_saver.store import BackupStore


class TestFileHandlerSave:
    """Tests for FileHandler.save."""

    def test_save_single_file(self, tmp_path):
        """Saves a single source file to the backup store."""
        src = tmp_path / "source.txt"
        src.write_text("hello", encoding="utf-8")
        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="file", source=str(src))

        handler = FileHandler()
        handler.save("test_item", item, store)

        backed_up = store.item_dir("test_item") / "source.txt"
        assert backed_up.is_file()
        assert backed_up.read_text(encoding="utf-8") == "hello"

    def test_save_multiple_files(self, tmp_path):
        """Saves source and additional_files."""
        src1 = tmp_path / "main.txt"
        src1.write_text("main", encoding="utf-8")
        src2 = tmp_path / "extra.txt"
        src2.write_text("extra", encoding="utf-8")
        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(
            handler="file",
            source=str(src1),
            additional_files=[str(src2)],
        )

        handler = FileHandler()
        handler.save("multi", item, store)

        dest = store.item_dir("multi")
        assert (dest / "main.txt").is_file()
        assert (dest / "extra.txt").is_file()

    def test_save_missing_file_warns(self, tmp_path, capsys):
        """Missing source files are skipped with warning."""
        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(
            handler="file",
            source=str(tmp_path / "nonexistent.txt"),
        )

        handler = FileHandler()
        handler.save("missing", item, store)
        # Should not crash; backup dir may be empty


class TestFileHandlerRestore:
    """Tests for FileHandler.restore."""

    def test_restore_file(self, tmp_path):
        """Restores a file from backup to its original location."""
        # Set up source and backup
        src = tmp_path / "orig" / "file.txt"
        src.parent.mkdir()
        src.write_text("original", encoding="utf-8")
        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="file", source=str(src))

        handler = FileHandler()
        handler.save("restore_test", item, store)

        # Modify source
        src.write_text("modified", encoding="utf-8")

        # Restore
        handler.restore("restore_test", item, store)
        assert src.read_text(encoding="utf-8") == "original"

    def test_restore_dry_run(self, tmp_path):
        """Dry run does not modify files."""
        src = tmp_path / "file.txt"
        src.write_text("original", encoding="utf-8")
        store = BackupStore(str(tmp_path / "backup"))
        store.ensure_dirs()
        item = ConfigItem(handler="file", source=str(src))

        handler = FileHandler()
        handler.save("dry", item, store)
        src.write_text("modified", encoding="utf-8")

        handler.restore("dry", item, store, dry_run=True)
        assert src.read_text(encoding="utf-8") == "modified"


class TestFileHandlerCollectPaths:
    """Tests for _collect_source_paths."""

    def test_source_as_string(self, tmp_path):
        """String source produces single path."""
        item = ConfigItem(handler="file", source=str(tmp_path / "f.txt"))
        paths = FileHandler._collect_source_paths(item)
        assert len(paths) == 1

    def test_source_as_list(self, tmp_path):
        """List source produces multiple paths."""
        item = ConfigItem(
            handler="file",
            source=[str(tmp_path / "a.txt"), str(tmp_path / "b.txt")],
        )
        paths = FileHandler._collect_source_paths(item)
        assert len(paths) == 2

    def test_additional_files_included(self, tmp_path):
        """additional_files are appended to paths."""
        item = ConfigItem(
            handler="file",
            source=str(tmp_path / "main.txt"),
            additional_files=[str(tmp_path / "extra.txt")],
        )
        paths = FileHandler._collect_source_paths(item)
        assert len(paths) == 2
