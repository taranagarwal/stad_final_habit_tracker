"""
White-Box Tests for habit_io.py

Goal: cover every conditional branch in the I/O module — file existence
checks, JSON decode errors, backup recovery paths, permission toggling,
and data-validation guards.

All tests use patched paths (via conftest.py fixtures) to stay isolated.
"""

import json
import os
import stat
import pytest
from unittest.mock import patch, MagicMock

from habit_engine.habit_io import (
    load_settings,
    save_settings,
    _write_defaults,
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
    make_files_readonly,
    make_files_writable,
    get_asset_path,
    DEFAULT_SETTINGS,
)


# _write_defaults

class TestWriteDefaults:
    """WB: covers the helper that writes DEFAULT_SETTINGS to disk."""

    def test_writes_default_settings(self, patch_io_paths):
        """Branch: file is created with DEFAULT_SETTINGS content."""
        _write_defaults()
        with open(patch_io_paths["settings_file"]) as f:
            assert json.load(f) == DEFAULT_SETTINGS


# load_settings — branches

class TestLoadSettingsWB:
    """WB: target every branch in load_settings."""

    def test_file_missing_branch(self, patch_io_paths):
        """Branch: not os.path.exists → _write_defaults, return copy (line 75-77)."""
        s = load_settings()
        assert s == DEFAULT_SETTINGS
        assert os.path.exists(patch_io_paths["settings_file"])

    def test_valid_json_with_missing_keys_branch(self, patch_io_paths):
        """Branch: file exists, json.load succeeds, setdefault fills gaps (line 82-84)."""
        with open(patch_io_paths["settings_file"], "w") as f:
            json.dump({"appearance_mode": "Dark"}, f)
        s = load_settings()
        assert s["appearance_mode"] == "Dark"
        assert s["autosave_interval"] == 30  # default filled

    def test_json_decode_error_branch(self, patch_io_paths):
        """Branch: JSONDecodeError → _write_defaults, return defaults (line 85-88)."""
        with open(patch_io_paths["settings_file"], "w") as f:
            f.write("not json at all {{{{")
        s = load_settings()
        assert s == DEFAULT_SETTINGS

    def test_io_error_branch(self, patch_io_paths):
        """Branch: IOError → _write_defaults, return defaults (line 85-88)."""
        with open(patch_io_paths["settings_file"], "w") as f:
            json.dump(DEFAULT_SETTINGS, f)
        with patch("builtins.open", side_effect=IOError("disk error")):
            with patch("habit_engine.habit_io._write_defaults"):
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        s = load_settings()
        assert s == DEFAULT_SETTINGS


# save_with_backup — branch-by-branch

class TestSaveWithBackupWB:
    """WB: cover all branches in save_with_backup."""

    def test_new_file_no_original(self, tmp_path):
        """Branch: os.path.exists(file_path) is False → skip backup creation (line 193)."""
        fp = str(tmp_path / "new.json")
        assert save_with_backup(fp, [1]) is True

    def test_original_exists_first_replace_succeeds(self, tmp_path):
        """Branch: original exists → os.replace succeeds first try (line 195)."""
        fp = str(tmp_path / "data.json")
        with open(fp, "w") as f:
            json.dump([0], f)
        assert save_with_backup(fp, [1]) is True
        with open(fp) as f:
            assert json.load(f) == [1]

    def test_replace_to_backup_fails_then_remove_replace(self, tmp_path):
        """Branch: first os.replace(file, backup) raises → remove+replace fallback (line 196-198)."""
        fp = str(tmp_path / "data.json")
        bak = fp + ".bak"
        with open(fp, "w") as f:
            json.dump([0], f)
        with open(bak, "w") as f:
            json.dump([-1], f)

        original_replace = os.replace
        call_count = {"n": 0}

        def patched_replace(src, dst):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("first replace fails")
            return original_replace(src, dst)

        with patch("os.replace", side_effect=patched_replace):
            result = save_with_backup(fp, [1])
        assert result is True

    def test_temp_to_final_fallback(self, tmp_path):
        """Branch: os.replace(temp, file) fails first try → remove+replace fallback (line 203-205).
        After the original file is moved to backup, file_path no longer exists, so we also
        mock os.remove to succeed (simulating the case where the file is present)."""
        fp = str(tmp_path / "data.json")

        original_replace = os.replace
        original_remove = os.remove
        state = {"first_tmp_attempt": True}

        def mock_replace(src, dst):
            if src.endswith(".tmp") and not dst.endswith(".bak") and state["first_tmp_attempt"]:
                state["first_tmp_attempt"] = False
                raise OSError("simulated first replace failure")
            return original_replace(src, dst)

        def mock_remove(path):
            if path == fp and not os.path.exists(path):
                return  # no-op: file was already moved to backup
            return original_remove(path)

        with open(fp, "w") as f:
            json.dump([0], f)

        with patch("os.replace", side_effect=mock_replace):
            with patch("os.remove", side_effect=mock_remove):
                result = save_with_backup(fp, [1])
        assert result is True

    def test_exception_restores_backup(self, tmp_path):
        """Branch: Exception caught → restore from backup if available (line 214-219)."""
        fp = str(tmp_path / "data.json")
        bak = fp + ".bak"
        with open(bak, "w") as f:
            json.dump({"backup": True}, f)

        with patch("builtins.open", side_effect=IOError("write fail")):
            result = save_with_backup(fp, [1])
        assert result is False

    def test_finally_cleans_temp(self, tmp_path):
        """Branch: finally block removes .tmp if it exists (line 222-227)."""
        fp = str(tmp_path / "data.json")
        tmp_fp = fp + ".tmp"
        with open(tmp_fp, "w") as f:
            f.write("leftover")

        save_with_backup(fp, [1])
        assert not os.path.exists(tmp_fp)


