"""
Issue #6 — Validation & Side-Effect Checks
==========================================

Traceability Map
-------------------------------------------------
1. Read-only invariant (--view-logs does not modify any JSON file)
   - tests/integration/test_proposal_validation.py
       TestReadOnlyInvariant::test_view_logs_does_not_change_mtime_or_hash
   - tests/integration/test_cli_integration.py
       TestSideEffectValidation::test_display_logs_does_not_modify_files
       TestSideEffectValidation::test_load_functions_have_no_side_effects

2. --reset functionality (wipes logs.json, streaks.json, plots/)
   - tests/integration/test_proposal_validation.py
       TestResetWipesPlots::test_reset_wipes_plots_directory
   - tests/integration/test_cli_integration.py
       TestResetIntegration::test_reset_clears_all_data
       TestClearTrackingIntegration::test_clear_preserves_habits

3. --lock / --dev (file permission cycle)
   - tests/integration/test_proposal_validation.py
       TestLockDevPermissionCycle::test_lock_then_dev_round_trip
   - tests/whitebox/test_habit_io_wb.py
       TestMakeFilesReadonlyWB::test_protects_existing_files
       TestMakeFilesWritableWB::test_unlocks_existing_files

4. Streak reset rules (streak resets to 0 on a missed day, not just decrements)
   - tests/integration/test_proposal_validation.py
       TestStreakResetRule::test_streak_resets_to_zero_when_today_missed
       TestStreakResetRule::test_streak_does_not_decrement_only_resets
   - tests/whitebox/test_habit_logic_wb.py
       TestUpdateStreaksWB::test_not_completed_breaks
   - tests/integration/test_cli_integration.py
       TestMultiDayStreakIntegration::test_streak_broken_mid_sequence

5. Minimum habit count enforcement (cannot complete setup with < 2 habits)
   - tests/integration/test_proposal_validation.py
       TestMinimumHabitCount::test_setup_rejects_below_minimum
   - tests/whitebox/test_habit_setup_wb.py
       TestSetupHabitsWB::test_below_minimum_then_valid
       TestSetupHabitsWB::test_minimum_habits

6. Visualization accuracy (plot values match raw data)
   - tests/integration/test_proposal_validation.py
       TestVisualizationAccuracy::test_completion_values_match_raw_logs
       TestVisualizationAccuracy::test_completion_values_after_filter
   - tests/integration/test_cli_integration.py
       TestVisualizationIntegration::test_plot_generation
"""

import hashlib
import json
import os
import stat
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from habit_engine.habit_io import (
    initialize_data_files,
    load_daily_logs,
    load_habit_streaks,
    load_habits,
    make_files_readonly,
    make_files_writable,
    reset_app_data,
    save_daily_logs,
    save_habits,
)
from habit_engine.habit_display import display_logs
from habit_engine.habit_logic import update_streaks
from habit_engine.habit_setup import setup_habits


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _snapshot(paths):
    """Capture (mtime_ns, sha256) for each existing path in a dict."""
    snap = {}
    for p in paths:
        if os.path.exists(p):
            st = os.stat(p)
            snap[p] = (st.st_mtime_ns, _sha256(p))
    return snap



class TestReadOnlyInvariant:
    """
    --view-logs is a read-only operation; JSON files on
    disk must remain bit-for-bit identical (verified by both mtime and
    SHA-256 hash) after the command runs.
    """

    def test_view_logs_does_not_change_mtime_or_hash(self, seeded_data_dir):
        paths = seeded_data_dir
        files = [paths["habits_file"], paths["logs_file"], paths["streaks_file"]]

        before = _snapshot(files)
        # Sleep long enough that any accidental rewrite would change mtime_ns
        time.sleep(0.05)

        # Simulate exactly what `python main.py --view-logs` does:
        #   load_daily_logs() → load_habit_streaks() → display_logs(...)
        logs = load_daily_logs()
        streaks = load_habit_streaks()
        display_logs(logs, streaks)

        after = _snapshot(files)

        assert set(before.keys()) == set(after.keys()), (
            "A JSON file disappeared or was created during --view-logs"
        )
        for path, (mtime, digest) in before.items():
            after_mtime, after_digest = after[path]
            assert after_mtime == mtime, (
                f"mtime changed for {path}: {mtime} -> {after_mtime}"
            )
            assert after_digest == digest, (
                f"sha256 changed for {path}: {digest} -> {after_digest}"
            )


