"""Base handler class and handler registry."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

# Global handler registry: handler name -> handler class
_HANDLER_REGISTRY: dict[str, type[BaseHandler]] = {}


class BaseHandler(abc.ABC):
    """Abstract base class for all configuration handlers."""

    name: str = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Auto-register handler subclasses that define a name."""
        super().__init_subclass__(**kwargs)
        if cls.name:
            _HANDLER_REGISTRY[cls.name] = cls

    @abc.abstractmethod
    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Save the configuration item to the backup store."""

    @abc.abstractmethod
    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Restore the configuration item from the backup store."""


def get_handler(handler_name: str) -> BaseHandler:
    """Look up and instantiate a handler by name."""
    cls = _HANDLER_REGISTRY.get(handler_name)
    if cls is None:
        available = ", ".join(sorted(_HANDLER_REGISTRY))
        msg = f"Unknown handler: {handler_name!r}. Available: {available}"
        raise ValueError(msg)
    return cls()


def list_handlers() -> list[str]:
    """Return sorted list of registered handler names."""
    return sorted(_HANDLER_REGISTRY)
