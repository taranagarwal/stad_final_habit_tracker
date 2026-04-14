"""
Black-Box Tests for habit_logic.py

Testing techniques applied:
  - Equivalence Partitioning (EP): inputs grouped by expected behavior class
  - Boundary Analysis (BA): edge values at partition borders
  - Error Guessing (EG): historically fault-prone scenarios (type mismatches,
    empty inputs, special characters, date edge cases)

Each test docstring states which technique(s) it exercises and the partition
or boundary it targets.
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


# validate_date_format

class TestValidateDateFormat:
    """BB tests for validate_date_format(date_str)."""

    # EP: valid partition (well-formed YYYY-MM-DD strings)
    @pytest.mark.parametrize("date_str", [
        "2024-01-15",   # typical mid-year date
        "2000-06-30",   # Y2K era
        "1999-12-31",   # end of century
    ])
    def test_valid_dates(self, date_str):
        """EP – valid dates in YYYY-MM-DD format should return True."""
        assert validate_date_format(date_str) is True

    # EP: invalid partition (wrong format or non-date strings)
    @pytest.mark.parametrize("date_str", [
        "01-15-2024",   # MM-DD-YYYY
        "2024/01/15",   # slashes
        "15-01-2024",   # DD-MM-YYYY
        "hello",        # non-date word
        "",             # empty string
    ])
    def test_invalid_format_strings(self, date_str):
        """EP – strings not matching YYYY-MM-DD should return False."""
        assert validate_date_format(date_str) is False

    # BA: leap year boundary
    def test_leap_year_valid(self):
        """BA – Feb 29 in a leap year (2024) is valid."""
        assert validate_date_format("2024-02-29") is True

    def test_leap_year_invalid(self):
        """BA – Feb 29 in a non-leap year (2023) is invalid."""
        assert validate_date_format("2023-02-29") is False

    # BA: month boundaries
    def test_month_zero(self):
        """BA – month 00 is below the valid range [01-12]."""
        assert validate_date_format("2024-00-15") is False

    def test_month_thirteen(self):
        """BA – month 13 exceeds the valid range [01-12]."""
        assert validate_date_format("2024-13-01") is False

    # BA: day boundaries
    def test_day_zero(self):
        """BA – day 00 is below the valid range."""
        assert validate_date_format("2024-01-00") is False

    def test_day_31_valid_month(self):
        """BA – day 31 for a 31-day month (January) is valid."""
        assert validate_date_format("2024-01-31") is True

    def test_day_31_invalid_month(self):
        """BA – day 31 for a 30-day month (April) is invalid."""
        assert validate_date_format("2024-04-31") is False

    # EG: type / edge-case guessing
    def test_none_input(self):
        """EG – None should not crash; expected to return False."""
        with pytest.raises((TypeError, AttributeError)):
            validate_date_format(None)

    def test_integer_input(self):
        """EG – integer input should raise or return False."""
        with pytest.raises((TypeError, AttributeError)):
            validate_date_format(20240115)

    def test_extra_whitespace(self):
        """EG – leading/trailing whitespace breaks strptime."""
        assert validate_date_format(" 2024-01-15 ") is False

    def test_date_with_time(self):
        """EG – datetime string (includes time) should fail format check."""
        assert validate_date_format("2024-01-15 12:00:00") is False


# validate_habit_data

class TestValidateHabitData:
    """BB tests for validate_habit_data(habits, habit_streaks)."""

    # EP: valid partition
    def test_valid_data(self):
        """EP – well-formed habits list and streaks dict → (True, None)."""
        habits = ["Exercise", "Read"]
        streaks = {"Exercise": 5, "Read": 0}
        valid, err = validate_habit_data(habits, streaks)
        assert valid is True
        assert err is None

    # EP: invalid habits type
    def test_habits_not_list(self):
        """EP – habits as a dict instead of list → (False, error msg)."""
        valid, err = validate_habit_data({"a": 1}, {})
        assert valid is False
        assert "habits data type" in err.lower() or "Invalid" in err

    # EP: invalid streaks type
    def test_streaks_not_dict(self):
        """EP – streaks as a list instead of dict → (False, error msg)."""
        valid, err = validate_habit_data(["Exercise"], [1, 2])
        assert valid is False

    # BA: empty containers
    def test_empty_habits_and_streaks(self):
        """BA – empty list and empty dict are valid (no habits yet)."""
        valid, err = validate_habit_data([], {})
        assert valid is True

    # BA: habit name length boundary
    def test_habit_name_exactly_50_chars(self):
        """BA – habit name at the 50-char limit is valid."""
        name = "a" * 50
        valid, err = validate_habit_data([name], {})
        assert valid is True

    def test_habit_name_51_chars(self):
        """BA – habit name at 51 chars exceeds the limit."""
        name = "a" * 51
        valid, err = validate_habit_data([name], {})
        assert valid is False
        assert "too long" in err.lower()

    # EG: whitespace-only habit name
    def test_whitespace_habit_name(self):
        """EG – a habit name of only spaces should be rejected."""
        valid, err = validate_habit_data(["   "], {})
        assert valid is False
        assert "empty" in err.lower() or "Empty" in err

    # EG: non-string habit name
    def test_integer_habit_name(self):
        """EG – integer in the habits list should be caught."""
        valid, err = validate_habit_data([123], {})
        assert valid is False

    # EG: negative streak value
    def test_negative_streak(self):
        """EG – streak of -1 is logically invalid."""
        valid, err = validate_habit_data(["Read"], {"Read": -1})
        assert valid is False
        assert "negative" in err.lower() or "Negative" in err

    # EG: float streak value
    def test_float_streak(self):
        """EG – streak as a float (2.5) should be rejected."""
        valid, err = validate_habit_data(["Read"], {"Read": 2.5})
        assert valid is False

    # EG: non-string key in streaks
    def test_non_string_streak_key(self):
        """EG – integer key in streaks dict should fail validation."""
        valid, err = validate_habit_data(["Read"], {1: 5})
        assert valid is False


# validate_log_entry

class TestValidateLogEntry:
    """BB tests for validate_log_entry(log)."""

    # EP: valid partition
    def test_valid_log_list(self):
        """EP – standard [habit, date, bool] list → (True, None)."""
        valid, err = validate_log_entry(["Exercise", "2024-06-15", True])
        assert valid is True
        assert err is None

    def test_valid_log_tuple(self):
        """EP – tuple form is also accepted per the isinstance check."""
        valid, err = validate_log_entry(("Exercise", "2024-06-15", False))
        assert valid is True

    # EP: invalid format
    def test_too_few_elements(self):
        """EP – log with only 2 elements should be invalid."""
        valid, err = validate_log_entry(["Exercise", "2024-06-15"])
        assert valid is False

    def test_too_many_elements(self):
        """EP – log with 4 elements should be invalid."""
        valid, err = validate_log_entry(["Exercise", "2024-06-15", True, "extra"])
        assert valid is False

    def test_not_a_list_or_tuple(self):
        """EP – string input should be invalid."""
        valid, err = validate_log_entry("Exercise,2024-06-15,True")
        assert valid is False

    # BA: edge habit names
    def test_empty_habit_name(self):
        """BA – empty-string habit name is invalid."""
        valid, err = validate_log_entry(["", "2024-06-15", True])
        assert valid is False

    def test_whitespace_only_habit(self):
        """BA – whitespace-only habit name is invalid."""
        valid, err = validate_log_entry(["   ", "2024-06-15", True])
        assert valid is False

    # EG: wrong types in fields
    def test_integer_habit_name(self):
        """EG – numeric habit name should be caught."""
        valid, err = validate_log_entry([123, "2024-06-15", True])
        assert valid is False

    def test_non_bool_completed(self):
        """EG – string 'yes' instead of boolean should be invalid."""
        valid, err = validate_log_entry(["Exercise", "2024-06-15", "yes"])
        assert valid is False

    def test_integer_completed(self):
        """EG – integer 1 instead of boolean True should be invalid."""
        valid, err = validate_log_entry(["Exercise", "2024-06-15", 1])
        assert valid is False

    def test_none_input(self):
        """EG – None as log should not crash."""
        valid, err = validate_log_entry(None)
        assert valid is False

    def test_bad_date_in_log(self):
        """EG – malformed date within an otherwise correct structure."""
        valid, err = validate_log_entry(["Exercise", "not-a-date", True])
        assert valid is False


# update_streaks

class TestUpdateStreaks:
    """BB tests for update_streaks(logs, habits, habit_streaks)."""

    def _make_date(self, days_ago):
        """Helper: return YYYY-MM-DD string for `days_ago` days before today."""
        return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    # EP: no logs at all
    def test_no_logs(self):
        """EP – empty log list should return True and leave streaks at 0."""
        streaks = {"Exercise": 0}
        result = update_streaks([], ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 0

    # EP: single completed day (today)
    def test_single_completed_day(self):
        """EP – one completed log today → streak of 1."""
        today = self._make_date(0)
        streaks = {"Exercise": 0}
        logs = [["Exercise", today, True]]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 1

    # EP: two consecutive completed days
    def test_two_consecutive_days(self):
        """EP – completed yesterday + today → streak of 2."""
        yesterday = self._make_date(1)
        today = self._make_date(0)
        streaks = {"Exercise": 0}
        logs = [
            ["Exercise", yesterday, True],
            ["Exercise", today, True],
        ]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 2

    # EP: streak broken by incomplete day
    def test_streak_broken_by_false(self):
        """EP – completed two days ago, NOT completed yesterday, completed today → streak of 1."""
        two_ago = self._make_date(2)
        yesterday = self._make_date(1)
        today = self._make_date(0)
        streaks = {"Exercise": 0}
        logs = [
            ["Exercise", two_ago, True],
            ["Exercise", yesterday, False],
            ["Exercise", today, True],
        ]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 1

    # EP: streak broken by gap (missing day)
    def test_streak_broken_by_gap(self):
        """EP – completed 2 days ago and today but NO log yesterday → streak of 1."""
        two_ago = self._make_date(2)
        today = self._make_date(0)
        streaks = {"Exercise": 0}
        logs = [
            ["Exercise", two_ago, True],
            ["Exercise", today, True],
        ]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 1

    # BA: future dates ignored
    def test_future_dates_ignored(self):
        """BA – logs with future dates should not contribute to streak."""
        today = self._make_date(0)
        future = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        streaks = {"Exercise": 0}
        logs = [
            ["Exercise", today, True],
            ["Exercise", future, True],
        ]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 1

    # BA: long streak (7 consecutive days)
    def test_seven_day_streak(self):
        """BA – seven consecutive completed days → streak of 7."""
        streaks = {"Exercise": 0}
        logs = [
            ["Exercise", self._make_date(i), True]
            for i in range(6, -1, -1)
        ]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 7

    # EP: multiple habits independent
    def test_independent_habits(self):
        """EP – streaks are computed independently per habit."""
        today = self._make_date(0)
        yesterday = self._make_date(1)
        habits = ["Exercise", "Read"]
        streaks = {"Exercise": 0, "Read": 0}
        logs = [
            ["Exercise", yesterday, True],
            ["Exercise", today, True],
            ["Read", today, True],
        ]
        result = update_streaks(logs, habits, streaks)
        assert result is True
        assert streaks["Exercise"] == 2
        assert streaks["Read"] == 1

    # EG: invalid habit data triggers validation failure
    def test_invalid_habits_type(self):
        """EG – non-list habits input should return False."""
        result = update_streaks([], "Exercise", {})
        assert result is False

    # EG: mixed valid and invalid logs
    def test_skips_invalid_logs(self):
        """EG – invalid log entries are skipped; valid ones still processed."""
        today = self._make_date(0)
        streaks = {"Exercise": 0}
        logs = [
            ["Exercise", today, True],
            ["bad_entry"],              # too short
            [123, today, True],         # non-string habit
        ]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert streaks["Exercise"] == 1

    # EG: new habit not in streaks dict yet
    def test_new_habit_initialized(self):
        """EG – habit not in streaks dict should be initialized to 0, then updated."""
        today = self._make_date(0)
        streaks = {}
        logs = [["Exercise", today, True]]
        result = update_streaks(logs, ["Exercise"], streaks)
        assert result is True
        assert "Exercise" in streaks
        assert streaks["Exercise"] == 1

    # EG: logs for habits not in the current habits list
    def test_logs_for_removed_habit(self):
        """EG – logs referencing a habit not in the current list are ignored."""
        today = self._make_date(0)
        streaks = {"Read": 0}
        logs = [
            ["OldHabit", today, True],
            ["Read", today, True],
        ]
        result = update_streaks(logs, ["Read"], streaks)
        assert result is True
        assert streaks["Read"] == 1
        assert "OldHabit" not in streaks

# log_habits (interactive — requires mocking input)

class TestLogHabits:
    """BB tests for log_habits(habits)."""

    # EP: valid input with 'yes' responses
    def test_all_yes(self):
        """EP – answering 'yes' for every habit produces all-True logs."""
        with patch("builtins.input", side_effect=["yes", "yes"]):
            result = log_habits(["Exercise", "Read"])
        assert result is not None
        assert len(result) == 2
        assert all(log[2] is True for log in result)

    # EP: valid input with 'no' responses
    def test_all_no(self):
        """EP – answering 'no' for every habit produces all-False logs."""
        with patch("builtins.input", side_effect=["no", "no"]):
            result = log_habits(["Exercise", "Read"])
        assert result is not None
        assert all(log[2] is False for log in result)

    # EP: short-form answers
    def test_short_form_y_n(self):
        """EP – 'y' and 'n' are accepted as valid short-form answers."""
        with patch("builtins.input", side_effect=["y", "n"]):
            result = log_habits(["Exercise", "Read"])
        assert result is not None
        assert result[0][2] is True
        assert result[1][2] is False

    # EP: invalid habits arg
    def test_non_list_habits(self):
        """EP – non-list input returns None immediately."""
        result = log_habits("not_a_list")
        assert result is None

    def test_empty_habits(self):
        """EP – empty list returns None."""
        result = log_habits([])
        assert result is None

    # EG: invalid response retried then valid
    def test_invalid_then_valid_response(self):
        """EG – invalid answer 'maybe' is retried, then 'yes' is accepted."""
        with patch("builtins.input", side_effect=["maybe", "yes"]):
            result = log_habits(["Exercise"])
        assert result is not None
        assert len(result) == 1
        assert result[0][2] is True

    # EG: KeyboardInterrupt returns None
    def test_keyboard_interrupt(self):
        """EG – Ctrl+C during input returns None."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = log_habits(["Exercise"])
        assert result is None

    # EG: non-string habit in list skipped
    def test_non_string_habit_skipped(self):
        """EG – non-string items in habits list are skipped."""
        with patch("builtins.input", side_effect=["yes"]):
            result = log_habits([123, "Exercise"])
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == "Exercise"

    # BA: log date is always today
    def test_log_date_is_today(self):
        """BA – every log entry uses today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        with patch("builtins.input", side_effect=["yes"]):
            result = log_habits(["Exercise"])
        assert result[0][1] == today
