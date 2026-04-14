"""
Black-Box Tests for habit_io.py

Testing techniques applied:
  - Equivalence Partitioning (EP): grouping inputs by expected I/O behavior
  - Boundary Analysis (BA): file-existence edges, empty vs non-empty data
  - Error Guessing (EG): corrupted JSON, permission errors, type mismatches

All tests use the ``patch_io_paths`` / ``seeded_data_dir`` fixtures from
conftest.py so that real data files are never modified.
"""

import json
import os
import pytest

from habit_engine.habit_io import (
    load_settings,
    save_settings,
    load_habits,
    save_habits,
    load_habit_streaks,
    load_daily_logs,
    save_daily_logs,
    save_with_backup,
    try_load_json,
    initialize_data_files,
    reset_app_data,
    clear_tracking_data,
    DEFAULT_SETTINGS,
)


# load_settings / save_settings

class TestLoadSettings:
    """BB tests for load_settings()."""

    def test_creates_defaults_when_missing(self, patch_io_paths):
        """EP – no settings file on disk → creates file, returns defaults."""
        settings = load_settings()
        assert settings == DEFAULT_SETTINGS
        assert os.path.exists(patch_io_paths["settings_file"])

    def test_loads_existing_valid_settings(self, patch_io_paths):
        """EP – valid settings file → returns contents."""
        custom = {**DEFAULT_SETTINGS, "autosave_interval": 60}
        with open(patch_io_paths["settings_file"], "w") as f:
            json.dump(custom, f)
        settings = load_settings()
        assert settings["autosave_interval"] == 60

    def test_missing_keys_get_defaults(self, patch_io_paths):
        """BA – settings file with a subset of keys → missing keys filled from defaults."""
        partial = {"appearance_mode": "Dark"}
        with open(patch_io_paths["settings_file"], "w") as f:
            json.dump(partial, f)
        settings = load_settings()
        assert settings["appearance_mode"] == "Dark"
        assert settings["autosave_interval"] == DEFAULT_SETTINGS["autosave_interval"]

    def test_corrupted_json_resets_to_defaults(self, patch_io_paths):
        """EG – corrupted (non-JSON) settings file → overwritten with defaults."""
        with open(patch_io_paths["settings_file"], "w") as f:
            f.write("{{{bad json")
        settings = load_settings()
        assert settings == DEFAULT_SETTINGS


class TestSaveSettings:
    """BB tests for save_settings()."""

    def test_round_trip(self, patch_io_paths):
        """EP – save then load produces identical dict."""
        custom = {**DEFAULT_SETTINGS, "chart_style": "Bar Chart"}
        save_settings(custom)
        with open(patch_io_paths["settings_file"]) as f:
            on_disk = json.load(f)
        assert on_disk["chart_style"] == "Bar Chart"


# load_habits / save_habits

class TestLoadHabits:
    """BB tests for load_habits()."""

    def test_no_file_returns_empty(self, patch_io_paths):
        """EP – habits file does not exist → empty list."""
        assert load_habits() == []

    def test_loads_valid_habits(self, seeded_data_dir):
        """EP – valid habits file → list of strings."""
        habits = load_habits()
        assert isinstance(habits, list)
        assert len(habits) == 3
        assert "Exercise" in habits

    def test_non_list_file_returns_empty(self, patch_io_paths):
        """EG – file contains a dict instead of a list → returns []."""
        with open(patch_io_paths["habits_file"], "w") as f:
            json.dump({"habit": "Exercise"}, f)
        assert load_habits() == []

    def test_mixed_types_coerced_to_str(self, patch_io_paths):
        """EG – non-string items in list are coerced via str()."""
        with open(patch_io_paths["habits_file"], "w") as f:
            json.dump([123, True, "Read"], f)
        habits = load_habits()
        assert all(isinstance(h, str) for h in habits)
        assert "123" in habits


