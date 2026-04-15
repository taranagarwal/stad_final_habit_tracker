# Mutation Testing — Baseline Report

**Date:** April 15, 2026  
**Tool:** mutmut 2.5.1  
**Test Suite:** 242 tests (pytest)  
**Target:** 6 non-GUI modules in `habit_engine/` (excluding `gui.py`)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Mutants Generated** | 684 |
| **Killed (detected by tests)** | 327 |
| **Survived (undetected)** | 355 |
| **Timed Out** | 2 |
| **Baseline Mutation Score** | **47.9%** |

---

## Per-Module Breakdown

| Module | Killed | Survived | Timeout | Total | Score |
|--------|--------|----------|---------|-------|-------|
| `__init__.py` | 6 | 28 | 0 | 34 | 17.6% |
| `habit_display.py` | 27 | 56 | 0 | 83 | 32.5% |
| `habit_io.py` | 93 | 68 | 0 | 161 | 57.8% |
| `habit_logic.py` | 102 | 30 | 1 | 133 | 77.3% |
| `habit_setup.py` | 17 | 21 | 1 | 39 | 44.7% |
| `habit_visualization.py` | 82 | 152 | 0 | 234 | 35.0% |
| **TOTAL** | **327** | **355** | **2** | **684** | **47.9%** |

---

## Analysis

### Strongest Module: `habit_logic.py` (77.3%)
This module has the highest mutation score, reflecting the strong blackbox + whitebox test coverage. 30 mutants still survive, mostly in validation helper functions and streak logic edge cases.

### Weakest Module: `__init__.py` (17.6%)
28 of 34 mutants survive. This is expected — `__init__.py` contains package metadata (version strings, feature lists, credits) which are mostly string constants. Many of these are **equivalent mutants** or low-value targets.

### Largest Opportunity: `habit_visualization.py` (35.0%, 152 survivors)
This module has the most surviving mutants in absolute terms. The visualization logic has many branches for chart styles, date ranges, and streak annotations that existing tests don't fully exercise.

### `habit_display.py` (32.5%, 56 survivors)
Display functions are mostly `print()` formatting. Many survivors involve string formatting changes that don't affect return values — they are cosmetic and may be equivalent mutants.

### `habit_io.py` (57.8%, 68 survivors)
I/O operations have moderate coverage but survivors exist in backup/restore logic, file permission handling, and edge cases in `save_with_backup` / `try_load_json`.

### `habit_setup.py` (44.7%, 21 survivors)
Interactive setup function relies on `input()` which makes it harder to test. Many survivors are in the user interaction loop.

---

## Configuration

```ini
# setup.cfg
[mutmut]
paths_to_mutate=habit_engine/habit_logic.py,habit_engine/habit_io.py,habit_engine/habit_setup.py,habit_engine/habit_display.py,habit_engine/habit_visualization.py,habit_engine/__init__.py
tests_dir=tests/
runner=python -m pytest -x --tb=short -q
```

---

## Next Steps (Issue #2)

1. Categorize the 355 survivors by mutation type
2. Identify and mark equivalent mutants (especially in `__init__.py` and `habit_display.py`)
3. Write targeted tests to kill survivors, prioritizing:
   - `habit_logic.py` (30 survivors — closest to 100%)
   - `habit_io.py` (68 survivors — high-value module)
   - `habit_visualization.py` (152 survivors — largest count)
4. Re-run mutmut after each batch and track score improvement