# try_load_json — branches

class TestTryLoadJsonWB:
    """WB: every branch in try_load_json."""

    def test_file_exists_valid(self, tmp_path):
        """Branch: file exists, json.load succeeds → return data (line 232-234)."""
        fp = str(tmp_path / "ok.json")
        with open(fp, "w") as f:
            json.dump({"a": 1}, f)
        assert try_load_json(fp) == {"a": 1}

    def test_file_missing_no_backup(self, tmp_path):
        """Branch: file missing, no backup → return None (line 245)."""
        assert try_load_json(str(tmp_path / "missing.json")) is None

    def test_file_corrupt_backup_recovers(self, tmp_path):
        """Branch: primary corrupt, backup exists → load backup (line 236-243)."""
        fp = str(tmp_path / "data.json")
        bak = str(tmp_path / "data.json.bak")
        with open(fp, "w") as f:
            f.write("{{bad")
        with open(bak, "w") as f:
            json.dump([99], f)
        assert try_load_json(fp, bak) == [99]

    def test_file_corrupt_backup_also_corrupt(self, tmp_path):
        """Branch: both primary and backup corrupt → return None (line 243-244)."""
        fp = str(tmp_path / "data.json")
        bak = str(tmp_path / "data.json.bak")
        with open(fp, "w") as f:
            f.write("{{bad")
        with open(bak, "w") as f:
            f.write("{{also bad")
        assert try_load_json(fp, bak) is None

    def test_file_corrupt_no_backup_path(self, tmp_path):
        """Branch: primary corrupt, backup_path is None → return None (line 236)."""
        fp = str(tmp_path / "data.json")
        with open(fp, "w") as f:
            f.write("{{bad")
        assert try_load_json(fp) is None


# load_habits — branches

class TestLoadHabitsWB:
    """WB: branches in load_habits."""

    def test_valid_list_coercion(self, seeded_data_dir):
        """Branch: isinstance(habits, list) → list comp with str() (line 251)."""
        habits = load_habits()
        assert all(isinstance(h, str) for h in habits)

    def test_non_list_returns_empty(self, patch_io_paths):
        """Branch: not isinstance(habits, list) → [] (line 251)."""
        with open(patch_io_paths["habits_file"], "w") as f:
            json.dump(42, f)
        assert load_habits() == []

    def test_try_load_returns_none(self, patch_io_paths):
        """Branch: try_load_json returns None → [] (line 251)."""
        assert load_habits() == []

    def test_exception_returns_empty(self, patch_io_paths):
        """Branch: except Exception → [] (line 252-254)."""
        with open(patch_io_paths["habits_file"], "w") as f:
            json.dump(["ok"], f)
        with patch("habit_engine.habit_io.try_load_json", side_effect=RuntimeError):
            assert load_habits() == []


# save_habits — branches