class TestSaveHabits:
    """BB tests for save_habits()."""

    def test_save_valid_list(self, patch_io_paths):
        """EP – saving a valid list succeeds and data round-trips."""
        assert save_habits(["A", "B"]) is True
        with open(patch_io_paths["habits_file"]) as f:
            assert json.load(f) == ["A", "B"]

    def test_non_list_rejected(self, patch_io_paths):
        """EP – passing a dict instead of list returns False."""
        assert save_habits({"a": 1}) is False

    def test_empty_list(self, patch_io_paths):
        """BA – empty list is a valid save (user cleared habits)."""
        assert save_habits([]) is True
        with open(patch_io_paths["habits_file"]) as f:
            assert json.load(f) == []


# load_daily_logs

class TestLoadDailyLogs:
    """BB tests for load_daily_logs()."""

    def test_no_file_returns_empty(self, patch_io_paths):
        """EP – logs file does not exist → []."""
        assert load_daily_logs() == []

    def test_valid_logs_loaded(self, seeded_data_dir):
        """EP – valid logs file → list of [str, str, bool] entries."""
        logs = load_daily_logs()
        assert len(logs) == 6
        assert all(isinstance(l, list) and len(l) == 3 for l in logs)

    def test_malformed_entries_skipped(self, patch_io_paths):
        """EG – entries with wrong length are dropped during load."""
        data = [
            ["Exercise", "2024-01-01", True],
            ["Bad"],
            ["Exercise", "2024-01-02"],
        ]
        with open(patch_io_paths["logs_file"], "w") as f:
            json.dump(data, f)
        logs = load_daily_logs()
        assert len(logs) == 1
        assert logs[0][0] == "Exercise"

    def test_non_list_file_returns_empty(self, patch_io_paths):
        """EG – file contains a string instead of list → []."""
        with open(patch_io_paths["logs_file"], "w") as f:
            json.dump("not_a_list", f)
        assert load_daily_logs() == []


# save_daily_logs

class TestSaveDailyLogs:
    """BB tests for save_daily_logs(logs, streaks)."""

    def test_save_valid(self, patch_io_paths):
        """EP – valid logs + streaks → both files written, returns True."""
        logs = [["Exercise", "2024-01-01", True]]
        streaks = {"Exercise": 1}
        assert save_daily_logs(logs, streaks) is True
        with open(patch_io_paths["logs_file"]) as f:
            assert json.load(f) == logs
        with open(patch_io_paths["streaks_file"]) as f:
            assert json.load(f) == streaks

    def test_invalid_logs_type(self, patch_io_paths):
        """EP – non-list logs → returns False."""
        assert save_daily_logs("not_a_list", {}) is False

    def test_invalid_streaks_type(self, patch_io_paths):
        """EP – non-dict streaks → returns False."""
        assert save_daily_logs([], "not_a_dict") is False


# save_with_backup / try_load_json

class TestSaveWithBackup:
    """BB tests for save_with_backup(file_path, data)."""

    def test_creates_new_file(self, tmp_path):
        """EP – writing to a non-existent path creates the file."""
        fp = str(tmp_path / "new.json")
        assert save_with_backup(fp, {"key": "val"}) is True
        with open(fp) as f:
            assert json.load(f) == {"key": "val"}

    def test_overwrites_existing(self, tmp_path):
        """EP – writing over an existing file replaces contents."""
        fp = str(tmp_path / "data.json")
        save_with_backup(fp, {"v": 1})
        save_with_backup(fp, {"v": 2})
        with open(fp) as f:
            assert json.load(f)["v"] == 2

    def test_backup_cleaned_after_success(self, tmp_path):
        """BA – .bak file is removed after a successful save."""
        fp = str(tmp_path / "data.json")
        save_with_backup(fp, {"v": 1})
        save_with_backup(fp, {"v": 2})
        assert not os.path.exists(fp + ".bak")


