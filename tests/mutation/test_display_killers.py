import pytest
from unittest.mock import patch
from habit_engine import habit_display

def test_habit_display_logs(capsys):
    # Kill 335, 336
    habit_display.display_logs([], {})
    out = capsys.readouterr().out
    assert "No logs found!" in out
    assert "XX" not in out
    
    # Kill len mutants: 338, 339
    # Log with len=2 creates a Date header but no log content in normal code.
    habit_display.display_logs([["A", "2023-01-01"]], {})
    out = capsys.readouterr().out
    assert "Date: 2023-01-01" in out
    
    # Normal log - also kill 347 (by passing a bad log like an int which causes exception if `or` is used)
    # Also pass a habit streak mapping showing streak=1 to kill 357 (`>0` -> `>1` where 1 is ignored by mutant)
    habit_display.display_logs([
        ["A", "2023-01-01", True], 
        ["B", "2023-01-01", False],
        ["C", "2023-01-01", True],
        123
    ], {"A": 5, "B": 0, "C": 1})
    out = capsys.readouterr().out
    assert "All recorded logs" in out
    assert "Date: 2023-01-01" in out
    assert "Error displaying logs" not in out  # If mutant 347 is alive, 'or len()' crashes on 123
    assert "XX" not in out
    
    # Kill 351, 352, 353 (streak display logic defaults, string XX variations)
    # Check streak > 0, streak == 0 formatting, completed/uncompleted formatting.
    assert "🔥 5" in out
    assert "🔥 1" in out  # Kill 357
    assert "🔥 0" not in out  # should not display if streak is not > 0
    assert "✓" in out
    assert "✗" in out
    
    # Kill 352 (.get(..., 1) default for dict)
    habit_display.display_logs([["A", "2023-01-01", True]], {}) # Empty dict -> should get 0. Mutant gets 1.
    out = capsys.readouterr().out
    assert "🔥 1" not in out
    
    # Kill 353 (get() if dict else 1)
    habit_display.display_logs([["A", "2023-01-01", True]], "not a dict") # Should default to 0. Mutant gets 1.
    out = capsys.readouterr().out
    assert "🔥 1" not in out

    # Kill 361 (Exception string format XX)
    with patch('builtins.sorted', side_effect=Exception("Test Sort Exception")):
         habit_display.display_logs([["A", "2023-01-01", True]], {})
         out = capsys.readouterr().out
         assert "Error displaying logs" in out
         assert "XX" not in out

def test_display_app_info_strings(capsys):
    # Kill ALL XX string mutants across display_app_info
    habit_display.display_app_info()
    out = capsys.readouterr().out
    clean_out = out.replace("HERALDEXX", "")
    assert "XX" not in clean_out
    assert "=*51" not in out  # Check if mutant changed formatting string directly
    # Check 366, 370 (50 -> 51)
    assert out.count("==================================================") >= 2
    assert "===================================================" not in out

def test_display_license_strings(capsys):
    # Kill XX string mutants for display_license, and 393, 397
    # Mock file access so we test normal read
    with patch('os.path.exists', return_value=True), patch('builtins.open') as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "FAKE FILE LICENSE"
        habit_display.display_license()
        out = capsys.readouterr().out
        assert "XX" not in out
        assert out.count("==================================================") >= 2
        assert "===================================================" not in out
        # Kill 397 (reads None from file) by checking if we printed our fake file
        assert "FAKE FILE LICENSE" in out

def test_display_license_fallback(capsys):
    # Kill 393, 397 by testing the fallback mode (no LICENSE file)
    with patch('os.path.exists', return_value=False):
        habit_display.display_license()
        out = capsys.readouterr().out
        assert "LICENSE" in out
        assert "XX" not in out
        
    # Kill 415 (exception string in fallback)
    with patch('os.path.exists', side_effect=Exception('Test Exc')):
        habit_display.display_license()
        out = capsys.readouterr().out
        assert "Error displaying license" in out
        assert "XX" not in out
