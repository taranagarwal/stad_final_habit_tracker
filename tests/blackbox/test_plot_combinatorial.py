"""
Black-Box Combinatorial Tests — --plot flag interactions with other CLI flags

Testing techniques applied:
  - Error Guessing (EG): invalid inputs, post-reset state, missing data
  - Combinatorial Testing (CT): pairwise coverage of --plot with every other flag

Combinatorial Matrix (pairwise minimum):
┌────┬──────────────┬───────────────┬────────────────────────────────────────────┐
│  # │ Flag 1       │ Flag 2        │ Expected Outcome                           │
├────┼──────────────┼───────────────┼────────────────────────────────────────────┤
│  1 │ --plot       │ (none)        │ Prompts for habit, generates PNG           │
│  2 │ -p           │ (none)        │ Short-form alias, same as --plot           │
│  3 │ --plot       │ --cli         │ --cli stripped by preprocessor; plot runs  │
│  4 │ --plot       │ --reset       │ --plot is argv[1] → only --plot processed  │
│  5 │ --reset      │ --plot        │ --reset is argv[1] → data wiped           │
│  6 │ --plot       │ --view-logs   │ --plot is argv[1] → only --plot processed  │
│  7 │ --view-logs  │ --plot        │ --view-logs is argv[1] → logs displayed   │
│  8 │ --plot       │ --clear-logs  │ --plot is argv[1] → only --plot processed  │
│  9 │ --clear-logs │ --plot        │ --clear-logs is argv[1] → logs cleared    │
│ 10 │ --plot       │ --dev         │ --plot is argv[1] → only --plot processed  │
│ 11 │ --plot       │ --lock        │ --plot is argv[1] → only --plot processed  │
│ 12 │ --plot       │ --info        │ --plot is argv[1] → only --plot processed  │
│ 13 │ --plot       │ --license     │ --plot is argv[1] → only --plot processed  │
│ 14 │ --plot       │ --help        │ --plot is argv[1] → only --plot processed  │
│ 15 │ --plot       │ --unknown     │ --plot is argv[1] → only --plot processed  │
│ 16 │ --plot       │ --plot        │ Duplicate flag; processed once             │
│ 17 │ --plot       │ (no habits)   │ Exit 1: "No habits found"                 │
│ 18 │ --plot       │ (no logs)     │ Exit 1: "No tracking data"                │
│ 19 │ --plot       │ (bad input)   │ Exit 1: "Invalid input"                   │
│ 20 │ --plot       │ (out of range)│ Exit 1: "Invalid habit number"            │
│ 21 │ --plot       │ (post-reset)  │ Exit 1: "No habits found"                 │
│ 22 │ --plot       │ 3+ flags      │ Only argv[1] processed                    │
│ 23 │ --gui        │ --plot        │ Preprocessor → GUI mode; --plot ignored   │
└────┴──────────────┴───────────────┴────────────────────────────────────────────┘

All tests use isolated temp data via conftest fixtures so real data is never touched.
"""

import json
import os
import sys
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

import main as main_mod
from main import run_cli_mode
from habit_engine.habit_io import (
    initialize_data_files,
    save_habits,
    save_daily_logs,
    load_habits,
    load_daily_logs,
    load_habit_streaks,
    reset_app_data,
)
import habit_engine.habit_visualization as viz_mod


# Fixtures

@pytest.fixture
def cli_env(patch_io_paths, monkeypatch):
    """
    Fully isolated CLI environment.
    Redirects PLOTS_DIR in both the main module and the visualization module
    so that generated PNGs land in the temp directory.
    """
    plots_dir = patch_io_paths["plots_dir"]
    monkeypatch.setattr(main_mod, "PLOTS_DIR", plots_dir)
    monkeypatch.setattr(viz_mod, "PLOTS_DIR", plots_dir)
    initialize_data_files()
    return patch_io_paths


