"""
White-Box Tests for habit_setup.py

Goal: cover all branches in setup_habits including input validation loops,
habit count boundaries, duplicate detection, name length limit, and
interrupt handling.
"""

import pytest
from unittest.mock import patch

from habit_engine.habit_setup import setup_habits


class TestSetupHabitsWB:
    """WB: branch coverage for setup_habits."""

    # happy path: 2 valid habits (minimum)
    def test_minimum_habits(self):
        """Branch: num_habits=2 (minimum valid), two valid names → returns list of 2."""
        with patch("builtins.input", side_effect=["2", "Exercise", "Read"]):
            result = setup_habits()
        assert result == ["Exercise", "Read"]

    # happy path: 10 valid habits (maximum)
    def test_maximum_habits(self):
        """Branch: num_habits=10 (maximum valid) → returns list of 10."""
        names = [f"Habit{i}" for i in range(1, 11)]
        with patch("builtins.input", side_effect=["10"] + names):
            result = setup_habits()
        assert len(result) == 10

    # BA: below minimum (1) then corrected
    def test_below_minimum_then_valid(self):
        """Branch: num_habits=1 rejected, then 2 accepted."""
        with patch("builtins.input", side_effect=["1", "2", "A", "B"]):
            result = setup_habits()
        assert len(result) == 2

    # BA: above maximum (11) then corrected
    def test_above_maximum_then_valid(self):
        """Branch: num_habits=11 rejected, then 3 accepted."""
        with patch("builtins.input", side_effect=["11", "3", "A", "B", "C"]):
            result = setup_habits()
        assert len(result) == 3

    # non-integer input for count → ValueError
    def test_non_integer_count(self):
        """Branch: 'abc' raises ValueError → retry loop."""
        with patch("builtins.input", side_effect=["abc", "2", "A", "B"]):
            result = setup_habits()
        assert len(result) == 2

    # KeyboardInterrupt during count input
    def test_keyboard_interrupt_during_count(self):
        """Branch: KeyboardInterrupt during count → return []."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = setup_habits()
        assert result == []

    # empty habit name rejected
    def test_empty_habit_name_rejected(self):
        """Branch: empty string → 'cannot be empty', retry."""
        with patch("builtins.input", side_effect=["2", "", "Exercise", "Read"]):
            result = setup_habits()
        assert result == ["Exercise", "Read"]

    # duplicate habit name rejected
    def test_duplicate_habit_rejected(self):
        """Branch: duplicate name → 'already added', retry."""
        with patch("builtins.input", side_effect=["2", "Exercise", "Exercise", "Read"]):
            result = setup_habits()
        assert result == ["Exercise", "Read"]

    # habit name too long rejected
    def test_habit_name_too_long(self):
        """Branch: name > 50 chars → 'too long', retry."""
        long_name = "x" * 51
        with patch("builtins.input", side_effect=["2", long_name, "Exercise", "Read"]):
            result = setup_habits()
        assert result == ["Exercise", "Read"]

    # BA: habit name exactly 50 chars accepted
    def test_habit_name_exactly_50_chars(self):
        """BA: name at 50 chars passes the len check."""
        name_50 = "x" * 50
        with patch("builtins.input", side_effect=["2", name_50, "Read"]):
            result = setup_habits()
        assert name_50 in result

    # KeyboardInterrupt during habit name input
    def test_keyboard_interrupt_during_name_input(self):
        """Branch: KeyboardInterrupt during name entry → return []."""
        with patch("builtins.input", side_effect=["2", KeyboardInterrupt]):
            result = setup_habits()
        assert result == []

    # generic Exception
    def test_generic_exception(self):
        """Branch: unexpected Exception → return []."""
        with patch("builtins.input", side_effect=RuntimeError("unexpected")):
            result = setup_habits()
        assert result == []
