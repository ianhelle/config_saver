"""Tests for hooks execution system."""

from __future__ import annotations

from config_saver.hooks import run_hook, run_hooks_for_phase
from config_saver.models import HookConfig


class TestRunHook:
    """Tests for run_hook function."""

    def test_none_command_returns_true(self):
        """A None command is a no-op that returns True."""
        assert run_hook("pre_save", None, "test") is True

    def test_empty_command_returns_true(self):
        """An empty string command is a no-op."""
        assert run_hook("pre_save", "", "test") is True

    def test_successful_command(self):
        """A successful command returns True."""
        result = run_hook(
            "post_save",
            "echo hello",
            "test_item",
        )
        assert result is True

    def test_failing_command_returns_false(self):
        """A command that exits non-zero returns False."""
        result = run_hook(
            "post_save",
            "exit 1",
            "test_item",
        )
        assert result is False


class TestRunHooksForPhase:
    """Tests for run_hooks_for_phase function."""

    def test_phase_with_hook(self):
        """Runs the hook matching the phase."""
        hooks = HookConfig(pre_save="echo test")
        result = run_hooks_for_phase("pre_save", hooks, "item1")
        assert result is True

    def test_phase_without_hook(self):
        """Returns True when phase has no hook defined."""
        hooks = HookConfig()
        result = run_hooks_for_phase("pre_save", hooks, "item1")
        assert result is True

    def test_invalid_phase_returns_true(self):
        """An unrecognized phase returns True (no-op)."""
        hooks = HookConfig()
        result = run_hooks_for_phase("not_a_phase", hooks, "item1")
        assert result is True
