from unittest.mock import patch
from habit_engine import habit_setup

def test_setup_habits_normal_and_errors(capsys):
    # Kill 295, 297, 298, 305, 306, 307, 308, 309, 312, 313, 314, 315, 316, 318, 321, 325, 329, 330, 331, 332
    
    # We will simulate a user session that types:
    # 1. Invalid number type "abc"
    # 2. Number 1 (too small)
    # 3. Number 2 (valid)
    # 4. Empty habit ""
    # 5. Habit "A" (valid)
    # 6. Habit "A" again (duplicate)
    # 7. Habit "VERY_LONG..." (too long)
    # 8. Habit "B" (valid)
    long_habit = "A" * 51
    inputs = [
        "abc",  # ValueError
        "1",    # Not between 2 and 10
        "2",    # Valid num_habits
        "",     # Empty habit -> error
        "A",    # Valid habit 1
        "A",    # Duplicate habit -> error
        long_habit, # Long habit -> error
        "B"     # Valid habit 2
    ]
    
    with patch('builtins.input', side_effect=inputs):
        habits = habit_setup.setup_habits()
        assert habits == ["A", "B"]
        
    out = capsys.readouterr().out
    
    # Check XX mutants
    assert "XX" not in out
    
    # Check specific texts to ensure string mutants are killed
    assert "Please enter a valid number." in out
    assert "Please enter a number between 2 and 10." in out
    assert "Habit cannot be empty. Please enter a valid habit." in out
    assert "You've already added this habit. Please enter a different one." in out
    assert "Habit name too long. Please keep it under 50 characters." in out
    
    # Check index mutants (312, 313, 331)
    # Should ask for Habit #1 and Habit #2
    assert "Habit #1: " in out
    assert "Habit #2: " in out
    assert "Habit #0: " not in out
    assert "Habit #3: " not in out
    
    # Should list result as "1. A" and "2. B"
    assert "1. A" in out
    assert "2. B" in out
    assert "2. A" not in out  # If enumerate started at 2, A would be 2

def test_setup_habits_interrupts(capsys):
    # Kill 307, 328 (KeyboardInterrupt string formats)
    # Inside number input
    with patch('builtins.input', side_effect=KeyboardInterrupt):
        habits = habit_setup.setup_habits()
        assert habits == []
        out = capsys.readouterr().out
        assert "XX" not in out
        assert "Setup cancelled." in out

    # Inside habit input
    with patch('builtins.input', side_effect=["2", KeyboardInterrupt]):
        habits = habit_setup.setup_habits()
        assert habits == []
        out = capsys.readouterr().out
        assert "XX" not in out
        assert "Setup cancelled." in out

def test_setup_habits_unexpected_error(capsys):
    # Kill 333 (Exception string format XX)
    # The try except block catches around the whole thing?
    # Wait, the try starts at the top, let's see.
    with patch('builtins.input', side_effect=Exception("Test Error")):
        habits = habit_setup.setup_habits()
        assert habits == []
        out = capsys.readouterr().out
        assert "Unexpected error during setup: Test Error" in out
        assert "XX" not in out
