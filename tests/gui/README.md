# GUI Test Infrastructure

## Chosen Approach

**Raw tkinter / CustomTkinter introspection** (no mainloop).

### Alternatives Evaluated

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| **pytest-tk** | Purpose-built for Tk testing | Unmaintained; no CustomTkinter support | Rejected |
| **pyautogui** | Simulates real clicks/keystrokes | Requires a visible display; fragile coordinates; slow | Rejected |
| **Raw introspection** | No extra dependencies; fast; works headless; full widget-tree access | Must manage Tk lifecycle manually | **Selected** |

### How It Works

1. The real `HabitTrackerGUI` class is instantiated with either **stub callbacks** (`MagicMock`) or the **real I/O functions** (pointed at a temp directory).
2. `mainloop()` is **never called**. Instead, `update_idletasks()` pumps geometry/layout events as needed.
3. The production `_load_data()` method (which uses a background thread + `window.after()`) is replaced with a **synchronous version** so that data loading works without an active event loop.
4. On teardown, all pending `after` callbacks are cancelled and the root window is destroyed.

## Fixtures (defined in `conftest.py`)

| Fixture | Scope | Description |
|---|---|---|
| `gui_data_dir` | function | Isolated `tmp_path/data` + `data/plots` directory |
| `gui_patch_paths` | function | Redirects all `habit_io` and `gui` module path constants to the temp dir |
| `gui_seeded_paths` | function | `gui_patch_paths` + pre-written habits/logs/streaks JSON |
| `stub_callbacks` | function | 7 `MagicMock` callables matching `HabitTrackerGUI.__init__` signature |
| `io_callbacks` | function | 7 real I/O functions (paths already redirected) |
| `gui_app` | function | Fully constructed `HabitTrackerGUI` with stubs; yields and destroys |
| `gui_app_with_data` | function | Same as `gui_app` but wired to real I/O with seeded data |

### Helper Utilities

- **`pump_events(app, rounds=5)`** — Pump the Tk event loop for `rounds` iterations (useful when `after` callbacks must fire before assertions).

## Running the Tests

```bash
# Run just the GUI tests
python -m pytest tests/gui/ -v

# Run with the full suite
python -m pytest -v
```

### Headless CI (Linux)

On headless CI servers, wrap with `xvfb-run`:

```bash
xvfb-run python -m pytest tests/gui/ -v
```

Or install and start Xvfb manually:

```bash
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
python -m pytest tests/gui/ -v
```

macOS and Windows CI runners have a display by default and need no special setup.

## Limitations

1. **No mainloop** — Tests cannot verify behaviour that depends on the Tk event loop running continuously (e.g., real-time autosave timers, daily reminder popups). These should be tested by calling the underlying methods directly.
2. **No real user interaction** — Mouse clicks and keyboard input are not simulated. Button commands can be invoked programmatically via `button.invoke()` or `button.cget("command")()`.
3. **CustomTkinter quirks** — Some CTk methods behave differently from standard tkinter (e.g., `minsize()` is setter-only on `CTk`; use `wm_minsize()` to read). Test code must account for these differences.
4. **Background threads** — The production `_load_data` uses a background thread. Tests replace it with a synchronous version. Any future async-loading methods will need similar treatment.
5. **Icon loading** — `set_window_icon` may print a warning on macOS test runs because CTk's `_set_window_icon` is not always available. This is harmless and does not affect test outcomes.
