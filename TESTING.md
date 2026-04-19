# Testing & Reproduction Guide


| Category    | Location                          | Approx. count |
| ----------- | --------------------------------- | -------------:|
| Blackbox    | `tests/blackbox/`                 | 135           |
| Whitebox    | `tests/whitebox/`                 | 134           |
| Integration | `tests/integration/`              | 18            |
| Mutation    | `tests/mutation/` (kill scripts) + `mutmut` | 23 + survivor sweep |
| GUI         | `tests/gui/`                      | 45            |
| **Total**   | `tests/`                          | **355**       |

> Counts are accurate as of the final commit on the `main` branch. They may
> grow slightly if mutant-killer tests are added before submission.

---

## 1. Prerequisites

### 1.1 Python

- **Python 3.10 or newer** (CI runs Python 3.12; development is on 3.11).
  Verify with:
  ```bash
  python3 --version
  ```

### 1.2 System packages (Tk / matplotlib backends)

The GUI tests instantiate a real `customtkinter` window, which requires the
system Tk libraries. These are **not** installable via `pip`.

| OS          | Install command                                  |
| ----------- | ------------------------------------------------ |
| Ubuntu / Debian | `sudo apt-get install -y python3-tk xvfb`        |
| Fedora      | `sudo dnf install python3-tkinter xorg-x11-server-Xvfb` |
| macOS (Homebrew Python) | `brew install python-tk`              |
| macOS (system Python) | Already includes Tk — no install needed |
| Windows     | Already included with the official Python installer |

`xvfb` is only needed on **headless Linux** (e.g. CI without a display).

### 1.3 Python packages

All Python dependencies, including the testing tools, are pinned in
`requirements.txt`:

```
matplotlib >= 3.8
colorama   >= 0.4.6
customtkinter >= 5.2
pillow     >= 10.0
darkdetect >= 0.8
pytest     >= 7.0
pytest-cov >= 4.0
mutmut     >= 2.5, < 3.0
```

---

## 2. Step-by-Step Setup

### 2.1 Clone the repository

```bash
git clone https://github.com/HERALDEXX/habit-tracker.git
cd habit-tracker
```

> If the team submitted a fork or zip archive, clone / extract that instead.

### 2.2 Create an isolated virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows PowerShell
```

### 2.3 Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Sanity-check the install

```bash
python -c "import customtkinter, matplotlib, pytest, mutmut; print('ok')"
```

If this prints `ok`, the environment is ready.

---

## 3. Running the Tests

All commands below assume the virtual environment is active and you are in
the repository root.

### 3.1 Run the entire suite

```bash
pytest -v
```

**Expected:** `355 passed` in roughly 10–15 seconds on a modern laptop.

### 3.2 Run a single test category

```bash
pytest tests/blackbox/    -v   # equivalence / boundary / error-guessing / combo
pytest tests/whitebox/    -v   # branch-coverage-driven unit tests
pytest tests/integration/ -v   # end-to-end CLI workflows + proposal validation
pytest tests/mutation/    -v   # bespoke mutant-killer tests (separate from mutmut)
pytest tests/gui/         -v   # tkinter / customtkinter introspection tests
```

### 3.3 GUI tests on a headless Linux box

```bash
xvfb-run -a pytest tests/gui/ -v
```

macOS and Windows have a display by default, so plain `pytest tests/gui/ -v`
works.

### 3.4 Branch coverage report

```bash
pytest --cov=habit_engine --cov-branch -v
```

**Expected coverage (terminal output):**

```
Name                                  Stmts   Miss Branch BrPart  Cover
-----------------------------------------------------------------------
habit_engine/__init__.py                 14      0      0      0   100%
habit_engine/habit_display.py            63      0     16      0   100%
habit_engine/habit_io.py                230      6     62      3    97%
habit_engine/habit_logic.py             117      0     64      0   100%
habit_engine/habit_setup.py              47      0     14      1    98%
habit_engine/habit_visualization.py     138     19     44      4    87%
habit_engine/gui.py                    1638    994    350     43    37%
-----------------------------------------------------------------------
TOTAL                                  2247   1019    550     51    54%
```

The proposal targets **≥85% branch coverage on non-GUI logic modules**;
the five non-GUI modules above sit between **87% and 100%**, well above
the bar. `gui.py` accounts for ~70% of the codebase and is intentionally
exercised by the alternate (introspection) suite, not branch coverage.

### 3.5 HTML coverage report

```bash
pytest --cov=habit_engine --cov-branch --cov-report=html
open htmlcov/index.html        # macOS
xdg-open htmlcov/index.html    # Linux
start htmlcov\index.html       # Windows
```

The HTML report shows per-line and per-branch hit/miss for every module —
useful for inspecting exactly which branches the suite covers.

---

## 4. Mutation Testing (`mutmut`)

Mutmut is configured in `setup.cfg`:

```ini
[mutmut]
paths_to_mutate = habit_engine/habit_logic.py,
                  habit_engine/habit_io.py,
                  habit_engine/habit_setup.py,
                  habit_engine/habit_display.py,
                  habit_engine/habit_visualization.py,
                  habit_engine/__init__.py