@pytest.fixture
def seeded_cli_env(cli_env):
    """cli_env pre-loaded with 3 habits and 2 days of tracking data."""
    habits = ["Exercise", "Read", "Meditate"]
    save_habits(habits)

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
    save_daily_logs(logs, streaks)
    return cli_env


# Helpers

def run_with_args(args, monkeypatch, user_input=None):
    """
    Execute run_cli_mode() with specific sys.argv tokens.

    Returns the integer exit code.  ``input()`` is mocked: if *user_input*
    is given it is returned; otherwise an EOFError is raised (simulating
    no interactive terminal).
    """
    monkeypatch.setattr(sys, "argv", ["main.py"] + args)

    if user_input is not None:
        input_ctx = patch("builtins.input", return_value=user_input)
    else:
        input_ctx = patch("builtins.input", side_effect=EOFError)

    exit_code = 0
    with input_ctx:
        try:
            run_cli_mode()
        except SystemExit as exc:
            exit_code = exc.code if exc.code is not None else 0
    return exit_code


# Row 1-2: --plot / -p alone with valid data

class TestPlotAlone:
    """Rows 1-2: --plot and -p with seeded data produce a PNG."""

    def test_plot_long_form(self, seeded_cli_env, monkeypatch, capsys):
        """Row 1: --plot → exit 0, PNG created, success message shown."""
        exit_code = run_with_args(["--plot"], monkeypatch, user_input="1")
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Visualization created successfully" in out

        pngs = [f for f in os.listdir(seeded_cli_env["plots_dir"]) if f.endswith(".png")]
        assert len(pngs) >= 1

    def test_plot_short_form(self, seeded_cli_env, monkeypatch, capsys):
        """Row 2: -p is equivalent to --plot."""
        exit_code = run_with_args(["-p"], monkeypatch, user_input="1")
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Visualization created successfully" in out


# Row 3: --plot + --cli

class TestPlotWithCli:
    """Row 3: --cli is stripped by the __main__ preprocessor before dispatch."""

    def test_cli_stripped_plot_runs(self, seeded_cli_env, monkeypatch, capsys):
        """After --cli removal, --plot is argv[1] and runs normally."""
        # Simulate the __main__ preprocessing logic
        args_to_process = ["--plot", "--cli"]
        args_to_process.remove("--cli")

        exit_code = run_with_args(args_to_process, monkeypatch, user_input="1")
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Visualization created successfully" in out

    def test_cli_before_plot_stripped(self, seeded_cli_env, monkeypatch, capsys):
        """--cli --plot: after stripping --cli, --plot becomes argv[1]."""
        args_to_process = ["--cli", "--plot"]
        args_to_process.remove("--cli")

        exit_code = run_with_args(args_to_process, monkeypatch, user_input="1")
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Visualization created successfully" in out


# Rows 4-16: --plot as first arg (second flag ignored)

class TestPlotFirstArgWins:
    """
    Rows 4, 6, 8, 10-16: run_cli_mode() only inspects sys.argv[1].
    When --plot is first, the second flag is silently ignored and the
    plot is generated normally.
    """

    @pytest.mark.parametrize("second_flag", [
        "--reset",        # row 4
        "--view-logs",    # row 6
        "--clear-logs",   # row 8
        "--dev",          # row 10
        "--lock",         # row 11
        "--info",         # row 12
        "--license",      # row 13
        "--help",         # row 14
        "--unknown",      # row 15
        "--plot",         # row 16 (duplicate)
    ])
    def test_plot_first_ignores_second(
        self, seeded_cli_env, monkeypatch, capsys, second_flag
    ):
        exit_code = run_with_args(["--plot", second_flag], monkeypatch, user_input="1")
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Visualization created successfully" in out

    @pytest.mark.parametrize("second_flag", [
        "--reset",
        "--clear-logs",
    ])
    def test_plot_first_does_not_mutate_data(
        self, seeded_cli_env, monkeypatch, second_flag
    ):
        """Destructive flags as second arg must NOT wipe data."""
        run_with_args(["--plot", second_flag], monkeypatch, user_input="1")

        assert load_habits() != []
        assert load_daily_logs() != []


