"""
Integration Tests — end-to-end CLI workflow

These tests verify that the modules work together correctly by simulating
realistic user workflows: initializing data, setting up habits, logging
habits, computing streaks, and verifying persistent state.

All tests use isolated temp data dirs via conftest fixtures.
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from habit_engine.habit_io import (
    initialize_data_files,
    load_habits,
    save_habits,
    load_daily_logs,
    save_daily_logs,
    load_habit_streaks,
    reset_app_data,
    clear_tracking_data,
)
from habit_engine.habit_logic import update_streaks, log_habits
from habit_engine.habit_display import display_logs


class TestFullWorkflowIntegration:
    """Integration: simulate a complete first-time-user workflow."""

    def test_init_setup_log_streak_cycle(self, patch_io_paths):
        """
        End-to-end: initialize → save habits → simulate logging →
        update streaks → save → reload and verify.
        """
        # 1. Initialize data files
        assert initialize_data_files() is True

        # 2. Save habits (simulates what setup_habits would produce)
        habits = ["Exercise", "Read", "Meditate"]
        assert save_habits(habits) is True

        # 3. Reload and verify habits persisted
        loaded = load_habits()
        assert loaded == habits

        # 4. Simulate logging (mock stdin)
        with patch("builtins.input", side_effect=["yes", "no", "yes"]):
            new_logs = log_habits(habits)
        assert new_logs is not None
        assert len(new_logs) == 3

        # 5. Save logs and compute streaks
        streaks = load_habit_streaks()
        update_streaks(new_logs, habits, streaks)
        assert save_daily_logs(new_logs, streaks) is True

        # 6. Reload and verify persistence
        reloaded_logs = load_daily_logs()
        assert len(reloaded_logs) == 3

        reloaded_streaks = load_habit_streaks()
        assert reloaded_streaks["Exercise"] == 1
        assert reloaded_streaks["Read"] == 0
        assert reloaded_streaks["Meditate"] == 1


class TestMultiDayStreakIntegration:
    """Integration: simulate logging over multiple days and verify streak math."""

    def test_three_day_streak(self, patch_io_paths):
        """Log the same habit completed over 3 consecutive days; verify streak = 3."""
        initialize_data_files()
        habits = ["Exercise"]
        save_habits(habits)

        today = datetime.now()
        logs = []
        for i in range(2, -1, -1):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            logs.append(["Exercise", date_str, True])

        streaks = {"Exercise": 0}
        update_streaks(logs, habits, streaks)
        assert streaks["Exercise"] == 3

        save_daily_logs(logs, streaks)
        reloaded = load_habit_streaks()
        assert reloaded["Exercise"] == 3

    def test_streak_broken_mid_sequence(self, patch_io_paths):
        """
        Day 1: completed, Day 2: not completed, Day 3: completed
        → streak should be 1 (only the most recent completed day counts).
        """
        initialize_data_files()
        habits = ["Exercise"]
        save_habits(habits)

        today = datetime.now()
        logs = [
            ["Exercise", (today - timedelta(days=2)).strftime("%Y-%m-%d"), True],
            ["Exercise", (today - timedelta(days=1)).strftime("%Y-%m-%d"), False],
            ["Exercise", today.strftime("%Y-%m-%d"), True],
        ]
        streaks = {"Exercise": 0}
        update_streaks(logs, habits, streaks)
        assert streaks["Exercise"] == 1


class TestResetIntegration:
    """Integration: verify reset_app_data wipes everything end-to-end."""

    def test_reset_clears_all_data(self, patch_io_paths):
        """After seeding data, reset should return all files to empty defaults."""
        initialize_data_files()
        save_habits(["Exercise", "Read"])
        save_daily_logs(
            [["Exercise", "2024-06-01", True]],
            {"Exercise": 1},
        )

        assert reset_app_data() is True

        assert load_habits() == []
        assert load_daily_logs() == []
        assert load_habit_streaks() == {}


class TestClearTrackingIntegration:
    """Integration: clear_tracking_data preserves habits but wipes logs/streaks."""

    def test_clear_preserves_habits(self, patch_io_paths):
        """Habits survive a tracking-data clear."""
        initialize_data_files()
        save_habits(["Exercise", "Read"])
        save_daily_logs(
            [["Exercise", "2024-06-01", True]],
            {"Exercise": 1},
        )

        assert clear_tracking_data() is True

        assert load_habits() == ["Exercise", "Read"]
        assert load_daily_logs() == []
        assert load_habit_streaks() == {}


class TestDisplayLogsIntegration:
    """Integration: display_logs with real data after the full workflow."""

    def test_display_after_logging(self, patch_io_paths, capsys):
        """After logging, display_logs should print the logged entries."""
        initialize_data_files()
        habits = ["Exercise"]
        save_habits(habits)

        with patch("builtins.input", side_effect=["yes"]):
            new_logs = log_habits(habits)

        streaks = {"Exercise": 0}
        update_streaks(new_logs, habits, streaks)
        save_daily_logs(new_logs, streaks)

        reloaded_logs = load_daily_logs()
        reloaded_streaks = load_habit_streaks()
        display_logs(reloaded_logs, reloaded_streaks)

        out = capsys.readouterr().out
        assert "Exercise" in out


class TestVisualizationIntegration:
    """Integration: generate a visualization from real logged data."""

    def test_plot_generation(self, patch_io_paths):
        """After logging data, visualize_habit_streak produces a PNG file."""
        from habit_engine.habit_visualization import visualize_habit_streak
        import habit_engine.habit_visualization as viz_mod

        initialize_data_files()
        plots_dir = patch_io_paths["plots_dir"]

        with patch.object(viz_mod, "PLOTS_DIR", plots_dir):
            today = datetime.now().strftime("%Y-%m-%d")
            logs = [["Exercise", today, True]]
            result = visualize_habit_streak(logs, "Exercise")

        assert result is not None
        assert os.path.exists(result)
        assert result.endswith(".png")


class TestSideEffectValidation:
    """
    Validation: verify that read-only operations do not modify data files.
    This addresses the proposal's 'Negative Validation' requirement.
    """

    def test_display_logs_does_not_modify_files(self, seeded_data_dir):
        """display_logs must be a pure read operation with no side effects on JSON."""
        paths = seeded_data_dir
        before_habits = open(paths["habits_file"]).read()
        before_logs = open(paths["logs_file"]).read()
        before_streaks = open(paths["streaks_file"]).read()

        logs = load_daily_logs()
        streaks = load_habit_streaks()
        display_logs(logs, streaks)

        assert open(paths["habits_file"]).read() == before_habits
        assert open(paths["logs_file"]).read() == before_logs
        assert open(paths["streaks_file"]).read() == before_streaks

    def test_load_functions_have_no_side_effects(self, seeded_data_dir):
        """All load_* functions should not alter the underlying files."""
        paths = seeded_data_dir
        before_habits = open(paths["habits_file"]).read()
        before_logs = open(paths["logs_file"]).read()
        before_streaks = open(paths["streaks_file"]).read()

        load_habits()
        load_daily_logs()
        load_habit_streaks()

        assert open(paths["habits_file"]).read() == before_habits
        assert open(paths["logs_file"]).read() == before_logs
        assert open(paths["streaks_file"]).read() == before_streaks
