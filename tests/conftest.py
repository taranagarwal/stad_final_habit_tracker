"""
Shared pytest fixtures for the Habit Tracker test suite.

Provides isolated temporary data directories and sample data so that tests
never touch the real user data files.
"""

import json
import os
import shutil
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create an isolated data directory with all required sub-dirs."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    plots_dir = data_dir / "plots"
    plots_dir.mkdir()
    return data_dir


@pytest.fixture
def patch_io_paths(tmp_data_dir, monkeypatch):
    """
    Redirect every module-level path constant in habit_io to the temp directory.
    This ensures load/save functions operate on isolated files.
    """
    import habit_engine.habit_io as io_mod

    data_dir = str(tmp_data_dir)
    plots_dir = str(tmp_data_dir / "plots")

    monkeypatch.setattr(io_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(io_mod, "PLOTS_DIR", plots_dir)
    monkeypatch.setattr(io_mod, "HABITS_FILE", os.path.join(data_dir, "habits.json"))
    monkeypatch.setattr(io_mod, "LOGS_FILE", os.path.join(data_dir, "logs.json"))
    monkeypatch.setattr(io_mod, "STREAKS_FILE", os.path.join(data_dir, "streaks.json"))
    monkeypatch.setattr(io_mod, "SETTINGS_PATH", os.path.join(data_dir, "settings.json"))
    monkeypatch.setattr(io_mod, "CORE_FILES", [])

    return {
        "data_dir": data_dir,
        "plots_dir": plots_dir,
        "habits_file": os.path.join(data_dir, "habits.json"),
        "logs_file": os.path.join(data_dir, "logs.json"),
        "streaks_file": os.path.join(data_dir, "streaks.json"),
        "settings_file": os.path.join(data_dir, "settings.json"),
    }


@pytest.fixture
def sample_habits():
    """A standard set of 3 habits used across many tests."""
    return ["Exercise", "Read", "Meditate"]


@pytest.fixture
def sample_logs():
    """
    Two consecutive days of complete logs for 3 habits.
    Dates are always relative to *today* so streak logic stays deterministic.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return [
        ["Exercise", yesterday, True],
        ["Read", yesterday, True],
        ["Meditate", yesterday, False],
        ["Exercise", today, True],
        ["Read", today, True],
        ["Meditate", today, True],
    ]


@pytest.fixture
def sample_streaks():
    """Initial zeroed-out streaks dict matching sample_habits."""
    return {"Exercise": 0, "Read": 0, "Meditate": 0}


@pytest.fixture
def seeded_data_dir(patch_io_paths, sample_habits, sample_logs, sample_streaks):
    """
    Write sample habits, logs, and streaks into the patched temp directory
    so that load_* functions find realistic data.
    """
    paths = patch_io_paths
    with open(paths["habits_file"], "w") as f:
        json.dump(sample_habits, f)
    with open(paths["logs_file"], "w") as f:
        json.dump(sample_logs, f)
    with open(paths["streaks_file"], "w") as f:
        json.dump(sample_streaks, f)
    return paths
