"""
White-Box Tests for habit_visualization.py

Goal: cover branches in _filter_logs_by_date_range and visualize_habit_streak
including date-range filtering, chart styles, streak annotations, empty-data
paths, and error handling.
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from habit_engine.habit_visualization import (
    _filter_logs_by_date_range,
    visualize_habit_streak,
)


# _filter_logs_by_date_range — branches

class TestFilterLogsByDateRange:
    """WB: branches in _filter_logs_by_date_range."""

    def _make_log(self, days_ago, habit="Ex", completed=True):
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        return [habit, date, completed]

    # "All Time" branch (no date filter)
    def test_all_time_returns_all(self):
        """Branch: date_range_str not in 7/30 → start_date_filter is None → all logs pass."""
        logs = [self._make_log(100), self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "All Time")
        assert len(result) == 2

    # "Last 7 Days" branch
    def test_last_7_days_filters(self):
        """Branch: 'Last 7 Days' → start_date_filter = today-6."""
        logs = [self._make_log(10), self._make_log(5), self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "Last 7 Days")
        assert len(result) == 2  # 5 days ago and today

    # "Last 30 Days" branch
    def test_last_30_days_filters(self):
        """Branch: 'Last 30 Days' → start_date_filter = today-29."""
        logs = [self._make_log(50), self._make_log(20), self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "Last 30 Days")
        assert len(result) == 2

    # malformed log structure skipped
    def test_malformed_log_skipped(self):
        """Branch: log doesn't have correct structure → continue."""
        logs = [["bad"], self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "All Time")
        assert len(result) == 1

    # non-list log skipped
    def test_non_list_log_skipped(self):
        """Branch: not isinstance(log, list) → continue."""
        logs = ["not_a_list", self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "All Time")
        assert len(result) == 1

    # malformed date ValueError
    def test_invalid_date_format_skipped(self):
        """Branch: ValueError from strptime → continue."""
        logs = [["Ex", "not-a-date", True], self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "All Time")
        assert len(result) == 1

    # non-string date field
    def test_non_string_date_skipped(self):
        """Branch: isinstance(log[1], str) is False → continue."""
        logs = [["Ex", 12345, True], self._make_log(0)]
        result = _filter_logs_by_date_range(logs, "All Time")
        assert len(result) == 1

    # empty input
    def test_empty_logs(self):
        """Branch: no logs → returns empty list."""
        assert _filter_logs_by_date_range([], "All Time") == []


# visualize_habit_streak — branches

class TestVisualizeHabitStreak:
    """WB: cover major branches in visualize_habit_streak."""

    def _make_log(self, days_ago, habit="Ex", completed=True):
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        return [habit, date, completed]

    # no logs for habit → return None
    def test_no_logs_for_habit_returns_none(self, tmp_path, monkeypatch):
        """Branch: habit_logs_for_name empty → return None."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [["Other", "2024-01-01", True]]
        assert visualize_habit_streak(logs, "Ex") is None

    # successful line plot
    def test_line_plot_creates_file(self, tmp_path, monkeypatch):
        """Branch: chart_style == 'Line Plot' → creates PNG."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [self._make_log(1), self._make_log(0)]
        result = visualize_habit_streak(logs, "Ex", chart_style="Line Plot")
        assert result is not None
        assert os.path.exists(result)
        assert result.endswith(".png")

    # bar chart branch
    def test_bar_chart_creates_file(self, tmp_path, monkeypatch):
        """Branch: chart_style == 'Bar Chart' → creates PNG."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [self._make_log(1), self._make_log(0)]
        result = visualize_habit_streak(logs, "Ex", chart_style="Bar Chart")
        assert result is not None
        assert os.path.exists(result)

    # streak annotations enabled with data
    def test_streak_annotations_enabled(self, tmp_path, monkeypatch):
        """Branch: show_streak_annotations and filtered_habit_logs."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [self._make_log(1), self._make_log(0)]
        result = visualize_habit_streak(
            logs, "Ex", show_streak_annotations=True
        )
        assert result is not None

    # streak annotations disabled
    def test_streak_annotations_disabled(self, tmp_path, monkeypatch):
        """Branch: show_streak_annotations is False → skip annotations."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [self._make_log(0)]
        result = visualize_habit_streak(
            logs, "Ex", show_streak_annotations=False
        )
        assert result is not None

    # annotation with bar chart y_offset
    def test_annotation_bar_chart_offset(self, tmp_path, monkeypatch):
        """Branch: chart_style == 'Bar Chart' → y_offset = 0.05."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [self._make_log(0)]
        result = visualize_habit_streak(
            logs, "Ex", chart_style="Bar Chart", show_streak_annotations=True
        )
        assert result is not None

    # empty filtered logs after date range → blank chart
    def test_empty_after_filter_last_7(self, tmp_path, monkeypatch):
        """Branch: filtered_habit_logs empty, date_range='Last 7 Days' → blank chart."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        old_log = [["Ex", "2020-01-01", True]]
        result = visualize_habit_streak(
            old_log, "Ex", date_range="Last 7 Days"
        )
        assert result is not None

    def test_empty_after_filter_last_30(self, tmp_path, monkeypatch):
        """Branch: filtered empty, date_range='Last 30 Days' → blank chart."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        old_log = [["Ex", "2020-01-01", True]]
        result = visualize_habit_streak(
            old_log, "Ex", date_range="Last 30 Days"
        )
        assert result is not None

    def test_empty_after_filter_all_time(self, tmp_path, monkeypatch):
        """Branch: filtered empty, date_range='All Time' → show today only."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        future = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
        logs = [["Ex", future, True]]
        # _filter_logs_by_date_range will include this since All Time has no date filter,
        # but the habit_logs_for_name will have data. We need logs that pass the name
        # filter but fail the date range filter. Use "Last 7 Days" with old data instead.
        # Actually for All Time empty path, we need no logs at all after filtering.
        # This is hard to trigger with All Time since it passes everything through.
        # Skip and test with a direct mock.
        with patch.object(viz_mod, "_filter_logs_by_date_range", return_value=[]):
            result = visualize_habit_streak(
                [["Ex", "2024-01-01", True]], "Ex", date_range="All Time"
            )
        assert result is not None

    # date_range extends to today for Last N days
    def test_date_range_extends_to_today(self, tmp_path, monkeypatch):
        """Branch: date_range in Last 7/30 → plot_end_date = max(last_log, today)."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [self._make_log(5)]
        result = visualize_habit_streak(
            logs, "Ex", date_range="Last 7 Days"
        )
        assert result is not None

    # streak resets on missed day in annotations
    def test_streak_annotation_resets_on_miss(self, tmp_path, monkeypatch):
        """Branch: is_completed False → current_streak=0."""
        import habit_engine.habit_visualization as viz_mod
        monkeypatch.setattr(viz_mod, "PLOTS_DIR", str(tmp_path))
        logs = [
            self._make_log(2, completed=True),
            self._make_log(1, completed=False),
            self._make_log(0, completed=True),
        ]
        result = visualize_habit_streak(
            logs, "Ex", show_streak_annotations=True
        )
        assert result is not None

    # exception in visualize → return None
    def test_exception_returns_none(self):
        """Branch: except Exception → return None."""
        with patch("habit_engine.habit_visualization.plt", side_effect=RuntimeError):
            result = visualize_habit_streak([["Ex", "2024-01-01", True]], "Ex")
        assert result is None
