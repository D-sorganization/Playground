Title: CRITICAL: Revert commit ef2d121a46b4f771fc667363015e87c004dea50c (Massive Unrelated Changes)
Labels: bug, critical, revert

### Description
The recent commit `ef2d121a46b4f771fc667363015e87c004dea50c` titled "fix: improve DbC error messages in asteroid_jumper physics (#265)" contains severe scope creep and represents a damaging change.

While the commit message implies a targeted fix to `asteroid_jumper` error messages, the actual commit:
- Modifies 266 files
- Adds over 36,000 lines of code
- Modifies 246 files completely unrelated to the stated scope (including agent workflows, GitHub actions, scripts, and documentation)

This violates coherent plan alignment and basic code review principles. The code introduces 82 TODOs, 44 FIXMEs, 34 type ignores, and multiple potential CI/CD gaming indicators.

### Recommended Action
Immediately revert this commit and create a new, properly scoped PR for the `asteroid_jumper` DbC error messages fix.
