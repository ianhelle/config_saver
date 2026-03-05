"""Tests for config_saver.store — BackupStore operations."""

from __future__ import annotations

import time

from config_saver.store import BackupStore


class TestBackupStoreInit:
    """Tests for BackupStore initialization."""

    def test_creates_store_paths(self, backup_root):
        """Store sets up latest and archive dir paths."""
        store = BackupStore(str(backup_root))
        assert store.latest_dir == store.root / "latest"
        assert store.archive_dir == store.root / "archive"

    def test_ensure_dirs_creates_structure(self, backup_root):
        """ensure_dirs creates the directory tree."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        assert store.latest_dir.is_dir()
        assert store.archive_dir.is_dir()


class TestBackupStoreItemDir:
    """Tests for item_dir method."""

    def test_item_dir_in_latest(self, backup_root):
        """item_dir creates subdirectory under latest/."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        d = store.item_dir("vscode_profile")
        assert d.is_dir()
        assert d.parent == store.latest_dir

    def test_item_dir_in_archive(self, backup_root):
        """item_dir with archive_ts creates subdirectory under archive/."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        d = store.item_dir(
            "vscode_profile",
            archive_ts="2026-01-01T00-00-00",
        )
        assert d.is_dir()
        assert "2026-01-01T00-00-00" in str(d)


class TestBackupStoreArchive:
    """Tests for archive snapshot operations."""

    def test_create_archive_empty_latest(self, backup_root):
        """Archive snapshot works even with empty latest/."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        ts = store.create_archive_snapshot()
        assert ts is not None
        assert (store.archive_dir / ts).is_dir()

    def test_create_archive_copies_latest(self, backup_root):
        """Archive snapshot copies files from latest/."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        # Put a file in latest/
        item_dir = store.item_dir("test_item")
        (item_dir / "settings.json").write_text('{"key": "value"}', encoding="utf-8")
        ts = store.create_archive_snapshot()
        archived = store.archive_dir / ts / "test_item" / "settings.json"
        assert archived.is_file()
        assert archived.read_text(encoding="utf-8") == '{"key": "value"}'

    def test_list_archives_empty(self, backup_root):
        """list_archives returns empty when no archives exist."""
        store = BackupStore(str(backup_root))
        assert store.list_archives() == []

    def test_list_archives_sorted(self, backup_root):
        """list_archives returns timestamps newest first."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        ts1 = store.create_archive_snapshot()
        time.sleep(1.1)
        ts2 = store.create_archive_snapshot()
        archives = store.list_archives()
        assert len(archives) >= 2
        assert archives[0] == ts2
        assert archives[1] == ts1


class TestBackupStoreListItems:
    """Tests for list_items method."""

    def test_list_items_empty(self, backup_root):
        """list_items returns empty for non-existent backup."""
        store = BackupStore(str(backup_root))
        assert store.list_items() == []

    def test_list_items_in_latest(self, backup_root):
        """list_items returns item names from latest/."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        store.item_dir("alpha")
        store.item_dir("beta")
        items = store.list_items()
        assert "alpha" in items
        assert "beta" in items

    def test_list_items_in_archive(self, backup_root):
        """list_items returns items from a specific archive."""
        store = BackupStore(str(backup_root))
        store.ensure_dirs()
        store.item_dir("only_latest")
        ts = store.create_archive_snapshot()
        items = store.list_items(archive_ts=ts)
        assert "only_latest" in items