tests_dir       = tests/
runner          = python -m pytest -x --tb=short -q
```

### 4.1 Generate mutants and run them through the test suite

```bash
mutmut run
```

> ⏱️ This is slow — expect **15–45 minutes** depending on the machine
> because every mutant runs the full pytest suite. Re-runs are
> incremental and much faster.

### 4.2 Inspect the results

```bash
mutmut results          # summary: killed / survived / suspicious / timeout
mutmut show <ID>        # show the diff for a specific mutant
mutmut show all         # show every surviving mutant
```

### 4.3 Expected outcome

After Issue #8 (Mutation Testing & Coverage Refinement) the **mutation
score is ≥ 90%** with the surviving mutants documented as equivalent
or intentionally-not-killed in `docs/mutation/`. The exact survivor
count is captured in the final report; reproduce it locally with
`mutmut results` after the run completes.

### 4.4 Reset mutation state

```bash
rm -rf .mutmut-cache mutants/
```

Use this if you want a clean baseline before re-running.

---

## 5. End-to-End Reproduction Recipe (TL;DR)

For an evaluator who just wants to verify everything from a clean shell:

```bash
# 1. Clone & enter
git clone https://github.com/HERALDEXX/habit-tracker.git
cd habit-tracker

# 2. System Tk (Linux only)
sudo apt-get install -y python3-tk xvfb     # skip on macOS/Windows

# 3. Virtualenv & deps
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Full functional suite + coverage
pytest --cov=habit_engine --cov-branch -v

# 5. GUI suite (use xvfb-run on headless Linux)
pytest tests/gui/ -v
# xvfb-run -a pytest tests/gui/ -v

# 6. HTML coverage report
pytest --cov=habit_engine --cov-branch --cov-report=html
echo "Open htmlcov/index.html in a browser."

# 7. Mutation testing (slow)
mutmut run
mutmut results
```

---

## 6. Troubleshooting

### `ModuleNotFoundError: No module named '_tkinter'`

The system Tk package is missing. Install it as described in §1.2.

### GUI tests fail with `couldn't connect to display`

You are on a headless Linux machine. Wrap the command:

```bash
xvfb-run -a pytest tests/gui/ -v
```

Or start Xvfb manually:

```bash
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
pytest tests/gui/ -v
```

### `UserWarning: Glyph 128293 (FIRE) missing from font(s) DejaVu Sans`

Harmless — matplotlib can't render the 🔥 emoji used in streak
annotations on systems lacking a colour-emoji font. The plot is still
generated and the test still passes. Install a colour-emoji font
(`fonts-noto-color-emoji` on Debian/Ubuntu) to silence it.

### `customtkinter` raises `_set_window_icon` warnings on macOS

Cosmetic only — does not affect test outcomes. Documented in
`tests/gui/README.md` under *Limitations*.

### Tests pass locally but mutmut reports many surviving mutants

Make sure you ran `mutmut run` from the **repository root** with the
**virtualenv active**, so it picks up `setup.cfg` and the same
`pytest` binary the suite was developed against.

### `pytest: command not found` after activating the venv

You forgot to install the dev dependencies. Run:

```bash
pip install -r requirements.txt
```

### `ImportError` for `darkdetect` or `customtkinter` on import

Older Python (< 3.10) is unsupported. Verify with `python --version`
and recreate the virtualenv with a newer interpreter.

---

## 7. Pointers to Other Test Documentation

- `tests/gui/README.md` — design rationale and fixtures for the
  `customtkinter` introspection suite (alternate testing strategy).
- `docs/mutation/` — mutation-testing baseline, surviving mutants, and
  equivalent-mutant analysis (added in Issue #8).
- `tests/integration/test_proposal_validation.py` — single-source
  traceability map between the proposal's Validation Strategy items
  and their corresponding tests (added in Issue #6).