class TestSaveHabitsWB:
    """WB: branches in save_habits."""

    def test_valid_list(self, patch_io_paths):
        """Branch: isinstance check passes → call save_with_backup (line 264)."""
        assert save_habits(["A"]) is True

    def test_not_a_list(self, patch_io_paths):
        """Branch: not isinstance → return False (line 260-262)."""
        assert save_habits(42) is False

    def test_exception(self, patch_io_paths):
        """Branch: except Exception → return False (line 265-267)."""
        with patch("habit_engine.habit_io.save_with_backup", side_effect=RuntimeError):
            assert save_habits(["A"]) is False


# load_habit_streaks — branches

class TestLoadHabitStreaksWB:
    """WB: branches in load_habit_streaks."""

    def test_valid_dict_coercion(self, patch_io_paths):
        """Branch: isinstance(streaks, dict) → dict comp str(k):int(v) (line 273)."""
        with open(patch_io_paths["streaks_file"], "w") as f:
            json.dump({"Ex": "3"}, f)
        streaks = load_habit_streaks()
        assert streaks == {"Ex": 3}

    def test_non_dict_returns_empty(self, patch_io_paths):
        """Branch: not isinstance(streaks, dict) → {} (line 273)."""
        with open(patch_io_paths["streaks_file"], "w") as f:
            json.dump([1, 2], f)
        assert load_habit_streaks() == {}

    def test_exception_returns_empty(self, patch_io_paths):
        """Branch: except Exception → {} (line 274-276)."""
        with patch("habit_engine.habit_io.try_load_json", side_effect=RuntimeError):
            assert load_habit_streaks() == {}


# load_daily_logs — branches

class TestLoadDailyLogsWB:
    """WB: branches in load_daily_logs."""

    def test_valid_logs_filtered(self, patch_io_paths):
        """Branch: isinstance(logs, list) → filter valid 3-element lists (line 282-287)."""
        data = [["Ex", "2024-01-01", True], ["bad"], 42]
        with open(patch_io_paths["logs_file"], "w") as f:
            json.dump(data, f)
        logs = load_daily_logs()
        assert len(logs) == 1

    def test_non_list_returns_empty(self, patch_io_paths):
        """Branch: not isinstance(logs, list) → fall through to return [] (line 291)."""
        with open(patch_io_paths["logs_file"], "w") as f:
            json.dump("string", f)
        assert load_daily_logs() == []

    def test_exception_returns_empty(self, patch_io_paths):
        """Branch: except Exception → return [] (line 289-291)."""
        with patch("habit_engine.habit_io.try_load_json", side_effect=RuntimeError):
            assert load_daily_logs() == []


# save_daily_logs — branches

class TestSaveDailyLogsWB:
    """WB: branches in save_daily_logs."""

    def test_valid_types(self, patch_io_paths):
        """Branch: both type checks pass → save both files (line 301-305)."""
        assert save_daily_logs([], {}) is True

    def test_logs_not_list(self, patch_io_paths):
        """Branch: not isinstance(logs, list) → return False (line 297-299)."""
        assert save_daily_logs("bad", {}) is False

    def test_streaks_not_dict(self, patch_io_paths):
        """Branch: not isinstance(streaks, dict) → return False (line 297-299)."""
        assert save_daily_logs([], "bad") is False

    def test_exception(self, patch_io_paths):
        """Branch: except Exception → return False (line 306-308)."""
        with patch("habit_engine.habit_io.save_with_backup", side_effect=RuntimeError):
            assert save_daily_logs([], {}) is False


# initialize_data_files — branches

class TestInitializeDataFilesWB:
    """WB: branches in initialize_data_files."""

    def test_creates_missing_files(self, patch_io_paths):
        """Branch: not os.path.exists for each file → create (line 159-171)."""
        assert initialize_data_files() is True
        for key in ("habits_file", "logs_file", "streaks_file"):
            assert os.path.exists(patch_io_paths[key])

    def test_skips_existing_files(self, seeded_data_dir):
        """Branch: os.path.exists is True → skip creation (lines 159,164,169)."""
        initialize_data_files()
        with open(seeded_data_dir["habits_file"]) as f:
            assert len(json.load(f)) == 3

    def test_exception_returns_false(self, patch_io_paths):
        """Branch: except Exception → return False (line 177-179)."""
        with patch("os.makedirs", side_effect=OSError("perm denied")):
            assert initialize_data_files() is False


# reset_app_data — branches

