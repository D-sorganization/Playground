## 2025-12-11 - Physics Loop Optimization
**Learning:** Heavy use of static utility methods inside tight loops (like `OrbitalMechanics.radius_at_true_anomaly`) can hide redundant calculations (trig functions, constant re-derivations). Inlining and algebraic simplification (e.g., using half-angle iteration to derive sin/cos without extra calls) yielded ~36% speedup.
**Action:** When profiling physics loops, identify redundant trig calls across multiple method invocations and hoist/inline logic to reuse intermediate values.

## 2025-05-23 - SymPy Parsing Overhead
**Learning:** SymPy's `parse_expr` is expensive not just because of parsing, but because of repeated dictionary creation for `local_dict` and `global_dict`. Even small dictionaries (~10 items) add up when called thousands of times.
**Action:** Cache static dictionaries and transformation tuples passed to `parse_expr` to avoid reconstruction overhead.
