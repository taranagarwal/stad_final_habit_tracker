import os
from habit_engine import habit_io

def test_habit_io_constants_mutations():
    # Kill mutations in DEFAULT_SETTINGS keys and values
    assert habit_io.DEFAULT_SETTINGS["appearance_mode"] == "System", "appearance_mode must be 'System'"
    assert habit_io.DEFAULT_SETTINGS["autosave_interval"] == 30, "autosave_interval must be 30"
    assert habit_io.DEFAULT_SETTINGS["daily_reminder_enabled"] == 0, "daily_reminder_enabled must be 0"
    assert habit_io.DEFAULT_SETTINGS["reminder_time"] == "09:00", "reminder_time must be '09:00'"
    assert habit_io.DEFAULT_SETTINGS["chart_style"] == "Line Plot", "chart_style must be 'Line Plot'"
    assert habit_io.DEFAULT_SETTINGS["show_streak_annotations"] is True, "show_streak_annotations must be True"
    assert habit_io.DEFAULT_SETTINGS["chart_date_range"] == "Last 30 Days", "chart_date_range must be 'Last 30 Days'"

def test_habit_io_core_files_mutations():
    # Kill mutations in CORE_FILES
    assert len(habit_io.CORE_FILES) == 10, "CORE_FILES should contain exactly 10 paths"
    assert os.path.basename(habit_io.CORE_FILES[0]) == "__init__.py"
    assert os.path.basename(habit_io.CORE_FILES[1]) == "habit_setup.py"
    assert os.path.basename(habit_io.CORE_FILES[2]) == "habit_io.py"
    assert os.path.basename(habit_io.CORE_FILES[3]) == "habit_logic.py"
    assert os.path.basename(habit_io.CORE_FILES[4]) == "habit_display.py"
    assert os.path.basename(habit_io.CORE_FILES[5]) == "gui.py"
    assert os.path.basename(habit_io.CORE_FILES[6]) == "habit_visualization.py"
    assert os.path.basename(habit_io.CORE_FILES[7]) == "main.py"
    assert os.path.basename(habit_io.CORE_FILES[8]) == "README.md"
    assert os.path.basename(habit_io.CORE_FILES[9]) == "LICENSE"

def test_habit_io_paths_mutations():
    # Kill mutations in hardcoded paths
    assert os.path.basename(habit_io.DATA_DIR) == "data", "DATA_DIR should be 'data'"
    assert os.path.basename(habit_io.PLOTS_DIR) == "plots", "PLOTS_DIR should be 'plots'"
    assert os.path.basename(habit_io.ASSETS_DIR) == "assets", "ASSETS_DIR should be 'assets'"
    assert os.path.basename(habit_io.SETTINGS_PATH) == "settings.json", "SETTINGS_PATH should end with 'settings.json'"
    assert os.path.basename(habit_io.HABITS_FILE) == "habits.json", "HABITS_FILE should end with 'habits.json'"
    assert os.path.basename(habit_io.LOGS_FILE) == "logs.json", "LOGS_FILE should end with 'logs.json'"
    assert os.path.basename(habit_io.STREAKS_FILE) == "streaks.json", "STREAKS_FILE should end with 'streaks.json'"

import sys
from importlib import reload
from unittest.mock import patch

def test_habit_io_frozen_paths():
    # Test the frozen logic in habit_io to kill mutations 149-153, 159, 161, 162, 200
    with patch.object(sys, 'frozen', True, create=True), \
         patch.object(sys, '_MEIPASS', '/tmp/mock_meipass', create=True):
        
        # We need to reload the module so the module-level if statements are re-evaluated
        reload(habit_io)
        
        assert habit_io.BASE_DIR == os.path.join(os.path.expanduser('~'), '.heraldexx-habit-tracker')
        assert habit_io.ASSETS_DIR == os.path.join('/tmp/mock_meipass', 'assets')

    # Reload back to normal so we don't break other tests
    reload(habit_io)

import stat
def test_habit_io_permissions_mutation():
    # Kill 208
    with patch('os.stat') as mock_stat, patch('os.chmod') as mock_chmod:
        class DummyStat:
            st_mode = 0o777 # rwxrwxrwx
        mock_stat.return_value = DummyStat()
        
        # Test make_files_readonly
        with patch('habit_engine.habit_io.CORE_FILES', ['/tmp/dummy.py']):
            habit_io.make_files_readonly()
            
            # Should have removed all W permissions. 0o777 & ~0o222 = 0o555
            mock_chmod.assert_called_with('/tmp/dummy.py', 0o555)

def test_habit_io_load_backup_suffixes():
    # Kill 251, 260, 264
    with patch('habit_engine.habit_io.try_load_json') as mock_try_load:
        mock_try_load.return_value = []
        habit_io.load_habits()
        mock_try_load.assert_called_with(habit_io.HABITS_FILE, habit_io.HABITS_FILE + '.bak')
        
        mock_try_load.return_value = {}
        habit_io.load_habit_streaks()
        mock_try_load.assert_called_with(habit_io.STREAKS_FILE, habit_io.STREAKS_FILE + '.bak')
        
        mock_try_load.return_value = []
        habit_io.load_daily_logs()
        mock_try_load.assert_called_with(habit_io.LOGS_FILE, habit_io.LOGS_FILE + '.bak')

def test_habit_io_save_both_fail():
    # Kill 279
    with patch('habit_engine.habit_io.save_with_backup') as mock_save:
        mock_save.side_effect = [True, False]
        assert habit_io.save_daily_logs([], {}) == False
        
        mock_save.side_effect = [False, True]
        assert habit_io.save_daily_logs([], {}) == False

