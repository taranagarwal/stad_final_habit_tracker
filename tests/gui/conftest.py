"""
GUI test fixtures for the Habit Tracker test suite.

Approach: raw tkinter / customtkinter introspection
────────────────────────────────────────────────────
We instantiate the real HabitTrackerGUI class with dependency-injected stub
callbacks and isolated data paths.  The Tk event loop is *not* started
(no ``mainloop``); instead, individual tests call ``root.update_idletasks()``
or ``root.update()`` to pump events when needed.

This avoids the need for pyautogui (fragile, display-dependent) or pytest-tk
(unmaintained) while still exercising the full widget tree.

On headless CI the tests require Xvfb (or ``xvfb-run``); on macOS / Windows
they run natively.
"""

import json
import os
import tkinter as tk
import pytest
from unittest.mock import MagicMock

import habit_engine.habit_io as io_mod
import habit_engine.gui as gui_mod


# Data isolation

@pytest.fixture
def gui_data_dir(tmp_path):
    """Create a temp data directory with required subdirectories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "plots").mkdir()
    return data_dir


@pytest.fixture
def gui_patch_paths(gui_data_dir, monkeypatch):
    """
    Redirect all habit_io path constants AND the gui module's own
    cached references so no test ever touches real user data.
    """
    data_dir = str(gui_data_dir)
    plots_dir = str(gui_data_dir / "plots")

    monkeypatch.setattr(io_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(io_mod, "PLOTS_DIR", plots_dir)
    monkeypatch.setattr(io_mod, "HABITS_FILE", os.path.join(data_dir, "habits.json"))
    monkeypatch.setattr(io_mod, "LOGS_FILE", os.path.join(data_dir, "logs.json"))
    monkeypatch.setattr(io_mod, "STREAKS_FILE", os.path.join(data_dir, "streaks.json"))
    monkeypatch.setattr(io_mod, "SETTINGS_PATH", os.path.join(data_dir, "settings.json"))
    monkeypatch.setattr(io_mod, "CORE_FILES", [])

    monkeypatch.setattr(gui_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(gui_mod, "PLOTS_DIR", plots_dir)

    io_mod.initialize_data_files()

    return {
        "data_dir": data_dir,
        "plots_dir": plots_dir,
        "habits_file": os.path.join(data_dir, "habits.json"),
        "logs_file": os.path.join(data_dir, "logs.json"),
        "streaks_file": os.path.join(data_dir, "streaks.json"),
        "settings_file": os.path.join(data_dir, "settings.json"),
    }


@pytest.fixture
def gui_seeded_paths(gui_patch_paths):
    """Write sample habits/logs/streaks so the GUI finds data on launch."""
    from datetime import datetime, timedelta

    habits = ["Exercise", "Read", "Meditate"]
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    logs = [
        ["Exercise", yesterday, True],
        ["Read", yesterday, True],
        ["Meditate", yesterday, False],
        ["Exercise", today, True],
        ["Read", today, True],
        ["Meditate", today, True],
    ]
    streaks = {"Exercise": 2, "Read": 2, "Meditate": 1}

    with open(gui_patch_paths["habits_file"], "w") as f:
        json.dump(habits, f)
    with open(gui_patch_paths["logs_file"], "w") as f:
        json.dump(logs, f)
    with open(gui_patch_paths["streaks_file"], "w") as f:
        json.dump(streaks, f)

    return gui_patch_paths


# Stub callbacks

@pytest.fixture
def stub_callbacks():
    """
    Return the seven dependency-injected callback functions expected by
    HabitTrackerGUI.__init__.  All return realistic default values so the
    GUI can initialise without errors.
    """
    return {
        "load_habits_fn": MagicMock(return_value=[]),
        "save_habits_fn": MagicMock(return_value=True),
        "load_logs_fn": MagicMock(return_value=[]),
        "save_logs_fn": MagicMock(return_value=True),
        "update_streaks_fn": MagicMock(return_value=None),
        "load_streaks_fn": MagicMock(return_value={}),
        "visualize_fn": MagicMock(return_value=None),
    }


@pytest.fixture
def io_callbacks():
    """
    Return the seven callbacks wired to the *real* habit_io / habit_logic
    functions (paths already redirected by gui_patch_paths).
    Use this when you want the GUI to load/save actual data in the temp dir.
    """
    from habit_engine.habit_io import (
        load_habits, save_habits,
        load_daily_logs, save_daily_logs,
        load_habit_streaks,
    )
    from habit_engine.habit_logic import update_streaks
    from habit_engine.habit_visualization import visualize_habit_streak

    return {
        "load_habits_fn": load_habits,
        "save_habits_fn": save_habits,
        "load_logs_fn": load_daily_logs,
        "save_logs_fn": save_daily_logs,
        "update_streaks_fn": update_streaks,
        "load_streaks_fn": load_habit_streaks,
        "visualize_fn": visualize_habit_streak,
    }


# ── Core GUI fixture ─────────────────────────────────────────────────

@pytest.fixture
def gui_app(gui_patch_paths, stub_callbacks, monkeypatch):
    """
    Instantiate HabitTrackerGUI with stub callbacks and isolated paths.

    The window is created but ``mainloop()`` is never called; tests can
    pump the event loop manually with ``app.window.update_idletasks()``.

    ``_load_data`` is replaced with a synchronous version so that no
    background thread tries to call ``window.after()`` (which fails
    without an active mainloop).

    Yields the app instance and destroys the root window on teardown.
    """
    monkeypatch.setattr(gui_mod, "_ctk_instance", None)
    monkeypatch.setattr(
        gui_mod.HabitTrackerGUI, "_load_data", _sync_load_data,
    )

    app = gui_mod.HabitTrackerGUI(**stub_callbacks)

    # Process any pending widget events (geometry, after-idle callbacks)
    app.window.update_idletasks()

    yield app

    # ── Teardown: cancel scheduled callbacks, then destroy the root ──
    _cancel_all_after_callbacks(app.window)
    try:
        app.window.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def gui_app_with_data(gui_seeded_paths, io_callbacks, monkeypatch):
    """
    Like ``gui_app`` but wired to the real I/O functions with pre-seeded
    data.  Use when tests need to inspect loaded habits, logs, or streaks
    inside the GUI.
    """
    monkeypatch.setattr(gui_mod, "_ctk_instance", None)
    monkeypatch.setattr(
        gui_mod.HabitTrackerGUI, "_load_data", _sync_load_data,
    )

    app = gui_mod.HabitTrackerGUI(**io_callbacks)
    app.window.update_idletasks()

    yield app

    _cancel_all_after_callbacks(app.window)
    try:
        app.window.destroy()
    except tk.TclError:
        pass


# ── Helpers ───────────────────────────────────────────────────────────

def _sync_load_data(self):
    """
    Synchronous replacement for HabitTrackerGUI._load_data.

    The production version spawns a background thread that calls
    ``window.after()`` to push UI updates back to the main thread.
    That pattern requires an active ``mainloop()``, which tests don't run.
    This version executes everything on the main thread directly.
    """
    try:
        self.habits = self._load_habits()
        self.logs = self._load_logs()
        self.streaks = self._load_streaks()

        if not self.habits:
            self.show_setup_view()
        else:
            self.show_habits_view()

        if self.habits:
            self.habits_button.configure(state="normal")
            self.logs_button.configure(state="normal")
            self.stats_button.configure(state="normal")
        else:
            self.habits_button.configure(state="disabled")
            self.logs_button.configure(state="disabled")
            self.stats_button.configure(state="disabled")

        self.update_clear_buttons_state()
    except Exception as e:
        print(f"[test] _sync_load_data error: {e}")


def _cancel_all_after_callbacks(root):
    """
    Cancel every pending ``after`` callback on *root* and all its
    descendants to prevent "invalid command name" errors during
    teardown.
    """
    try:
        # Tk stores pending after-events; eval('after info') lists their ids
        after_ids = root.tk.eval("after info").split()
        for aid in after_ids:
            try:
                root.after_cancel(aid)
            except (tk.TclError, ValueError):
                pass
    except tk.TclError:
        pass


def pump_events(app, rounds=5):
    """
    Utility: pump the Tk event loop for *rounds* iterations.

    Call this from tests that need side-effects of ``after`` callbacks
    (e.g. data loading in a background thread) to complete before
    assertions.
    """
    import time
    for _ in range(rounds):
        app.window.update()
        time.sleep(0.05)
