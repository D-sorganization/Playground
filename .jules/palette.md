## 2025-05-18 - Calculator Button Accessibility
**Learning:** The calculator app relies heavily on `data-token` attributes and abbreviated text (e.g., "expₘ", "SE₃^") for buttons, which are not descriptive for screen readers.
**Action:** Always verify that buttons with technical symbols or abbreviations have descriptive `aria-label` attributes to explain their function (e.g., "Matrix exponential", "SE3 Hat operator").

## 2025-12-13 - Calculator Accessibility Gaps
**Learning:** Core calculator keys (., =, ,) and the result display lacked ARIA attributes, making the app difficult to use with a screen reader despite other buttons having labels.
**Action:** Ensure all interactive elements, even common symbols, have `aria-label`, and use `aria-live` for dynamic result regions.
