"""Tests for env_vars handler filtering logic."""

from __future__ import annotations

from config_saver.handlers.env_vars import _filter_vars


class TestFilterVars:
    """Tests for _filter_vars helper."""

    def test_no_filters(self):
        """No filters returns all vars."""
        env = {"PATH": "/usr/bin", "HOME": "/home/user"}
        result = _filter_vars(env, None, None)
        assert result == env

    def test_include_filter(self):
        """Include filter keeps only matching vars."""
        env = {"PATH": "x", "HOME": "y", "TEMP": "z"}
        result = _filter_vars(env, ["PATH", "HOME"], None)
        assert set(result.keys()) == {"PATH", "HOME"}

    def test_exclude_filter(self):
        """Exclude filter removes matching vars."""
        env = {"PATH": "x", "HOME": "y", "TEMP": "z"}
        result = _filter_vars(env, None, ["TEMP"])
        assert "TEMP" not in result
        assert "PATH" in result

    def test_include_and_exclude(self):
        """Both filters applied: include first, then exclude."""
        env = {"A": "1", "B": "2", "C": "3", "D": "4"}
        result = _filter_vars(env, ["A", "B", "C"], ["B"])
        assert set(result.keys()) == {"A", "C"}

    def test_case_insensitive(self):
        """Filters are case-insensitive."""
        env = {"Path": "x", "home": "y"}
        result = _filter_vars(env, ["PATH"], None)
        assert "Path" in result
        result2 = _filter_vars(env, None, ["HOME"])
        assert "home" not in result2