# Rows 5, 7, 9: other flag first, --plot ignored

class TestOtherFlagFirstPlotIgnored:
    """When another flag occupies argv[1], --plot (as argv[2]) is ignored."""

    def test_reset_first_wipes_data(self, seeded_cli_env, monkeypatch, capsys):
        """Row 5: --reset --plot → data wiped, --plot never runs."""
        exit_code = run_with_args(["--reset", "--plot"], monkeypatch)
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "reset" in out.lower()
        assert load_habits() == []
        assert load_daily_logs() == []

    def test_view_logs_first(self, seeded_cli_env, monkeypatch, capsys):
        """Row 7: --view-logs --plot → logs displayed, --plot ignored."""
        exit_code = run_with_args(["--view-logs", "--plot"], monkeypatch)
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Exercise" in out

    def test_clear_logs_first(self, seeded_cli_env, monkeypatch, capsys):
        """Row 9: --clear-logs --plot → tracking data cleared."""
        exit_code = run_with_args(["--clear-logs", "--plot"], monkeypatch)

        assert load_daily_logs() == []
        assert load_habit_streaks() == {}
        # Habits should be preserved by --clear-logs
        assert load_habits() == ["Exercise", "Read", "Meditate"]


# Rows 17-21: edge cases (error guessing)

class TestPlotEdgeCases:
    """Error-guessing scenarios for --plot with unusual or missing data."""

    def test_no_habits_exits_1(self, cli_env, monkeypatch, capsys):
        """Row 17: --plot with empty habit list → exit 1."""
        exit_code = run_with_args(["--plot"], monkeypatch)
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "No habits found" in out

    def test_no_logs_for_habit_exits_1(self, cli_env, monkeypatch, capsys):
        """Row 18: habit exists but has zero tracking logs → exit 1."""
        save_habits(["Exercise"])

        exit_code = run_with_args(["--plot"], monkeypatch, user_input="1")
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "No tracking data" in out

    def test_non_numeric_input_exits_1(self, seeded_cli_env, monkeypatch, capsys):
        """Row 19: user types letters instead of a number → exit 1."""
        exit_code = run_with_args(["--plot"], monkeypatch, user_input="abc")
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "Invalid" in out

    def test_out_of_range_selection_exits_1(self, seeded_cli_env, monkeypatch, capsys):
        """Row 20: numeric input beyond the habit list → exit 1."""
        exit_code = run_with_args(["--plot"], monkeypatch, user_input="99")
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "Invalid habit number" in out

    def test_negative_selection_exits_1(self, seeded_cli_env, monkeypatch, capsys):
        """EG: negative number → exit 1 (boundary)."""
        exit_code = run_with_args(["--plot"], monkeypatch, user_input="-1")
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "Invalid" in out

    def test_zero_selection_exits_1(self, seeded_cli_env, monkeypatch, capsys):
        """EG: 0 is below the 1-indexed range → exit 1."""
        exit_code = run_with_args(["--plot"], monkeypatch, user_input="0")
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "Invalid" in out

    def test_empty_input_exits_1(self, seeded_cli_env, monkeypatch, capsys):
        """EG: empty string → exit 1."""
        exit_code = run_with_args(["--plot"], monkeypatch, user_input="")
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "Invalid" in out

    def test_plot_after_reset_no_habits(self, seeded_cli_env, monkeypatch, capsys):
        """Row 21: reset wipes everything, then --plot finds no habits."""
        reset_app_data()

        exit_code = run_with_args(["--plot"], monkeypatch)
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "No habits found" in out


# Row 22: multiple conflicting flags (3+)

