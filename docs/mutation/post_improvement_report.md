# Mutation Testing — Post-Improvement Report

**Date:** April 15, 2026
**Tool:** mutmut 2.5.1
**Target:** 6 non-GUI modules in `habit_engine/`

## Executive Summary

Following an intensive targeted testing phase based on baseline results, the mutation score was significantly improved from **47.9%** to **76.1%**.

### Before and After Comparison

| Metric | Baseline | Post-Improvement | Delta |
|--------|----------|-----------------|-------|
| **Total Mutants Generated** | 684 | 684 | 0 |
| **Killed (Detected by Tests)** | 327 | 521 | +194 |
| **Survived / Timed Out** | 357 | 163 | -194 |
| **Mutation Score** | **47.9%** | **76.1%** | **+28.2%** |

## Key module achievements
- **`habit_setup.py`**: Achieved near 100% kill rate of logical mutants using CLI/`builtins.input` simulation mocks.
- **`__init__.py`**: Achieved 100% kill rate (all 28 mutants killed) by asserting expected strings.
- **`habit_logic.py`**: Killed all remaining reachable execution paths. The 2 remaining mutants were proved out mathematically as Equivalent Mutants (e.g., date evaluation loop `continue` vs `break` on an immediately failing date condition).
- **`habit_io.py`**: Killed file handling and boolean attribute defaults for PyInstaller environment path logic.
- **`habit_display.py`**: Killed almost all logical branches down to just cosmetic mutations (e.g. `< 0` to `< 1`).
- **`habit_visualization.py`**: Left mostly as-is due to the 'diminishing returns' bounds of testing aesthetic formatting options (e.g. `figsize`, titles, exact color codes, print/spinner animations). These account for the vast majority of the remaining 163 surviving mutants.

## Equivalent Mutants and Plateau Justification
As defined in the project objectives, pushing the mutation score upwards hit a practical plateau primarily in `habit_visualization.py` and some display printing strings.
Mutants that swap cosmetic strings (e.g., `line_label = "Completed"` to `XXCompletedXX`) do not alter the behavioral logic of the data pipeline or application logic. While they can be killed by strict output assertion (which was done heavily for CLI modules), doing so for Matplotlib plotting attributes is discouraged as it overfits tests to visual specs rather than correctness.
