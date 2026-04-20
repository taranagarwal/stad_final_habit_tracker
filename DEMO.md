# DEMO

Command reference for the live presentation. One section per step, matching the speaker notes.

## Preamble

Fresh clone — create the venv and install deps:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Already set up — just activate the project venv before running anything (do NOT stay in `(base)`, otherwise `pytest` / `mutmut` will not be found):

```bash
source .venv/bin/activate
```

Sanity check (should print the `.venv` path and a mutmut version):

```bash
which python && python -c "import mutmut; print(mutmut.__version__)"
```

---

## Step 1 — App walkthrough (Taran)

Launch the GUI (default), then show the CLI mode.

```bash
python main.py
```

```bash
python main.py --cli
```

---

## Step 2 — Blackbox run (Taran)

Expected: **135 passed**. Key files: `test_habit_logic_bb.py` (57), `test_habit_io_bb.py` (36), `test_plot_combinatorial.py` (26).

```bash
pytest tests/blackbox/ -v
```

Optional per-file drilldown:

```bash
pytest tests/blackbox/test_habit_logic_bb.py -v
pytest tests/blackbox/test_habit_io_bb.py -v
pytest tests/blackbox/test_plot_combinatorial.py -v
```

---

## Step 3 — Branch coverage (Taran)

```bash
pytest --cov=habit_engine --cov-branch -v
```

Optional HTML report:

```bash
pytest --cov=habit_engine --cov-branch --cov-report=html && open htmlcov/index.html
```

---

## Step 4 — Validation suite (Justin)

```bash
pytest tests/integration/test_proposal_validation.py -v
```

This file is organized by proposal requirement rather than by testing technique, so each promise we made has one test class that proves it. We verify that `--view-logs` is truly read-only by SHA-256 hashing every JSON file before and after, that `--reset` wipes the `plots/` directory along with the data, and that `--lock` and `--dev` actually flip the filesystem permission bits. We also confirm a missed day resets a streak to zero instead of decrementing, that habit setup rejects counts below two, and that our charts plot the raw data accurately — `True` maps to `1`, `False` to `0`, and out-of-range dates are filtered out.

---

## Step 5 — Mutation report (Justin)

Do NOT run `mutmut run` live — it takes ~4 minutes. Show the post-improvement report instead.

```bash
cat docs/mutation/post_improvement_report.md
```

For reference only — the commands that produced the report (do not run during the demo):

```bash
mutmut run
mutmut results
```

Troubleshooting — `zsh: command not found: mutmut`

This means you are in the `(base)` conda env (or any env without the project deps). Activate the project venv first, or invoke mutmut via the current Python:

```bash
source .venv/bin/activate
mutmut run
```

Or, without activating:

```bash
python -m pip install "mutmut>=2.5,<3.0"
python -m mutmut run
```

---

## Step 6 — GUI introspection (Justin)

```bash
pytest tests/gui/ -v
```

Headless-Linux variant:

```bash
xvfb-run -a pytest tests/gui/ -v
```
