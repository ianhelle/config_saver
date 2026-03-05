"""Tests for config_saver.utils — path expansion helpers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from config_saver.utils import expand_env_vars, expand_path


class TestExpandEnvVars:
    """Tests for expand_env_vars function."""

    def test_expand_windows_style(self):
        """Expand %VAR% style environment variables."""
        with patch.dict(os.environ, {"MY_VAR": "hello"}):
            result = expand_env_vars("%MY_VAR%\\sub")
        assert "hello" in str(result)

    def test_unknown_var_kept_literal(self):
        """Unknown %VAR% is left as-is."""
        var = "UNLIKELY_VAR_39bx7"
        os.environ.pop(var, None)
        result = expand_env_vars(f"%{var}%\\file.txt")
        assert var in str(result)

    def test_expand_dollar_style(self):
        """Expand $VAR style environment variables."""
        with patch.dict(os.environ, {"MY_VAR2": "world"}):
            result = expand_env_vars("$MY_VAR2/sub")
        assert "world" in str(result)

    def test_returns_path_object(self):
        """Result is always a Path object."""
        result = expand_env_vars("plain_path")
        assert isinstance(result, Path)


class TestExpandPath:
    """Tests for expand_path function."""

    def test_resolves_to_absolute(self):
        """expand_path always returns an absolute path."""
        result = expand_path("relative\\path")
        assert result.is_absolute()

    def test_expands_env_and_resolves(self):
        """expand_path combines env expansion and resolution."""
        with patch.dict(os.environ, {"TEST_DIR": "C:\\Users\\test"}):
            result = expand_path("%TEST_DIR%\\file.txt")
        assert "test" in str(result).lower()
        assert result.is_absolute()
