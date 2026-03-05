"""Tests for handler base class and registry."""

from __future__ import annotations

import pytest

from config_saver.handlers.base import (
    _HANDLER_REGISTRY,
    BaseHandler,
    get_handler,
    list_handlers,
)


class TestHandlerRegistry:
    """Tests for handler auto-registration."""

    def test_builtin_handlers_registered(self):
        """All built-in handlers are registered."""
        names = list_handlers()
        assert "file" in names
        assert "registry" in names
        assert "env_vars" in names
        assert "git_repos" in names
        assert "personalization" in names

    def test_get_handler_returns_instance(self):
        """get_handler returns a handler instance."""
        handler = get_handler("file")
        assert isinstance(handler, BaseHandler)

    def test_get_unknown_handler_raises(self):
        """get_handler raises ValueError for unknown name."""
        with pytest.raises(ValueError, match="Unknown handler"):
            get_handler("nonexistent_handler")

    def test_list_handlers_sorted(self):
        """list_handlers returns sorted names."""
        names = list_handlers()
        assert names == sorted(names)

    def test_subclass_auto_registers(self):
        """Subclassing BaseHandler with a name auto-registers."""

        class _TestHandler(BaseHandler):
            name = "_test_auto_reg"

            def save(self, item_name, config_item, store) -> None:
                """No-op save."""

            def restore(self, item_name, config_item, store, *, dry_run=False) -> None:
                """No-op restore."""

        assert "_test_auto_reg" in _HANDLER_REGISTRY
        handler = get_handler("_test_auto_reg")
        assert isinstance(handler, _TestHandler)
        # Clean up
        del _HANDLER_REGISTRY["_test_auto_reg"]
