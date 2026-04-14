"""
White-Box Tests for habit_display.py

Goal: cover branches in display_logs, display_app_info, and display_license.
"""

import os
import pytest
from unittest.mock import patch

from habit_engine.habit_display import display_logs, display_app_info, display_license


# display_logs

class TestDisplayLogsWB:
    """WB: branches in display_logs."""

    def test_empty_logs(self, capsys):
        """Branch: not logs → print 'No logs found' (line 9-11)."""
        display_logs([], {})
        assert "No logs" in capsys.readouterr().out

    def test_valid_logs_grouped_by_date(self, capsys):
        """Branch: logs non-empty → iterate by date, print each (line 16-25)."""
        logs = [
            ["Exercise", "2024-06-01", True],
            ["Read", "2024-06-01", False],
        ]
        streaks = {"Exercise": 3, "Read": 0}
        display_logs(logs, streaks)
        out = capsys.readouterr().out
        assert "2024-06-01" in out
        assert "Exercise" in out

    def test_streak_display_when_positive(self, capsys):
        """Branch: streak > 0 → shows fire emoji and count (line 24)."""
        logs = [["Exercise", "2024-06-01", True]]
        streaks = {"Exercise": 5}
        display_logs(logs, streaks)
        out = capsys.readouterr().out
        assert "5" in out

    def test_streak_display_when_zero(self, capsys):
        """Branch: streak == 0 → no streak_display (line 24 else)."""
        logs = [["Exercise", "2024-06-01", True]]
        streaks = {"Exercise": 0}
        display_logs(logs, streaks)
        out = capsys.readouterr().out
        assert "Exercise" in out

    def test_non_dict_streaks_handled(self, capsys):
        """Branch: isinstance(habit_streaks, dict) is False → streak=0 (line 23)."""
        logs = [["Exercise", "2024-06-01", True]]
        display_logs(logs, "not_a_dict")
        out = capsys.readouterr().out
        assert "Exercise" in out

    def test_malformed_log_skipped(self, capsys):
        """Branch: log not list/tuple or len < 3 → skipped (line 20)."""
        logs = [["Exercise", "2024-06-01", True], ["bad"]]
        display_logs(logs, {})
        out = capsys.readouterr().out
        assert "Exercise" in out

    def test_exception_handled(self, capsys):
        """Branch: except Exception → prints error (line 26-27)."""
        with patch("habit_engine.habit_display.sorted", side_effect=RuntimeError("fail")):
            display_logs([["Ex", "2024-01-01", True]], {})
        out = capsys.readouterr().out
        assert "Error" in out or "No logs" in out


# display_app_info

class TestDisplayAppInfoWB:
    """WB: display_app_info has no real branches; just verify it runs."""

    def test_prints_info(self, capsys):
        """Covers the single execution path through display_app_info."""
        display_app_info()
        out = capsys.readouterr().out
        assert "HERALDEXX" in out
        assert "Description" in out


# display_license

class TestDisplayLicenseWB:
    """WB: branches in display_license."""

    def test_reads_license_file(self, capsys):
        """Branch: os.path.exists(license_path) → read from file (line 74-76)."""
        result = display_license()
        out = capsys.readouterr().out
        assert result is True
        assert "LICENSE" in out or "MIT" in out

    def test_fallback_to_embedded(self, capsys):
        """Branch: license file missing → import __license_text__ (line 78-80)."""
        with patch("os.path.exists", return_value=False):
            result = display_license()
        out = capsys.readouterr().out
        assert result is True
        assert "MIT" in out

    def test_exception_returns_false(self, capsys):
        """Branch: except Exception → return False (line 88-90)."""
        with patch("os.path.exists", side_effect=RuntimeError("fail")):
            result = display_license()
        assert result is False