class TestTryLoadJson:
    """BB tests for try_load_json(file_path, backup_path)."""

    def test_loads_valid_file(self, tmp_path):
        """EP – valid JSON file → returns parsed data."""
        fp = str(tmp_path / "data.json")
        with open(fp, "w") as f:
            json.dump([1, 2, 3], f)
        assert try_load_json(fp) == [1, 2, 3]

    def test_missing_file_returns_none(self, tmp_path):
        """EP – non-existent file without backup → None."""
        fp = str(tmp_path / "missing.json")
        assert try_load_json(fp) is None

    def test_corrupted_falls_back_to_backup(self, tmp_path):
        """EG – corrupted primary, valid backup → returns backup data."""
        fp = str(tmp_path / "data.json")
        bak = str(tmp_path / "data.json.bak")
        with open(fp, "w") as f:
            f.write("{{corrupt")
        with open(bak, "w") as f:
            json.dump({"restored": True}, f)
        result = try_load_json(fp, bak)
        assert result == {"restored": True}

    def test_corrupted_no_backup_returns_none(self, tmp_path):
        """EG – corrupted primary, no backup → None."""
        fp = str(tmp_path / "data.json")
        with open(fp, "w") as f:
            f.write("{{corrupt")
        assert try_load_json(fp) is None


# reset_app_data / clear_tracking_data

class TestResetAppData:
    """BB tests for reset_app_data()."""

    def test_resets_all_files(self, seeded_data_dir):
        """EP – after reset, habits/logs/streaks return to empty defaults."""
        assert reset_app_data() is True
        with open(seeded_data_dir["habits_file"]) as f:
            assert json.load(f) == []
        with open(seeded_data_dir["logs_file"]) as f:
            assert json.load(f) == []
        with open(seeded_data_dir["streaks_file"]) as f:
            assert json.load(f) == {}

    def test_plots_dir_recreated(self, seeded_data_dir):
        """BA – plots directory is wiped but re-created."""
        plots = seeded_data_dir["plots_dir"]
        open(os.path.join(plots, "dummy.png"), "w").close()
        reset_app_data()
        assert os.path.isdir(plots)
        assert len(os.listdir(plots)) == 0


class TestClearTrackingData:
    """BB tests for clear_tracking_data()."""

    def test_clears_logs_and_streaks_keeps_habits(self, seeded_data_dir):
        """EP – logs/streaks wiped but habits file untouched."""
        assert clear_tracking_data() is True
        with open(seeded_data_dir["habits_file"]) as f:
            habits = json.load(f)
        assert len(habits) == 3  # habits preserved
        with open(seeded_data_dir["logs_file"]) as f:
            assert json.load(f) == []
        with open(seeded_data_dir["streaks_file"]) as f:
            assert json.load(f) == {}

    def test_succeeds_when_no_files_exist(self, patch_io_paths):
        """BA – clearing when data files don't exist should still succeed."""
        assert clear_tracking_data() is True


# initialize_data_files

class TestInitializeDataFiles:
    """BB tests for initialize_data_files()."""

    def test_creates_all_files(self, patch_io_paths):
        """EP – on fresh directory, all JSON files are created."""
        assert initialize_data_files() is True
        for key in ("habits_file", "logs_file", "streaks_file"):
            assert os.path.exists(patch_io_paths[key])

    def test_does_not_overwrite_existing(self, seeded_data_dir):
        """BA – existing files are NOT overwritten by re-initialization."""
        initialize_data_files()
        with open(seeded_data_dir["habits_file"]) as f:
            habits = json.load(f)
        assert len(habits) == 3  # seeded data preserved


# load_habit_streaks

class TestLoadHabitStreaks:
    """BB tests for load_habit_streaks()."""

    def test_no_file_returns_empty_dict(self, patch_io_paths):
        """EP – streaks file missing → {}."""
        assert load_habit_streaks() == {}

    def test_loads_valid_streaks(self, seeded_data_dir):
        """EP – valid streaks file → dict with str keys and int values."""
        streaks = load_habit_streaks()
        assert isinstance(streaks, dict)
        assert all(isinstance(k, str) for k in streaks)
        assert all(isinstance(v, int) for v in streaks.values())

    def test_non_dict_returns_empty(self, patch_io_paths):
        """EG – file contains a list → {}."""
        with open(patch_io_paths["streaks_file"], "w") as f:
            json.dump([1, 2], f)
        assert load_habit_streaks() == {}

    def test_coerces_keys_and_values(self, patch_io_paths):
        """EG – numeric keys and string values are coerced to str/int."""
        with open(patch_io_paths["streaks_file"], "w") as f:
            json.dump({"Exercise": "5", "Read": 3}, f)
        streaks = load_habit_streaks()
        assert streaks["Exercise"] == 5
        assert isinstance(streaks["Exercise"], int)
