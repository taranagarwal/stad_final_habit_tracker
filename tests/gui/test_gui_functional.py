"""
GUI Functional Tests — comprehensive user-flow tests for the Habit Tracker.

These tests exercise the major interactive paths through the application:
setup wizard, main dashboard, theme switching, navigation, log view,
statistics view, notification/reminder, autosave, and edge cases.

All tests use the ``gui_app`` / ``gui_app_with_data`` fixtures from
conftest.py, which provide full data isolation via temp directories.
The Tk event loop is *not* started (no ``mainloop``); widget commands
are invoked programmatically.

**Acceptance Criteria (Issue #5):**
  - ≥15 GUI test cases covering all major views and interactions
  - Tests document which GUI components they exercise
  - All tests pass in headless mode
"""

import json
import os
import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch, call

from tests.gui.conftest import (
    pump_events,
    find_widget_by_text,
    find_all_widgets_of_type,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Setup Wizard Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSetupWizard:
    """
    Tests for the initial setup wizard (``_show_setup_view``).

    GUI components exercised:
      - ``num_habits_var`` (CTkOptionMenu for habit count 2-10)
      - ``habit_entries`` (list of CTkEntry widgets)
      - ``save_initial_habits()`` button command
    """

    def test_setup_view_shows_habit_count_selector(self, gui_app):
        """The setup view contains a habit count selector with values 2-10.

        Validates: valid habit count entry (2-10).
        """
        # gui_app starts with no habits → setup view is shown automatically
        gui_app.window.update_idletasks()

        assert hasattr(gui_app, "num_habits_var"), "num_habits_var not set up"
        # The default value should be "2"
        assert gui_app.num_habits_var.get() == "2"

    def test_setup_default_creates_two_entries(self, gui_app):
        """With default count of 2, exactly 2 habit entry widgets are created.

        Validates: habit count defaults produce the correct number of entries.
        """
        gui_app.window.update_idletasks()

        assert hasattr(gui_app, "habit_entries"), "habit_entries not initialised"
        assert len(gui_app.habit_entries) == 2, (
            f"Expected 2 entries, got {len(gui_app.habit_entries)}"
        )

    def test_setup_change_count_updates_entries(self, gui_app):
        """Changing the habit count to 5 produces exactly 5 entry fields.

        Validates: dynamic entry creation when habit count changes.
        """
        gui_app.window.update_idletasks()

        gui_app.num_habits_var.set("5")
        gui_app.update_habit_entries()
        gui_app.window.update_idletasks()

        assert len(gui_app.habit_entries) == 5, (
            f"Expected 5 entries after changing count, got {len(gui_app.habit_entries)}"
        )

    def test_save_initial_habits_validates_and_saves(self, gui_app):
        """Filling in valid habit names and saving calls _save_habits with the
        correct list and enables navigation buttons.

        Validates: habit name entry and submission.
        """
        gui_app.window.update_idletasks()

        # Fill in the two default entries
        gui_app.habit_entries[0].insert(0, "Running")
        gui_app.habit_entries[1].insert(0, "Cooking")

        # The stub _save_habits returns True
        gui_app.save_initial_habits()
        gui_app.window.update_idletasks()

        # Verify save was called with title-cased habit names
        gui_app._save_habits.assert_called_once_with(["Running", "Cooking"])

        # After a successful save, nav buttons should be enabled
        assert gui_app.habits_button.cget("state") == "normal"
        assert gui_app.logs_button.cget("state") == "normal"
        assert gui_app.stats_button.cget("state") == "normal"


# ═══════════════════════════════════════════════════════════════════════
# 2. Main Dashboard Tests
# ═══════════════════════════════════════════════════════════════════════

class TestMainDashboard:
    """
    Tests for the main habits check-in dashboard (``_show_habits_view``).

    GUI components exercised:
      - ``habit_vars`` dict (BooleanVar per habit)
      - ``streak_labels`` dict (CTkLabel per habit)
      - Checkbox command (``on_checkbox_click``)
      - ``_save_logs`` callback
    """

    def test_habits_displayed_with_checkboxes(self, gui_app_with_data):
        """Each seeded habit has a corresponding checkbox variable.

        Validates: all habits displayed correctly.
        """
        app = gui_app_with_data
        app.show_habits_view()
        app.window.update_idletasks()

        assert hasattr(app, "habit_vars"), "habit_vars not created"
        assert set(app.habit_vars.keys()) == {"Exercise", "Read", "Meditate"}

    def test_habit_checkbox_toggle(self, gui_app_with_data):
        """Toggling a habit's BooleanVar changes its value.

        Validates: habit completion toggle (check/uncheck).
        """
        app = gui_app_with_data
        app.show_habits_view()
        app.window.update_idletasks()

        var = app.habit_vars["Exercise"]
        original = var.get()
        var.set(not original)
        assert var.get() != original

    def test_streak_labels_present(self, gui_app_with_data):
        """Every habit has a streak label containing the fire emoji.

        Validates: streak counter display.
        """
        app = gui_app_with_data
        app.show_habits_view()
        app.window.update_idletasks()

        assert hasattr(app, "streak_labels"), "streak_labels not created"
        for habit in ("Exercise", "Read", "Meditate"):
            label = app.streak_labels[habit]
            assert "🔥" in label.cget("text"), (
                f"Streak label for '{habit}' missing fire emoji"
            )

    def test_checkbox_triggers_save(self, gui_app_with_data):
        """Invoking a checkbox's command calls _save_logs.

        Validates: auto-save on habit completion.
        """
        app = gui_app_with_data
        app.show_habits_view()
        app.window.update_idletasks()

        # Find a checkbox widget for "Exercise" by walking the widget tree
        checkboxes = find_all_widgets_of_type(
            app.main_frame, app.ctk.CTkCheckBox
        )
        assert len(checkboxes) > 0, "No checkboxes found in habits view"

        exercise_cb = None
        for cb in checkboxes:
            if "Exercise" in cb.cget("text"):
                exercise_cb = cb
                break

        # _save_logs should be called. Since gui_app_with_data uses real functions, we patch it
        with patch.object(app, '_save_logs', return_value=True) as mock_save:
            exercise_cb.toggle()
            command = getattr(exercise_cb, "_command", None)
            if command:
                command()
            app.window.update_idletasks()
            mock_save.assert_called()


# ═══════════════════════════════════════════════════════════════════════
# 3. Theme Switching Tests
# ═══════════════════════════════════════════════════════════════════════

class TestThemeSwitching:
    """
    Tests for appearance mode switching (``change_appearance_mode``).

    GUI components exercised:
      - ``current_appearance_mode`` attribute
      - ``settings["appearance_mode"]`` persistence
      - ``ctk.set_appearance_mode()``
    """

    def test_change_appearance_mode_updates_setting(self, gui_app):
        """Switching to Dark mode updates the settings dict.

        Validates: theme switching Dark → Light → System.
        """
        app = gui_app
        app.change_appearance_mode("Dark")
        app.window.update_idletasks()

        assert app.current_appearance_mode == "Dark"
        assert app.settings["appearance_mode"] == "Dark"

    def test_appearance_mode_cycles(self, gui_app):
        """Cycling through all three modes updates current_appearance_mode
        correctly each time.

        Validates: sequential theme changes do not cause errors.
        """
        app = gui_app

        for mode in ("Light", "Dark", "System"):
            app.change_appearance_mode(mode)
            app.window.update_idletasks()
            assert app.current_appearance_mode == mode, (
                f"Expected '{mode}', got '{app.current_appearance_mode}'"
            )


# ═══════════════════════════════════════════════════════════════════════
# 4. Navigation Tests
# ═══════════════════════════════════════════════════════════════════════

class TestNavigation:
    """
    Tests for sidebar navigation between views.

    GUI components exercised:
      - ``show_habits_view()`` → "Daily Habits Check-in" title
      - ``show_logs_view()`` → "Habit Logs" header
      - ``show_stats_view()`` → "Statistics & Visualization" title
    """

    def test_show_habits_view_renders(self, gui_app_with_data):
        """The habits view contains the 'Daily Habits Check-in' title.

        Validates: Dashboard view renders without errors.
        """
        app = gui_app_with_data
        app.show_habits_view()
        app.window.update_idletasks()

        widget = find_widget_by_text(app.main_frame, "Daily Habits Check-in")
        assert widget is not None, "Habits view title not found"

    def test_show_logs_view_renders(self, gui_app_with_data):
        """The logs view contains the 'Habit Logs' header.

        Validates: Logs view renders without errors.
        """
        app = gui_app_with_data
        app.show_logs_view()
        app.window.update_idletasks()

        widget = find_widget_by_text(app.main_frame, "Habit Logs")
        assert widget is not None, "Logs view header not found"

    def test_show_stats_view_renders(self, gui_app_with_data):
        """The stats view contains the 'Statistics & Visualization' title.

        Validates: Statistics view renders without errors.
        """
        app = gui_app_with_data
        app.show_stats_view()
        app.window.update_idletasks()

        widget = find_widget_by_text(app.main_frame, "Statistics & Visualization")
        assert widget is not None, "Stats view title not found"


# ═══════════════════════════════════════════════════════════════════════
# 5. Log View Tests
# ═══════════════════════════════════════════════════════════════════════

class TestLogView:
    """
    Tests for the habit logs view (``_show_logs_view``).

    GUI components exercised:
      - Date labels and ✓/✗ status labels
      - "No habit logs found" placeholder
      - "Clear Tracking History" button
    """

    def test_logs_display_dates_and_status(self, gui_app_with_data):
        """With seeded data, the logs view shows date labels and completion
        status markers (✓ or ✗).

        Validates: logs display correct dates and completion status.
        """
        app = gui_app_with_data
        app.show_logs_view()
        app.window.update_idletasks()

        # Look for status markers in the widget tree
        check_mark = find_widget_by_text(app.main_frame, "✓")
        cross_mark = find_widget_by_text(app.main_frame, "✗")

        # At least one of each should exist in the seeded data
        assert check_mark is not None, "No ✓ status marker found in logs view"
        assert cross_mark is not None, "No ✗ status marker found in logs view"

    def test_empty_logs_show_placeholder(self, gui_app):
        """With no logs, the view displays a 'No habit logs found' placeholder.

        Validates: empty state message for logs.
        """
        app = gui_app

        # Give the app some habits so nav buttons are enabled and we can
        # switch to logs view, but keep logs empty via stubs
        app.habits = ["TestHabit"]
        app.habits_button.configure(state="normal")
        app.logs_button.configure(state="normal")
        app.stats_button.configure(state="normal")

        app.show_logs_view()
        app.window.update_idletasks()

        placeholder = find_widget_by_text(app.main_frame, "No habit logs found")
        assert placeholder is not None, "Missing empty-state placeholder in logs view"


# ═══════════════════════════════════════════════════════════════════════
# 6. Statistics / Visualization View Tests
# ═══════════════════════════════════════════════════════════════════════

class TestStatsView:
    """
    Tests for the statistics/visualization view (``_show_stats_view``).

    GUI components exercised:
      - ``selected_habit`` StringVar and habit dropdown
      - ``visualize_btn`` button
      - Placeholder when no habits exist
    """

    def test_stats_view_has_dropdown_and_button(self, gui_app_with_data):
        """The stats view includes a habit dropdown and a Visualize button.

        Validates: chart controls render correctly.
        """
        app = gui_app_with_data
        app.show_stats_view()
        app.window.update_idletasks()

        assert hasattr(app, "selected_habit"), "selected_habit not set"
        assert hasattr(app, "visualize_btn"), "visualize_btn not set"
        assert app.visualize_btn.cget("state") == "normal", (
            "Visualize button should be enabled when habits exist"
        )

    def test_stats_view_no_habits_disabled(self, gui_app):
        """With no habits, the dropdown shows 'No habits yet' and the
        Visualize button is disabled.

        Validates: disabled state when no data is available.
        """
        app = gui_app

        # Need to get into stats view despite having no habits — call the
        # internal method directly to bypass nav-button state checks
        app.show_view(app._show_stats_view)
        app.window.update_idletasks()

        assert app.selected_habit.get() == "No habits yet"
        assert app.visualize_btn.cget("state") == "disabled"


# ═══════════════════════════════════════════════════════════════════════
# 7. Notification / Reminder Tests
# ═══════════════════════════════════════════════════════════════════════

class TestNotificationReminder:
    """
    Tests for the daily reminder popup (``_show_reminder_popup``).

    GUI components exercised:
      - ``MessageWindow`` popup
      - ``_current_reminder_popup`` attribute
    """

    def test_reminder_popup_creates_message_window(self, gui_app_with_data):
        """Calling _show_reminder_popup() creates a visible popup with the
        expected reminder message text.

        Validates: daily reminder triggers correctly.
        """
        app = gui_app_with_data
        app.daily_reminder_enabled = True

        app._show_reminder_popup()
        app.window.update_idletasks()

        assert hasattr(app, "_current_reminder_popup"), (
            "_current_reminder_popup not set after popup"
        )
        assert app._current_reminder_popup is not None, "Popup was not created"

        # The popup window should exist
        popup_window = app._current_reminder_popup.window
        assert popup_window.winfo_exists(), "Popup window does not exist"

        # Verify it contains the expected message
        reminder_text = find_widget_by_text(popup_window, "Time to track your habits")
        assert reminder_text is not None, (
            "Reminder popup missing expected message text"
        )

        # Cleanup: destroy the popup
        try:
            app._current_reminder_popup.destroy()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
# 8. Autosave Tests
# ═══════════════════════════════════════════════════════════════════════

class TestAutosave:
    """
    Tests for autosave interval configuration (``change_autosave_interval``).

    GUI components exercised:
      - ``autosave_interval`` attribute
      - ``settings["autosave_interval"]`` persistence
    """

    def test_autosave_interval_persists(self, gui_app):
        """Changing the autosave interval via the settings method updates both
        the instance attribute and the settings dict.

        Validates: data persistence after configuration change.
        """
        app = gui_app

        app.change_autosave_interval("1 minute")
        app.window.update_idletasks()

        assert app.autosave_interval == 60, (
            f"Expected autosave_interval=60, got {app.autosave_interval}"
        )
        assert app.settings["autosave_interval"] == 60


# ═══════════════════════════════════════════════════════════════════════
# 9. Edge Cases
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """
    Tests for edge-case scenarios that could cause crashes or data corruption.

    GUI components exercised:
      - Setup wizard validation (duplicate names)
      - View-switching stability
      - Error handling for corrupt data
    """

    def test_duplicate_habit_names_rejected(self, gui_app):
        """Submitting duplicate habit names shows an error and does NOT call
        _save_habits.

        Validates: double-submission / duplicate name guard.
        """
        app = gui_app
        app.window.update_idletasks()

        # Fill both entries with the same name
        app.habit_entries[0].insert(0, "Running")
        app.habit_entries[1].insert(0, "Running")

        app.save_initial_habits()
        app.window.update_idletasks()

        # _save_habits should NOT have been called
        app._save_habits.assert_not_called()

    def test_rapid_view_switching(self, gui_app_with_data):
        """Rapidly switching between all views does not raise an exception.

        Validates: rapid clicking / rapid navigation resilience.
        """
        app = gui_app_with_data

        # Cycle through views several times in quick succession
        for _ in range(3):
            app.show_habits_view()
            app.window.update_idletasks()

            app.show_logs_view()
            app.window.update_idletasks()

            app.show_stats_view()
            app.window.update_idletasks()

        # If we get here without an exception, the test passes
        assert app.window.winfo_exists()

    def test_corrupted_data_graceful_handling(self, gui_app, gui_patch_paths):
        """When the habits file contains invalid JSON, the GUI handles the
        error gracefully without crashing.

        Validates: app behavior with corrupted data files.
        """
        app = gui_app

        # Write corrupt JSON to the habits file
        habits_file = gui_patch_paths["habits_file"]
        with open(habits_file, "w") as f:
            f.write("{{{CORRUPT DATA///")

        # Attempt to load — the load callback is a MagicMock, so simulate
        # what would happen if the real loader raised an exception
        app._load_habits.side_effect = json.JSONDecodeError(
            "Expecting value", "{{{CORRUPT DATA///", 0
        )

        # Call _sync_load_data (the synchronous version used in tests)
        # It should catch the exception and print an error, not crash
        from tests.gui.conftest import _sync_load_data
        _sync_load_data(app)
        app.window.update_idletasks()

        # The window should still be alive
        assert app.window.winfo_exists(), "Window crashed after corrupted data load"
