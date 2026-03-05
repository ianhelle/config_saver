"""Pydantic models for the config-saver YAML schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HookConfig(BaseModel):
    """Pre/post hook commands for save/restore operations."""

    pre_save: str | None = None
    post_save: str | None = None
    pre_restore: str | None = None
    post_restore: str | None = None


class ConfigItem(BaseModel):
    """A single configuration item to save/restore."""

    handler: str
    description: str = ""
    # File handler fields
    source: str | list[str] | None = None
    additional_files: list[str] | None = None
    # Registry handler fields
    keys: list[str] | None = None
    # Environment variables handler fields
    scope: str = "user"
    include_vars: list[str] | None = None
    exclude_vars: list[str] | None = None
    # Git repos handler fields
    scan_roots: list[str] | None = None
    # Personalization handler fields
    settings: list[str] | None = None
    # VS Code handler fields
    variants: list[str] | None = None
    # Hook system
    hooks: HookConfig = Field(default_factory=HookConfig)
    # Catch-all for future handler-specific fields
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class BackupConfig(BaseModel):
    """Top-level configuration schema."""

    backup_root: str
    max_archives: int = 10
    configs: dict[str, ConfigItem] = Field(default_factory=dict)
