from unittest.mock import patch
from habit_engine import habit_logic

def test_habit_logic_validate_returns():
    # Kill string modification mutants: 6, 9, 12, 15, 19, 22, 25, 29, 36, 42, 47, 50, 52, 53
    # 6
    v, msg = habit_logic.validate_habit_data("not a list", {})
    assert msg == "Invalid habits data type"
    # 9
    v, msg = habit_logic.validate_habit_data(["A"], "not a dict")
    assert msg == "Invalid streaks data type"
    # 12
    v, msg = habit_logic.validate_habit_data([123], {})
    assert msg == "Invalid habit name type"
    # 15
    v, msg = habit_logic.validate_habit_data(["   "], {})
    assert msg == "Empty habit name"
    # 19
    v, msg = habit_logic.validate_habit_data(["x" * 51], {})
    assert msg == "Habit name too long"
    # 22
    v, msg = habit_logic.validate_habit_data(["A"], {123: 1})
    assert msg == "Invalid streak habit name type"
    # 25
    v, msg = habit_logic.validate_habit_data(["A"], {"A": "1"})
    assert msg == "Invalid streak value type"
    # 29
    v, msg = habit_logic.validate_habit_data(["A"], {"A": -1})
    assert msg == "Negative streak value"

    # Validation logs strings
    # 34: and instead of or
    v, msg = habit_logic.validate_log_entry("not_a_list")
    assert msg == "Invalid log entry format"
    v, msg = habit_logic.validate_log_entry(["a", "b"])  # len != 3 but is list
    assert msg == "Invalid log entry format"
    # 36
    assert msg == "Invalid log entry format"
    # 42
    v, msg = habit_logic.validate_log_entry([123, "2023-01-01", True])
    assert msg == "Invalid habit name in log"
    # 47
    v, msg = habit_logic.validate_log_entry(["A", "invalid_date", True])
    assert msg == "Invalid date format in log"
    # 50
    v, msg = habit_logic.validate_log_entry(["A", "2023-01-01", "True"])
    assert msg == "Invalid completion status in log"

    # 52, 53 (Exception)
    with patch('habit_engine.habit_logic.validate_date_format', side_effect=Exception('Test Error')):
        v, msg = habit_logic.validate_log_entry(["A", "2023-01-01", True])
        assert v is False
        assert msg == "Error validating log entry"

def test_habit_logic_update_streaks_mutants():
    # Kill 97, 98: break -> continue
    # If it continues instead of breaking, it will count older days as part of the streak!
    habits = ["A"]
    streaks = {"A": 0}
    # Logs are chronological. Day1 missed, Day2 done, Day3 missed, Day4 done.
    logs = [
        ["A", "2023-01-01", True],
        ["A", "2023-01-02", False],
        ["A", "2023-01-03", True],
    ]
    # Should only count 2023-01-03. Current streak should be 1.
    with patch('datetime.datetime') as mock_date:
        import datetime
        mock_date.now.return_value = datetime.datetime(2023, 1, 3)
        mock_date.strptime = datetime.datetime.strptime
        
        habit_logic.update_streaks(logs, habits, streaks)
        # If it continued, it might count 1+1=2.
        assert streaks["A"] == 1

def test_habit_logic_prints(capsys):
    # Kill 56, 63, 101, 104, 106, 110, 111, 115, 118, 119, 131, 132, 133
    from colorama import Fore, Style
    
    habit_logic.update_streaks([], "not a list", {})
    assert f"{Fore.LIGHTRED_EX}Error: Invalid habits data type{Style.RESET_ALL}\n" in capsys.readouterr().out
    
    habit_logic.update_streaks([["A", "2023-01-01", "not_bool"]], ["A"], {"A": 0})
    assert f"{Fore.LIGHTRED_EX}Warning: Skipping invalid log - Invalid completion status in log{Style.RESET_ALL}\n" in capsys.readouterr().out

    with patch('habit_engine.habit_logic.validate_log_entry', side_effect=Exception('Test Error')):
        habit_logic.update_streaks([["A", "2023-01-01", True]], ["A"], {"A": 0})
        assert f"{Fore.LIGHTRED_EX}Error updating streaks: Test Error{Style.RESET_ALL}\n" in capsys.readouterr().out

    habit_logic.log_habits("not a list")
    assert f"{Fore.LIGHTRED_EX}Error: Invalid habits data format{Style.RESET_ALL}\n" in capsys.readouterr().out
    
    habit_logic.log_habits([])
    assert f"{Fore.LIGHTRED_EX}Error: No habits to log{Style.RESET_ALL}\n" in capsys.readouterr().out
    
    with patch('builtins.input', side_effect=['y']), patch('habit_engine.habit_logic.datetime') as mock_dt:
        mock_dt.now.return_value.strftime.return_value = '2023-01-01'
        habit_logic.log_habits(["A"])
        out = capsys.readouterr().out
        assert f"\n{Fore.LIGHTWHITE_EX}=== Daily Habit Check-in ==={Style.RESET_ALL}\n" in out
        assert f"{Fore.LIGHTBLACK_EX}Date: 2023-01-01{Style.RESET_ALL}\n" in out
        assert f"\n{Fore.LIGHTGREEN_EX}Did you complete '{Fore.LIGHTBLUE_EX}A{Fore.LIGHTGREEN_EX}' today? (yes/no or y/n): {Style.RESET_ALL}" in out
        assert "XX" not in out

    with patch('builtins.input', side_effect=['maybe', 'y']):
        habit_logic.log_habits(["A"])
        out = capsys.readouterr().out
        assert f"{Fore.LIGHTRED_EX}Please enter 'yes' or 'no' (or 'y' or 'n'){Style.RESET_ALL}\n" in out
        assert "XX" not in out
        
    habit_logic.log_habits([""])  # Test skipping invalid habit
    out = capsys.readouterr().out
    assert f"{Fore.LIGHTRED_EX}Warning: Skipping invalid habit{Style.RESET_ALL}\n" in out
    assert "XX" not in out

    with patch('builtins.input', side_effect=KeyboardInterrupt):
        habit_logic.log_habits(["A"])
        out = capsys.readouterr().out
        assert f"\n{Fore.LIGHTRED_EX}Log entry cancelled.{Style.RESET_ALL}\n" in out

    with patch('builtins.input', side_effect=Exception('Test Error')):
        habit_logic.log_habits(["A"])
        out = capsys.readouterr().out
        assert f"{Fore.LIGHTRED_EX}Error logging habits: Test Error{Style.RESET_ALL}\n" in out
