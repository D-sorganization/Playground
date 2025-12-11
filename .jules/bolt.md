## 2025-12-11 - Physics Loop Optimization
**Learning:** Heavy use of static utility methods inside tight loops (like `OrbitalMechanics.radius_at_true_anomaly`) can hide redundant calculations (trig functions, constant re-derivations). Inlining and algebraic simplification (e.g., using half-angle iteration to derive sin/cos without extra calls) yielded ~36% speedup.
**Action:** When profiling physics loops, identify redundant trig calls across multiple method invocations and hoist/inline logic to reuse intermediate values.