class TestResetWipesPlots:
    """
    `--reset` wipes the plots/ directory in addition
    to logs.json and streaks.json. (Also documents that the current
    implementation wipes habits.json — see audit note at bottom.)
    """

    def test_reset_wipes_plots_directory(self, patch_io_paths):
        import habit_engine.habit_io as io_mod

        plots_dir = patch_io_paths["plots_dir"]
        os.makedirs(plots_dir, exist_ok=True)

        plot_a = os.path.join(plots_dir, "habit_streak_Exercise_20240101.png")
        plot_b = os.path.join(plots_dir, "habit_streak_Read_20240102.png")
        with open(plot_a, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nfake")
        with open(plot_b, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nfake")
        assert os.path.exists(plot_a) and os.path.exists(plot_b)

        initialize_data_files()
        save_habits(["Exercise", "Read"])
        save_daily_logs([["Exercise", "2024-06-01", True]], {"Exercise": 1})

        assert reset_app_data() is True

        assert os.path.isdir(plots_dir), "plots/ should be recreated empty"
        assert os.listdir(plots_dir) == [], (
            "plots/ should contain no files after --reset"
        )
        assert load_daily_logs() == []
        assert load_habit_streaks() == {}


class TestLockDevPermissionCycle:
    """
    `--lock` removes write permissions from core files;
    `--dev` restores them. Verified against the actual filesystem mode
    bits (preserved across a full lock → dev round trip).
    """

    def test_lock_then_dev_round_trip(self, tmp_path, monkeypatch):
        import habit_engine.habit_io as io_mod

        f1 = tmp_path / "core_a.py"
        f2 = tmp_path / "core_b.py"
        f1.write_text("# core a")
        f2.write_text("# core b")

        os.chmod(str(f1), stat.S_IRUSR | stat.S_IWUSR)
        os.chmod(str(f2), stat.S_IRUSR | stat.S_IWUSR)

        monkeypatch.setattr(io_mod, "CORE_FILES", [str(f1), str(f2)])

        assert make_files_readonly() is True
        for path in (str(f1), str(f2)):
            mode = os.stat(path).st_mode
            assert not (mode & stat.S_IWUSR), f"--lock failed: {path} still user-writable"
            assert not (mode & stat.S_IWGRP), f"--lock failed: {path} still group-writable"
            assert not (mode & stat.S_IWOTH), f"--lock failed: {path} still world-writable"

        assert make_files_writable() is True
        for path in (str(f1), str(f2)):
            mode = os.stat(path).st_mode
            assert mode & stat.S_IWUSR, f"--dev failed: {path} not user-writable"


class TestStreakResetRule:
    """
    when a day is missed, the streak resets to 0 — it
    does NOT merely decrement by 1.
    """

    def _date(self, days_ago):
        return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    def test_streak_resets_to_zero_when_today_missed(self, patch_io_paths):
        initialize_data_files()
        habits = ["Exercise"]
        save_habits(habits)

        logs = [
            ["Exercise", self._date(3), True],
            ["Exercise", self._date(2), True],
            ["Exercise", self._date(1), True],
            ["Exercise", self._date(0), False],
        ]
        streaks = {"Exercise": 0}
        update_streaks(logs, habits, streaks)

        assert streaks["Exercise"] == 0, (
            "Missed day must reset streak to 0, not decrement to 2"
        )

    def test_streak_does_not_decrement_only_resets(self, patch_io_paths):
        """
        Build a streak of 5, then miss the most recent day. The streak
        must collapse to 0 (full reset) rather than become 4.
        """
        initialize_data_files()
        habits = ["Read"]
        save_habits(habits)

        logs = [["Read", self._date(d), True] for d in range(5, 0, -1)]
        logs.append(["Read", self._date(0), False])
        streaks = {"Read": 0}
        update_streaks(logs, habits, streaks)

        assert streaks["Read"] != 4, "Streak appears to decrement; should reset"
        assert streaks["Read"] == 0


class TestMinimumHabitCount:
    """
    setup must reject any habit count < 2 and only
    proceed once the user enters a value in the [2, 10] range.
    """

    def test_setup_rejects_below_minimum(self, capsys):
        with patch(
            "builtins.input",
            side_effect=["0", "1", "2", "Exercise", "Read"],
        ):
            result = setup_habits()

        assert result == ["Exercise", "Read"]
        out = capsys.readouterr().out
        assert "between 2 and 10" in out, (
            "Expected the boundary-rejection message to appear at least once"
        )

    def test_setup_rejects_one_habit_specifically(self, capsys):
        with patch("builtins.input", side_effect=["1", "2", "A", "B"]):
            result = setup_habits()
        assert len(result) == 2
        assert "between 2 and 10" in capsys.readouterr().out


class TestVisualizationAccuracy:
    """
    the data plotted by visualize_habit_streak must
    match the raw log values: 1 for completed, 0 for missed/missing.
    We capture the actual array passed to ax.plot / ax.bar by mocking
    matplotlib.pyplot.subplots and inspect the values directly.
    """

    def _date(self, days_ago):
        return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    def _capture_plot_values(self, logs, habit, **kwargs):
        """Run visualize_habit_streak with subplots() mocked and return
        the (date_labels, completion_values) actually passed to the chart."""
        import habit_engine.habit_visualization as viz_mod

        captured = {"x": None, "y": None, "labels": None}

        fake_ax = MagicMock()

        def fake_plot(x, y, *args, **kwds):
            captured["x"] = list(x)
            captured["y"] = list(y)
            return MagicMock()

        def fake_bar(x, y, *args, **kwds):
            captured["x"] = list(x)
            captured["y"] = list(y)
            return MagicMock()

        def fake_set_xticklabels(labels, *args, **kwds):
            captured["labels"] = list(labels)

        fake_ax.plot.side_effect = fake_plot
        fake_ax.bar.side_effect = fake_bar
        fake_ax.set_xticklabels.side_effect = fake_set_xticklabels

        fake_fig = MagicMock()

        with patch.object(viz_mod.plt, "subplots", return_value=(fake_fig, fake_ax)), \
             patch.object(viz_mod.plt, "savefig"), \
             patch.object(viz_mod.plt, "close"), \
             patch.object(viz_mod.plt, "tight_layout"):
            viz_mod.visualize_habit_streak(logs, habit, **kwargs)

        return captured

    def test_completion_values_match_raw_logs(self, tmp_path, monkeypatch):
        """All-Time bar chart over a contiguous 4-day window must produce
        completion_values exactly equal to the bool-cast logs."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))

        logs = [
            ["Exercise", self._date(3), True],
            ["Exercise", self._date(2), False],
            ["Exercise", self._date(1), True],
            ["Exercise", self._date(0), True],
        ]

        captured = self._capture_plot_values(
            logs, "Exercise", chart_style="Bar Chart", date_range="All Time"
        )

        assert captured["y"] == [1, 0, 1, 1], (
            f"Plotted values {captured['y']} do not match raw completion "
            f"flags [True, False, True, True]"
        )
        assert captured["labels"] is not None
        assert len(captured["labels"]) == 4

        sorted_dates = sorted({log[1] for log in logs})
        assert captured["labels"] == sorted_dates

    def test_completion_values_after_filter(self, tmp_path, monkeypatch):
        """A log outside the 'Last 7 Days' window must not appear in
        the plotted series; in-range entries must be plotted accurately."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))

        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        logs = [
            ["Read", old_date, True],
            ["Read", self._date(2), True],
            ["Read", self._date(0), False],
        ]

        captured = self._capture_plot_values(
            logs, "Read", chart_style="Bar Chart", date_range="Last 7 Days"
        )

        assert captured["y"] is not None and captured["labels"] is not None
        for label, value in zip(captured["labels"], captured["y"]):
            assert label != old_date, "Out-of-range log leaked into plot"
            assert value in (0, 1)

        d2 = self._date(2)
        d0 = self._date(0)
        assert d2 in captured["labels"]
        assert d0 in captured["labels"]
        assert captured["y"][captured["labels"].index(d2)] == 1
        assert captured["y"][captured["labels"].index(d0)] == 0