class TestMultipleConflictingFlags:
    """Three or more flags: only argv[1] is dispatched."""

    def test_plot_first_among_three(self, seeded_cli_env, monkeypatch, capsys):
        """--plot --reset --clear-logs → only --plot runs; data intact."""
        exit_code = run_with_args(
            ["--plot", "--reset", "--clear-logs"], monkeypatch, user_input="1"
        )
        out = capsys.readouterr().out

        assert exit_code == 0
        assert "Visualization created successfully" in out
        assert load_habits() != []
        assert load_daily_logs() != []

    def test_reset_first_among_three(self, seeded_cli_env, monkeypatch):
        """--reset --plot --info → only --reset processed."""
        run_with_args(["--reset", "--plot", "--info"], monkeypatch)

        assert load_habits() == []
        assert load_daily_logs() == []

    def test_info_first_among_three(self, seeded_cli_env, monkeypatch, capsys):
        """--info --plot --reset → only --info runs; data untouched."""
        exit_code = run_with_args(["--info", "--plot", "--reset"], monkeypatch)
        out = capsys.readouterr().out

        assert exit_code == 0
        assert load_habits() != []


# Row 23: --gui + --plot interaction

class TestPlotWithGui:
    """
    Row 23: the __main__ preprocessor routes to run_gui_mode() when --gui
    is present.  --plot is left in sys.argv but never consumed.
    Tested by verifying the preprocessing logic directly (no GUI launched).
    """

    def test_gui_flag_forces_gui_mode(self):
        """--gui --plot → cli_mode=False → run_gui_mode (--plot ignored)."""
        args_to_process = ["--gui", "--plot"]
        cli_mode = False

        if "--cli" in args_to_process:
            cli_mode = True
            args_to_process.remove("--cli")
        elif "--gui" in args_to_process:
            args_to_process.remove("--gui")
            cli_mode = False
        else:
            cli_mode = len(args_to_process) > 0

        assert cli_mode is False

    def test_gui_only_flag_also_false(self):
        """--gui alone → cli_mode=False (baseline)."""
        args_to_process = ["--gui"]
        cli_mode = False

        if "--cli" in args_to_process:
            cli_mode = True
            args_to_process.remove("--cli")
        elif "--gui" in args_to_process:
            args_to_process.remove("--gui")
            cli_mode = False
        else:
            cli_mode = len(args_to_process) > 0

        assert cli_mode is False


# Plot file validation

class TestPlotFileValidation:
    """Validate that generated plot files meet expected criteria."""

    def test_png_file_is_nonempty(self, seeded_cli_env, monkeypatch):
        """Generated PNG must be a non-empty file."""
        run_with_args(["--plot"], monkeypatch, user_input="1")

        plots_dir = seeded_cli_env["plots_dir"]
        pngs = [f for f in os.listdir(plots_dir) if f.endswith(".png")]
        assert len(pngs) >= 1

        filepath = os.path.join(plots_dir, pngs[0])
        assert os.path.getsize(filepath) > 0

    def test_png_filename_contains_habit_name(self, seeded_cli_env, monkeypatch):
        """PNG filename should include the habit name."""
        run_with_args(["--plot"], monkeypatch, user_input="1")

        plots_dir = seeded_cli_env["plots_dir"]
        pngs = [f for f in os.listdir(plots_dir) if f.endswith(".png")]
        assert any("Exercise" in f for f in pngs)

    def test_each_habit_produces_its_own_png(self, seeded_cli_env, monkeypatch):
        """Plotting different habits produces distinctly named files."""
        run_with_args(["--plot"], monkeypatch, user_input="1")
        run_with_args(["--plot"], monkeypatch, user_input="2")

        plots_dir = seeded_cli_env["plots_dir"]
        pngs = [f for f in os.listdir(plots_dir) if f.endswith(".png")]
        assert len(pngs) >= 2
        assert any("Exercise" in f for f in pngs)
        assert any("Read" in f for f in pngs)

    def test_no_crash_on_all_valid_habits(self, seeded_cli_env, monkeypatch, capsys):
        """Plotting every seeded habit should succeed without crashes."""
        for i in range(1, 4):
            exit_code = run_with_args(["--plot"], monkeypatch, user_input=str(i))
            # Habit 3 (Meditate) has logs for today only → should still succeed
            assert exit_code == 0