def test_habit_io_makedirs_exist_ok():
    # Kill 285, 291
    with patch('os.path.exists', return_value=True), \
         patch('shutil.rmtree'), \
         patch('os.makedirs') as mock_makedirs, \
         patch('habit_engine.habit_io.save_settings'), \
         patch('habit_engine.habit_io.initialize_data_files'):
        
        habit_io.reset_app_data()
        mock_makedirs.assert_called_with(habit_io.PLOTS_DIR, exist_ok=True)
        
        mock_makedirs.reset_mock()
        with patch('os.remove'):
            habit_io.clear_tracking_data()
            mock_makedirs.assert_called_with(habit_io.PLOTS_DIR, exist_ok=True)

def test_habit_io_prints(capsys):
    # Kill mutations that change error prints (210, 213, 220, 223, 233, 244, 253, 255, 257, 262, 271, 275, 280, 287, 293)
    from colorama import Fore, Style
    
    with patch('habit_engine.habit_io.CORE_FILES', ['/tmp/dummy.py']):
        with patch('os.path.exists', return_value=True):
            with patch('os.stat', side_effect=Exception('Test Error')):
                habit_io.make_files_readonly()
                captured = capsys.readouterr()
                assert f"{Fore.LIGHTRED_EX}Error setting read-only for dummy.py: Test Error{Style.RESET_ALL}\n" in captured.out
                
                habit_io.make_files_writable()
                captured = capsys.readouterr()
                assert f"{Fore.LIGHTRED_EX}Error setting writable for dummy.py: Test Error{Style.RESET_ALL}\n" in captured.out

    with patch('habit_engine.habit_io.DATA_DIR', '/tmp/dummy_data'):
        with patch('os.makedirs', side_effect=Exception('Test Error')):
            habit_io.initialize_data_files()
            captured = capsys.readouterr()
            assert f"{Fore.LIGHTRED_EX}Error initializing data files: Test Error{Style.RESET_ALL}\n" in captured.out
            
            with patch('shutil.rmtree', side_effect=Exception('Test Error')), patch('os.path.exists', return_value=True):
                habit_io.reset_app_data()
                captured = capsys.readouterr()
                assert f"{Fore.LIGHTRED_EX}Error resetting application data: Test Error{Style.RESET_ALL}\n" in captured.out
                
                habit_io.clear_tracking_data()
                captured = capsys.readouterr()
                assert f"{Fore.LIGHTRED_EX}Error clearing tracking data: Test Error{Style.RESET_ALL}\n" in captured.out

    with patch('builtins.open', side_effect=Exception('Test Error')):
        habit_io.save_with_backup('/tmp/test', {})
        captured = capsys.readouterr()
        assert f"{Fore.LIGHTRED_EX}Error in save_with_backup: Test Error{Style.RESET_ALL}\n" in captured.out

    habit_io.save_habits("not a list")
    captured = capsys.readouterr()
    assert f"{Fore.LIGHTRED_EX}Error: Invalid habits data format{Style.RESET_ALL}\n" in captured.out
    
    habit_io.save_daily_logs("not a list", {})
    captured = capsys.readouterr()
    assert f"{Fore.LIGHTRED_EX}Error: Invalid data format{Style.RESET_ALL}\n" in captured.out

    with patch('habit_engine.habit_io.save_with_backup', side_effect=Exception('Test Error')):
        habit_io.save_habits([])
        captured = capsys.readouterr()
        assert f"{Fore.LIGHTRED_EX}Error saving habits: Test Error{Style.RESET_ALL}\n" in captured.out
        
        habit_io.save_daily_logs([], {})
        captured = capsys.readouterr()
        assert f"{Fore.LIGHTRED_EX}Error saving logs: Test Error{Style.RESET_ALL}\n" in captured.out
        
    with patch('habit_engine.habit_io.try_load_json', side_effect=Exception('Test Error')):
        habit_io.load_habits()
        captured = capsys.readouterr()
        assert f"{Fore.LIGHTRED_EX}Error loading habits: Test Error{Style.RESET_ALL}\n" in captured.out
        
        habit_io.load_habit_streaks()
        captured = capsys.readouterr()
        assert f"{Fore.LIGHTRED_EX}Error loading streaks: Test Error{Style.RESET_ALL}\n" in captured.out
        
        habit_io.load_daily_logs()
        captured = capsys.readouterr()
        assert f"{Fore.LIGHTRED_EX}Error loading logs: Test Error{Style.RESET_ALL}\n" in captured.out


def test_habit_io_frozen_default(capsys):
    # Kill 150 (the default False in getattr). Just reloading normal mode should have False default.
    from importlib import reload
    import sys
    reload(habit_io)
    # in dev mode, ASSETS_DIR is not from MEIPASS
    assert habit_io.ASSETS_DIR == os.path.join(habit_io.BASE_DIR, "assets")

def test_habit_io_print_success(capsys):
    # Kill 213, 223
    with patch('habit_engine.habit_io.CORE_FILES', ['/tmp/dummy.py']):
        with patch('os.path.exists', return_value=True):
            with patch('os.stat') as m_stat, patch('os.chmod'):
                m_stat.return_value.st_mode = 0o777
                habit_io.make_files_readonly()
                assert "Protected 1 core files" in capsys.readouterr().out
                
                habit_io.make_files_writable()
                assert "Unlocked 1 core files" in capsys.readouterr().out

def test_habit_io_get_asset_path_frozen():
    # Kill 200
    with patch('sys.frozen', True, create=True), \
         patch('sys._MEIPASS', '/tmp/mock_meipass', create=True):
        assert habit_io.get_asset_path('test.png') == os.path.join('/tmp/mock_meipass', 'assets', 'test.png')
