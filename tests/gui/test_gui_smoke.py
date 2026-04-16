"""
GUI Smoke Tests — verify the application launches and closes cleanly.

These tests exercise the real HabitTrackerGUI class through tkinter
introspection (no mainloop, no display automation).  They confirm:

  1. The window instantiates without exceptions
  2. Core window properties (title, geometry, widget tree) are correct
  3. The app tears down cleanly with no Tcl errors
  4. Both empty-state and seeded-data launches work

All tests use the ``gui_app`` / ``gui_app_with_data`` fixtures from
conftest.py, which provide full data isolation via temp directories.
"""

import tkinter as tk
import platform
import pytest

from tests.gui.conftest import pump_events


# Window launch & teardown

class TestWindowLifecycle:
    """Verify the GUI can start and stop without crashing."""

    def test_window_exists(self, gui_app):
        """The CTk root window is created and alive."""
        assert gui_app.window is not None
        assert gui_app.window.winfo_exists()

    def test_window_title(self, gui_app):
        """Main window title matches the expected app name."""
        assert gui_app.window.title() == "HERALDEXX HABIT TRACKER"

    def test_window_is_toplevel(self, gui_app):
        """The root window is a Tk toplevel (not a child frame)."""
        assert gui_app.window.winfo_toplevel() == gui_app.window

    def test_clean_destroy(self, gui_app):
        """Destroying the window does not raise."""
        gui_app.window.destroy()
        # After destroy, winfo_exists should return False or raise TclError
        with pytest.raises(tk.TclError):
            gui_app.window.winfo_exists()


# Window geometry / dimensions

class TestWindowGeometry:
    """Verify size constraints set by _setup_platform_specifics."""

    def test_minimum_size_is_set(self, gui_app):
        """The window has a minimum size configured (not 1x1)."""
        gui_app.window.update_idletasks()
        # CustomTkinter's CTk.minsize() has a setter-only override;
        # use the underlying Tk wm_minsize() to read current values.
        min_w, min_h = gui_app.window.wm_minsize()
        assert min_w >= 800, f"min width {min_w} is too small"
        assert min_h >= 550, f"min height {min_h} is too small"

    def test_initial_size_within_bounds(self, gui_app):
        """Initial requested geometry should not exceed the defined caps."""
        gui_app.window.update_idletasks()
        geom = gui_app.window.geometry()
        # geometry() returns "WxH+X+Y"
        size_part = geom.split("+")[0]
        w, h = (int(v) for v in size_part.split("x"))
        assert w <= 1200, f"width {w} exceeds 1200 cap"
        assert h <= 800, f"height {h} exceeds 800 cap"

    def test_geometry_has_positive_position(self, gui_app):
        """Window position offsets should be non-negative (on-screen)."""
        gui_app.window.update_idletasks()
        geom = gui_app.window.geometry()
        parts = geom.replace("x", "+").split("+")
        x, y = int(parts[1]), int(parts[2])
        assert x >= 0, f"x offset {x} is negative"
        assert y >= 0, f"y offset {y} is negative"


# Widget tree / sidebar

class TestSidebarWidgets:
    """Verify core sidebar widgets are created."""

    def test_sidebar_frame_exists(self, gui_app):
        """A sidebar frame is attached to the root window."""
        assert hasattr(gui_app, "sidebar")
        assert gui_app.sidebar.winfo_exists()

    def test_logo_label_text(self, gui_app):
        """The sidebar displays the 'HABIT TRACKER' logo text."""
        assert hasattr(gui_app, "logo_label")
        assert "HABIT TRACKER" in gui_app.logo_label.cget("text")

    def test_navigation_buttons_exist(self, gui_app):
        """All four navigation buttons are present in the sidebar."""
        for attr in ("habits_button", "logs_button", "stats_button", "settings_button"):
            assert hasattr(gui_app, attr), f"missing {attr}"
            btn = getattr(gui_app, attr)
            assert btn.winfo_exists(), f"{attr} widget does not exist"

    def test_nav_buttons_disabled_when_no_habits(self, gui_app):
        """
        With no habits loaded (stub returns []), data-dependent buttons
        should be disabled; settings should always be enabled.
        """
        gui_app.window.update_idletasks()
        assert gui_app.habits_button.cget("state") == "disabled"
        assert gui_app.logs_button.cget("state") == "disabled"
        assert gui_app.stats_button.cget("state") == "disabled"
        assert gui_app.settings_button.cget("state") == "normal"


class TestMainFrame:
    """Verify the main content frame is created."""

    def test_main_frame_exists(self, gui_app):
        """The main_frame widget is present and visible."""
        assert hasattr(gui_app, "main_frame")
        assert gui_app.main_frame.winfo_exists()

    def test_main_frame_is_child_of_root(self, gui_app):
        """main_frame's parent should be the root window."""
        parent = gui_app.main_frame.winfo_parent()
        root_name = str(gui_app.window)
        assert parent == root_name or parent.startswith(root_name)


# Seeded data launch

class TestLaunchWithData:
    """Verify the GUI initialises correctly when data already exists."""

    def test_window_launches_with_seeded_data(self, gui_app_with_data):
        """App starts without errors when habits/logs exist."""
        assert gui_app_with_data.window.winfo_exists()

    def test_title_unchanged_with_data(self, gui_app_with_data):
        """Title is the same regardless of whether data is present."""
        assert gui_app_with_data.window.title() == "HERALDEXX HABIT TRACKER"

    def test_data_loads_into_app(self, gui_app_with_data):
        """
        With synchronous data loading, the app object should hold the
        seeded habits immediately after construction.
        """
        assert len(gui_app_with_data.habits) == 3
        assert "Exercise" in gui_app_with_data.habits

    def test_nav_buttons_enabled_after_data_load(self, gui_app_with_data):
        """Once data is loaded, data-dependent nav buttons should be enabled."""
        assert gui_app_with_data.habits_button.cget("state") == "normal"
        assert gui_app_with_data.logs_button.cget("state") == "normal"
        assert gui_app_with_data.stats_button.cget("state") == "normal"


# ── Platform attribute checks ────────────────────────────────────────

class TestPlatformAttributes:
    """Verify platform-specific setup ran without errors."""

    def test_platform_attribute_set(self, gui_app):
        """The app stores the current platform string."""
        assert hasattr(gui_app, "platform")
        assert gui_app.platform in ("windows", "darwin", "linux")

    def test_is_windows_flag(self, gui_app):
        """The is_windows boolean matches the platform string."""
        expected = platform.system().lower() == "windows"
        assert gui_app.is_windows is expected


# Internal state initialisation

class TestInitialState:
    """Verify the GUI's internal bookkeeping is correctly initialised."""

    def test_no_pending_changes_on_start(self, gui_app):
        assert gui_app.pending_changes is False

    def test_empty_plot_windows_list(self, gui_app):
        assert gui_app.plot_windows == []

    def test_autosave_interval_from_defaults(self, gui_app):
        """Autosave interval should match the default settings value."""
        assert gui_app.autosave_interval == 30

    def test_settings_loaded(self, gui_app):
        """Settings dict should be populated (not None/empty)."""
        assert gui_app.settings is not None
        assert isinstance(gui_app.settings, dict)
        assert "chart_style" in gui_app.settings
