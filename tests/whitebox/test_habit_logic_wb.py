"""
White-Box Tests for habit_logic.py

Goal: maximize branch coverage by deliberately targeting every conditional
branch in validate_date_format, validate_habit_data, validate_log_entry,
update_streaks, and log_habits.

Each test docstring cites the branch it is designed
to cover.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from habit_engine.habit_logic import (
    validate_date_format,
    validate_habit_data,
    validate_log_entry,
    update_streaks,
    log_habits,
)


# validate_date_format — branches: try→True | except→False

class TestValidateDateFormatWB:
    """WB: two branches – strptime succeeds (True) or raises ValueError (False)."""

    def test_success_branch(self):
        """Covers try body → return True ."""
        assert validate_date_format("2024-06-15") is True

    def test_value_error_branch(self):
        """Covers except ValueError → return False."""
        assert validate_date_format("invalid") is False


# validate_habit_data — branches per condition

class TestValidateHabitDataWB:
    """WB: one test per conditional branch in validate_habit_data."""

    def test_habits_not_list_branch(self):
        """Branch: isinstance(habits, list) is False."""
        valid, _ = validate_habit_data("string", {})
        assert valid is False

    def test_streaks_not_dict_branch(self):
        """Branch: isinstance(habit_streaks, dict) is False."""
        valid, _ = validate_habit_data([], "string")
        assert valid is False

    def test_habit_not_string_branch(self):
        """Branch: isinstance(habit, str) is False."""
        valid, _ = validate_habit_data([42], {})
        assert valid is False

    def test_habit_empty_after_strip_branch(self):
        """Branch: not habit.strip() is True."""
        valid, _ = validate_habit_data(["  "], {})
        assert valid is False

    def test_habit_too_long_branch(self):
        """Branch: len(habit) > 50 is True."""
        valid, _ = validate_habit_data(["x" * 51], {})
        assert valid is False

    def test_streak_key_not_string_branch(self):
        """Branch: isinstance(habit, str) is False in streak loop."""
        valid, _ = validate_habit_data([], {1: 5})
        assert valid is False

    def test_streak_value_not_int_branch(self):
        """Branch: isinstance(streak, int) is False."""
        valid, _ = validate_habit_data([], {"a": "five"})
        assert valid is False

    def test_streak_negative_branch(self):
        """Branch: streak < 0 is True."""
        valid, _ = validate_habit_data([], {"a": -1})
        assert valid is False

    def test_all_valid_branch(self):
        """Branch: all checks pass → return True, None."""
        valid, err = validate_habit_data(["Read"], {"Read": 3})
        assert valid is True
        assert err is None


# validate_log_entry — branches per condition

class TestValidateLogEntryWB:
    """WB: one test per conditional branch."""

    def test_not_list_or_tuple_branch(self):
        """Branch: not isinstance(log, (list, tuple))."""
        valid, _ = validate_log_entry({"a": 1})
        assert valid is False

    def test_wrong_length_branch(self):
        """Branch: len(log) != 3."""
        valid, _ = validate_log_entry(["a", "b"])
        assert valid is False

    def test_habit_not_string_branch(self):
        """Branch: not isinstance(habit, str)."""
        valid, _ = validate_log_entry([42, "2024-01-01", True])
        assert valid is False

    def test_habit_empty_strip_branch(self):
        """Branch: not habit.strip()."""
        valid, _ = validate_log_entry(["", "2024-01-01", True])
        assert valid is False

    def test_date_not_string_branch(self):
        """Branch: not isinstance(date, str)."""
        valid, _ = validate_log_entry(["Ex", 20240101, True])
        assert valid is False

    def test_date_invalid_format_branch(self):
        """Branch: not validate_date_format(date)."""
        valid, _ = validate_log_entry(["Ex", "bad-date", True])
        assert valid is False

    def test_completed_not_bool_branch(self):
        """Branch: not isinstance(completed, bool)."""
        valid, _ = validate_log_entry(["Ex", "2024-01-01", 1])
        assert valid is False

    def test_all_valid_branch(self):
        """Branch: all checks pass → (True, None)."""
        valid, err = validate_log_entry(["Ex", "2024-01-01", True])
        assert valid is True

    def test_generic_exception_branch(self):
        """Branch: except Exception — triggered by unpacking error."""
        valid, _ = validate_log_entry([])
        assert valid is False


# update_streaks — branch-coverage-driven tests

class TestUpdateStreaksWB:
    """WB: target every branch in the update_streaks function."""

    def _date(self, days_ago):
        return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    # validation failure branch
    def test_validation_failure_returns_false(self):
        """Branch: valid is False → print error, return False."""
        result = update_streaks([], "not_a_list", {})
        assert result is False

    # habit not in streaks → initialize
    def test_initializes_missing_streak(self):
        """Branch: habit not in habit_streaks → set to 0."""
        streaks = {}
        update_streaks([], ["NewHabit"], streaks)
        assert streaks["NewHabit"] == 0

    # invalid log skipped
    def test_invalid_log_produces_warning(self):
        """Branch: log_valid is False → print warning."""
        streaks = {"Ex": 0}
        result = update_streaks([["bad"]], ["Ex"], streaks)
        assert result is True

    # no valid dates → early return True
    def test_no_valid_dates_returns_true(self):
        """Branch: not dates → return True."""
        streaks = {"Ex": 0}
        logs = [["OtherHabit", self._date(0), True]]
        result = update_streaks(logs, ["Ex"], streaks)
        assert result is True
        assert streaks["Ex"] == 0

    # future date skipped via continue
    def test_future_date_continue_branch(self):
        """Branch: log_date > today → continue."""
        future = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        today = self._date(0)
        streaks = {"Ex": 0}
        logs = [["Ex", future, True], ["Ex", today, True]]
        update_streaks(logs, ["Ex"], streaks)
        assert streaks["Ex"] == 1

    # no log for habit on date → habit_log is None
    def test_no_log_for_habit_on_date(self):
        """Branch: habit_log is None → no streak update for that date.
        Date exists due to another habit but this habit has no log."""
        today = self._date(0)
        streaks = {"A": 0, "B": 0}
        logs = [["A", today, True]]
        update_streaks(logs, ["A", "B"], streaks)
        assert streaks["A"] == 1
        assert streaks["B"] == 0

    # first completed date: last_completed_date is None
    def test_first_completed_sets_streak_to_1(self):
        """Branch: last_completed_date is None and completed → streak=1."""
        today = self._date(0)
        streaks = {"Ex": 0}
        update_streaks([["Ex", today, True]], ["Ex"], streaks)
        assert streaks["Ex"] == 1

    # consecutive day: days_between == 1
    def test_consecutive_day_increments(self):
        """Branch: days_between == 1 → streak += 1."""
        streaks = {"Ex": 0}
        logs = [["Ex", self._date(1), True], ["Ex", self._date(0), True]]
        update_streaks(logs, ["Ex"], streaks)
        assert streaks["Ex"] == 2

    # non-consecutive completed: days_between > 1
    def test_non_consecutive_breaks_streak(self):
        """Branch: days_between != 1 → break."""
        streaks = {"Ex": 0}
        logs = [["Ex", self._date(3), True], ["Ex", self._date(0), True]]
        update_streaks(logs, ["Ex"], streaks)
        assert streaks["Ex"] == 1

    # not completed → break
    def test_not_completed_breaks(self):
        """Branch: completed is False → break."""
        streaks = {"Ex": 0}
        logs = [
            ["Ex", self._date(1), False],
            ["Ex", self._date(0), True],
        ]
        update_streaks(logs, ["Ex"], streaks)
        assert streaks["Ex"] == 1

    # generic exception in update_streaks
    def test_exception_returns_false(self):
        """Branch: except Exception → return False.
        Force an exception by passing a log whose date field causes strptime to fail
        but that passes validate_log_entry (not possible with current validation,
        so we mock validate_log_entry to let a bad log through)."""
        with patch("habit_engine.habit_logic.validate_log_entry", return_value=(True, None)):
            streaks = {"Ex": 0}
            bad_logs = [["Ex", "not-a-date", True]]
            result = update_streaks(bad_logs, ["Ex"], streaks)
            assert result is False


# log_habits — branch coverage

class TestLogHabitsWB:
    """WB: target every branch in log_habits."""

    # not isinstance(habits, list)
    def test_non_list_returns_none(self):
        """Branch: habits is not a list → return None."""
        assert log_habits("string") is None

    # empty habits
    def test_empty_list_returns_none(self):
        """Branch: not habits → return None."""
        assert log_habits([]) is None

    # habit is not a string → skip
    def test_non_string_habit_skipped(self):
        """Branch: not isinstance(habit, str) → continue."""
        with patch("builtins.input", side_effect=["yes"]):
            result = log_habits([None, "Exercise"])
        assert len(result) == 1

    # whitespace-only habit → skip
    def test_whitespace_habit_skipped(self):
        """Branch: not habit.strip() → continue."""
        with patch("builtins.input", side_effect=["yes"]):
            result = log_habits(["   ", "Exercise"])
        assert len(result) == 1

    # valid 'y'/'yes' response
    def test_yes_response(self):
        """Branch: response in ['y', 'yes'] → completed=True."""
        with patch("builtins.input", side_effect=["y"]):
            result = log_habits(["Ex"])
        assert result[0][2] is True

    # valid 'n'/'no' response
    def test_no_response(self):
        """Branch: response in ['n', 'no'] → completed=False."""
        with patch("builtins.input", side_effect=["no"]):
            result = log_habits(["Ex"])
        assert result[0][2] is False

    # invalid response → retry loop
    def test_retry_on_invalid(self):
        """Branch: response not in valid set → print error, loop."""
        with patch("builtins.input", side_effect=["maybe", "n"]):
            result = log_habits(["Ex"])
        assert result[0][2] is False

    # KeyboardInterrupt
    def test_keyboard_interrupt(self):
        """Branch: KeyboardInterrupt → return None."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            assert log_habits(["Ex"]) is None

    # generic Exception
    def test_generic_exception(self):
        """Branch: Exception → return None."""
        with patch("builtins.input", side_effect=RuntimeError("fail")):
            assert log_habits(["Ex"]) is None

    # no new_logs produced → return None 
    def test_all_habits_invalid_returns_none(self):
        """Branch: new_logs is empty → return None."""
        result = log_habits([123, None])
        assert result is None