class TestResetAppDataWB:
    """WB: branches in reset_app_data."""

    def test_resets_existing_files(self, seeded_data_dir):
        """Branch: each os.path.exists → overwrite (line 314-324)."""
        assert reset_app_data() is True

    def test_plots_dir_exists_branch(self, seeded_data_dir):
        """Branch: PLOTS_DIR exists → rmtree + makedirs (line 327-329)."""
        plots = seeded_data_dir["plots_dir"]
        open(os.path.join(plots, "test.png"), "w").close()
        reset_app_data()
        assert os.listdir(plots) == []

    def test_files_do_not_exist(self, patch_io_paths):
        """Branch: os.path.exists is False → skip each file reset."""
        assert reset_app_data() is True

    def test_exception_returns_false(self, seeded_data_dir):
        """Branch: except Exception → return False (line 335-337)."""
        with patch("os.path.exists", side_effect=OSError):
            assert reset_app_data() is False


# clear_tracking_data — branches

class TestClearTrackingDataWB:
    """WB: branches in clear_tracking_data."""

    def test_clears_existing(self, seeded_data_dir):
        """Branch: files exist → overwrite logs/streaks, rmtree plots (line 342-355)."""
        assert clear_tracking_data() is True

    def test_no_files_exist(self, patch_io_paths):
        """Branch: os.path.exists is False for each → skip."""
        assert clear_tracking_data() is True

    def test_exception_returns_false(self, seeded_data_dir):
        """Branch: except Exception → return False (line 358-360)."""
        with patch("os.path.exists", side_effect=OSError):
            assert clear_tracking_data() is False


# make_files_readonly / make_files_writable

class TestMakeFilesReadonlyWB:
    """WB: branches in make_files_readonly."""

    def test_protects_existing_files(self, tmp_path, monkeypatch):
        """Branch: file exists → chmod to readonly (line 113-120)."""
        import habit_engine.habit_io as io_mod
        test_file = str(tmp_path / "test.py")
        with open(test_file, "w") as f:
            f.write("pass")
        monkeypatch.setattr(io_mod, "CORE_FILES", [test_file])
        assert make_files_readonly() is True
        mode = os.stat(test_file).st_mode
        assert not (mode & stat.S_IWUSR)

    def test_skips_missing_files(self, monkeypatch):
        """Branch: not os.path.exists → skip (line 113)."""
        import habit_engine.habit_io as io_mod
        monkeypatch.setattr(io_mod, "CORE_FILES", ["/nonexistent/file.py"])
        assert make_files_readonly() is True

    def test_chmod_error(self, tmp_path, monkeypatch):
        """Branch: Exception during chmod → success=False (line 121-123)."""
        import habit_engine.habit_io as io_mod
        test_file = str(tmp_path / "test.py")
        with open(test_file, "w") as f:
            f.write("pass")
        monkeypatch.setattr(io_mod, "CORE_FILES", [test_file])
        with patch("os.chmod", side_effect=OSError("perm")):
            assert make_files_readonly() is False


class TestMakeFilesWritableWB:
    """WB: branches in make_files_writable."""

    def test_unlocks_existing_files(self, tmp_path, monkeypatch):
        """Branch: file exists → chmod writable (line 135-142)."""
        import habit_engine.habit_io as io_mod
        test_file = str(tmp_path / "test.py")
        with open(test_file, "w") as f:
            f.write("pass")
        os.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP)
        monkeypatch.setattr(io_mod, "CORE_FILES", [test_file])
        assert make_files_writable() is True
        mode = os.stat(test_file).st_mode
        assert mode & stat.S_IWUSR

    def test_chmod_error(self, tmp_path, monkeypatch):
        """Branch: Exception during chmod → success=False (line 143-145)."""
        import habit_engine.habit_io as io_mod
        test_file = str(tmp_path / "test.py")
        with open(test_file, "w") as f:
            f.write("pass")
        monkeypatch.setattr(io_mod, "CORE_FILES", [test_file])
        with patch("os.chmod", side_effect=OSError("perm")):
            assert make_files_writable() is False


# get_asset_path

class TestGetAssetPathWB:
    """WB: branches for frozen vs development mode."""

    def test_development_mode(self):
        """Branch: not frozen → use ASSETS_DIR (line 103-105)."""
        path = get_asset_path("icon.png")
        assert "icon.png" in path

    def test_frozen_mode(self, monkeypatch):
        """Branch: sys.frozen is True → use sys._MEIPASS (line 100-102)."""
        import sys as real_sys
        monkeypatch.setattr(real_sys, "frozen", True, raising=False)
        monkeypatch.setattr(real_sys, "_MEIPASS", "/fake/meipass", raising=False)
        path = get_asset_path("icon.png")
        assert "/fake/meipass" in path
