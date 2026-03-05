"""Utility functions for path expansion, logging, and helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path


def expand_env_vars(path_str: str) -> Path:
    """Expand %ENV_VAR% style and $ENV_VAR style variables in a path string."""
    # Expand %VAR% style (Windows)
    expanded = re.sub(
        r"%([^%]+)%",
        lambda m: os.environ.get(m.group(1), m.group(0)),
        path_str,
    )
    # Also expand $VAR / ${VAR} style (bash)
    expanded = os.path.expandvars(expanded)
    return Path(expanded)


def expand_path(path_str: str) -> Path:
    """Expand environment variables and resolve a path."""
    return expand_env_vars(path_str).expanduser().resolve()
